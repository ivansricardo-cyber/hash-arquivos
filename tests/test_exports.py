import os
import subprocess
from pathlib import Path
import pytest
import xlrd
from pypdf import PdfReader
from hash_arquivos.core import process, Result, Block
from hash_arquivos.exporters import export, converter

@pytest.fixture
def results(tmp_path):
    p = tmp_path / 'ação & arquivo.bin'
    p.write_bytes(b'abcdefghijk')
    return process([p], block_size=4)

@pytest.mark.parametrize('details', [False, True])
def test_pdf(tmp_path, results, details):
    p = tmp_path / 'result.pdf'
    export(p, results, details)
    text = '\n'.join(page.extract_text() for page in PdfReader(p).pages)
    assert 'Hash Arquivos' in text and 'Concluído' in text
    assert results[0].digest in text.replace('\n', '').replace(' ', '')
    assert ('Detalhes dos blocos' in text) == details

@pytest.mark.parametrize('details', [False, True])
def test_xls(tmp_path, results, details):
    p = tmp_path / 'result.xls'
    export(p, results, details)
    assert p.read_bytes()[:8] == bytes.fromhex('D0CF11E0A1B11AE1')
    book = xlrd.open_workbook(p)
    sheet = book.sheet_by_name('Arquivos 1')
    assert sheet.cell_value(1, 4) == results[0].digest
    assert sheet.cell_value(1, 0) == results[0].name
    assert ('Blocos 1' in book.sheet_names()) == details
    if details:
        assert book.sheet_by_name('Blocos 1').cell_value(3, 3) == '3'

def test_xls_pagination(tmp_path):
    r = Result('file', blocks=[Block(i + 1, i, 1, 'hash') for i in range(65536)])
    p = tmp_path / 'many.xls'
    export(p, [r], True)
    book = xlrd.open_workbook(p)
    assert book.sheet_by_name('Blocos 1').nrows == 65536
    assert book.sheet_by_name('Blocos 2').cell_value(1, 1) == '65536'

@pytest.mark.parametrize('details', [False, True])
def test_doc(tmp_path, results, details):
    if not converter():
        if os.environ.get('REQUIRE_DOC_TEST') == '1':
            pytest.fail('LibreOffice obrigatório neste ambiente de validação')
        pytest.skip('LibreOffice indisponível; CI Windows exige este teste')
    p = tmp_path / 'result.doc'
    export(p, results, details)
    assert p.read_bytes()[:8] == bytes.fromhex('D0CF11E0A1B11AE1')
    out = tmp_path / 'roundtrip'
    out.mkdir()
    subprocess.run([converter(), '-env:UserInstallation=' + (tmp_path / 'profile').as_uri(), '--headless', '--convert-to', 'txt:Text', '--outdir', str(out), str(p)], check=True, timeout=120)
    text = (out / 'result.txt').read_text(encoding='utf-8-sig')
    assert results[0].digest in text
    assert ('Detalhes dos blocos' in text) == details

def test_atomic_failure(tmp_path, results, monkeypatch):
    from hash_arquivos import exporters
    p = tmp_path / 'result.doc'
    p.write_bytes(b'original')
    monkeypatch.setattr(exporters, 'converter', lambda: None)
    with pytest.raises(RuntimeError):
        export(p, results)
    assert p.read_bytes() == b'original'

def test_invalid_extension(tmp_path):
    with pytest.raises(ValueError):
        export(tmp_path / 'report.docx', [])
