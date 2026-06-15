"""
AlertUpgradeTriggerResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AlertUpgradeTriggerResponse(SDKBaseModel):
    """手动触发告警升级响应"""

    upgraded_count: int = Field()
    message: str = Field()
