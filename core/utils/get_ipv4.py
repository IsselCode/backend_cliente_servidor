import socket

def get_ipv4() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 1))
        address = s.getsockname()[0]
        if address is None or address.startswith("127."):
            raise RuntimeError("Solo acepta direcciones loopback IPv4")
        return address
    except OSError as exc:
        raise RuntimeError("No se pudo determinar la ipv4") from exc
    finally:
        s.close()