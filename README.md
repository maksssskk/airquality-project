# Monitor jakości powietrza

Projekt zaliczeniowy z Programowania w języku Python (laboratorium).

**Temat:** 5.4 Monitor jakości powietrza z danych publicznych
**Poziom:** 5, projekt indywidualny
**Autor:** Maksym Kot(23898)

## O projekcie

Aplikacja pobiera dane o jakości powietrza z publicznego API GIOŚ i pokazuje je w prostym panelu webowym. Pobrane dane zapisuję w lokalnej bazie SQLite, żeby nie ściągać ich za każdym razem od nowa. Dane są czyszczone w Pandas, a panel pokazuje wykresy, porównanie stacji i przekroczenia norm.

## Wymagania

- Python 3.12 lub nowszy
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Git

## Uruchomienie

```pwsh
uv sync                    # instalacja zależności
uv run monitor-powietrza   # uruchomienie aplikacji
uv run pytest              # testy
```

## Technologie

- Flask – panel webowy
- SQLAlchemy + SQLite – cache pobranych danych
- Pandas – czyszczenie i analiza danych
- Matplotlib – wykresy
- requests – komunikacja z API
- pytest, pytest-cov – testy

## Model domeny

| Klasa | Opis |
| --- | --- |
| `Stacja` | stacja pomiarowa: id, nazwa, miasto, lista stanowisk |
| `Stanowisko` | stanowisko na stacji: id, mierzony parametr (np. PM10), jednostka |
| `Pomiar` | pojedynczy wynik: stanowisko, czas, wartość (może być pusta) |
| `Norma` | dopuszczalny poziom parametru i sprawdzenie, czy został przekroczony |

## Własne wyjątki

- `BladMonitoraPowietrza` – klasa bazowa
  - `BladSieci` – problem z połączeniem lub przekroczony czas oczekiwania
  - `BladOdpowiedziApi` – niepoprawna odpowiedź API
  - `BrakDanychPomiarowych` – brak pomiarów dla stacji lub stanowiska

## Planowana struktura

```text
monitor-powietrza/
├── pyproject.toml
├── README.md
├── src/
│   └── monitor_powietrza/
│       ├── __init__.py
│       ├── model.py          # klasy domeny
│       ├── wyjatki.py        # własne wyjątki
│       ├── klient_api.py     # pobieranie danych z API
│       ├── cache.py          # modele SQLAlchemy, zapis do SQLite
│       ├── przetwarzanie.py  # czyszczenie i analiza (Pandas, NumPy)
│       └── web/              # aplikacja Flask
└── tests/
    └── test_model.py
```

