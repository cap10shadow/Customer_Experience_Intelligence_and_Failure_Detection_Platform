from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Tuple


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


def resolve_comparison_windows(days: int) -> Tuple[TrendWindow, TrendWindow]:
    """
    Resolves two equal-sized, back-to-back windows ending now: the current
    window and the immediately preceding "previous equivalent" window used
    as the anomaly detection baseline (e.g. "Last 7 Days" vs "Previous 7 Days").
    """
    current = resolve_window(days)
    previous = TrendWindow(
        start=current.start - timedelta(days=days),
        end=current.start,
        label=f"Previous {days} Days",
    )
    return current, previous
