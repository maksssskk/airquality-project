# Monitor jakości powietrza

Projekt zaliczeniowy z Programowania w języku Python (laboratorium).

**Temat:** 5.4 Monitor jakości powietrza z danych publicznych  
**Poziom:** 5, projekt indywidualny  
**Autor:** Maksym Kot (23898)

## O projekcie

Aplikacja pobiera dane o jakości powietrza z publicznego API GIOŚ i prezentuje je w panelu webowym. Pobrane dane zapisuję w lokalnej bazie SQLite, żeby nie ściągać ich za każdym razem od nowa. Wyniki są czyszczone w Pandas, a panel pokazuje wykresy, porównanie stacji i przekroczenia norm.

## Wymagania

- Python 3.12 lub nowszy
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Git

## Uruchomienie

```bash
uv sync                                                        # instalacja zależności
uv run monitor-powietrza                                     # uruchomienie aplikacji
uv run pytest --cov=monitor_powietrza --cov-report=term-missing # testy i pokrycie kodu
uv run ruff check .                                            # sprawdzenie stylu kodu
```

## Technologie

- Flask – panel webowy
- SQLAlchemy + SQLite – cache pobranych danych
- Pandas, NumPy – czyszczenie i analiza danych
- Matplotlib – wykresy
- requests – komunikacja z API GIOŚ
- pytest, pytest-cov – testy jednostkowe i pokrycie kodu (aktualnie 99%)
- Ruff – linter i formater kodu

## Model domeny

| Klasa | Opis |
| --- | --- |
| `Stacja` | stacja pomiarowa: id, nazwa, miasto, lista stanowisk |
| `Stanowisko` | stanowisko na stacji: id, mierzony parametr (np. PM10), jednostka |
| `Pomiar` | pojedynczy wynik: stanowisko, czas, wartość (może być pusta / `None`) |
| `Norma` | dopuszczalny poziom parametru i sprawdzenie, czy został przekroczony |

## Własne wyjątki

- `BladMonitoraPowietrza` – klasa bazowa
  - `BladSieci` – problem z połączeniem, timeout lub błąd serwera `5xx` (po 3 próbach)
  - `BladOdpowiedziApi` – niepoprawna odpowiedź API, błąd `4xx` lub brak oczekiwanych pól w JSON
  - `BrakDanychPomiarowych` – brak pomiarów dla stacji lub stanowiska

## Klient API GIOŚ (`klient_api.py`)

Moduł łączy się z REST API GIOŚ (`https://api.gios.gov.pl/pjp-api/v1/rest`) i obsługuje:
- automatyczną paginację odpowiedzi (`page`, `size=500`, `totalPages`),
- ponawianie zapytań przy błędach sieci i statusach `5xx` (do 3 prób z pauzą 2 s),
- natychmiastowe zgłaszanie `BladOdpowiedziApi` przy błędach klienta `4xx` i nieprawidłowym JSON,
- mapowanie odpowiedzi do obiektów `Stacja`, `Stanowisko` oraz `Pomiar` (z obsługą brakujących wartości `null`).

Sprawdzenie na żywym API GIOŚ potwierdziło:
- pobranie wszystkich 288 stacji w Polsce na jednej stronie przy `size=500`,
- dla stacji `12096` (Lublin, ul. Okopowa) API zwraca 5 stanowisk (`NO2`, `PM10`, `PM2.5`, `NOx`, `NO`),
- dla pojedynczego stanowiska zwracanych jest ok. 60 ostatnich odczytów godzinowych, w których zdarzają się wartości `null` (np. podczas kalibracji czujnika).

## Struktura projektu

```text
monitor-powietrza/
├── pyproject.toml
├── README.md
└── src/
    ├── monitor_powietrza/
    │   ├── __init__.py
    │   ├── model.py          # klasy domeny
    │   ├── wyjatki.py        # własne wyjątki
    │   ├── klient_api.py     # pobieranie i parsowanie danych z API GIOŚ
    │   ├── cache.py          # [w trakcie] modele SQLAlchemy, zapis do SQLite
    │   ├── przetwarzanie.py  # [planowane] czyszczenie i analiza (Pandas, NumPy)
    │   └── web/              # [planowane] aplikacja Flask
    └── tests/
        ├── conftest.py
        ├── dane/             # przykładowe odpowiedzi JSON z API
        ├── test_model.py
        ├── test_klient_api.py
        └── test_klient_http.py
```