"""
AnomalyBatchResultResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class AnomalyBatchResultResponse(SDKBaseModel):
    """批量操作结果响应"""

    total: Optional[int] = Field(description="总数量", default=0)
    success: Optional[int] = Field(description="成功数量", default=0)
    failed: Optional[int] = Field(description="失败数量", default=0)
    failed_ids: Optional[List[int]] = Field(description="失败的ID列表", default=None)
