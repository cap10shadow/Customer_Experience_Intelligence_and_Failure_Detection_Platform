import asyncio
from typing import Union

from backend.services.evaluation_service.app.application.completed_intelligence import CompletedIntelligence
from backend.services.evaluation_service.app.application.evaluation_context_mapper import EvaluationContextMapper
from backend.services.evaluation_service.app.domain.confidence_analyzer import ConfidenceAnalyzer
from backend.services.evaluation_service.app.domain.domain_evaluation_context import DomainEvaluationContext
from backend.services.evaluation_service.app.domain.evaluation import Evaluation
from backend.services.evaluation_service.app.domain.evaluation_builder import EvaluationBuilder
from backend.services.evaluation_service.app.domain.explainability_assessment import ExplainabilityAssessment
from backend.services.evaluation_service.app.domain.explainability_engine import ExplainabilityEngine
from backend.services.evaluation_service.app.domain.quality_assessment import QualityAssessment
from backend.services.evaluation_service.app.domain.quality_engine import QualityEngine
from backend.services.evaluation_service.app.domain.validation_engine import ValidationEngine
from backend.services.evaluation_service.app.domain.validation_summary import ValidationSummary


class EvaluationOrchestrator:
    """
    Evaluation Orchestrator

    Ownership:
    Owned by the Evaluation Service's application layer.

    Operational Purpose:
    Coordinates the Evaluation pipeline end to end: maps the incoming
    CompletedIntelligence DTO into a Domain-owned DomainEvaluationContext,
    then runs ValidationEngine, then -- only if validation succeeds --
    QualityEngine and ExplainabilityEngine in parallel, then
    ConfidenceAnalyzer, then EvaluationBuilder.

    Architectural Boundaries:
    - Orchestration only: this class contains no scoring, no thresholds, no
      business rules of any kind. Every decision (what counts as valid,
      what counts as high quality, what counts as explainable, how
      confidence is summarized, how the aggregate is assembled) belongs to
      the Domain-layer component responsible for it; this class only calls
      those components in the right order and passes data between them.
    - Owns the one boundary crossing between the Application and Domain
      layers: it is the only component that ever touches both
      CompletedIntelligence (Application) and DomainEvaluationContext
      (Domain), via EvaluationContextMapper. Every Domain-layer engine
      depends only on DomainEvaluationContext, never on the Application
      layer -- preserving Clean Architecture's dependency direction.
    - QualityEngine and ExplainabilityEngine are independent of each other
      (neither depends on the other's output) and are executed concurrently
      via `asyncio.gather`, reflecting that independence directly in the
      orchestration shape.
    - Depends only on the four engines and the builder, injected at
      construction time -- no dependency injection framework, no
      configuration, no I/O of any kind in Step 1.
    """

    def __init__(
        self,
        validation_engine: ValidationEngine,
        quality_engine: QualityEngine,
        explainability_engine: ExplainabilityEngine,
        confidence_analyzer: ConfidenceAnalyzer,
        evaluation_builder: EvaluationBuilder,
    ) -> None:
        self._validation_engine = validation_engine
        self._quality_engine = quality_engine
        self._explainability_engine = explainability_engine
        self._confidence_analyzer = confidence_analyzer
        self._evaluation_builder = evaluation_builder

    async def evaluate(self, completed_intelligence: CompletedIntelligence) -> Union[Evaluation, ValidationSummary]:
        """
        Runs the full Evaluation pipeline for one CompletedIntelligence
        snapshot. Returns the failed ValidationSummary directly if
        validation does not pass -- never an Evaluation in that case.
        """
        context = EvaluationContextMapper.to_domain(completed_intelligence)

        validation_summary = self._validation_engine.validate(context)
        if not validation_summary.is_valid:
            return validation_summary

        quality_assessment, explainability_assessment = await asyncio.gather(
            self._run_quality_engine(context),
            self._run_explainability_engine(context),
        )

        confidence_summary = self._confidence_analyzer.summarize(context)

        return self._evaluation_builder.build(
            incident_id=context.incident_id,
            validation_summary=validation_summary,
            quality_assessment=quality_assessment,
            explainability_assessment=explainability_assessment,
            confidence_summary=confidence_summary,
        )

    async def _run_quality_engine(self, context: DomainEvaluationContext) -> QualityAssessment:
        return self._quality_engine.evaluate(context)

    async def _run_explainability_engine(self, context: DomainEvaluationContext) -> ExplainabilityAssessment:
        return self._explainability_engine.evaluate(context)
