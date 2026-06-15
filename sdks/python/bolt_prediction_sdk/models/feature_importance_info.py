"""
FeatureImportanceInfo 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FeatureImportanceInfo(SDKBaseModel):
    """特征重要性分析（各通道对预测结果的贡献度）"""

    preload: Optional[float] = Field(description="预紧力通道重要性", default=0.0)
    temperature: Optional[float] = Field(description="温度通道重要性", default=0.0)
    humidity: Optional[float] = Field(description="湿度通道重要性", default=0.0)
    vibration: Optional[float] = Field(description="振动通道重要性", default=0.0)
    torque: Optional[float] = Field(description="扭矩通道重要性", default=0.0)
    others: Optional[Dict[str, float]] = Field(description="其他扩展通道的重要性", default=None)
