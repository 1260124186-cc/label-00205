"""
QualityReportRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class QualityReportRequest(SDKBaseModel):
    """生成质量报告请求"""

    report_date: Optional[Any] = Field(description="报告日期，默认今日", default=None)
    sensor_ids: Optional[Any] = Field(description="传感器ID列表，默认全部", default=None)
    save_to_db: Optional[bool] = Field(description="是否保存到数据库", default=True)
