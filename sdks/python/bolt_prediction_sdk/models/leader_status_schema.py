"""
LeaderStatusSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class LeaderStatusSchema(SDKBaseModel):
    """Leader选举状态"""

    leader_key: str = Field(description="Leader锁键")
    leader_id: str = Field(description="当前Leader实例ID")
    lease_expire_time: datetime = Field(description="租约过期时间")
    last_heartbeat: datetime = Field(description="最后心跳时间")
    version: int = Field(description="版本号")
    is_expired: bool = Field(description="租约是否已过期")
    is_current_instance: bool = Field(description="当前实例是否为Leader")
