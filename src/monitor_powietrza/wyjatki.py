class BladMonitoraPowietrza(Exception):
    """Bazowy wyjątek aplikacji."""


class BladSieci(BladMonitoraPowietrza): ...


class BladOdpowiedziApi(BladMonitoraPowietrza): ...


class BrakDanychPomiarowych(BladMonitoraPowietrza): ...
