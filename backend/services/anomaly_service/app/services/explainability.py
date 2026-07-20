from typing import Optional

from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType


def describe_entity(entity_type: str, entity_value: Optional[str]) -> str:
    return entity_type if entity_value is None else f"{entity_type}={entity_value}"


def build_explanation(
    type_: AnomalyType,
    entity_type: str,
    entity_value: Optional[str],
    baseline_value: float,
    current_value: float,
    percentage_change: Optional[float],
    severity: AnomalySeverity,
) -> str:
    """
    Builds the human-readable explanation stored on every anomaly. Every
    value shown here is a raw input already computed by the detector — no
    hidden calculations happen inside this function.
    """
    entity_desc = describe_entity(entity_type, entity_value)
    change_desc = "undefined (baseline was zero)" if percentage_change is None else f"{percentage_change:+.1f}%"

    return (
        f"{type_.value} detected for {entity_desc}: "
        f"baseline={baseline_value:g}, current={current_value:g}, "
        f"change={change_desc}, severity={severity.value}."
    )


def build_detected_reason(explanation: str) -> str:
    return f"New anomaly detected. {explanation}"


def build_updated_reason(old_severity: AnomalySeverity, new_severity: AnomalySeverity, explanation: str) -> str:
    return f"Severity changed from {old_severity.value} to {new_severity.value}. {explanation}"


def build_resolved_reason(entity_type: str, entity_value: Optional[str]) -> str:
    entity_desc = describe_entity(entity_type, entity_value)
    return f"No longer detected for {entity_desc} in the current window; values returned to baseline."
