import pytest
import requests

from monitor_powietrza.klient_api import (
    BAZOWY_URL,
    ILOSC_PROB,
    TIMEOUT,
    _pobierz,
    _pobierz_wszystkie,
    pobierz_stacje,
)
from monitor_powietrza.model import Stacja
from monitor_powietrza.wyjatki import BladOdpowiedziApi, BladSieci
from tests.test_klient_api import wczytaj_json


class Odpowiedz:
    def __init__(self, status_code: int, dane: object = None, zly_json: bool = False):
        self.status_code = status_code
        self.dane = dane
        self.zly_json = zly_json

    def json(self):
        if self.zly_json == True:
            raise ValueError('Zły JSON plik!')
        else:
            return self.dane

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError('Status code większy za 400!')

def dowolne_kroki(monkeypatch, scenariusz):
    call = []
    def falszywy_get(url, params=None, timeout=None):
        call.append((url, params, timeout))
        krok = scenariusz.pop(0)
        if isinstance(krok, Exception):
            raise krok
        else:
            return krok
    monkeypatch.setattr("monitor_powietrza.klient_api.requests.get", falszywy_get)
    monkeypatch.setattr("monitor_powietrza.klient_api.time.sleep", lambda _: None)
    return call

def test_win_firsttime(monkeypatch):
    call = dowolne_kroki(monkeypatch, [Odpowiedz(200, {"klucz": "wartosc"})])
    func = _pobierz('/test')
    assert isinstance(func, dict)
    assert len(call) == 1
    assert call[0][0] == BAZOWY_URL + '/test'
    assert call[0][2] == TIMEOUT

def test_2fail_1win(monkeypatch):
    call = dowolne_kroki(monkeypatch, [requests.Timeout(), requests.ConnectionError(), Odpowiedz(200, {"ok": True})])
    func = _pobierz('/test')
    assert func == {"ok": True}
    assert len(call) == 3

def test_3fail(monkeypatch):
    call = dowolne_kroki(monkeypatch, [requests.ConnectionError()] * ILOSC_PROB)
    with pytest.raises(BladSieci):
        _pobierz('/test')
    assert len(call) == ILOSC_PROB

def test_res500(monkeypatch):
    call = dowolne_kroki(monkeypatch, [Odpowiedz(503, {})] * ILOSC_PROB)
    with pytest.raises(BladSieci): 
        _pobierz("/test")
    assert len(call) == ILOSC_PROB

def test_res400(monkeypatch):
    call = dowolne_kroki(monkeypatch, [Odpowiedz(404, {})])
    with pytest.raises(BladOdpowiedziApi): 
        _pobierz("/test")
    assert len(call) == 1

def test_bad_json(monkeypatch):
    call = dowolne_kroki(monkeypatch, [Odpowiedz(200, {}, zly_json=True)])
    with pytest.raises(BladOdpowiedziApi):
        _pobierz("/test")
    assert len(call) == 1

def test_pobierz_wszystkie_paginacja(monkeypatch):
    wywolania = dowolne_kroki(
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


def test_pobierz_wszystkie_brak_total_pages(monkeypatch):
    dowolne_kroki(
        monkeypatch,
        [Odpowiedz(200, {"lista": [1, 2]})],
    )

    with pytest.raises(BladOdpowiedziApi):
        _pobierz_wszystkie("/test", "lista")


def test_pobierz_stacje_sukces(monkeypatch):
    dane = wczytaj_json("stacje.json")
    dane["totalPages"] = 1

    dowolne_kroki(monkeypatch, [Odpowiedz(200, dane)])

    stacje = pobierz_stacje()

    assert len(stacje) == 3
    assert all(isinstance(s, Stacja) for s in stacje)