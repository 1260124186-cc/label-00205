"""
RiskCalibrationUpdateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class RiskCalibrationUpdateRequest(SDKBaseModel):
    """RiskCalibrationUpdateRequest"""

    node_type: str = Field(description="节点类型 bolt/flange/production_line")
    node_id: str = Field(description="节点ID")
    prior_weights: Optional[Any] = Field(description="自定义权重覆盖", default=None)
    risk_thresholds: Optional[Any] = Field(description="自定义阈值覆盖", default=None)
    description: Optional[Any] = Field(description="变更说明", default=None)
    operator_id: Optional[Any] = Field(description="操作人ID", default=None)
    operator_name: Optional[Any] = Field(description="操作人姓名", default=None)
