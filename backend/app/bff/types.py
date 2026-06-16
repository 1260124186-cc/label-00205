import strawberry
from typing import Optional, List
from datetime import datetime


@strawberry.type
class PredictionInfo:
    bolt_id: str
    status_code: int
    status_label: str
    confidence: float
    risk_level: str
    predicted_at: Optional[datetime] = None


@strawberry.type
class HealthFactor:
    factor_name: str
    factor_code: str
    score: float
    weight: float
    contribution: float


@strawberry.type
class HealthInfo:
    bolt_id: str
    hi_score: float
    hi_level: str
    trend: Optional[str] = None
    trend_rate: Optional[float] = None
    factors: List[HealthFactor] = strawberry.field(default_factory=list)
    calculated_at: Optional[datetime] = None


@strawberry.type
class RULForecastPoint:
    day: float
    predicted_hi: float
    lower_bound: float
    upper_bound: float
    is_prediction: bool


@strawberry.type
class RULInfo:
    bolt_id: str
    current_hi: float
    rul_days: float
    rul_lower_bound: float
    rul_upper_bound: float
    rul_confidence: float
    failure_threshold: float
    warning_threshold: float
    days_to_warning: Optional[float] = None
    degradation_model: str
    r_squared: Optional[float] = None
    forecast_series: List[RULForecastPoint] = strawberry.field(default_factory=list)


@strawberry.type
class AnomalyRecord:
    id: int
    sensor_id: str
    anomaly_type: Optional[str] = None
    anomaly_score: Optional[float] = None
    anomaly_value: Optional[float] = None
    classification: Optional[str] = None
    original_time: Optional[datetime] = None
    is_confirmed: bool = False
    is_false_positive: bool = False


@strawberry.type
class WorkOrderRecord:
    id: int
    order_no: str
    title: str
    priority: str
    status: str
    assignee: Optional[str] = None
    due_time: Optional[datetime] = None
    created_at: Optional[datetime] = None


@strawberry.type
class KnowledgeRecommendation:
    case_id: int
    case_title: str
    similarity_score: float
    fault_type: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_summary: Optional[str] = None
    effectiveness_score: Optional[float] = None


@strawberry.type
class BoltDashboard:
    bolt_id: str
    prediction: Optional[PredictionInfo] = None
    health: Optional[HealthInfo] = None
    rul: Optional[RULInfo] = None
    recent_anomalies: List[AnomalyRecord] = strawberry.field(default_factory=list)
    work_orders: List[WorkOrderRecord] = strawberry.field(default_factory=list)
    knowledge_recommendations: List[KnowledgeRecommendation] = strawberry.field(
        default_factory=list
    )
