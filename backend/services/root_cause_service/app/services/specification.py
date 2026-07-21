from abc import ABC, abstractmethod

from backend.services.root_cause_service.app.domain.incident import Incident
from backend.shared.constants.enums.anomaly import AnomalySeverity, AnomalyType
from backend.shared.constants.enums.complaint import IssueCategory, UrgencyLabel


class Specification(ABC):
    """
    Base for a single, reusable, composable condition over an Incident.

    Each concrete specification evaluates exactly one condition. Rules
    combine them with `&` (and), `|` (or), and `~` (not) instead of nested
    if/else chains.
    """

    @abstractmethod
    def is_satisfied_by(self, incident: Incident) -> bool:
        raise NotImplementedError

    def __and__(self, other: "Specification") -> "Specification":
        return _AndSpecification(self, other)

    def __or__(self, other: "Specification") -> "Specification":
        return _OrSpecification(self, other)

    def __invert__(self) -> "Specification":
        return _NotSpecification(self)


class _AndSpecification(Specification):
    def __init__(self, left: Specification, right: Specification) -> None:
        self._left = left
        self._right = right

    def is_satisfied_by(self, incident: Incident) -> bool:
        return self._left.is_satisfied_by(incident) and self._right.is_satisfied_by(incident)


class _OrSpecification(Specification):
    def __init__(self, left: Specification, right: Specification) -> None:
        self._left = left
        self._right = right

    def is_satisfied_by(self, incident: Incident) -> bool:
        return self._left.is_satisfied_by(incident) or self._right.is_satisfied_by(incident)


class _NotSpecification(Specification):
    def __init__(self, spec: Specification) -> None:
        self._spec = spec

    def is_satisfied_by(self, incident: Incident) -> bool:
        return not self._spec.is_satisfied_by(incident)


# ----------------------------------------------------------------------
# Category specifications
# ----------------------------------------------------------------------

class CategorySpecification(Specification):
    """Satisfied when the incident includes the given issue category."""

    def __init__(self, category: IssueCategory) -> None:
        self._category = category

    def is_satisfied_by(self, incident: Incident) -> bool:
        return self._category in incident.categories


class BillingCategorySpecification(CategorySpecification):
    """Satisfied when the incident includes payment/billing-related complaints."""

    def __init__(self) -> None:
        super().__init__(IssueCategory.PAYMENT_ISSUE)


class LogisticsCategorySpecification(Specification):
    """Satisfied when the incident includes delivery or service-delay complaints."""

    def is_satisfied_by(self, incident: Incident) -> bool:
        return IssueCategory.DELIVERY_ISSUE in incident.categories or IssueCategory.SERVICE_DELAY in incident.categories


class OutageCategorySpecification(Specification):
    """Satisfied when the incident includes operational-failure or technical complaints."""

    def is_satisfied_by(self, incident: Incident) -> bool:
        return IssueCategory.OPERATIONAL_FAILURE in incident.categories or IssueCategory.TECHNICAL_ISSUE in incident.categories


class InventoryCategorySpecification(Specification):
    """Satisfied when the incident includes product/inventory-related complaints."""

    def is_satisfied_by(self, incident: Incident) -> bool:
        return IssueCategory.PRODUCT_ISSUE in incident.categories


class SupportCategorySpecification(Specification):
    """Satisfied when the incident includes customer-support complaints."""

    def is_satisfied_by(self, incident: Incident) -> bool:
        return IssueCategory.SUPPORT_ISSUE in incident.categories


# ----------------------------------------------------------------------
# Severity / urgency / sentiment specifications
# ----------------------------------------------------------------------

class CriticalSeveritySpecification(Specification):
    """Satisfied when the incident's severity is CRITICAL."""

    def is_satisfied_by(self, incident: Incident) -> bool:
        return incident.severity == AnomalySeverity.CRITICAL


class HighUrgencySpecification(Specification):
    """Satisfied when the incident includes a HIGH or CRITICAL urgency signal."""

    def is_satisfied_by(self, incident: Incident) -> bool:
        return UrgencyLabel.HIGH in incident.urgency_levels or UrgencyLabel.CRITICAL in incident.urgency_levels


class NegativeSentimentSpecification(Specification):
    """
    Satisfied when the incident includes a sentiment-deterioration signal.

    SENTIMENT_SHIFT anomalies are only ever raised on decline (Phase 5 Step
    2's SentimentDetector is decline-only), so its mere presence already
    implies negative sentiment — no separate label is needed.
    """

    def is_satisfied_by(self, incident: Incident) -> bool:
        return AnomalyType.SENTIMENT_SHIFT in incident.anomaly_types


# ----------------------------------------------------------------------
# Supporting-signal specifications
# ----------------------------------------------------------------------

class RegionalSpikeSpecification(Specification):
    """Satisfied when the incident includes a regional complaint spike."""

    def is_satisfied_by(self, incident: Incident) -> bool:
        return AnomalyType.REGIONAL_SPIKE in incident.anomaly_types


class VolumeSpikeSpecification(Specification):
    """Satisfied when the incident includes an overall complaint volume spike."""

    def is_satisfied_by(self, incident: Incident) -> bool:
        return AnomalyType.COMPLAINT_SPIKE in incident.anomaly_types
