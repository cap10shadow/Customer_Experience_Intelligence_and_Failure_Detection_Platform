from backend.shared.constants.enums.base import BaseStringEnum

class OperationalArea(BaseStringEnum):
    """Represents the operational business domain affected by complaints."""
    LOGISTICS = "logistics"
    PAYMENTS = "payments"
    CUSTOMER_SUPPORT = "customer_support"
    DELIVERY = "delivery"
    INVENTORY = "inventory"
    PRODUCT_QUALITY = "product_quality"
    RETURNS = "returns"
    ACCOUNT_MANAGEMENT = "account_management"
    SUBSCRIPTION_SERVICES = "subscription_services"
    TECHNICAL_PLATFORM = "technical_platform"


class ServiceType(BaseStringEnum):
    """Represents the affected operational service category."""
    FULFILLMENT = "fulfillment"
    PAYMENT_PROCESSING = "payment_processing"
    CUSTOMER_SERVICE = "customer_service"
    DELIVERY_OPERATIONS = "delivery_operations"
    DIGITAL_SERVICES = "digital_services"
    SUBSCRIPTION_MANAGEMENT = "subscription_management"
    PLATFORM_OPERATIONS = "platform_operations"


class EscalationPriority(BaseStringEnum):
    """Represents business escalation urgency."""
    ROUTINE = "routine"
    ELEVATED = "elevated"
    URGENT = "urgent"
    EXECUTIVE_ATTENTION = "executive_attention"
