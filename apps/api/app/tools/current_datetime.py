from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ALLOWED_TIMEZONES = {
    "UTC",
    "Asia/Kuala_Lumpur",
    "Asia/Singapore",
    "America/New_York",
    "Europe/London",
}


def get_current_datetime(timezone: str = "UTC") -> dict[str, str]:
    tz_name = timezone.strip() if timezone else "UTC"
    if tz_name not in ALLOWED_TIMEZONES:
        raise ValueError(f"Timezone not allowed: {tz_name}")
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: {tz_name}") from exc
    now = datetime.now(tz)
    return {
        "datetime_utc": datetime.now(ZoneInfo("UTC")).isoformat(),
        "datetime_local": now.isoformat(),
        "timezone": tz_name,
    }
