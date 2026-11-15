from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class DateRangeInfo(BaseModel):
    range: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    days_count: int = 0

class CompletionTrendPoint(BaseModel):
    date: str
    label: str
    day_name: str
    completed_count: int
    cumulative_count: int

class StatusSegment(BaseModel):
    status: str
    count: int
    percentage: float

class StatusDistributionData(BaseModel):
    total: int
    pending: int
    completed: int
    overdue: int
    pending_percentage: float
    completed_percentage: float
    overdue_percentage: float
    segments: List[StatusSegment]

class PriorityDistributionPoint(BaseModel):
    priority: str
    count: int
    percentage: float

class CategoryDistributionPoint(BaseModel):
    category: str
    count: int
    percentage: float

class AnalyticsSummary(BaseModel):
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    overdue_tasks: int
    completion_rate: float

class AnalyticsOverviewResponse(BaseModel):
    date_range: DateRangeInfo
    summary: AnalyticsSummary
    completion_trend: List[CompletionTrendPoint]
    status_distribution: StatusDistributionData
    priority_distribution: List[PriorityDistributionPoint]
    category_distribution: List[CategoryDistributionPoint]
