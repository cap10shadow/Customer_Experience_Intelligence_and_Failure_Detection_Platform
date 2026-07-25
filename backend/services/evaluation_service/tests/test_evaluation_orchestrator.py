import asyncio

import pytest

from backend.services.evaluation_service.app.application.evaluation_context_mapper import EvaluationContextMapper
from backend.services.evaluation_service.app.application.evaluation_orchestrator import EvaluationOrchestrator
from backend.services.evaluation_service.app.domain.confidence_analyzer import ConfidenceAnalyzer
from backend.services.evaluation_service.app.domain.evaluation import Evaluation
from backend.services.evaluation_service.app.domain.evaluation_builder import EvaluationBuilder
from backend.services.evaluation_service.app.domain.explainability_engine import ExplainabilityEngine
from backend.services.evaluation_service.app.domain.quality_engine import QualityEngine
from backend.services.evaluation_service.app.domain.validation_summary import ValidationSummary
from backend.services.evaluation_service.app.domain.validation_engine import ValidationEngine


def _orchestrator() -> EvaluationOrchestrator:
    return EvaluationOrchestrator(
        validation_engine=ValidationEngine(),
        quality_engine=QualityEngine(),
        explainability_engine=ExplainabilityEngine(),
        confidence_analyzer=ConfidenceAnalyzer(),
        evaluation_builder=EvaluationBuilder(),
    )


@pytest.mark.anyio
async def test_successful_execution_produces_a_complete_evaluation(make_completed_intelligence):
    result = await _orchestrator().evaluate(make_completed_intelligence())

    assert isinstance(result, Evaluation)
    assert result.incident_id == "INC-TEST0001"
    assert result.validation_summary.is_valid is True
    assert result.quality_assessment.quality_score >= 0
    assert result.explainability_assessment.explainability_score >= 0
    assert result.confidence_summary.average_confidence >= 0


@pytest.mark.anyio
async def test_validation_failure_returns_validation_summary_not_an_evaluation(make_completed_intelligence):
    completed_intelligence = make_completed_intelligence(incident_id="")

    result = await _orchestrator().evaluate(completed_intelligence)

    assert isinstance(result, ValidationSummary)
    assert not isinstance(result, Evaluation)
    assert result.is_valid is False
    assert len(result.reasons) > 0


@pytest.mark.anyio
async def test_validation_failure_never_runs_quality_or_explainability_engines(make_completed_intelligence):
    calls = []

    class _SpyQualityEngine(QualityEngine):
        def evaluate(self, completed_intelligence):
            calls.append("quality")
            return super().evaluate(completed_intelligence)

    class _SpyExplainabilityEngine(ExplainabilityEngine):
        def evaluate(self, completed_intelligence):
            calls.append("explainability")
            return super().evaluate(completed_intelligence)

    orchestrator = EvaluationOrchestrator(
        validation_engine=ValidationEngine(),
        quality_engine=_SpyQualityEngine(),
        explainability_engine=_SpyExplainabilityEngine(),
        confidence_analyzer=ConfidenceAnalyzer(),
        evaluation_builder=EvaluationBuilder(),
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
    parallelize them the moment either becomes I/O-bound, e.g. Phase 8
    Step 2's repository calls).
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
    completed_intelligence = make_completed_intelligence()
    orchestrator = _orchestrator()

    first = await orchestrator.evaluate(completed_intelligence)
    second = await orchestrator.evaluate(completed_intelligence)

    assert first == second


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

    orchestrator = EvaluationOrchestrator(
        validation_engine=ValidationEngine(),
        quality_engine=QualityEngine(),
        explainability_engine=ExplainabilityEngine(),
        confidence_analyzer=ConfidenceAnalyzer(),
        evaluation_builder=EvaluationBuilder(),
    )
    result = await orchestrator.evaluate(completed_intelligence)

    assert isinstance(result, Evaluation)
    assert result.validation_summary == expected_validation
    assert result.quality_assessment == expected_quality
    assert result.explainability_assessment == expected_explainability
    assert result.confidence_summary == expected_confidence
