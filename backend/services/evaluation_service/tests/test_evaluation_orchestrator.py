import asyncio
import uuid

import pytest

from backend.services.evaluation_service.app.application.evaluation_context_mapper import EvaluationContextMapper
from backend.services.evaluation_service.app.application.evaluation_orchestrator import EvaluationOrchestrator
from backend.services.evaluation_service.app.domain.confidence_analyzer import ConfidenceAnalyzer
from backend.services.evaluation_service.app.domain.evaluation_builder import EvaluationBuilder
from backend.services.evaluation_service.app.domain.evaluation_record import EvaluationRecord
from backend.services.evaluation_service.app.domain.explainability_engine import ExplainabilityEngine
from backend.services.evaluation_service.app.domain.quality_engine import QualityEngine
from backend.services.evaluation_service.app.domain.validation_engine import ValidationEngine
from backend.services.evaluation_service.app.domain.validation_summary import ValidationSummary
from backend.services.evaluation_service.tests.fakes import FakeEvaluationRepository


def _orchestrator(repository=None) -> EvaluationOrchestrator:
    return EvaluationOrchestrator(
        validation_engine=ValidationEngine(),
        quality_engine=QualityEngine(),
        explainability_engine=ExplainabilityEngine(),
        confidence_analyzer=ConfidenceAnalyzer(),
        evaluation_builder=EvaluationBuilder(),
        repository=repository if repository is not None else FakeEvaluationRepository(),
    )


@pytest.mark.anyio
async def test_successful_execution_produces_a_complete_persisted_evaluation(make_completed_intelligence):
    result = await _orchestrator().evaluate(make_completed_intelligence())

    assert isinstance(result, EvaluationRecord)
    assert result.evaluation_id is not None
    assert result.evaluation.incident_id == "INC-TEST0001"
    assert result.evaluation.validation_summary.is_valid is True
    assert result.evaluation.quality_assessment.quality_score >= 0
    assert result.evaluation.explainability_assessment.explainability_score >= 0
    assert result.evaluation.confidence_summary.average_confidence >= 0


@pytest.mark.anyio
async def test_successful_execution_persists_via_the_repository(make_completed_intelligence):
    repository = FakeEvaluationRepository()
    orchestrator = _orchestrator(repository)

    result = await orchestrator.evaluate(make_completed_intelligence())

    assert repository.by_id[result.evaluation_id] is result


@pytest.mark.anyio
async def test_validation_failure_returns_validation_summary_not_an_evaluation(make_completed_intelligence):
    completed_intelligence = make_completed_intelligence(incident_id="")

    result = await _orchestrator().evaluate(completed_intelligence)

    assert isinstance(result, ValidationSummary)
    assert not isinstance(result, EvaluationRecord)
    assert result.is_valid is False
    assert len(result.reasons) > 0


@pytest.mark.anyio
async def test_validation_failure_never_persists_anything(make_completed_intelligence):
    repository = FakeEvaluationRepository()
    orchestrator = _orchestrator(repository)

    await orchestrator.evaluate(make_completed_intelligence(incident_id=""))

    assert repository.by_id == {}


@pytest.mark.anyio
async def test_validation_failure_never_runs_quality_or_explainability_engines(make_completed_intelligence):
    calls = []

    class _SpyQualityEngine(QualityEngine):
        def evaluate(self, context):
            calls.append("quality")
            return super().evaluate(context)

    class _SpyExplainabilityEngine(ExplainabilityEngine):
        def evaluate(self, context):
            calls.append("explainability")
            return super().evaluate(context)

    orchestrator = EvaluationOrchestrator(
        validation_engine=ValidationEngine(),
        quality_engine=_SpyQualityEngine(),
        explainability_engine=_SpyExplainabilityEngine(),
        confidence_analyzer=ConfidenceAnalyzer(),
        evaluation_builder=EvaluationBuilder(),
        repository=FakeEvaluationRepository(),
    )

    result = await orchestrator.evaluate(make_completed_intelligence(incident_id=""))

    assert isinstance(result, ValidationSummary)
    assert calls == []


@pytest.mark.anyio
async def test_orchestrator_uses_asyncio_gather_for_parallel_stage():
    """Structural check: the orchestrator's parallel stage is implemented with asyncio.gather, per the approved design."""
    import inspect

    source = inspect.getsource(EvaluationOrchestrator.evaluate)
    assert "asyncio.gather" in source


