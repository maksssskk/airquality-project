from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from monitor_powietrza.model import Norma, Pomiar, Stacja, Stanowisko
from monitor_powietrza.wyjatki import BrakDanychPomiarowych


def test_norma_przekroczona():
    norma = Norma("PM10", 50)
    assert norma.przekroczona(60) is True

def test_norma_nie_przekroczona():
    norma = Norma("PM10", 50)
    assert norma.przekroczona(40) is False

def test_norma_brak_wartosci():
    norma = Norma("PM10", 50)
    assert norma.przekroczona(None) is False

def test_stanowisko_dla():
    st = Stanowisko(1, "PM10", "µg/m³")
    s = Stacja(1, 'Stacja 1', 'Lublin', [st])
    wynik = s.stanowisko_dla("PM10") 
    assert wynik == st

def test_brak_parametru():
    st = Stanowisko(1, "PM10", "µg/m³")
    s = Stacja(1, 'Stacja 1', 'Lublin', [st])
    with pytest.raises(BrakDanychPomiarowych):
        s.stanowisko_dla('NO2')

def test_dodaj_stanowisko():
    st = Stanowisko(1, "PM10", "µg/m³")
    s = Stacja(1, "Stacja 1", "Lublin")
    assert s.stanowiska == []
    s.dodaj_stanowisko(st)
    assert st in s.stanowiska

def test_default_factory():
    st = Stanowisko(1, "PM10", "µg/m³")
    s = Stacja(1, 'Stacja 1', 'Lublin')
    s2 = Stacja(1, "Stacja 1", "Lublin")
    s.dodaj_stanowisko(st)
    assert s2.stanowiska == []

def test_pomiar_none():
    p = Pomiar(1, datetime(2026, 11, 17, 14, 0), None)
    assert p.wartosc is None

def test_const_pomiar():
    p = Pomiar(1, datetime(2026, 11, 17, 14, 0), 14.89)
    with pytest.raises(FrozenInstanceError):
        p.wartosc = 5