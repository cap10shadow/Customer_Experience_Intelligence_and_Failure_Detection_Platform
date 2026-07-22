from dataclasses import dataclass
from typing import Any, Mapping, Optional

from backend.services.business_impact_service.app.domain.impact_dimension import ImpactDimension
from backend.services.business_impact_service.app.domain.impact_level import ImpactLevel


@dataclass(frozen=True)
class ImpactEvaluation:
    """
    A single ImpactRule's verdict for one business-impact dimension.

    Every rule returns one of these instead of a bare ImpactLevel, so the
    Explanation Engine never needs hidden coupling back into rule logic --
    the reason was already decided by the rule and is simply carried here.
    `metadata` is populated only when a rule has genuinely useful
    supporting figures to attach (e.g. a raw count the reason references).
    """

    impact_dimension: ImpactDimension
    impact_level: ImpactLevel
    reason: str
    metadata: Optional[Mapping[str, Any]] = None