@pytest.mark.anyio
async def test_quality_and_explainability_wrapper_coroutines_are_independently_awaitable(make_completed_intelligence):
    """
    QualityEngine and ExplainabilityEngine depend on nothing but the same
    DomainEvaluationContext, and neither wrapper coroutine awaits the other
    -- they are genuinely independent tasks that `asyncio.gather` schedules
    together (both engines are pure, synchronous, and CPU-bound today, so
    there is no I/O to interleave yet; the orchestration is shaped to
    parallelize them the moment either becomes I/O-bound, e.g. a future
    repository-backed engine).
    """
    orchestrator = _orchestrator()
    context = EvaluationContextMapper.to_domain(make_completed_intelligence())

    quality_task = asyncio.ensure_future(orchestrator._run_quality_engine(context))
    explainability_task = asyncio.ensure_future(orchestrator._run_explainability_engine(context))

    quality_result, explainability_result = await asyncio.gather(quality_task, explainability_task)

    assert quality_result == QualityEngine().evaluate(context)
    assert explainability_result == ExplainabilityEngine().evaluate(context)


@pytest.mark.anyio
async def test_is_deterministic_across_repeated_calls(make_completed_intelligence):
    """
    Every call persists a new, independent record (its own evaluation_id,
    created_at, and lineage-chained previous_evaluation_id) -- by design,
    per the append-only architecture. Determinism is verified on the
    business fields the (frozen) Step 1 engines actually compute, not on
    persistence identity.
    """
    completed_intelligence = make_completed_intelligence()
    orchestrator = _orchestrator()

    first = await orchestrator.evaluate(completed_intelligence)
    second = await orchestrator.evaluate(completed_intelligence)

    assert first.evaluation_id != second.evaluation_id
    assert first.evaluation.validation_summary == second.evaluation.validation_summary
    assert first.evaluation.quality_assessment == second.evaluation.quality_assessment
    assert first.evaluation.explainability_assessment == second.evaluation.explainability_assessment
    assert first.evaluation.confidence_summary == second.evaluation.confidence_summary
    assert first.evaluation.metadata.evaluation_version == second.evaluation.metadata.evaluation_version


@pytest.mark.anyio
async def test_second_evaluation_for_the_same_incident_links_to_the_first(make_completed_intelligence):
    completed_intelligence = make_completed_intelligence()
    orchestrator = _orchestrator()

    first = await orchestrator.evaluate(completed_intelligence)
    second = await orchestrator.evaluate(completed_intelligence)

    assert first.evaluation.metadata.previous_evaluation_id is None
    assert second.evaluation.metadata.previous_evaluation_id == str(first.evaluation_id)


@pytest.mark.anyio
async def test_evaluate_forwards_lineage_identifiers_to_the_repository(make_completed_intelligence):
    """
    Phase 8 Step 3: event_id/root_cause_id/business_impact_id are threaded
    through verbatim to EvaluationRepository.save() -- the orchestrator
    never derives, validates, or interprets them.
    """
    repository = FakeEvaluationRepository()
    orchestrator = _orchestrator(repository)
    event_id = uuid.uuid4()
    root_cause_id = uuid.uuid4()
    business_impact_id = uuid.uuid4()

    result = await orchestrator.evaluate(
        make_completed_intelligence(),
        event_id=event_id,
        root_cause_id=root_cause_id,
        business_impact_id=business_impact_id,
    )

    assert isinstance(result, EvaluationRecord)
    assert result.event_id == event_id
    assert result.root_cause_id == root_cause_id
    assert result.business_impact_id == business_impact_id


@pytest.mark.anyio
async def test_evaluate_defaults_lineage_identifiers_to_none(make_completed_intelligence):
    """Omitting event_id/root_cause_id/business_impact_id preserves Step 2's exact prior behavior."""
    result = await _orchestrator().evaluate(make_completed_intelligence())

    assert isinstance(result, EvaluationRecord)
    assert result.event_id is None
    assert result.root_cause_id is None
    assert result.business_impact_id is None


@pytest.mark.anyio
async def test_orchestrator_contains_no_business_rules_of_its_own(make_completed_intelligence):
    """
    The orchestrator must not duplicate scoring/validation logic: running
    the same input through the orchestrator and through the engines
    directly must produce identical sub-results.
    """
    completed_intelligence = make_completed_intelligence()
    context = EvaluationContextMapper.to_domain(completed_intelligence)

    validation_engine = ValidationEngine()
    quality_engine = QualityEngine()
    explainability_engine = ExplainabilityEngine()
    confidence_analyzer = ConfidenceAnalyzer()

    expected_validation = validation_engine.validate(context)
    expected_quality = quality_engine.evaluate(context)
    expected_explainability = explainability_engine.evaluate(context)
    expected_confidence = confidence_analyzer.summarize(context)

    orchestrator = _orchestrator()
    result = await orchestrator.evaluate(completed_intelligence)

    assert isinstance(result, EvaluationRecord)
    assert result.evaluation.validation_summary == expected_validation
    assert result.evaluation.quality_assessment == expected_quality
    assert result.evaluation.explainability_assessment == expected_explainability
    assert result.evaluation.confidence_summary == expected_confidence
