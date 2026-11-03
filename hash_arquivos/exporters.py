"""Relatórios locais: PDF, BIFF8 (.xls) e Word 97 (.doc via LibreOffice)."""
from collections import Counter
from pathlib import Path
import html
import os
import shutil
import subprocess
import sys
import tempfile

HEADERS = ['Nome', 'Caminho', 'Tamanho (bytes)', 'Algoritmo', 'Hash completo', 'Blocos', 'Status', 'Observação']
BLOCK_HEADERS = ['Arquivo', 'Número', 'Posição inicial (bytes)', 'Tamanho (bytes)', 'Hash do bloco']

def rows(results):
    return [[r.name, r.path, str(r.size), r.algorithm, r.digest, str(len(r.blocks)), r.status, r.error] for r in results]

def block_rows(results):
    return [[r.path, str(b.number), str(b.offset), str(b.size), b.digest] for r in results for b in r.blocks]

def summary(results):
    counts = ', '.join(f'{k}: {v}' for k, v in sorted(Counter(r.status for r in results).items()))
    return f'Arquivos: {len(results)} | Bytes declarados: {sum(r.size for r in results)} | {counts}'

def converter():
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).parent.parent))
    candidates = [root / 'libreoffice/program/soffice.exe', Path(os.environ.get('PROGRAMFILES', 'C:/Program Files')) / 'LibreOffice/program/soffice.exe']
    return next((str(p) for p in candidates if p.is_file()), None) or shutil.which('libreoffice') or shutil.which('soffice')

def export(path, results, include_blocks=False):
    """Escreve temporariamente e substitui o destino somente após sucesso."""
    path = Path(path).absolute()
    if path.suffix.lower() not in ('.pdf', '.xls', '.doc'):
        raise ValueError('Escolha .doc, .pdf ou .xls.')
    with tempfile.TemporaryDirectory(dir=path.parent) as directory:
        target = Path(directory) / ('relatorio' + path.suffix.lower())
        if path.suffix.lower() == '.pdf':
            pdf(target, results, include_blocks)
        elif path.suffix.lower() == '.xls':
            xls(target, results, include_blocks)
        else:
            doc(target, results, include_blocks)
        os.replace(target, path)

def pdf(path, results, details):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    styles = getSampleStyleSheet()
    cell = styles['BodyText'].clone('cell', fontSize=6, leading=8, splitLongWords=True)
    story = [Paragraph('Hash Arquivos', styles['Title']), Paragraph(html.escape(summary(results)), styles['BodyText']), Spacer(1, 12)]
    def table(headers, data, widths):
        # Um bloco/arquivo por linha; hashes e caminhos longos podem quebrar linhas.
        content = [[Paragraph(html.escape(str(v)), cell) for v in row] for row in [headers] + data]
        t = LongTable(content, colWidths=widths, repeatRows=1, splitInRow=1)
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('GRID', (0, 0), (-1, -1), .25, colors.grey)]))
        story.extend([t, Spacer(1, 12)])
    table(HEADERS, rows(results), [65, 130, 50, 45, 180, 35, 55, 210])
    if details:
        story.append(Paragraph('Detalhes dos blocos', styles['Heading2']))
        table(BLOCK_HEADERS, block_rows(results), [230, 40, 80, 70, 350])
    SimpleDocTemplate(str(path), pagesize=landscape(A4), leftMargin=36, rightMargin=36).build(story)

def xls(path, results, details):
    import xlwt
    book = xlwt.Workbook()
    sheet = book.add_sheet('Resumo')
    sheet.write(0, 0, 'Hash Arquivos')
    sheet.write(1, 0, summary(results))
    def sheets(prefix, headers, data):
        # BIFF8 suporta 65.536 linhas; criar novas abas sem truncar blocos.
        sheet = None
        for i, values in enumerate(data):
            row = i % 65535 + 1
            if row == 1:
                sheet = book.add_sheet(f'{prefix} {i // 65535 + 1}')
                for c, value in enumerate(headers):
                    sheet.write(0, c, value)
                    sheet.col(c).width = 6000
            for c, value in enumerate(values):
                # xlwt recebe strings explicitamente: nomes nunca viram fórmulas.
                if len(str(value)) > 32767:
                    raise ValueError('Texto excede o limite de uma célula XLS (32.767 caracteres).')
                sheet.write(row, c, value)
        if sheet is None:
            sheet = book.add_sheet(f'{prefix} 1')
            for c, value in enumerate(headers):
                sheet.write(0, c, value)
    sheets('Arquivos', HEADERS, rows(results))
    if details:
        sheets('Blocos', BLOCK_HEADERS, block_rows(results))
    book.save(str(path))

def doc(path, results, details):
    executable = converter()
    if not executable:
        raise RuntimeError('Conversor LibreOffice não encontrado. Use o pacote Windows completo ou instale LibreOffice para desenvolver.')
    def table(headers, data):
        return '<table border="1">' + ''.join('<tr>' + ''.join('<td>' + html.escape(str(v)) + '</td>' for v in row) + '</tr>' for row in [headers] + data) + '</table>'
    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        source = directory / 'relatorio.html'
        source.write_text('<html><head><meta charset="utf-8"></head><body><h1>Hash Arquivos</h1><p>' + html.escape(summary(results)) + '</p>' + table(HEADERS, rows(results)) + (('<h2>Detalhes dos blocos</h2>' + table(BLOCK_HEADERS, block_rows(results))) if details else '') + '</body></html>', encoding='utf-8')
        run = subprocess.run([executable, '-env:UserInstallation=' + (directory / 'profile').as_uri(), '--headless', '--convert-to', 'doc:MS Word 97', '--outdir', str(directory), str(source)], capture_output=True, timeout=300, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        output = directory / 'relatorio.doc'
        if run.returncode or not output.exists() or output.read_bytes()[:8] != bytes.fromhex('D0CF11E0A1B11AE1'):
            raise RuntimeError('Falha na conversão Word 97: ' + run.stderr.decode(errors='replace'))
        shutil.copyfile(output, path)
