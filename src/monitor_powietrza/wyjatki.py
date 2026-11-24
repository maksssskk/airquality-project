class BladMonitoraPowietrza(Exception):
    """Bazowy wyjątek aplikacji."""


class BladSieci(BladMonitoraPowietrza):
    pass


class BladOdpowiedziApi(BladMonitoraPowietrza):
    pass


class BrakDanychPomiarowych(BladMonitoraPowietrza):
    pass


class BladCache(BladMonitoraPowietrza):
    pass
