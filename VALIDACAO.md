# Validação executada

Ambiente: Linux, Python 3.12.14. Execução final:

```text
REQUIRE_DOC_TEST=1 .venv/bin/python -m pytest -q --junitxml=work/test-results.xml
36 passed, 1 skipped in 6.20s
```

Os testes DOC usaram o LibreOffice headless disponível no ambiente, geraram arquivos Word 97 com assinatura OLE e converteram os resultados novamente para texto para conferir hash e inclusão/exclusão de blocos. PDF foi reaberto com pypdf e XLS com xlrd. Foi validada a divisão de 65.536 blocos em duas abas XLS, sem perda.

O teste da janela Tk foi pulado por ausência de display gráfico. `compileall` e `git diff --check` concluíram sem erros. O workflow Windows exige o conversor DOC e inclui teste da janela, empacotamento e verificação de inicialização do executável.

Não foi executado GitHub Actions, não foi gerado `.exe` e não foi feita validação interativa em Windows. O artefato Windows estará disponível após a primeira execução bem-sucedida do workflow, conforme README. A verificação automática de inicialização não substitui testes manuais de seleção de pasta, cancelamento e exportação no Windows de destino.
