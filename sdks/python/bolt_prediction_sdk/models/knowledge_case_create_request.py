"""
KnowledgeCaseCreateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class KnowledgeCaseCreateRequest(SDKBaseModel):
    """创建案例请求"""

    case_title: str = Field(description="案例标题")
    node_type: Optional[Any] = Field(description="节点类型 bolt/flange", default=None)
    node_id: Optional[Any] = Field(description="节点ID", default=None)
    fault_type: Optional[Any] = Field(description="故障类型", default=None)
    fault_level: Optional[Any] = Field(description="故障级别 1-4", default=None)
    working_condition: Optional[Any] = Field(description="工况信息", default=None)
    sensor_data: Optional[Any] = Field(description="传感器时序数据 [[时间, 数值], ...]", default=None)
    sensor_features: Optional[Any] = Field(description="传感器特征 (58维特征名值对)", default=None)
    diagnosis: Optional[Any] = Field(description="诊断结论", default=None)
    root_cause: Optional[Any] = Field(description="根本原因分析", default=None)
    treatment_plan: Optional[Any] = Field(description="处置方案", default=None)
    effect_evaluation: Optional[Any] = Field(description="效果评估", default=None)
    source_alert_id: Optional[Any] = Field(description="来源告警ID", default=None)
    source_prediction_id: Optional[Any] = Field(description="来源预测记录ID", default=None)
    tags: Optional[Any] = Field(description="标签列表", default=None)
    creator_id: Optional[Any] = Field(description="创建人ID", default=None)
    creator_name: Optional[Any] = Field(description="创建人姓名", default=None)
    tenant_id: Optional[Any] = Field(description="租户ID", default=None)
    submit_for_review: Optional[bool] = Field(description="是否提交审核", default=False)
