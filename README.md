# Hash Arquivos

Aplicativo gráfico em português para Windows x64, com processamento e exportação inteiramente locais. Não envia arquivos ou resultados para a internet. O pacote distribuído inclui Python e o conversor LibreOffice: o operador não precisa instalar Python, Excel, Word ou LibreOffice.

## Uso

1. Baixe o artefato **HashArquivos-Windows-x64** do GitHub Actions, extraia **todo** o ZIP em uma pasta e abra `HashArquivos.exe`. Preserve a pasta `_internal` junto ao executável. Não execute diretamente dentro do ZIP.
2. Clique em **Selecionar pasta**. Marque **Incluir subpastas** e clique em **Atualizar lista** quando necessário. Links simbólicos não são seguidos.
3. A lista mostra todos os arquivos encontrados. Até 100 são selecionados automaticamente; acima de 100, nenhum é selecionado automaticamente. Use Ctrl/Shift para escolher de 1 a 100. O motor também rejeita lotes maiores que 100; não há truncamento silencioso.
4. Escolha SHA-1, SHA-224, SHA-256, SHA-384 ou SHA-512 e o tamanho do bloco em MiB (padrão: 4; máximo: 64). Aceita vírgula decimal. O valor é convertido para bytes inteiros.
5. Clique em **Processar selecionados**. A tela mostra o arquivo atual, bytes lidos, progresso geral e log dos resultados. **Cancelar** interrompe a leitura no próximo limite de bloco e marca os arquivos restantes como cancelados.
6. Consulte a tabela de resultados. Clique duas vezes em uma linha para abrir os hashes independentes dos blocos. Numeração começa em 1; posição inicial começa em 0, em bytes.
7. Em **Exportar relatório**, escolha PDF, DOC ou XLS. A caixa de detalhes controla a inclusão de blocos. Os relatórios contêm resumo, tabela dos arquivos, status e mensagens de erro. A exportação ocorre fora da thread gráfica; aguarde sua conclusão antes de fechar. O cancelamento aplica-se à listagem e ao hashing, não à exportação.

Arquivos vazios recebem o hash do conteúdo vazio e zero blocos. Últimos blocos menores são registrados com seu tamanho real. Uma falha não interrompe os demais arquivos. Hashes parciais são descartados quando o arquivo falha, muda ou é cancelado. Erros de acesso na listagem aparecem no log.

## Decisões técnicas

- Python 3.12 + Tkinter: interface desktop nativa, sem servidor ou navegador. `hash_arquivos/gui.py` contém o frontend; `core.py` contém o motor testável e sem dependências gráficas; `exporters.py` concentra os relatórios.
- Uma thread de trabalho executa listagem, leitura e exportação. A thread principal atualiza os widgets por uma fila; progresso por bloco é agregado para não acumular eventos indefinidamente.
- `hashlib` calcula o hash completo incrementalmente e outro hash independente para cada bloco. O conteúdo dos arquivos é lido em blocos, nunca integralmente. Metadados dos blocos permanecem em memória para consulta e exportação: o consumo cresce com a quantidade de blocos, não só com o tamanho configurado do buffer. Evite blocos muito pequenos em arquivos enormes.
- Alteração é detectada comparando tamanho, timestamps em nanossegundos, dispositivo e inode antes/depois da leitura e verificando novamente o caminho. Isso detecta mudanças usuais e substituições; não oferece snapshot transacional contra alterações que restaurem todos os metadados. Para evidência imutável, processe uma cópia estável/snapshot.
- PDF usa ReportLab; XLS usa BIFF8/OLE real via xlwt, com divisão em abas após 65.535 linhas de dados. Strings são gravadas como texto, incluindo nomes que começam com `=`. DOC é Word 97 binário/OLE, convertido pelo LibreOffice local a partir de HTML temporário escapado. Não são extensões simplesmente renomeadas. Nenhuma integração com serviços de nuvem é utilizada.
- Exportações são gravadas em diretório temporário no destino e substituem o arquivo final apenas após sucesso. O DOC usa perfil temporário isolado do LibreOffice e timeout de 300 segundos.
- SHA-1 é oferecido por compatibilidade; para novas verificações prefira SHA-256 ou superior.

## Desenvolvimento

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python main.py
python -m pytest -v
```

Para testar/exportar DOC no desenvolvimento, instale LibreOffice em `C:\Program Files\LibreOffice` ou disponibilize `soffice`/`libreoffice` no PATH. Em Linux, a distribuição precisa também fornecer Tk e um display para a interface. Sem conversor o teste DOC é pulado, exceto quando `REQUIRE_DOC_TEST=1`, que torna sua ausência uma falha. O teste gráfico é pulado em Linux sem `DISPLAY`.

Os testes cobrem os cinco algoritmos, vetor conhecido SHA-256, arquivo vazio, bloco final incompleto, offsets/tamanhos, limite 100/101, parâmetros inválidos, arquivos ausentes/inacessíveis, continuação após falhas, alteração durante leitura, cancelamento, listagem recursiva, PDF lido por parser independente, XLS reaberto por xlrd (incluindo múltiplas abas), DOC binário convertido novamente para texto e preservação do destino em falhas. O teste gráfico verifica criação da janela e valores iniciais; não substitui avaliação manual de interação.

## Compilação Windows

No Windows x64 com Python 3.12 e LibreOffice instalados:

```powershell
python -m pip install -r requirements-dev.txt
$env:REQUIRE_DOC_TEST = '1'
python -m pytest -v
$lo = 'C:\Program Files\LibreOffice'
python -m PyInstaller --noconfirm --clean --windowed --onedir --name HashArquivos --add-data "${lo};libreoffice" --collect-all reportlab main.py
Copy-Item README.md,THIRD_PARTY.md dist\HashArquivos\
```

O resultado é `dist\HashArquivos\HashArquivos.exe` acompanhado de suas dependências. Distribua **toda a pasta**, preferencialmente em ZIP. O conversor aumenta bastante o tamanho do pacote. Não existe exigência de instalação de Python no computador do operador. O executável não possui assinatura digital; o Windows pode apresentar aviso de editor desconhecido.

## GitHub Actions: gerar e baixar

O workflow `.github/workflows/windows.yml` está configurado para push, pull request e acionamento manual. Ele instala LibreOffice no executor Windows, exige os testes DOC reais, testa a janela Tk, compila com PyInstaller e verifica se o executável permanece aberto. Publica o pacote completo e o relatório JUnit como artefatos.

1. Envie estes arquivos para uma branch do repositório GitHub (push).
2. Abra **Actions → Testar e compilar Windows → Run workflow**, selecione a branch e confirme **Run workflow**. Push/PR também acionam a execução automaticamente.
3. Aguarde a execução verde e abra seu resumo.
4. Em **Artifacts**, baixe **HashArquivos-Windows-x64**. O artefato **resultados-testes-windows** contém o XML de testes. Retenção segue a política do GitHub/repositório.

O workflow não foi acionado nesta implementação. Nenhum executável Windows foi gerado ou testado neste ambiente Linux. A validação real do pacote Windows depende da primeira execução desse workflow. Após baixar, recomenda-se verificar manualmente seleção de pasta, cancelamento e abertura dos três relatórios na máquina Windows de destino.
