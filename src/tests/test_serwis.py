from datetime import datetime, timedelta

import pytest

from monitor_powietrza.cache import Cache
from monitor_powietrza.model import Pomiar, Stacja, Stanowisko
from monitor_powietrza.serwis import TTL_POMIARY, TTL_STACJE, Serwis
from monitor_powietrza.wyjatki import (
    BladOdpowiedziApi,
    BladSieci,
    BrakDanychPomiarowych,
)


class FalszywyZegar:
    def __init__(self, start: datetime):
        self.teraz = start

    def __call__(self) -> datetime:
        return self.teraz


class FalszywyKlient:
    def __init__(
        self,
        stacje: list[Stacja] | None = None,
        stanowiska: dict[int, list[Stanowisko]] | None = None,
        pomiary: dict[int, list[Pomiar]] | None = None,
        blad: Exception | None = None,
    ) -> None:
        self.stacje = stacje if stacje is not None else []
        self.stanowiska = stanowiska if stanowiska is not None else {}
        self.pomiary = pomiary if pomiary is not None else {}
        self.blad = blad
        self.wywolania: list[str] = []

    def pobierz_stacje(self) -> list[Stacja]:
        self.wywolania.append("stacje")
        if self.blad is not None:
            raise self.blad
        return self.stacje

    def pobierz_stanowiska(self, stacja_id: int) -> list[Stanowisko]:
        self.wywolania.append(f"stanowiska:{stacja_id}")
        if self.blad is not None:
            raise self.blad
        return self.stanowiska.get(stacja_id, [])

    def pobierz_pomiary(self, stanowisko_id: int) -> list[Pomiar]:
        self.wywolania.append(f"pomiary:{stanowisko_id}")
        if self.blad is not None:
            raise self.blad
        return self.pomiary.get(stanowisko_id, [])


@pytest.fixture
def cache(tmp_path):
    c = Cache(f"sqlite:///{tmp_path / 'test.db'}")
    yield c
    c.zamknij()


@pytest.fixture
def zegar():
    return FalszywyZegar(datetime(2026, 11, 18, 10, 0))


@pytest.fixture
def klient():
    return FalszywyKlient(
        [Stacja(1, "Stacja 1", "Lublin"), Stacja(2, "Stacja 2", "Warszawa")]
    )


def test_pusty_cache_api(cache, klient, zegar):
    s1 = Stacja(1, "Stacja 1", "Lublin")
    s2 = Stacja(2, "Stacja 2", "Warszawa")
    serwis = Serwis(cache=cache, klient=klient, zegar=zegar)
    wynik = serwis.stacje()
    assert wynik.dane == [s1, s2]
    assert wynik.nieaktualne is False
    assert klient.wywolania == ["stacje"]


def test_cache_niepyta_api(cache, klient, zegar):
    s1 = Stacja(1, "Stacja 1", "Lublin")
    s2 = Stacja(2, "Stacja 2", "Warszawa")
    serwis1 = Serwis(cache=cache, klient=klient, zegar=zegar)
    serwis2 = Serwis(cache=cache, klient=klient, zegar=zegar)
    res1 = serwis1.stacje()
    res2 = serwis2.stacje()
    assert res1.dane == [s1, s2]
    assert res2.dane == [s1, s2]
    assert res1 == res2
    assert klient.wywolania == ["stacje"]


def test_cache_odswieza(cache, klient, zegar):
    s1 = Stacja(1, "Stacja 1", "Lublin")
    s2 = Stacja(2, "Stacja 2", "Warszawa")
    serwis1 = Serwis(cache=cache, klient=klient, zegar=zegar)
    serwis2 = Serwis(cache=cache, klient=klient, zegar=zegar)
    res1 = serwis1.stacje()
    zegar.teraz += timedelta(hours=25)
    res2 = serwis2.stacje()
    assert res1.dane == [s1, s2]
    assert res2.dane == [s1, s2]
    assert len(klient.wywolania) == 2


def test_ttl_odswieza(cache, klient, zegar):
    s1 = Stacja(1, "Stacja 1", "Lublin")
    s2 = Stacja(2, "Stacja 2", "Warszawa")
    serwis1 = Serwis(cache=cache, klient=klient, zegar=zegar)
    serwis2 = Serwis(cache=cache, klient=klient, zegar=zegar)
    res1 = serwis1.stacje()
    zegar.teraz += TTL_STACJE
    res2 = serwis2.stacje()
    assert res1.dane == [s1, s2]
    assert res2.dane == [s1, s2]
    assert len(klient.wywolania) == 2


