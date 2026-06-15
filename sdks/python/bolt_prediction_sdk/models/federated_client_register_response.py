"""
FederatedClientRegisterResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FederatedClientRegisterResponse(SDKBaseModel):
    """联邦学习客户端注册响应"""

    client_id: str = Field()
    status: str = Field()
    message: str = Field()
    registered_at: datetime = Field()
