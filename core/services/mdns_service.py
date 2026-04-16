"""
Servicio encargado de anunciar el backend en la red local mediante mDNS.

Registra el servidor como servicio HTTP para que otros clientes puedan
descubrir su IP y puerto sin configurarlos manualmente.
"""

import socket
from dataclasses import dataclass, field

from zeroconf import ServiceInfo, IPVersion
from zeroconf.asyncio import AsyncZeroconf

from core.utils.get_ipv4 import get_ipv4


@dataclass(slots=True)
class MDNSService:

    # Tipo de servicio HTTP con un protocolo TCP que se buscará o anunciará en la red local
    service_type: str = "_http._tcp.local."

    # Instancia AzyncZeroconf; se inicializa como None,
    # No se recibe en el constructor y tampoco aparece en la representacion del objeto
    _azc: AsyncZeroconf | None = field(init=False, default=None, repr=False)
    _service_info: ServiceInfo | None = field(init=False, default=None, repr=False)

    def is_registered(self) -> bool:
        return self._azc is not None and self._service_info is not None

    async def start(self, port: int) -> None:
        if self.is_registered():
            return

        # issel | Obtiene el nombre del equipo donde se ejecuta la aplicación
        host = socket.gethostname()
        ipv4 = get_ipv4()
        binary_ip = socket.inet_aton(ipv4)
        service_info = ServiceInfo(
            type_=self.service_type,
            name = f"{host}.{self.service_type}",
            addresses=[binary_ip],
            port=port,
            server=f"{host}.local."
        )

        # Crea el cliente Zeroconf usando solo direcciones IPv4
        azc = AsyncZeroconf(ip_version=IPVersion.V4Only)

        try:
            await azc.async_register_service(service_info, allow_name_change=True)
        except:
            await azc.async_close()
            raise

        self._azc = azc
        self._service_info = service_info

    async def stop(self) -> None:
        if not self.is_registered():
            return

        try:
            await self._azc.async_unregister_service(self._service_info)
        finally:
            await self._azc.async_close()
            self._azc = None
            self._service_info = None
