import pytest
import requests

from monitor_powietrza.klient_api import (
    BAZOWY_URL,
    ILOSC_PROB,
    KLUCZ_LISTA_POMIARY,
    TIMEOUT,
    _pobierz,
    _pobierz_wszystkie,
    pobierz_pomiary,
    pobierz_stacje,
    pobierz_stanowiska,
)
from monitor_powietrza.model import Pomiar, Stacja, Stanowisko
from monitor_powietrza.wyjatki import BladOdpowiedziApi, BladSieci


class Odpowiedz:
    def __init__(self, status_code: int, dane: object = None, zly_json: bool = False):
        self.status_code = status_code
        self.dane = dane
        self.zly_json = zly_json

    def json(self):
        if self.zly_json:
            raise ValueError("Zły JSON plik!")
        else:
            return self.dane

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("Status code większy za 400!")


def dowolne_kroki(monkeypatch, scenariusz):
    call = []

    def falszywy_get(url, params=None, timeout=None):
        call.append((url, params, timeout))
        krok = scenariusz.pop(0)
        if isinstance(krok, Exception):
            raise krok
        else:
            return krok

    pauzy = []
    monkeypatch.setattr("monitor_powietrza.klient_api.requests.get", falszywy_get)
    monkeypatch.setattr("monitor_powietrza.klient_api.time.sleep", pauzy.append)
    return call, pauzy


def test_win_firsttime(monkeypatch):
    call, _ = dowolne_kroki(monkeypatch, [Odpowiedz(200, {"klucz": "wartosc"})])
    func = _pobierz("/test")
    assert isinstance(func, dict)
    assert len(call) == 1
    assert call[0][0] == BAZOWY_URL + "/test"
    assert call[0][2] == TIMEOUT


def test_2fail_1win(monkeypatch):
    call, _ = dowolne_kroki(
        monkeypatch,
        [requests.Timeout(), requests.ConnectionError(), Odpowiedz(200, {"ok": True})],
    )
    func = _pobierz("/test")
    assert func == {"ok": True}
    assert len(call) == 3


def test_3fail(monkeypatch):
    call, pauzy = dowolne_kroki(monkeypatch, [requests.ConnectionError()] * ILOSC_PROB)
    with pytest.raises(BladSieci):
        _pobierz("/test")
    assert len(pauzy) == ILOSC_PROB - 1
    assert len(call) == ILOSC_PROB


def test_res500(monkeypatch):
    call, _ = dowolne_kroki(monkeypatch, [Odpowiedz(503, {})] * ILOSC_PROB)
    with pytest.raises(BladSieci):
        _pobierz("/test")
    assert len(call) == ILOSC_PROB


def test_res400(monkeypatch):
    call, _ = dowolne_kroki(monkeypatch, [Odpowiedz(404, {})])
    with pytest.raises(BladOdpowiedziApi):
        _pobierz("/test")
    assert len(call) == 1


def test_bad_json(monkeypatch):
    call, _ = dowolne_kroki(monkeypatch, [Odpowiedz(200, {}, zly_json=True)])
    with pytest.raises(BladOdpowiedziApi):
        _pobierz("/test")
    assert len(call) == 1


def test_pobierz_wszystkie_paginacja(monkeypatch):
    wywolania, _ = dowolne_kroki(
        monkeypatch,
        [
            Odpowiedz(200, {"totalPages": 3, "lista": [1, 2]}),
            Odpowiedz(200, {"totalPages": 3, "lista": [3, 4]}),
            Odpowiedz(200, {"totalPages": 3, "lista": [5, 6]}),
        ],
    )

    wynik = _pobierz_wszystkie("/test", "lista")

    assert wynik == {"lista": [1, 2, 3, 4, 5, 6]}
    assert len(wywolania) == 3
    assert [params["page"] for _, params, _ in wywolania] == [0, 1, 2]


def test_pobierz_stacje_sukces(monkeypatch, wczytaj_json):
    dane = wczytaj_json("stacje.json")
    dane["totalPages"] = 1

    dowolne_kroki(monkeypatch, [Odpowiedz(200, dane)])

    stacje = pobierz_stacje()

    assert len(stacje) == 3
    assert all(isinstance(s, Stacja) for s in stacje)


@pytest.mark.parametrize(
    "scenariusz",
    [
        [Odpowiedz(200, {"lista": [1, 2]})],
        [Odpowiedz(200, {"totalPages": "3", "lista": [1, 2]})],
        [Odpowiedz(200, {"totalPages": True, "lista": [1, 2]})],
        [Odpowiedz(200, {"totalPages": 1, "lista": {"nie": "lista"}})],
        [
            Odpowiedz(200, {"totalPages": 2, "lista": [1, 2]}),
            Odpowiedz(200, {"totalPages": 2, "lista": "nie_lista"}),
        ],
    ],
)
def test_pobierz_wszystkie(monkeypatch, scenariusz):
    dowolne_kroki(monkeypatch, list(scenariusz))
    with pytest.raises(BladOdpowiedziApi):
        _pobierz_wszystkie("/test", "lista")


def test_pobierz_stanowiska(monkeypatch, wczytaj_json):
    dane = wczytaj_json("stanowiska.json")
    dane["totalPages"] = 1
    call, _ = dowolne_kroki(monkeypatch, [Odpowiedz(200, dane)])
    stanowiska = pobierz_stanowiska(12096)
    assert len(stanowiska) == 4
    assert all(isinstance(s, Stanowisko) for s in stanowiska)
    assert call[0][0] == f"{BAZOWY_URL}/station/sensors/12096"


def test_pobierz_pomiary(monkeypatch, wczytaj_json):
    dane = wczytaj_json("pomiary.json")
    str_1 = {"totalPages": 2, KLUCZ_LISTA_POMIARY: dane[KLUCZ_LISTA_POMIARY][:2]}
    str_2 = {"totalPages": 2, KLUCZ_LISTA_POMIARY: dane[KLUCZ_LISTA_POMIARY][2:]}
    call, _ = dowolne_kroki(monkeypatch, [Odpowiedz(200, str_1), Odpowiedz(200, str_2)])
    pomiary = pobierz_pomiary(295)
    assert len(call) == 2
    assert call[0][0] == f"{BAZOWY_URL}/data/getData/295"
    assert len(pomiary) == len(dane[KLUCZ_LISTA_POMIARY])
    assert all(isinstance(p, Pomiar) for p in pomiary)
