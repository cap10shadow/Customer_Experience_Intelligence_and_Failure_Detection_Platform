from backend.shared.constants.enums.base import BaseStringEnum

class ComplaintStatus(BaseStringEnum):
    """Represents the operational lifecycle state of complaints."""
    PENDING = "pending"
    INGESTED = "ingested"
    NORMALIZED = "normalized"
    ENRICHED = "enriched"
    ANALYZED = "analyzed"
    CORRELATED = "correlated"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class SourceChannel(BaseStringEnum):
    """Represents the operational source of customer complaints."""
    EMAIL = "email"
    CHAT = "chat"
    SUPPORT_TICKET = "support_ticket"
    SOCIAL_MEDIA = "social_media"
    MOBILE_APP = "mobile_app"
    WEBSITE_FORM = "website_form"
    CALL_CENTER = "call_center"
    MARKETPLACE = "marketplace"
    INTERNAL_SYSTEM = "internal_system"


class CustomerSegment(BaseStringEnum):
    """Represents operational customer categorization."""
    INDIVIDUAL = "individual"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    PARTNER = "partner"
    RESELLER = "reseller"
    UNKNOWN = "unknown"


class CustomerType(BaseStringEnum):
    """Represents relationship type between customer and organization."""
    NEW_CUSTOMER = "new_customer"
    EXISTING_CUSTOMER = "existing_customer"
    HIGH_VALUE_CUSTOMER = "high_value_customer"
    AT_RISK_CUSTOMER = "at_risk_customer"
    CHURNED_CUSTOMER = "churned_customer"
    UNIDENTIFIED = "unidentified"


class IssueCategory(BaseStringEnum):
    """Represents high-level complaint classification."""
    DELIVERY_ISSUE = "delivery_issue"
    PAYMENT_ISSUE = "payment_issue"
    PRODUCT_ISSUE = "product_issue"
    SUPPORT_ISSUE = "support_issue"
    TECHNICAL_ISSUE = "technical_issue"
    ACCOUNT_ISSUE = "account_issue"
    REFUND_ISSUE = "refund_issue"
    SUBSCRIPTION_ISSUE = "subscription_issue"
    SERVICE_DELAY = "service_delay"
    OPERATIONAL_FAILURE = "operational_failure"


class SentimentLabel(BaseStringEnum):
    """Represents customer sentiment classification."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    HIGHLY_NEGATIVE = "highly_negative"


class UrgencyLabel(BaseStringEnum):
    """Represents operational urgency classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
