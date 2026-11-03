import os
import pytest

@pytest.mark.skipif(os.name != 'nt' and not os.environ.get('DISPLAY'), reason='Requer display gráfico')
def test_window():
    from hash_arquivos.gui import App
    app = App()
    app.withdraw()
    app.update()
    assert app.title() == 'Hash Arquivos'
    assert app.block.get() == '4'
    assert app.algorithm.get() == 'SHA-256'
    app.destroy()
