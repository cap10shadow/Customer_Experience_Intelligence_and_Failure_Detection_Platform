import httpx

from backend.services.copilot_service.app.core.config import settings
from backend.services.copilot_service.app.core.downstream import ToolError, get_json
from backend.services.copilot_service.app.schemas.copilot import EvidenceReference
from backend.services.copilot_service.app.schemas.tools import (
    AnalyticsToolInput,
    AnalyticsToolResult,
    CategoryTrendPoint,
    RegionTrendPoint,
    SentimentTrendPoint,
    UrgencyTrendPoint,
    VolumeTrendPoint,
)
from backend.services.copilot_service.app.services.tool_registry import ToolDefinition, register_tool

TOOL_NAME = "analytics_trends"

_BASE_URL = settings.ANOMALY_SERVICE_URL

_DIMENSION_PATHS = {
    "summary": "/api/v1/trends",
    "daily": "/api/v1/trends/daily",
    "categories": "/api/v1/trends/categories",
    "regions": "/api/v1/trends/regions",
    "sentiment": "/api/v1/trends/sentiment",
    "urgency": "/api/v1/trends/urgency",
}


async def run(client: httpx.AsyncClient, tool_input: AnalyticsToolInput) -> AnalyticsToolResult:
    """
    Endpoints (Phase 12 architecture §13.6/§9, verified against
    anomaly_service/app/api/trends.py): GET /trends[, /daily, /categories,
    /regions, /sentiment, /urgency], all `?days=` (1-365, matching the
    real `Query` bound exactly). There is no analytics_service -- these
    all belong to anomaly_service.

    AD-12: every one of these routes now requires `dataset_id` (trend data
    is dataset-scoped, same as anomalies/incidents). `tool_input.dataset_id`
    is never fabricated here -- it only arrives if the LLM copied it from
    the `filters.datasetId` hint `prompts.py` surfaces from the active
    dataset (workspace_context), the same "context text -> LLM-supplied
    argument" path `incident_id`/`recommendation_id` already use for the
    other tools. With no dataset selected, this tool reports that honestly
    instead of issuing a request guaranteed to 422.
    """
    path = _DIMENSION_PATHS.get(tool_input.dimension)
    if path is None:
        return AnalyticsToolResult(found=False, error=f"Unsupported dimension: {tool_input.dimension}.")

    if not tool_input.dataset_id:
        return AnalyticsToolResult(found=False, error="No dataset is selected; analytics trends require an active dataset.")

    days = max(1, min(tool_input.days, 365))

    try:
        payload = await get_json(
            client, f"{_BASE_URL}{path}", params={"days": days, "dataset_id": tool_input.dataset_id}
        )
    except ToolError as exc:
        return AnalyticsToolResult(found=False, error=exc.message)

    if payload is None:
        return AnalyticsToolResult(found=False)

    period = payload.get("period")
    result = AnalyticsToolResult(found=True, period=period)

    if tool_input.dimension == "summary":
        result.volume = [VolumeTrendPoint(**p) for p in payload.get("complaint_volume", [])]
        result.categories = [CategoryTrendPoint(**p) for p in payload.get("categories", [])]
        result.regions = [RegionTrendPoint(**p) for p in payload.get("regions", [])]
        result.sentiment = [SentimentTrendPoint(**p) for p in payload.get("sentiment", [])]
        result.urgency = [UrgencyTrendPoint(**p) for p in payload.get("urgency", [])]
    elif tool_input.dimension == "daily":
        result.volume = [VolumeTrendPoint(**p) for p in payload.get("complaint_volume", [])]
    elif tool_input.dimension == "categories":
        result.categories = [CategoryTrendPoint(**p) for p in payload.get("categories", [])]
    elif tool_input.dimension == "regions":
        result.regions = [RegionTrendPoint(**p) for p in payload.get("regions", [])]
    elif tool_input.dimension == "sentiment":
        result.sentiment = [SentimentTrendPoint(**p) for p in payload.get("sentiment", [])]
    elif tool_input.dimension == "urgency":
        result.urgency = [UrgencyTrendPoint(**p) for p in payload.get("urgency", [])]

    if period is not None:
        result.evidence_references = [
            EvidenceReference(
                evidence_id=f"trend:{tool_input.dimension}:{period}",
                source_type="trend",
                source_id=period,
                authority="anomaly_service",
                timestamp=None,
            )
        ]

    return result


register_tool(
    ToolDefinition(
        name=TOOL_NAME,
        description=(
            "Answer volume/category/region/sentiment/urgency complaint-trend questions over a bounded "
            "trailing time window. Requires dataset_id -- copy it verbatim from the conversation context's "
            "filters.datasetId when present; if there is none, do not call this tool, treat it as unavailable."
        ),
        input_model=AnalyticsToolInput,
        output_model=AnalyticsToolResult,
        executor=run,
    )
)
