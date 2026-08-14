"""
Evaluation execution flow (Batch 6 implementation prompt §10):

    Evaluation Dataset -> Evaluation Runner -> Copilot Invocation ->
    Observed Response -> Evaluation Checks -> Per-case Result ->
    Aggregate Evaluation Result

`run_evaluation` calls `conversation_service.handle_persisted_query` --
the exact same function `api/copilot.py` calls in production -- never a
second orchestration/conversation implementation (§12). Persistence,
history-loading, and conversation-identity resolution are therefore all
exercised for real, through the real Batch 4 path, not re-implemented
here.
"""

import uuid
from typing import Dict, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.copilot_service.app.evaluation.checks import ALL_CHECKS
from backend.services.copilot_service.app.evaluation.dataset import EvaluationCase, EvaluationDataset
from backend.services.copilot_service.app.evaluation.providers import ScriptedLLMProvider
from backend.services.copilot_service.app.evaluation.results import CaseResult, EvaluationReport
from backend.services.copilot_service.app.schemas.copilot import CopilotQueryRequest, WorkspaceContext
from backend.services.copilot_service.app.services.conversation_service import handle_persisted_query
from backend.services.copilot_service.app.services.orchestrator.llm_provider import LLMProvider, get_llm_provider


def _resolve_provider(case: EvaluationCase) -> LLMProvider:
    if case.scripted_decisions is not None:
        return ScriptedLLMProvider(case.scripted_decisions)
    # No script -> exercise whatever provider this environment actually
    # has configured (§9: never fabricate a "real LLM" result -- if none
    # is configured, this legitimately resolves to `NullLLMProvider`, and
    # the report says so honestly via `provider_used`).
    return get_llm_provider()


def _provider_label(provider: LLMProvider, was_scripted: bool) -> str:
    if was_scripted:
        return "scripted"
    return type(provider).__name__


async def run_evaluation(
    dataset: EvaluationDataset, *, client: httpx.AsyncClient, session: AsyncSession
) -> EvaluationReport:
    conversation_ids_by_case: Dict[str, str] = {}
    report = EvaluationReport()

    for case in dataset.cases:
        provider = _resolve_provider(case)
        provider_label = _provider_label(provider, case.scripted_decisions is not None)

        try:
            conversation_id = _resolve_conversation_id(case, conversation_ids_by_case)
            request = CopilotQueryRequest(
                message=case.message,
                conversation_id=conversation_id,
                workspace_context=WorkspaceContext(**case.workspace_context) if case.workspace_context else None,
            )
            response = await handle_persisted_query(
                request,
                client=client,
                request_id=f"eval-{case.case_id}-{uuid.uuid4()}",
                session=session,
                llm_provider=provider,
            )
        except Exception as exc:  # noqa: BLE001 -- a case-level failure must never abort the whole run; report it and continue.
            report.cases.append(
                CaseResult(case_id=case.case_id, category=case.category, provider_used=provider_label, error=str(exc))
            )
            continue

        conversation_ids_by_case[case.case_id] = response.conversation_id

        case_result = CaseResult(case_id=case.case_id, category=case.category, provider_used=provider_label)
        for check in ALL_CHECKS:
            case_result.dimension_results.append(check(case, response))
        report.cases.append(case_result)

    return report


def _resolve_conversation_id(case: EvaluationCase, conversation_ids_by_case: Dict[str, str]) -> Optional[str]:
    if case.conversation_id_from_case is None:
        return None
    try:
        return conversation_ids_by_case[case.conversation_id_from_case]
    except KeyError as exc:
        raise DatasetReferenceError(
            f"Case '{case.case_id}' references conversation_id_from_case='{case.conversation_id_from_case}', "
            "which has not run yet or does not exist -- dataset cases must be ordered so a referenced case runs first."
        ) from exc


class DatasetReferenceError(Exception):
    """Raised when a case references another case (for conversation continuity) that hasn't produced a result yet."""
