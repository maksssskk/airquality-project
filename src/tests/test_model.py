from monitor_powietrza.model import Norma

def test_norma_przekroczona():
    norma = Norma("PM10", 50)
    assert norma.przekroczona(60) is True

def test_norma_nie_przekroczona():
    norma = Norma("PM10", 50)
    assert norma.przekroczona(40) is False

def test_norma_brak_wartosci():
    norma = Norma("PM10", 50)
    assert norma.przekroczona(None) is False