from typing import Dict, List
from backend.shared.constants.enums.complaint import IssueCategory, SentimentLabel, UrgencyLabel

# -------------------------------------------------------------------
# Explainable NLP Constants
# These vocabularies drive the deterministic intelligence extraction.
# -------------------------------------------------------------------

SENTIMENT_KEYWORDS: Dict[SentimentLabel, List[str]] = {
    SentimentLabel.HIGHLY_NEGATIVE: [
        "lawsuit", "sue", "unacceptable", "disgusting", "terrible", "worst", "fraud", "scam", 
        "furious", "outraged", "stolen", "incompetent", "pathetic", "ruined", "threat"
    ],
    SentimentLabel.NEGATIVE: [
        "bad", "poor", "disappointed", "frustrated", "annoying", "broken", "delayed", 
        "failed", "slow", "unhelpful", "wrong", "error", "issue", "problem", "angry"
    ],
    SentimentLabel.POSITIVE: [
        "good", "great", "excellent", "amazing", "happy", "satisfied", "thanks", 
        "thank you", "appreciate", "helpful", "fast", "quick", "resolved", "love", "best"
    ],
    SentimentLabel.NEUTRAL: [
        "okay", "fine", "average", "normal", "expected", "standard"
    ]
}

URGENCY_KEYWORDS: Dict[UrgencyLabel, List[str]] = {
    UrgencyLabel.CRITICAL: [
        "lawsuit", "legal", "safety", "danger", "police", "media", "press", "injury", 
        "hospital", "breach", "leak", "hacked", "stolen", "immediately", "urgent"
    ],
    UrgencyLabel.HIGH: [
        "asap", "escalate", "unacceptable", "manager", "supervisor", "supervisor", 
        "blocked", "down", "offline", "crashed", "cancel", "refund now"
    ],
    UrgencyLabel.MEDIUM: [
        "soon", "waiting", "delay", "late", "missing", "broken", "not working"
    ],
    UrgencyLabel.LOW: [
        "whenever", "no rush", "feedback", "suggestion", "idea", "question", "inquiry"
    ]
}

ISSUE_CATEGORY_KEYWORDS: Dict[IssueCategory, List[str]] = {
    IssueCategory.DELIVERY_ISSUE: [
        "delivery", "shipping", "courier", "package", "arrived", "late", "lost", "tracking", "postage"
    ],
    IssueCategory.PAYMENT_ISSUE: [
        "payment", "charged", "billing", "invoice", "credit card", "declined", "double charge", "fee"
    ],
    IssueCategory.PRODUCT_ISSUE: [
        "product", "item", "quality", "broken", "damaged", "defective", "size", "color", "fit"
    ],
    IssueCategory.SUPPORT_ISSUE: [
        "support", "customer service", "agent", "rude", "unhelpful", "hold", "hung up", "ignored"
    ],
    IssueCategory.TECHNICAL_ISSUE: [
        "technical", "bug", "error", "crash", "login", "password", "app", "website", "load", "offline"
    ],
    IssueCategory.ACCOUNT_ISSUE: [
        "account", "profile", "locked", "suspended", "banned", "hacked", "security", "settings"
    ],
    IssueCategory.REFUND_ISSUE: [
        "refund", "return", "money back", "reimburse", "exchange"
    ],
    IssueCategory.SUBSCRIPTION_ISSUE: [
        "subscription", "cancel", "renew", "plan", "upgrade", "downgrade"
    ],
    IssueCategory.SERVICE_DELAY: [
        "delay", "slow", "waiting", "queue", "hours", "days", "months"
    ],
    IssueCategory.OPERATIONAL_FAILURE: [
        "system", "outage", "failure", "down", "process", "policy", "procedure"
    ]
}

# Stopwords for keyword extraction
OPERATIONAL_STOPWORDS = {
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", 
    "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", 
    "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", 
    "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", 
    "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", 
    "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", 
    "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", 
    "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", 
    "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", 
    "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", 
    "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", 
    "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"
}
