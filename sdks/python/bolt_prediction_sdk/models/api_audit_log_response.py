"""
APIAuditLogResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ApiAuditLogResponse(SDKBaseModel):
    """APIAuditLogResponse"""

    id: int = Field()
    key_id: Optional[str] = Field(description="API密钥ID", default='')
    key_name: Optional[str] = Field(description="密钥名称", default='')
    method: Optional[str] = Field(description="HTTP方法", default='')
    path: Optional[str] = Field(description="请求路径", default='')
    status_code: Optional[int] = Field(description="响应状态码", default=0)
    client_ip: Optional[str] = Field(description="客户端IP", default='')
    request_id: Optional[str] = Field(description="请求ID", default='')
    extra_info: Optional[Dict[str, Any]] = Field(description="扩展信息", default={})
    create_time: datetime = Field()
