"""
HealthIndexCalculateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class HealthIndexCalculateRequest(SDKBaseModel):
    """健康度计算请求"""

    node_id: str = Field(description="节点ID")
    node_type: str = Field(description="节点类型 bolt/flange/line")
    data: Optional[Any] = Field(description="预紧力时序数据 [[时间, 预紧力], ...]", default=None)
    working_condition: Optional[Any] = Field(description="工况信息", default=None)
    include_history: Optional[bool] = Field(description="是否包含历史数据", default=True)
    save_to_db: Optional[bool] = Field(description="是否保存到数据库", default=True)
