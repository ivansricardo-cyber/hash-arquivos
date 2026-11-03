# Componentes de terceiros

O pacote Windows incorpora componentes com licenças próprias. Preserve seus avisos e arquivos de licença ao redistribuir:

- Python: PSF License — https://docs.python.org/3/license.html
- Tcl/Tk: licença BSD — https://www.tcl.tk/software/tcltk/license.html
- PyInstaller: GPL com exceção para aplicativos empacotados — https://pyinstaller.org/en/stable/license.html
- ReportLab: BSD — https://www.reportlab.com/opensource/
- Pillow (dependência de ReportLab): HPND — https://python-pillow.org/
- xlwt: BSD — https://pypi.org/project/xlwt/
- LibreOffice e seus componentes: principalmente MPL 2.0 e LGPLv3+; os textos e avisos são incluídos no diretório LibreOffice do pacote — https://www.libreoffice.org/about-us/licenses/

Código-fonte e versões do LibreOffice: https://www.libreoffice.org/download/download-libreoffice/ e https://download.documentfoundation.org/libreoffice/src/

O workflow instala a versão corrente do pacote Chocolatey libreoffice-fresh. Consulte os metadados e avisos presentes no artefato para a versão efetivamente distribuída. O aplicativo usa o conversor como processo separado e não altera seus binários.
