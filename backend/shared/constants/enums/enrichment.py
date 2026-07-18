from backend.shared.constants.enums.base import BaseStringEnum

class ProcessingStage(BaseStringEnum):
    """Represents internal intelligence processing progression."""
    RAW_INGESTION = "raw_ingestion"
    PREPROCESSING = "preprocessing"
    ENRICHMENT = "enrichment"
    ANOMALY_ANALYSIS = "anomaly_analysis"
    BUSINESS_EVALUATION = "business_evaluation"
    RECOMMENDATION_GENERATION = "recommendation_generation"
    COMPLETED = "completed"
