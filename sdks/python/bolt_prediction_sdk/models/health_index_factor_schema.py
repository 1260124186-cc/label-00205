"""
HealthIndexFactorSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class HealthIndexFactorSchema(SDKBaseModel):
    """健康度因子详情"""

    factor_name: str = Field(description="因子名称")
    factor_code: str = Field(description="因子代码")
    score: float = Field(description="因子得分 0-100")
    weight: float = Field(description="因子权重")
    contribution: float = Field(description="对总健康度的贡献")
    description: Optional[Any] = Field(description="因子描述", default=None)
