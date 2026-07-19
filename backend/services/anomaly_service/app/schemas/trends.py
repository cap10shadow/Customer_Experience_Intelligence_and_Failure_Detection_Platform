from datetime import date
from typing import Dict, List

from pydantic import BaseModel


class VolumeTrendPoint(BaseModel):
    """Complaint count for a single day."""
    date: date
    count: int


class CategoryTrendPoint(BaseModel):
    """Complaint count for a single detected issue category."""
    category: str
    count: int


class RegionTrendPoint(BaseModel):
    """Complaint count for a single customer region."""
    region: str
    count: int


class SentimentTrendPoint(BaseModel):
    """Average sentiment score and label breakdown for a single day."""
    date: date
    average_score: float
    label_counts: Dict[str, int]


class UrgencyTrendPoint(BaseModel):
    """Complaint count for a single urgency level."""
    urgency: str
    count: int


class VolumeTrendResponse(BaseModel):
    period: str
    complaint_volume: List[VolumeTrendPoint]


class CategoryTrendResponse(BaseModel):
    period: str
    categories: List[CategoryTrendPoint]


class RegionTrendResponse(BaseModel):
    period: str
    regions: List[RegionTrendPoint]


class SentimentTrendResponse(BaseModel):
    period: str
    sentiment: List[SentimentTrendPoint]


class UrgencyTrendResponse(BaseModel):
    period: str
    urgency: List[UrgencyTrendPoint]


class TrendSummaryResponse(BaseModel):
    """Overall trend summary combining every descriptive analytic."""
    period: str
    complaint_volume: List[VolumeTrendPoint]
    categories: List[CategoryTrendPoint]
    regions: List[RegionTrendPoint]
    sentiment: List[SentimentTrendPoint]
    urgency: List[UrgencyTrendPoint]
