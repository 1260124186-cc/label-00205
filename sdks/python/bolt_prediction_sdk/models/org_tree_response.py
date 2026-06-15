"""
OrgTreeResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class OrgTreeResponse(SDKBaseModel):
    """OrgTreeResponse"""

    tenant_id: int = Field()
    nodes: List[OrgNodeResponse] = Field()
