import json
from pathlib import Path

import pytest

SCIEZKA_DANE = Path(__file__).parent / "dane"


@pytest.fixture
def wczytaj_json():
    def _wczytaj(plik: str) -> dict:
        with open(SCIEZKA_DANE / plik, encoding="utf-8") as f:
            return json.load(f)

    return _wczytaj
