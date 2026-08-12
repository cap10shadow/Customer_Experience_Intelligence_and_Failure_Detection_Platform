from typing import List

from pydantic import BaseModel


class DimensionWeightItem(BaseModel):
    """One `ImpactDimension`'s real, currently-active weight in the business score calculation."""

    dimension: str
    weight: float


class ImpactLevelPointsItem(BaseModel):
    """One `ImpactLevel`'s real, currently-active point value used when computing the weighted business score."""

    level: str
    points: int


class SeverityBandItem(BaseModel):
    """One (upper_bound_inclusive, severity) band boundary from the real, currently-active severity classification."""

    upper_bound_inclusive: int
    level: str


class BusinessImpactConfigurationResponse(BaseModel):
    """
    Read-only snapshot of Business Impact's real, currently-active engine
    configuration (Step 7.X G-05) -- `weighting.DIMENSION_WEIGHTS`,
    `scoring.IMPACT_LEVEL_POINTS`, and `scoring.SEVERITY_BANDS`, read
    directly off the same module-level constants the engine itself uses.
    Read-only by construction: this schema backs a `GET`-only endpoint,
    nothing here is persisted, and no corresponding request schema
    exists to mutate any of these values.
    """

    dimension_weights: List[DimensionWeightItem]
    impact_level_points: List[ImpactLevelPointsItem]
    severity_bands: List[SeverityBandItem]
