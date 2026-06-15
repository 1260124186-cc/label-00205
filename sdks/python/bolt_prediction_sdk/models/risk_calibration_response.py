"""
RiskCalibrationResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class RiskCalibrationResponse(SDKBaseModel):
    """RiskCalibrationResponse"""

    node_type: str = Field()
    node_id: str = Field()
    prior_weights: Dict[str, float] = Field()
    risk_thresholds: Dict[str, Any] = Field()
    version: Optional[int] = Field(default=1)
    is_active: Optional[bool] = Field(default=True)
    description: Optional[Any] = Field(default=None)
    create_time: Optional[Any] = Field(default=None)
