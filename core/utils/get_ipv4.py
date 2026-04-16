"""
Utilidad para obtener la direccion IPv4 local util del equipo.

Busca la IP de red que debe publicarse en mDNS y evita devolver direcciones
loopback como 127.0.0.1.
"""

import socket

def get_ipv4() -> str:
    # Crea un socket UDP IPv4 para detectar la ip local.
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Simula una conexión para detectar la IP local de salida.
        # la ip usada esta reservada para documentación y no necesita responder
        s.connect(("192.0.2.1", 1))
        address = s.getsockname()[0]
        if address is None or address.startswith("127."):
            raise RuntimeError("Solo acepta direcciones loopback IPv4")
        return address
    except OSError as exc:
        raise RuntimeError("No se pudo determinar la ipv4") from exc
    finally:
        s.close()
