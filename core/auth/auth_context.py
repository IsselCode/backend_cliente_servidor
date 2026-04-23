from dataclasses import dataclass

@dataclass(slots=True)
class AuthContext:
    uid: str
    username: str
    display_name: str
    role: str

    @classmethod
    def from_payload(cls, payload: dict) -> "AuthContext":
        return cls(
            uid=payload["uid"],
            username=payload["sub"],
            display_name=payload["display_name"],
            role=payload["role"],
        )
