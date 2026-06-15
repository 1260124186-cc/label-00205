"""
OrgNodeUpdateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class OrgNodeUpdateRequest(SDKBaseModel):
    """OrgNodeUpdateRequest"""

    node_name: Optional[Any] = Field(default=None)
    node_code: Optional[Any] = Field(default=None)
    sort_order: Optional[Any] = Field(default=None)
    extra_info: Optional[Any] = Field(default=None)
    status: Optional[Any] = Field(description="状态 active/inactive", default=None)
