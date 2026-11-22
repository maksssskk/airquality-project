from datetime import datetime

from monitor_powietrza.model import Pomiar, Stacja, Stanowisko
from monitor_powietrza.wyjatki import BladOdpowiedziApi

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
