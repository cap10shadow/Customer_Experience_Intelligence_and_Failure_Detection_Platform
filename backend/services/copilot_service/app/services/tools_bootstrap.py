"""
Imports every Batch 2 tool module for its side effect (each module calls
`register_tool(...)` at import time -- see `tool_registry.py`). This is
the one explicit place that knows the full set of registered tools;
Batch 3's orchestrator (and this batch's own registry tests) import this
module rather than each tool module individually.
"""

from backend.services.copilot_service.app.services import (  # noqa: F401
    administration_tool,
    analytics_tool,
    business_impact_tool,
    investigation_tool,
    recommendation_decision_status_tool,
    recommendation_tool,
    root_cause_tool,
)
