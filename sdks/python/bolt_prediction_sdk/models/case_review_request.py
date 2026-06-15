"""
CaseReviewRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class CaseReviewRequest(SDKBaseModel):
    """案例审核请求"""

    review_result: str = Field(description="审核结果 approved/rejected/revision_required")
    review_comment: Optional[Any] = Field(description="审核意见", default=None)
    reviewer_id: Optional[Any] = Field(description="审核人ID", default=None)
    reviewer_name: Optional[Any] = Field(description="审核人姓名", default=None)
    review_level: Optional[int] = Field(description="审核级别 1-3", default=1)
