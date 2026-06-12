"""
API请求和响应模型定义

使用Pydantic定义API的输入输出数据结构。

包含:
- 螺栓预测请求/响应
- 法兰面预测请求/响应
- 风险评估请求/响应
- 模型训练请求/响应
"""

from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


# ==================== 基础模型 ====================

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "healthy"
    version: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    """错误响应"""
    code: int
    message: str
    detail: Optional[str] = None


# ==================== 螺栓预测 ====================

class BoltPredictionRequest(BaseModel):
    """
    螺栓预测请求
    
    Attributes:
        螺栓id: 螺栓唯一标识
        data: 预紧力时序数据 [[时间, 预紧力], ...]
    """
    螺栓id: str = Field(..., description="螺栓唯一标识", alias="bolt_id")
    data: List[List[Any]] = Field(
        ..., 
        description="预紧力时序数据，每个元素为[时间字符串, 预紧力值]",
        min_length=1
    )
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "螺栓id": "B001",
                "data": [
                    ["20250201 00:00:00", 400.00],
                    ["20250201 00:01:00", 401.50],
                    ["20250201 00:02:00", 399.80]
                ]
            }
        }


class BoltPredictionResponse(BaseModel):
    """
    螺栓预测响应
    
    Attributes:
        bolt_id: 螺栓ID
        status: 预测状态
        status_code: 状态代码
        confidence: 置信度
        risk_score: 风险评分
        risk_level: 风险等级
        diagnosis: 诊断结论
        recommendations: 推荐措施
        prediction_time: 预测时间
    """
    bolt_id: str
    status: str
    status_code: int
    confidence: float
    risk_score: float
    risk_level: str
    diagnosis: str
    recommendations: List[str]
    prediction_time: datetime


# ==================== 法兰面预测 ====================

class FlangePredictionRequest(BaseModel):
    """
    法兰面预测请求
    
    Attributes:
        法兰面id: 法兰面唯一标识
        data: 多螺栓预紧力时序数据
    """
    法兰面id: str = Field(..., description="法兰面唯一标识", alias="flange_id")
    data: List[List[List[Any]]] = Field(
        ...,
        description="多螺栓预紧力数据，三维数组[螺栓][时间点][时间,预紧力]"
    )
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "法兰面id": "F001",
                "data": [
                    [["20250201 00:00:00", 605], ["20250201 00:01:00", 509]],
                    [["20250201 00:00:00", 598], ["20250201 00:01:00", 594]]
                ]
            }
        }


class FlangePredictionResponse(BaseModel):
    """法兰面预测响应"""
    flange_id: str
    status: str
    status_code: int
    confidence: float
    risk_score: float
    risk_level: str
    bolt_count: int
    attention_weights: Optional[List[float]] = None
    diagnosis: str
    recommendations: List[str]
    prediction_time: datetime


# ==================== 风险评估 ====================

class RiskAssessmentRequest(BaseModel):
    """风险评估请求"""
    node_id: str = Field(..., description="节点ID（螺栓或法兰面）")
    node_type: str = Field(..., description="节点类型: bolt/flange")
    data: List[List[Any]] = Field(..., description="预紧力时序数据")


class RiskAssessmentResponse(BaseModel):
    """风险评估响应"""
    node_id: str
    node_type: str
    risk_score: float
    risk_level: str
    factors: List[str]
    diagnosis: str
    recommendations: List[str]
    confidence: float


# ==================== 月度预测 ====================

class MonthlyForecastRequest(BaseModel):
    """月度预测请求"""
    node_id: str
    node_type: str
    forecast_days: int = Field(default=30, ge=1, le=90)


class MonthlyForecastResponse(BaseModel):
    """月度预测响应"""
    node_id: str
    node_type: str
    pw_type: str
    fault_type: Optional[str]
    begin_time: Optional[datetime]
    end_time: Optional[datetime]
    confidence: float
    rec_measures: str
    forecast_dates: List[datetime]
    forecast_values: List[float]


# ==================== 模型管理 ====================

class TrainingRequest(BaseModel):
    """模型训练请求"""
    model_type: str = Field(..., description="模型类型: bolt/flange")
    node_id: Optional[str] = Field(None, description="节点ID，空则训练所有")
    force_retrain: bool = Field(default=False, description="是否强制重新训练")


class TrainingResponse(BaseModel):
    """模型训练响应"""
    model_type: str
    node_id: Optional[str]
    status: str
    message: str
    training_time: float
    metrics: Optional[Dict[str, float]] = None


class ModelInfoResponse(BaseModel):
    """模型信息响应"""
    model_type: str
    node_id: str
    is_trained: bool
    last_training_time: Optional[datetime]
    training_samples: Optional[int]
    validation_accuracy: Optional[float]


# ==================== 策略配置 ====================

class StrategyConfigRequest(BaseModel):
    """预警策略配置请求"""
    strategy_type: int = Field(..., ge=1, le=2, description="策略类型: 1=应报尽报, 2=精准报警")
    confidence_threshold: Optional[float] = Field(None, ge=0, le=1)
    false_positive_threshold: Optional[float] = Field(None, ge=0, le=1)
    false_negative_threshold: Optional[float] = Field(None, ge=0, le=1)


class StrategyConfigResponse(BaseModel):
    """策略配置响应"""
    strategy_type: int
    confidence_threshold: float
    false_positive_threshold: Optional[float]
    false_negative_threshold: Optional[float]
    updated_at: datetime
