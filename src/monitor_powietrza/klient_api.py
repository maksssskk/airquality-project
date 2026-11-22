import time
from datetime import datetime

import requests

from monitor_powietrza.model import Pomiar, Stacja, Stanowisko
from monitor_powietrza.wyjatki import BladOdpowiedziApi, BladSieci

KLUCZ_LISTA_STACJI = "Lista stacji pomiarowych"
KLUCZ_LISTA_STANOWISKA = "Lista stanowisk pomiarowych dla podanej stacji"
KLUCZ_LISTA_POMIARY = "Lista danych pomiarowych"

KLUCZ_ID_ST = "Identyfikator stacji"
KLUCZ_NAZWA_ST = "Nazwa stacji"
KLUCZ_NAZWA_MIASTA = "Nazwa miasta"

KLUCZ_ID_STANOWISKA = "Identyfikator stanowiska"
KLUCZ_PARAMETR_ST = "Wskaźnik - kod"
JEDNOSTKA = "µg/m³"

KLUCZ_POM_DATA = "Data"
KLUCZ_POM_WARTOSC = "Wartość"

BAZOWY_URL = "https://api.gios.gov.pl/pjp-api/v1/rest"
TIMEOUT = 10
ILOSC_PROB = 3
PAUZA_PROBY = 2
ROZMIAR_STRONY = 500

def parsuj_stacje(dane: dict) -> list[Stacja]:
    try:
        lista_stacja = dane[KLUCZ_LISTA_STACJI]
        res = []
        for el in lista_stacja:
            st_id = el[KLUCZ_ID_ST]
            nazwa = el[KLUCZ_NAZWA_ST]
            miasto = el[KLUCZ_NAZWA_MIASTA]
            res.append(Stacja(st_id, nazwa, miasto))
        return res
    except (KeyError, ValueError, TypeError) as e:
        raise BladOdpowiedziApi(f"Nieprawidłowa struktura danych: {e}") from e


def parsuj_stanowiska(dane: dict) -> list[Stanowisko]:
    try:
        lista_st = dane[KLUCZ_LISTA_STANOWISKA]
        res = []
        for el in lista_st:
            stan_id = el[KLUCZ_ID_STANOWISKA]
            parametr = el[KLUCZ_PARAMETR_ST]
            jedn = JEDNOSTKA
            res.append(Stanowisko(stan_id, parametr, jedn))
        return res
    except (KeyError, ValueError, TypeError) as e:
        raise BladOdpowiedziApi(f"Nieprawidłowa struktura danych: {e}") from e


def parsuj_pomiary(dane: dict, stanowisko_id: int) -> list[Pomiar]:
    try:
        lista_pom = dane[KLUCZ_LISTA_POMIARY]
        res = []
        for el in lista_pom:
            data = datetime.strptime(el[KLUCZ_POM_DATA], "%Y-%m-%d %H:%M:%S")
            wartosc = el[KLUCZ_POM_WARTOSC]
            if wartosc is not None:
                wartosc = float(wartosc)
            res.append(Pomiar(stanowisko_id, data, wartosc))
        return res
    except (KeyError, ValueError, TypeError) as e:
        raise BladOdpowiedziApi(f"Nieprawidłowa struktura danych: {e}") from e

def _pobierz(sciezka: str, params: dict | None = None) -> dict:
    for proba in range(ILOSC_PROB):
        try:
            req = requests.get(BAZOWY_URL + sciezka, params=params, timeout=TIMEOUT)
            if 400 <= req.status_code < 500:
                raise BladOdpowiedziApi('Błąd odpowiedzi API w request!')
            elif req.status_code >= 500:
                req.raise_for_status()
            else:
                break
        except requests.RequestException as e:
            if proba < ILOSC_PROB - 1:
                time.sleep(PAUZA_PROBY)
            else:
                raise BladSieci(f'Błąd sieci: {e}') from e 
    try:
        dane = req.json()
        if not isinstance(dane, dict):
            raise TypeError('Dane nie są formatu dict!')
    except (ValueError, TypeError) as e:
        raise BladOdpowiedziApi(f'Błąd odpowiedzi API: {e}') from e
    return dane

def _pobierz_wszystkie(sciezka: str, klucz_listy: str) -> dict:
    try:
        req = _pobierz(sciezka, params={"page": 0, "size": ROZMIAR_STRONY})
        total_pages = req['totalPages']
        if not isinstance(total_pages, int) or isinstance(total_pages, bool):
            raise BladOdpowiedziApi ('Błąd odpowiedzi sieci!')
        if not isinstance(req[klucz_listy], list):
            raise BladOdpowiedziApi (f'Błąd odpowiedzi sieci - {req[klucz_listy]} nie jest listem!')
        else:
            lista_el = list(req[klucz_listy])
        for strona in range(1, total_pages):
            next_page = _pobierz(sciezka, params={"page": strona, "size": ROZMIAR_STRONY})
            if isinstance(next_page[klucz_listy], list):
                lista_el.extend(next_page[klucz_listy])
            else:
                raise BladOdpowiedziApi (f'Błąd odpowiedzi sieci - {next_page[klucz_listy]} nie jest listem!')
        return {klucz_listy: lista_el}
            
    except(KeyError, TypeError) as e:
        raise BladOdpowiedziApi(f'Błąd odpowiedzi sieci: {e}') from e

def pobierz_stacje() -> list[Stacja]:
    return parsuj_stacje(_pobierz_wszystkie("/station/findAll", KLUCZ_LISTA_STACJI))

def pobierz_stanowiska(stacja_id: int) -> list[Stanowisko]:
    return parsuj_stanowiska(_pobierz_wszystkie(f"/station/sensors/{stacja_id}", KLUCZ_LISTA_STANOWISKA))

def pobierz_pomiary(stanowisko_id: int) -> list[Pomiar]:
    return parsuj_pomiary(_pobierz(f"/data/getData/{stanowisko_id}"), stanowisko_id)



    

