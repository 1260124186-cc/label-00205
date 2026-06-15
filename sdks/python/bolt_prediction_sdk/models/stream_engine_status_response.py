"""
StreamEngineStatusResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class StreamEngineStatusResponse(SDKBaseModel):
    """流式预测引擎状态响应"""

    is_running: bool = Field()
    mode: str = Field()
    active_streams: int = Field()
    total_predictions: int = Field()
    status_changes: int = Field()
    window_manager: Dict[str, Any] = Field()
    backpressure: Dict[str, Any] = Field()
    events: Dict[str, Any] = Field()
    adapters: List[Dict[str, Any]] = Field()
