"""
KnowledgeCaseUpdateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class KnowledgeCaseUpdateRequest(SDKBaseModel):
    """更新案例请求"""

    case_title: Optional[Any] = Field(description="案例标题", default=None)
    fault_type: Optional[Any] = Field(description="故障类型", default=None)
    fault_level: Optional[Any] = Field(description="故障级别 1-4", default=None)
    working_condition: Optional[Any] = Field(description="工况信息", default=None)
    sensor_data: Optional[Any] = Field(description="传感器时序数据", default=None)
    sensor_features: Optional[Any] = Field(description="传感器特征", default=None)
    diagnosis: Optional[Any] = Field(description="诊断结论", default=None)
    root_cause: Optional[Any] = Field(description="根本原因分析", default=None)
    treatment_plan: Optional[Any] = Field(description="处置方案", default=None)
    effect_evaluation: Optional[Any] = Field(description="效果评估", default=None)
    tags: Optional[Any] = Field(description="标签列表", default=None)
    change_summary: Optional[Any] = Field(description="变更说明", default=None)
    submit_for_review: Optional[bool] = Field(description="是否提交审核", default=False)
    operator_id: Optional[Any] = Field(description="操作人ID", default=None)
    operator_name: Optional[Any] = Field(description="操作人姓名", default=None)
