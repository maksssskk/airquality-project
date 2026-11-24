from datetime import datetime

import pytest

from monitor_powietrza.cache import Cache
from monitor_powietrza.model import Pomiar, Stacja, Stanowisko
from monitor_powietrza.wyjatki import BladCache


@pytest.fixture
def cache_ze_stanowiskiem(cache):
    cache.zapisz_stacje([Stacja(12096, "Lublin, ul. Okopowa", "Lublin")])
    cache.zapisz_stanowiska(12096, [Stanowisko(295, "PM10", "µg/m³")])
    return cache


def test_stacje_pelny_cykl(cache):
    stacje = []
    stacje.append(Stacja(1, "Stacja 1", "Lublin"))
    stacje.append(Stacja(2, "Stacja 2", "Warszawa"))
    stacje.append(Stacja(3, "Stacja 3", "Radom"))
    cache.zapisz_stacje(stacje)
    res = cache.wczytaj_stacje()
    assert res == stacje


def test_stacje_noduplicates(cache):
    s = Stacja(12096, "Stara nazwa", "Lublin")
    s2 = Stacja(12096, "Nowa nazwa", "Lublin")
    cache.zapisz_stacje([s])
    cache.zapisz_stacje([s2])
    res = cache.wczytaj_stacje()
    assert len(res) == 1
    assert res[0].nazwa == "Nowa nazwa"


def test_stanowiska_zapis_izolacja(cache):
    cache.zapisz_stacje(
        [
            Stacja(12096, "Stacja 1", "Lublin"),
            Stacja(99999, "Stacja 2", "Warszawa"),
        ]
    )

    st1 = Stanowisko(295, "PM10", "µg/m³")
    st2 = Stanowisko(14397, "PM10", "µg/m³")
    st4 = Stanowisko(55555, "PM10", "µg/m³")

    cache.zapisz_stanowiska(12096, [st1, st2])
    cache.zapisz_stanowiska(99999, [st4])

    res = cache.wczytaj_stanowiska(12096)
    assert len(res) == 2
    assert res[0].id == 295
    assert res[1].id == 14397


def test_pomiary_pelny_cykl(cache_ze_stanowiskiem):
    t1 = datetime(2026, 11, 18, 10, 0)
    t2 = datetime(2026, 11, 18, 11, 0)
    t3 = datetime(2026, 11, 18, 12, 0)

    p1 = Pomiar(295, t1, 15.5)
    p2 = Pomiar(295, t2, None)
    p3 = Pomiar(295, t3, 22.0)

    cache_ze_stanowiskiem.zapisz_pomiary([p1, p2, p3])
    res = cache_ze_stanowiskiem.wczytaj_pomiary(295)
    assert res == [p1, p2, p3]
    assert res[1].wartosc is None


def test_dublowanie_pomiarom(cache_ze_stanowiskiem):
    t1 = datetime(2026, 11, 18, 10, 0)

    stary = Pomiar(295, t1, 18.2)
    nowy = Pomiar(295, t1, 20)

    cache_ze_stanowiskiem.zapisz_pomiary([stary])
    cache_ze_stanowiskiem.zapisz_pomiary([nowy])
    assert cache_ze_stanowiskiem.wczytaj_pomiary(295) == [nowy]


def test_od_do_filtr(cache_ze_stanowiskiem):
    t1 = datetime(2026, 11, 18, 10, 0)
    t2 = datetime(2026, 11, 18, 11, 0)
    t3 = datetime(2026, 11, 18, 12, 0)

    p1 = Pomiar(295, t1, 13.5)
    p2 = Pomiar(295, t2, 11.8)
    p3 = Pomiar(295, t3, 12.2)

    cache_ze_stanowiskiem.zapisz_pomiary([p1, p2, p3])
    res = cache_ze_stanowiskiem.wczytaj_pomiary(295, od=t2, do=t3)
    assert res == [p2, p3]


def test_izolacja_stanowisk(cache_ze_stanowiskiem):
    cache_ze_stanowiskiem.zapisz_stanowiska(12096, [Stanowisko(14397, "PM10", "µg/m³")])
    t1 = datetime(2026, 11, 18, 10, 0)
    t2 = datetime(2026, 11, 24, 15, 0)

    p1 = Pomiar(295, t1, 6.5)
    p2 = Pomiar(14397, t2, 2.0)

    cache_ze_stanowiskiem.zapisz_pomiary([p1, p2])
    res1 = cache_ze_stanowiskiem.wczytaj_pomiary(295)
    res2 = cache_ze_stanowiskiem.wczytaj_pomiary(14397)
    assert res1 == [p1]
    assert res2 == [p2]


def test_trwalosc_miedzy_instancjami(tmp_path):
    url = f"sqlite:///{tmp_path / 'trwaly.db'}"
    stacja = Stacja(12096, "Lublin, ul. Okopowa", "Lublin")
    stanowisko = Stanowisko(295, "PM10", "µg/m³")
    pomiar = Pomiar(295, datetime(2026, 11, 18, 10, 0), 18.5)

    cache1 = Cache(url)
    cache1.zapisz_stacje([stacja])
    cache1.zapisz_stanowiska(12096, [stanowisko])
    cache1.zapisz_pomiary([pomiar])

    cache2 = Cache(url)
    stacja.dodaj_stanowisko(stanowisko)
    assert cache2.wczytaj_stacje() == [stacja]
    assert cache2.wczytaj_stanowiska(12096) == [stanowisko]
    assert cache2.wczytaj_pomiary(295) == [pomiar]
    cache1.zamknij()
    cache2.zamknij()


def test_czas_pobrania(cache):
    assert cache.ostatnie_pobranie("stacje") is None

    t1 = datetime(2026, 11, 18, 10, 0)
    t2 = datetime(2026, 11, 18, 12, 30)

    cache.oznacz_pobranie("stacje", t1)
    assert cache.ostatnie_pobranie("stacje") == t1

    cache.oznacz_pobranie("stacje", t2)
    assert cache.ostatnie_pobranie("stacje") == t2


def test_pusta_baza(cache):
    assert cache.wczytaj_stacje() == []
    assert cache.wczytaj_stanowiska(12096) == []
    assert cache.wczytaj_pomiary(295) == []


def test_klucze_obce(cache):
    t1 = datetime(2026, 11, 11, 10, 0)
    with pytest.raises(BladCache):
        cache.zapisz_stanowiska(999999, [Stanowisko(1, "PM10", "µg/m³")])
    with pytest.raises(BladCache):
        cache.zapisz_pomiary([Pomiar(999999, t1, 10.0)])


def test_ponowny_zapis_stanowiska(cache):
    s = Stacja(12096, "Stara", "Lublin")
    cache.zapisz_stacje([s])
    st = Stanowisko(295, "PM10", "µg/m³")
    cache.zapisz_stanowiska(12096, [st])

    cache.zapisz_stacje([Stacja(12096, "Nowa", "Lublin")])
    res = cache.wczytaj_stacje()
    assert res[0].nazwa == "Nowa"
    assert res[0].stanowiska == [st]


def test_puste_listy(cache):
    cache.zapisz_stacje([])
    cache.zapisz_stanowiska(12096, [])
    cache.zapisz_pomiary([])


def test_blad_konstruktora(tmp_path):
    with pytest.raises(BladCache):
        Cache(f"sqlite:///{tmp_path / 'nieistniejacy_katalog' / 'test.db'}")


@pytest.fixture
def cache(tmp_path):
    c = Cache(f"sqlite:///{tmp_path / 'test.db'}")
    yield c
    c.zamknij()
