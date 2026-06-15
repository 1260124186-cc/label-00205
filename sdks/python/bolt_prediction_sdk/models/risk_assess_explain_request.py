"""
RiskAssessExplainRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class RiskAssessExplainRequest(SDKBaseModel):
    """RiskAssessExplainRequest"""

    node_id: str = Field(description="节点ID（螺栓或法兰面）")
    node_type: str = Field(description="节点类型: bolt/flange")
    data: List[List[Any]] = Field(description="预紧力时序数据")
