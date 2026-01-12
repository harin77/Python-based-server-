from datetime import datetime, timezone

def get_current_timestamp():
    """Returns ISO 8601 formatted UTC timestamp (e.g., 2023-10-27T10:00:00+00:00)."""
    return datetime.now(timezone.utc).isoformat()