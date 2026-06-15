"""
OrgNodeCreateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class OrgNodeCreateRequest(SDKBaseModel):
    """OrgNodeCreateRequest"""

    tenant_id: int = Field(description="所属租户ID")
    parent_id: Optional[Any] = Field(description="父节点ID, 空表示根节点", default=None)
    node_code: Optional[Any] = Field(description="节点编码", default=None)
    node_name: str = Field(description="节点名称")
    node_type: str = Field(description="节点类型 group/factory/unit/flange/bolt")
    sort_order: Optional[int] = Field(description="排序序号", default=0)
    extra_info: Optional[Any] = Field(description="扩展信息", default=None)
