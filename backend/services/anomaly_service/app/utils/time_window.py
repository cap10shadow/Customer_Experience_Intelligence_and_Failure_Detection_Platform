from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class TrendWindow:
    """A resolved [start, end] time range plus its human-readable label."""
    start: datetime
    end: datetime
    label: str


def resolve_window(days: int) -> TrendWindow:
    """
    Resolves a "last N days" window ending now, in UTC.

    Centralised so every aggregator and endpoint describes the same period
    identically (e.g. "Last 30 Days") regardless of which metric it computes.
    """
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return TrendWindow(start=start, end=end, label=f"Last {days} Days")
