"""
OrgNodeResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class OrgNodeResponse(SDKBaseModel):
    """OrgNodeResponse"""

    id: int = Field()
    tenant_id: int = Field()
    parent_id: Optional[Any] = Field(default=None)
    node_code: Optional[Any] = Field(default=None)
    node_name: str = Field()
    node_type: str = Field()
    path: Optional[Any] = Field(default=None)
    level: int = Field()
    sort_order: int = Field()
    extra_info: Optional[Any] = Field(default=None)
    status: str = Field()
    create_time: datetime = Field()
    update_time: datetime = Field()
    children: Optional[Any] = Field(default=None)
