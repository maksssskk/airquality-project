import datetime
import json
from pathlib import Path

import pytest

from monitor_powietrza.klient_api import (
    JEDNOSTKA,
    parsuj_pomiary,
    parsuj_stacje,
    parsuj_stanowiska,
)
from monitor_powietrza.wyjatki import BladOdpowiedziApi

SCIEZKA_DANE = Path(__file__).parent / "dane"

def wczytaj_json(plik: str) -> dict:
    with open(SCIEZKA_DANE/plik, encoding='utf-8') as f:
        return json.load(f)

def test_stacje():
    stacje = parsuj_stacje(wczytaj_json('stacje.json'))
    assert len(stacje) == 3
    assert stacje[0].id == 12096 
    assert stacje[0].nazwa == 'Lublin, ul. Okopowa' 
    assert stacje[0].miasto == 'Lublin'
    assert stacje[0].stanowiska == []

def test_stanowiska():
    stanowiska = parsuj_stanowiska(wczytaj_json('stanowiska.json'))
    assert len(stanowiska) == 4
    for s in stanowiska:
        assert s.jednostka == JEDNOSTKA
        assert s.parametr in ("NO2", "PM10", "PM2.5")
    pm10 = [s.id for s in stanowiska if s.parametr == "PM10"]
    assert pm10 == [295, 14397]

def test_pomiary():
    pomiary = parsuj_pomiary(wczytaj_json('pomiary.json'), 295)
    for p in pomiary:
        assert p.stanowisko_id == 295
        if p.wartosc is not None:
            assert isinstance(p.wartosc, float)
    assert pomiary[0].czas == datetime.datetime(2026, 11, 18, 12, 0)
    assert pomiary[0].czas > pomiary[-1].czas

def test_pomiary_null():
    pomiary = parsuj_pomiary(wczytaj_json('pomiary.json'), 295)
    assert pomiary[2].wartosc is None

@pytest.mark.parametrize('parser, zle_dane', [
    (parsuj_stacje, {}),
    (parsuj_stanowiska, {}),
    (lambda d: parsuj_pomiary(d, 295), {}),
    (lambda d: parsuj_pomiary(d, 295), {'Lista danych pomiarowych': [{'Wartość': 10.5}]}),
    (lambda d: parsuj_pomiary(d, 295), {"Lista danych pomiarowych": [{"Data": "abc", "Wartość": 10.5}]})
])

def test_pytest_raises(parser, zle_dane):
    with pytest.raises(BladOdpowiedziApi):
        parser(zle_dane)

