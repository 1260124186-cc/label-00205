"""
ConfigCenterResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ConfigCenterResponse(SDKBaseModel):
    """配置中心整体响应"""

    warning_strategy: WarningStrategyConfigSchema = Field()
    thresholds: ThresholdConfigSchema = Field()
    scheduled_jobs: List[ScheduledJobSchema] = Field()
    updated_at: datetime = Field()
