from datetime import datetime

from sqlalchemy import ForeignKey, create_engine, event, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from monitor_powietrza.model import Pomiar, Stacja, Stanowisko
from monitor_powietrza.wyjatki import BladCache


class Base(DeclarativeBase):
    pass


class StacjaTabl(Base):
    __tablename__ = "stacje"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    nazwa: Mapped[str]
    miasto: Mapped[str]
    stanowiska: Mapped[list["StanowiskoTabl"]] = relationship(
        back_populates="stacje", lazy="selectin"
    )


class StanowiskoTabl(Base):
    __tablename__ = "stanowiska"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    stacja_id: Mapped[int] = mapped_column(ForeignKey("stacje.id", ondelete="cascade"))
    parametr: Mapped[str]
    jednostka: Mapped[str]
    stacje: Mapped["StacjaTabl"] = relationship(back_populates="stanowiska")


class PomiaryTabl(Base):
    __tablename__ = "pomiary"
    stanowisko_id: Mapped[int] = mapped_column(
        ForeignKey("stanowiska.id", ondelete="cascade"), primary_key=True
    )
    czas: Mapped[datetime] = mapped_column(primary_key=True)
    wartosc: Mapped[float | None] = mapped_column(nullable=True)


class PobraniaTabl(Base):
    __tablename__ = "pobrania"
    klucz: Mapped[str] = mapped_column(primary_key=True)
    ostatnio: Mapped[datetime]


def _stacja_na_orm(stacja: Stacja) -> StacjaTabl:
    return StacjaTabl(id=stacja.id, nazwa=stacja.nazwa, miasto=stacja.miasto)


def _orm_na_stacje(orm: StacjaTabl) -> Stacja:
    stacja = Stacja(id=orm.id, nazwa=orm.nazwa, miasto=orm.miasto)
    for s in orm.stanowiska:
        stacja.dodaj_stanowisko(_orm_na_stanowisko(s))
    return stacja


def _stanowisko_na_orm(stacja_id: int, stanowisko: Stanowisko) -> StanowiskoTabl:
    return StanowiskoTabl(
        id=stanowisko.id,
        stacja_id=stacja_id,
        parametr=stanowisko.parametr,
        jednostka=stanowisko.jednostka,
    )


def _orm_na_stanowisko(orm: StanowiskoTabl) -> Stanowisko:
    return Stanowisko(id=orm.id, parametr=orm.parametr, jednostka=orm.jednostka)


def _pomiar_na_orm(pomiar: Pomiar) -> PomiaryTabl:
    return PomiaryTabl(
        stanowisko_id=pomiar.stanowisko_id, czas=pomiar.czas, wartosc=pomiar.wartosc
    )


def _orm_na_pomiar(orm: PomiaryTabl) -> Pomiar:
    return Pomiar(stanowisko_id=orm.stanowisko_id, czas=orm.czas, wartosc=orm.wartosc)


class Cache:
    def __init__(self, url: str = "sqlite:///monitor.db"):
        try:
            engine = create_engine(url)

            @event.listens_for(engine, "connect")
            def _wlacz_klucze_obce(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("pragma foreign_keys=ON")
                cursor.close()

            self._engine = engine
            Base.metadata.create_all(self._engine)
        except SQLAlchemyError as e:
            raise BladCache(f"Błąd cache: {e}") from e

    def zapisz_stacje(self, stacje: list[Stacja]) -> None:
        try:
            if not stacje:
                return
            else:
                with Session(self._engine) as s, s.begin():
                    for st in stacje:
                        s.merge(_stacja_na_orm(st))
        except SQLAlchemyError as e:
            raise BladCache(f"Błąd cache: {e}") from e

    def wczytaj_stacje(self) -> list[Stacja]:
        try:
            with Session(self._engine) as s:
                res = s.scalars(select(StacjaTabl).order_by(StacjaTabl.id.asc())).all()
                return [_orm_na_stacje(orm) for orm in res]
        except SQLAlchemyError as e:
            raise BladCache(f"Błąd cache: {e}") from e

    def zapisz_stanowiska(self, stacja_id: int, stanowiska: list[Stanowisko]) -> None:
        try:
            if not stanowiska:
                return
            else:
                with Session(self._engine) as s, s.begin():
                    for st in stanowiska:
                        s.merge(_stanowisko_na_orm(stacja_id, st))
        except SQLAlchemyError as e:
            raise BladCache(f"Błąd cache: {e}") from e

    def wczytaj_stanowiska(self, stacja_id: int) -> list[Stanowisko]:
        try:
            with Session(self._engine) as s:
                res = s.scalars(
                    select(StanowiskoTabl)
                    .where(StanowiskoTabl.stacja_id == stacja_id)
                    .order_by(StanowiskoTabl.id.asc())
                ).all()
                return [_orm_na_stanowisko(orm) for orm in res]
        except SQLAlchemyError as e:
            raise BladCache(f"Błąd cache: {e}") from e

    def zapisz_pomiary(self, pomiary: list[Pomiar]) -> None:
        try:
            if not pomiary:
                return
            else:
                with Session(self._engine) as s, s.begin():
                    d = [
                        {
                            "stanowisko_id": p.stanowisko_id,
                            "czas": p.czas,
                            "wartosc": p.wartosc,
                        }
                        for p in pomiary
                    ]
                    stmt = insert(PomiaryTabl).on_conflict_do_update(
                        index_elements=[PomiaryTabl.stanowisko_id, PomiaryTabl.czas],
                        set_={"wartosc": insert(PomiaryTabl).excluded.wartosc},
                    )
                    s.execute(stmt, d)
        except SQLAlchemyError as e:
            raise BladCache(f"Błąd cache: {e}") from e

    def wczytaj_pomiary(
        self, stanowisko_id: int, od: datetime | None = None, do: datetime | None = None
    ) -> list[Pomiar]:
        try:
            with Session(self._engine) as s:
                stmt = select(PomiaryTabl).where(
                    PomiaryTabl.stanowisko_id == stanowisko_id
                )
                if od is not None:
                    stmt = stmt.where(PomiaryTabl.czas >= od)
                if do is not None:
                    stmt = stmt.where(PomiaryTabl.czas <= do)
                stmt = stmt.order_by(PomiaryTabl.czas.asc())
                res = s.scalars(stmt).all()
                return [_orm_na_pomiar(orm) for orm in res]
        except SQLAlchemyError as e:
            raise BladCache(f"Błąd cache: {e}") from e

    def oznacz_pobranie(self, klucz: str, czas: datetime) -> None:
        try:
            with Session(self._engine) as s, s.begin():
                s.merge(PobraniaTabl(klucz=klucz, ostatnio=czas))
        except SQLAlchemyError as e:
            raise BladCache(f"Błąd cache: {e}") from e

    def ostatnie_pobranie(self, klucz: str) -> datetime | None:
        try:
            with Session(self._engine) as s:
                zapis = s.get(PobraniaTabl, klucz)
                if zapis is not None:
                    return zapis.ostatnio
                else:
                    return
        except SQLAlchemyError as e:
            raise BladCache(f"Błąd cache: {e}") from e

    def zamknij(self) -> None:
        self._engine.dispose()
