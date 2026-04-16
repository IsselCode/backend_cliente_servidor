"""
Script manual para comprobar descubrimiento mDNS.

Escucha servicios publicados en la red local y muestra nombre, servidor,
puerto y direcciones para verificar que el backend se esta anunciando.
"""

import time

from zeroconf import IPVersion, ServiceBrowser, ServiceStateChange, Zeroconf


def escuchar_mdns(service_type: str = "_http._tcp.local.", tiempo_escucha: float = 10.0) -> None:
    if tiempo_escucha <= 0:
        raise ValueError("tiempo_escucha debe ser mayor a 0")

    zeroconf = Zeroconf(ip_version=IPVersion.V4Only)

    def on_service_state_change(
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
        **_: object,
    ) -> None:
        info = zeroconf.get_service_info(service_type, name)

        print(f"[{state_change.name}] {name}")
        if info is None:
            return

        print(f"  servidor: {info.server}")
        print(f"  puerto: {info.port}")
        print(f"  direcciones: {info.parsed_addresses()}")
        print()

    browser = ServiceBrowser(zeroconf, service_type, handlers=[on_service_state_change])

    try:
        time.sleep(tiempo_escucha)
    finally:
        browser.cancel()
        zeroconf.close()

escuchar_mdns()
