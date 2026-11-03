"""Motor independente da interface; nenhuma operação de rede."""
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
import hashlib
import os

ALGORITHMS = {f'SHA-{n}': f'sha{n}' for n in (1, 224, 256, 384, 512)}
DEFAULT_BLOCK = 4 * 1024 * 1024
MAX_FILES = 100

@dataclass
class Block:
    number: int
    offset: int
    size: int
    digest: str

@dataclass
class Result:
    path: str
    size: int = 0
    algorithm: str = ''
    digest: str = ''
    blocks: list[Block] = field(default_factory=list)
    status: str = 'Pendente'
    error: str = ''

    @property
    def name(self):
        return Path(self.path).name


def scan(folder, recursive=False, cancel=None):
    """Não segue links de diretórios; retorna todos os caminhos e falhas visíveis."""
    paths, errors = [], []
    def visit(directory):
        if cancel and cancel.is_set():
            return
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if cancel and cancel.is_set():
                        return
                    try:
                        if entry.is_file(follow_symlinks=False):
                            paths.append(Path(entry.path))
                        elif recursive and entry.is_dir(follow_symlinks=False):
                            visit(entry.path)
                    except OSError as exc:
                        errors.append(f'{entry.path}: {exc}')
        except OSError as exc:
            errors.append(f'{directory}: {exc}')
    visit(Path(folder))
    return sorted(paths), errors


def signature(stat):
    return stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_dev, stat.st_ino


def process(paths, algorithm='SHA-256', block_size=DEFAULT_BLOCK, cancel=None, progress=None):
    paths = list(paths)
    if len(paths) > MAX_FILES:
        raise ValueError('Selecione no máximo 100 arquivos por processamento.')
    if algorithm not in ALGORITHMS:
        raise ValueError('Algoritmo inválido.')
    if isinstance(block_size, bool) or not isinstance(block_size, int) or not 1 <= block_size <= 64 * 1024 * 1024:
        raise ValueError('O bloco deve ter entre 1 byte e 64 MiB.')
    cancel = cancel or Event()
    progress = progress or (lambda *args: None)
    results = []
    for index, path in enumerate(paths):
        result = Result(str(Path(path).absolute()), algorithm=algorithm)
        results.append(result)
        if cancel.is_set():
            result.status = 'Cancelado'
            continue
        try:
            with open(path, 'rb') as stream:
                before = os.fstat(stream.fileno())
                path_before = os.stat(path)
                if not os.path.samestat(before, path_before):
                    raise OSError('Arquivo substituído ao iniciar a leitura.')
                result.size = before.st_size
                whole = hashlib.new(ALGORITHMS[algorithm])
                offset = 0
                progress(index, len(paths), str(path), 0, result.size)
                while True:
                    if cancel.is_set():
                        result.status = 'Cancelado'
                        break
                    data = stream.read(block_size)
                    if not data:
                        after = os.fstat(stream.fileno())
                        current = os.stat(path)
                        if signature(before) != signature(after) or signature(path_before) != signature(current) or offset != before.st_size:
                            result.status = 'Alterado'
                            result.error = 'Arquivo alterado ou substituído durante a leitura; hashes descartados.'
                        else:
                            result.digest = whole.hexdigest()
                            result.status = 'Concluído'
                        break
                    whole.update(data)
                    result.blocks.append(Block(len(result.blocks) + 1, offset, len(data), hashlib.new(ALGORITHMS[algorithm], data).hexdigest()))
                    offset += len(data)
                    progress(index, len(paths), str(path), offset, result.size)
        except OSError as exc:
            result.status = 'Erro'
            result.error = str(exc)
        if result.status != 'Concluído':
            result.digest = ''
            result.blocks.clear()
    return results
