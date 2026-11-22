from dataclasses import dataclass, field
from datetime import datetime

from monitor_powietrza.wyjatki import BrakDanychPomiarowych


@dataclass(frozen=True)
class Pomiar:
    stanowisko_id: int
    czas: datetime
    wartosc: float | None


@dataclass(frozen=True)
class Norma:
    parametr: str
    limit: float

    def przekroczona(self, wartosc: float | None) -> bool:
        return wartosc is not None and wartosc > self.limit


@dataclass(frozen=True)
class Stanowisko:
    id: int
    parametr: str
    jednostka: str


@dataclass
class Stacja:
    id: int
    nazwa: str
    miasto: str
    stanowiska: list[Stanowisko] = field(default_factory=list)

    def dodaj_stanowisko(self, stanowisko: Stanowisko) -> None:
        self.stanowiska.append(stanowisko)

    def stanowiska_dla(self, parametr: str) -> list[Stanowisko]:
        res = []
        for s in self.stanowiska:
            if parametr == s.parametr:
                res.append(s)

        if not res:
            raise BrakDanychPomiarowych(f"Nie znaleziono danych dla {parametr}!")
        else:
            return res
