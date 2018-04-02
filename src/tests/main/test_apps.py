
from main import apps

def test_ready():
    import main
    assert apps.MainConfig('main', main).ready() is True
