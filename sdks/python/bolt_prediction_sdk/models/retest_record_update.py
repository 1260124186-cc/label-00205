"""
RetestRecordUpdate 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class RetestRecordUpdate(SDKBaseModel):
    """更新复测记录请求"""

    retest_time: Optional[Any] = Field(default=None)
    retester_id: Optional[Any] = Field(default=None)
    retester_name: Optional[Any] = Field(default=None)
    retest_result: Optional[Any] = Field(default=None)
    measured_value: Optional[Any] = Field(default=None)
    data_points: Optional[Any] = Field(default=None)
    before_risk_score: Optional[Any] = Field(default=None)
    after_risk_score: Optional[Any] = Field(default=None)
    status_after_retest: Optional[Any] = Field(default=None)
    confidence: Optional[Any] = Field(default=None)
    retest_notes: Optional[Any] = Field(default=None)
    photos: Optional[Any] = Field(default=None)
    extra_info: Optional[Any] = Field(default=None)
