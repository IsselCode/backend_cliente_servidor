from datetime import datetime, UTC

def utc_now() -> datetime:
    return datetime.now(UTC)

def utc_now_iso() -> str:
    return utc_now().isoformat()