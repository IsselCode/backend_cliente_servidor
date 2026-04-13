import os
from dataclasses import dataclass

@dataclass(slots=True)
class AppSettings:
    app_name: str
    app_port: int

    @classmethod
    def from_env(cls) -> "AppSettings":
        return cls(
            app_name=os.getenv("APP_NAME", "Backend cliente servidor"),
            app_port=int(os.getenv("APP_PORT", 8000)),
        )