"""
WorkOrderResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class WorkOrderResponse(SDKBaseModel):
    """工单响应"""

    title: str = Field(description="工单标题")
    description: Optional[Any] = Field(description="工单描述", default=None)
    priority: Optional[str] = Field(description="优先级 low/medium/high/urgent", default='medium')
    status: Optional[Any] = Field(description="状态 open/assigned/in_progress/resolved/closed", default='open')
    node_type: Optional[Any] = Field(description="节点类型", default=None)
    node_id: Optional[Any] = Field(description="节点ID", default=None)
    alert_level: Optional[Any] = Field(description="告警级别", default=None)
    risk_score: Optional[Any] = Field(description="风险评分", default=None)
    assignee_id: Optional[Any] = Field(description="处理人ID", default=None)
    assignee_name: Optional[Any] = Field(description="处理人姓名", default=None)
    creator_id: Optional[Any] = Field(description="创建人ID", default='manual')
    creator_name: Optional[Any] = Field(description="创建人姓名", default='人工创建')
    due_time: Optional[Any] = Field(description="截止时间", default=None)
    recommendations: Optional[Any] = Field(description="推荐措施", default=None)
    extra_info: Optional[Any] = Field(description="扩展信息", default=None)
    id: int = Field()
    order_no: str = Field()
    alert_id: Optional[Any] = Field(default=None)
    resolve_time: Optional[Any] = Field(default=None)
    resolve_note: Optional[Any] = Field(default=None)
    create_time: datetime = Field()
    update_time: datetime = Field()