def test_blad_zwraca_nieaktualne(cache, klient, zegar):
    s1 = Stacja(1, "Stacja 1", "Lublin")
    s2 = Stacja(2, "Stacja 2", "Warszawa")
    serwis = Serwis(cache=cache, klient=klient, zegar=zegar)
    res = serwis.stacje()
    assert res.dane == [s1, s2]

    zegar.teraz += TTL_STACJE + timedelta(minutes=5)
    klient.blad = BladSieci("brak sieci")
    res2 = serwis.stacje()
    assert res2.nieaktualne is True


def test_bez_cache_wyjatek(cache, klient, zegar):
    serwis = Serwis(cache=cache, klient=klient, zegar=zegar)
    klient.blad = BladOdpowiedziApi("500")
    with pytest.raises(BladOdpowiedziApi):
        serwis.stacje()


def test_nieudane_nie_zmienia_czasu(cache, klient, zegar):
    serwis = Serwis(cache=cache, klient=klient, zegar=zegar)
    pierwszy_czas = zegar.teraz
    serwis.stacje()
    assert cache.ostatnie_pobranie("stacje") == pierwszy_czas

    zegar.teraz += TTL_STACJE + timedelta(minutes=5)
    klient.blad = BladOdpowiedziApi("500")
    wynik_blad = serwis.stacje()
    assert wynik_blad.nieaktualne is True
    assert cache.ostatnie_pobranie("stacje") == pierwszy_czas

    klient.blad = None
    wynik_ok = serwis.stacje()
    assert wynik_ok.nieaktualne is False
    assert cache.ostatnie_pobranie("stacje") == zegar.teraz


def test_akumulacja_bez_duplikatow(cache, klient, zegar):
    t1 = datetime(2026, 11, 18, 10, 0)
    t2 = datetime(2026, 11, 18, 11, 0)
    t3 = datetime(2026, 11, 18, 12, 0)

    klient.stanowiska = {1: [Stanowisko(10, "PM10", "µg/m³")]}
    klient.pomiary = {10: [Pomiar(10, t1, 15.0), Pomiar(10, t2, 18.0)]}

    serwis = Serwis(cache=cache, klient=klient, zegar=zegar)
    res1 = serwis.pomiary(1, 10)
    assert res1.dane == [Pomiar(10, t1, 15.0), Pomiar(10, t2, 18.0)]

    zegar.teraz += TTL_POMIARY + timedelta(minutes=1)
    klient.pomiary = {10: [Pomiar(10, t2, 19.5), Pomiar(10, t3, 21.0)]}

    res2 = serwis.pomiary(1, 10)
    assert res2.dane == [
        Pomiar(10, t1, 15.0),
        Pomiar(10, t2, 19.5),
        Pomiar(10, t3, 21.0),
    ]
    assert res2.nieaktualne is False


def test_pusta_api_nie_ponawia_zapytan(cache, klient, zegar):
    klient.stanowiska = {1: []}
    serwis = Serwis(cache=cache, klient=klient, zegar=zegar)

    res1 = serwis.stacja(1)
    res2 = serwis.stacja(1)

    assert res1.dane.stanowiska == []
    assert res2.dane.stanowiska == []
    assert klient.wywolania.count("stanowiska:1") == 1


def test_brak_stacji_lub_stanowiska(cache, klient, zegar):
    klient.stanowiska = {1: [Stanowisko(10, "PM10", "µg/m³")]}
    serwis = Serwis(cache=cache, klient=klient, zegar=zegar)

    with pytest.raises(BrakDanychPomiarowych):
        serwis.stacja(999999)

    with pytest.raises(BrakDanychPomiarowych):
        serwis.pomiary(1, 888888)


def test_pomiary_laczy_stanowiska(cache, klient, zegar):
    t1 = datetime(2026, 11, 18, 10, 0)
    t2 = datetime(2026, 11, 18, 11, 0)

    klient.stanowiska = {
        1: [
            Stanowisko(10, "PM10", "µg/m³"),
            Stanowisko(11, "PM10", "µg/m³"),
        ]
    }
    klient.pomiary = {
        10: [Pomiar(10, t2, 20.0)],
        11: [Pomiar(11, t1, 14.0)],
    }

    serwis = Serwis(cache=cache, klient=klient, zegar=zegar)
    res = serwis.pomiary_parametru(1, "PM10")

    assert res.dane == [Pomiar(11, t1, 14.0), Pomiar(10, t2, 20.0)]
    assert res.nieaktualne is False
