from fastapi import APIRouter

from backend.services.business_impact_service.app.schemas.configuration import (
    BusinessImpactConfigurationResponse,
    DimensionWeightItem,
    ImpactLevelPointsItem,
    SeverityBandItem,
)
from backend.services.business_impact_service.app.services.scoring import IMPACT_LEVEL_POINTS, SEVERITY_BANDS
from backend.services.business_impact_service.app.services.weighting import DIMENSION_WEIGHTS

router = APIRouter(prefix="/configuration", tags=["configuration"])


@router.get("/business-impact", response_model=BusinessImpactConfigurationResponse)
async def get_business_impact_configuration() -> BusinessImpactConfigurationResponse:
    """
    Read-only visibility into Business Impact's real, currently-active
    engine configuration (Step 7.X G-05). Reads the same module-level
    constants (`weighting.DIMENSION_WEIGHTS`, `scoring.IMPACT_LEVEL_POINTS`,
    `scoring.SEVERITY_BANDS`) the frozen scoring engine itself uses --
    never a copy, so the displayed value can never drift from real engine
    behavior. No persistence, no mutation route: this module has no
    corresponding POST/PUT/PATCH, and nothing here changes engine
    behavior or touches `scoring.py`/`weighting.py`'s own definitions.
    """
    return BusinessImpactConfigurationResponse(
        dimension_weights=[
            DimensionWeightItem(dimension=dimension.value, weight=weight)
            for dimension, weight in DIMENSION_WEIGHTS.items()
        ],
        impact_level_points=[
            ImpactLevelPointsItem(level=level.value, points=points) for level, points in IMPACT_LEVEL_POINTS.items()
        ],
        severity_bands=[
            SeverityBandItem(upper_bound_inclusive=upper_bound, level=level.value)
            for upper_bound, level in SEVERITY_BANDS
        ],
    )
