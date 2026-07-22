from dataclasses import dataclass


@dataclass(frozen=True)
class TrendMetrics:
    """
    Plain, persistence-independent summary of the trend signals (Phase 4)
    relevant to one Incident, as seen by the Business Impact Engine.

    `percentage_change` is the complaint-volume change between the current
    and baseline windows, already computed upstream -- this engine never
    recomputes it, only reads it.
    """

    current_volume: int
    baseline_volume: int
    percentage_change: float
