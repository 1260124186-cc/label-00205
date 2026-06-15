"""
CarbonModelConfigUpdateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class CarbonModelConfigUpdateRequest(SDKBaseModel):
    """碳排模型系数配置更新请求"""

    degradation: Optional[Any] = Field(description="预紧力劣化模型参数（可选更新）", default=None)
    leakage: Optional[Any] = Field(description="泄漏率估算模型参数（可选更新）", default=None)
    energy_carbon: Optional[Any] = Field(description="能耗与碳排模型参数（可选更新）", default=None)
    operator_id: Optional[Any] = Field(description="操作人ID", default=None)
    operator_name: Optional[Any] = Field(description="操作人姓名", default=None)
    description: Optional[Any] = Field(description="变更说明", default=None)
