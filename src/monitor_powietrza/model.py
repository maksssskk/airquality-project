from dataclasses import dataclass
from datetime import datetime

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