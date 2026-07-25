from dataclasses import dataclass

from backend.services.evaluation_service.app.domain.confidence_summary import ConfidenceSummary
from backend.services.evaluation_service.app.domain.evaluation_metadata import EvaluationMetadata
from backend.services.evaluation_service.app.domain.explainability_assessment import ExplainabilityAssessment
from backend.services.evaluation_service.app.domain.quality_assessment import QualityAssessment
from backend.services.evaluation_service.app.domain.validation_summary import ValidationSummary


@dataclass(frozen=True)
class Evaluation:
    """
    Evaluation Aggregate Root

    Ownership:
    Owned by the Evaluation Service.

    Operational Purpose:
    The Evaluation Service's sole output: an immutable, independent audit
    of one Incident's completed intelligence (Root Cause + Business
    Impact), composed of the ValidationSummary that gated its own
    construction, the QualityEngine's and ExplainabilityEngine's
    assessments, the ConfidenceAnalyzer's summary of pre-existing
    confidence values, and versioning/lineage metadata.

    Architectural Boundaries:
    - Only ever constructed by `EvaluationBuilder`, and only when the
      embedded `validation_summary.is_valid` is True -- a failed validation
      never produces an Evaluation (see EvaluationOrchestrator).
    - No `evaluation_id`: identity assignment is a persistence-layer
      concern, introduced in Phase 8 Step 2 -- the same precedent set by
      Phase 7 Step 1's `BusinessImpactAssessment`, which likewise carries no
      database identifier until its own Step 2 mapped it into an ORM entity.
    - Pure, in-memory, persistence-independent value object: no ORM fields,
      no timestamps, no database session ever touches this class.

    Explainability Philosophy:
    Every field here is a direct, unmodified copy of what the engine that
    produced it decided -- no additional calculation happens at aggregate
    construction time.
    """

    incident_id: str
    validation_summary: ValidationSummary
    quality_assessment: QualityAssessment
    explainability_assessment: ExplainabilityAssessment
    confidence_summary: ConfidenceSummary
    metadata: EvaluationMetadata
