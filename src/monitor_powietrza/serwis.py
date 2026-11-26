import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from monitor_powietrza import klient_api
from monitor_powietrza.cache import Cache
from monitor_powietrza.model import Pomiar, Stacja
from monitor_powietrza.wyjatki import (
    BladOdpowiedziApi,
    BladSieci,
    BrakDanychPomiarowych,
)

TTL_STACJE = timedelta(hours=24)
TTL_STANOWISKA = timedelta(hours=24)
TTL_POMIARY = timedelta(hours=1)
STACJE = [12096, 16753, 20548, 20928]
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Wynik[T]:
    dane: T
    nieaktualne: bool = False


class Serwis:
    def __init__(
        self,
        cache: Cache,
        klient=klient_api,
        zegar: Callable[[], datetime] = datetime.now,
        ttl_stacje: timedelta = TTL_STACJE,
        ttl_stanowiska: timedelta = TTL_STANOWISKA,
        ttl_pomiary: timedelta = TTL_POMIARY,
    ):
        self._cache = cache
        self._klient = klient
        self._zegar = zegar
        self._ttl_stacje = ttl_stacje
        self._ttl_stanowiska = ttl_stanowiska
        self._ttl_pomiary = ttl_pomiary

    def _odswiez_jesli_trzeba[T](
        self,
        klucz: str,
        ttl: timedelta,
        pobierz_z_api: Callable[[], T],
        zapisz_do_cache: Callable[[T], None],
    ) -> bool:
        ostatnio = self._cache.ostatnie_pobranie(klucz)
        czas_teraz = self._zegar()

        if ostatnio is not None and (czas_teraz - ostatnio) < ttl:
            return False
        else:
            try:
                dane = pobierz_z_api()
                zapisz_do_cache(dane)
                self._cache.oznacz_pobranie(klucz, czas_teraz)
                return False
            except (BladSieci, BladOdpowiedziApi) as e:
                if ostatnio is not None:
                    logger.warning("Nie udało się pobrać danych(%s): %s!", klucz, e)
                    return True
                else:
                    raise

    def _pobierz_pomiary_stanowiska(
        self,
        stanowisko_id: int,
        od: datetime | None = None,
        do: datetime | None = None,
    ) -> Wynik[list[Pomiar]]:
        nieaktualne = self._odswiez_jesli_trzeba(
            f"pomiary:{stanowisko_id}",
            self._ttl_pomiary,
            lambda: self._klient.pobierz_pomiary(stanowisko_id),
            self._cache.zapisz_pomiary,
        )
        dane = self._cache.wczytaj_pomiary(stanowisko_id, od=od, do=do)
        return Wynik(dane=dane, nieaktualne=nieaktualne)

    def stacje(self) -> Wynik[list[Stacja]]:
        nieaktualne = self._odswiez_jesli_trzeba(
            "stacje",
            self._ttl_stacje,
            self._klient.pobierz_stacje,
            self._cache.zapisz_stacje,
        )
        dane = self._cache.wczytaj_stacje()
        return Wynik(dane=dane, nieaktualne=nieaktualne)

    def stacja(self, stacja_id: int) -> Wynik[Stacja]:
        wynik_stacji = self.stacje()
        stacja = next((s for s in wynik_stacji.dane if s.id == stacja_id), None)
        if stacja is not None:
            nieaktualne_stanowiska = self._odswiez_jesli_trzeba(
                f"stanowiska:{stacja_id}",
                self._ttl_stanowiska,
                lambda: self._klient.pobierz_stanowiska(stacja_id),
                lambda dane: self._cache.zapisz_stanowiska(stacja_id, dane),
            )
            stanowiska = self._cache.wczytaj_stanowiska(stacja_id)
            pelna_stacja = Stacja(
                id=stacja.id, nazwa=stacja.nazwa, miasto=stacja.miasto
            )
            for st in stanowiska:
                pelna_stacja.dodaj_stanowisko(st)
            nieaktualne = wynik_stacji.nieaktualne or nieaktualne_stanowiska
            return Wynik(dane=pelna_stacja, nieaktualne=nieaktualne)
        else:
            raise BrakDanychPomiarowych(f"Brak stacji o id: {stacja_id}")

    def pomiary(
        self,
        stacja_id: int,
        stanowisko_id: int,
        od: datetime | None = None,
        do: datetime | None = None,
    ) -> Wynik[list[Pomiar]]:
        wynik_stacji = self.stacja(stacja_id)
        stanowisko = next(
            (s for s in wynik_stacji.dane.stanowiska if s.id == stanowisko_id), None
        )
        if stanowisko is not None:
            nieaktualne_pomiary = self._odswiez_jesli_trzeba(
                f"pomiary:{stanowisko_id}",
                self._ttl_pomiary,
                lambda: self._klient.pobierz_pomiary(stanowisko_id),
                self._cache.zapisz_pomiary,
            )
            dane = self._cache.wczytaj_pomiary(stanowisko_id, od=od, do=do)
            return Wynik(
                dane=dane, nieaktualne=wynik_stacji.nieaktualne or nieaktualne_pomiary
            )
        else:
            raise BrakDanychPomiarowych(
                f"Stanowisko {stanowisko_id} nie nalezy do stacji {stacja_id}"
            )

    def pomiary_parametru(
        self,
        stacja_id: int,
        parametr: str,
        od: datetime | None = None,
        do: datetime | None = None,
    ) -> Wynik[list[Pomiar]]:
        wynik_stacji = self.stacja(stacja_id)
        lista_stanowisk = wynik_stacji.dane.stanowiska_dla(parametr)
        lista_pomiary = []
        nieaktualne = wynik_stacji.nieaktualne
        for s in lista_stanowisk:
            wynik = self.pomiary(stacja_id, s.id, od=od, do=do)
            lista_pomiary.extend(wynik.dane)
            nieaktualne = nieaktualne or wynik.nieaktualne
        lista_pomiary.sort(key=lambda p: p.czas)
        return Wynik(dane=lista_pomiary, nieaktualne=nieaktualne)
