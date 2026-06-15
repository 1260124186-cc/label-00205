"""
DataQualityCheckBatchRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class DataQualityCheckBatchRequest(SDKBaseModel):
    """批量数据质量检查请求"""

    sensors_data: Dict[str, List[List[Any]]] = Field(description="传感器数据字典 {sensor_id: [[时间, 数值], ...]}")
