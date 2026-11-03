import hashlib
import threading
import builtins
from unittest.mock import patch
import pytest
from hash_arquivos.core import process, scan, ALGORITHMS

@pytest.mark.parametrize('algorithm', ALGORITHMS)
@pytest.mark.parametrize('data', [b'', b'abc', b'abcdefghijk'])
def test_hashes(tmp_path, algorithm, data):
    path = tmp_path / 'ação.bin'
    path.write_bytes(data)
    r = process([path], algorithm, 4)[0]
    assert r.status == 'Concluído'
    assert r.digest == hashlib.new(ALGORITHMS[algorithm], data).hexdigest()
    assert len(r.blocks) == (len(data) + 3) // 4
    for i, b in enumerate(r.blocks):
        part = data[i * 4:(i + 1) * 4]
        assert (b.number, b.offset, b.size) == (i + 1, i * 4, len(part))
        assert b.digest == hashlib.new(ALGORITHMS[algorithm], part).hexdigest()

def test_known_vector(tmp_path):
    p = tmp_path / 'abc'
    p.write_bytes(b'abc')
    assert process([p])[0].digest == 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'

def test_limit(tmp_path):
    p = tmp_path / 'empty'
    p.touch()
    assert len(process([p] * 100)) == 100
    with pytest.raises(ValueError, match='100'):
        process([p] * 101)

@pytest.mark.parametrize('size', [0, -1, 64 * 1024 * 1024 + 1, True, 1.5])
def test_invalid_size(size):
    with pytest.raises(ValueError):
        process([], block_size=size)

def test_error_continues(tmp_path):
    good = tmp_path / 'good'
    good.write_bytes(b'abc')
    results = process([tmp_path / 'missing', tmp_path, good])
    assert [r.status for r in results] == ['Erro', 'Erro', 'Concluído']
    assert results[0].error

def test_permission_denied(tmp_path):
    p = tmp_path / 'good'
    p.write_bytes(b'abc')
    original = builtins.open
    def denied(path, *args, **kwargs):
        if str(path).endswith('denied'):
            raise PermissionError('Acesso negado')
        return original(path, *args, **kwargs)
    with patch('builtins.open', denied):
        results = process([tmp_path / 'denied', p])
    assert [r.status for r in results] == ['Erro', 'Concluído']

def test_changed(tmp_path):
    p = tmp_path / 'file'
    p.write_bytes(b'12345678')
    def progress(i, count, path, read, total):
        if read == 4:
            p.write_bytes(b'changed file')
    r = process([p], block_size=4, progress=progress)[0]
    assert r.status == 'Alterado'
    assert not r.digest and not r.blocks

def test_cancel(tmp_path):
    p = tmp_path / 'file'
    p.write_bytes(b'abcdefgh')
    cancel = threading.Event()
    def progress(*args):
        if args[3]:
            cancel.set()
    results = process([p, p], block_size=4, cancel=cancel, progress=progress)
    assert [r.status for r in results] == ['Cancelado', 'Cancelado']
    assert all(not r.digest and not r.blocks for r in results)

def test_scan(tmp_path):
    (tmp_path / 'a').touch()
    (tmp_path / 'sub').mkdir()
    (tmp_path / 'sub' / 'b').touch()
    assert len(scan(tmp_path)[0]) == 1
    assert len(scan(tmp_path, True)[0]) == 2
    assert scan(tmp_path / 'missing')[1]
