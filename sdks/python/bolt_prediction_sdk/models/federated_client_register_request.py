"""
FederatedClientRegisterRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FederatedClientRegisterRequest(SDKBaseModel):
    """联邦学习客户端注册请求"""

    client_id: str = Field(description="客户端/厂区ID")
    factory_name: Optional[Any] = Field(description="厂区名称", default=None)
    location: Optional[Any] = Field(description="厂区位置", default=None)
    client_info: Optional[Any] = Field(description="客户端附加信息", default=None)
