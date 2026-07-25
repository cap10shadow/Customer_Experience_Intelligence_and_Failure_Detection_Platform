import ast
from pathlib import Path

from backend.services.evaluation_service.app.application.evaluation_context_mapper import EvaluationContextMapper
from backend.services.evaluation_service.app.domain.domain_evaluation_context import DomainEvaluationContext

DOMAIN_DIR = Path(__file__).resolve().parent.parent / "app" / "domain"


def test_maps_every_field_verbatim(make_completed_intelligence):
    completed_intelligence = make_completed_intelligence()

    context = EvaluationContextMapper.to_domain(completed_intelligence)

    assert isinstance(context, DomainEvaluationContext)
    assert context.incident_id == completed_intelligence.incident_id
    assert context.root_cause == completed_intelligence.root_cause
    assert context.root_cause_confidence_score == completed_intelligence.root_cause_confidence_score
    assert context.root_cause_explanation == completed_intelligence.root_cause_explanation
    assert context.root_cause_evidence_count == completed_intelligence.root_cause_evidence_count
    assert context.business_impact_overall_score == completed_intelligence.business_impact_overall_score
    assert context.business_impact_overall_severity == completed_intelligence.business_impact_overall_severity
    assert context.business_impact_business_priority == completed_intelligence.business_impact_business_priority
    assert context.business_impact_confidence == completed_intelligence.business_impact_confidence
    assert context.business_impact_explanation == completed_intelligence.business_impact_explanation


def test_is_deterministic(make_completed_intelligence):
    completed_intelligence = make_completed_intelligence()

    first = EvaluationContextMapper.to_domain(completed_intelligence)
    second = EvaluationContextMapper.to_domain(completed_intelligence)

    assert first == second


def test_no_domain_module_imports_the_application_layer():
    """
    Structural proof of the Clean Architecture refinement: nothing under
    app/domain/ may import from app/application/ -- the dependency arrow
    only ever points the other way (EvaluationContextMapper, in
    app/application/, is the only component allowed to import both
    CompletedIntelligence and DomainEvaluationContext).
    """
    offending_files = []

    for path in sorted(DOMAIN_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and "app.application" in node.module:
                offending_files.append(str(path))

    assert offending_files == []
