from backend.shared.constants.enums.base import BaseStringEnum


class RootCause(BaseStringEnum):
    """
    Represents the deterministic root-cause classifications the Root Cause
    Rule Engine can assign to an Incident. UNKNOWN is the deterministic
    fallback when no registered rule matches.
    """
    PAYMENT_GATEWAY_FAILURE = "payment_gateway_failure"
    LOGISTICS_DELAY = "logistics_delay"
    SERVICE_OUTAGE = "service_outage"
    AUTHENTICATION_FAILURE = "authentication_failure"
    INVENTORY_SHORTAGE = "inventory_shortage"
    CUSTOMER_SUPPORT_DELAY = "customer_support_delay"
    UNKNOWN = "unknown"
