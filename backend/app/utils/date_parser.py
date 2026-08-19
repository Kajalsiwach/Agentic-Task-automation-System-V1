import re
from datetime import datetime, timedelta, timezone
from typing import Optional

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

def parse_natural_date(raw_date: str, base_date: Optional[datetime] = None) -> Optional[str]:
    """
    Parse a natural language date string into an ISO format string (YYYY-MM-DD).
    Returns None if cannot be parsed.
    """
    if not raw_date:
        return None

    raw_clean = raw_date.strip().lower()
    now = base_date or datetime.now(timezone.utc)

    # 1. ISO format check (YYYY-MM-DD)
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw_clean):
        return raw_clean

    # 2. Relative keywords
    if raw_clean in ("today", "tonight"):
        return now.strftime("%Y-%m-%d")

    if raw_clean == "tomorrow":
        target = now + timedelta(days=1)
        return target.strftime("%Y-%m-%d")

    if raw_clean == "yesterday":
        target = now - timedelta(days=1)
        return target.strftime("%Y-%m-%d")

    if raw_clean in ("next week", "in a week"):
        target = now + timedelta(days=7)
        return target.strftime("%Y-%m-%d")

    # 3. "in X days" pattern
    in_days_match = re.search(r"in\s+(\d+)\s+days?", raw_clean)
    if in_days_match:
        days = int(in_days_match.group(1))
        target = now + timedelta(days=days)
        return target.strftime("%Y-%m-%d")

    # 4. Weekdays (e.g., "friday", "next monday", "this wednesday")
    for day_name, day_idx in WEEKDAYS.items():
        if day_name in raw_clean:
            current_day = now.weekday()
            days_ahead = (day_idx - current_day) % 7
            if "next" in raw_clean and days_ahead <= 0:
                days_ahead += 7
            elif days_ahead == 0 and "next" not in raw_clean:
                days_ahead = 7  # Treat upcoming same day as next week unless today
            target = now + timedelta(days=days_ahead if days_ahead > 0 else 7)
            return target.strftime("%Y-%m-%d")

    # Fallback to returning the cleaned string if it's descriptive
    return raw_clean.title()
