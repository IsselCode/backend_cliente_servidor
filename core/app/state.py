from dataclasses import dataclass

from core.app.settings import AppSettings
from core.services.mdns_service import MDNSService


@dataclass(slots=True)
class AppState:
    mdns_service: MDNSService
    settings: AppSettings