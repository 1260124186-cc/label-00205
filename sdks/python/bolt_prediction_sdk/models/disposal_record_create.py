"""
DisposalRecordCreate 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class DisposalRecordCreate(SDKBaseModel):
    """创建处置记录请求"""

    work_order_id: int = Field(description="关联工单ID")
    disposal_type: str = Field(description="处置类型 torque_adjustment/replacement/inspection/other")
    disposal_content: str = Field(description="处置内容描述")
    disposal_time: Optional[Any] = Field(description="处置时间", default=None)
    operator_id: Optional[Any] = Field(description="操作人ID", default=None)
    operator_name: Optional[Any] = Field(description="操作人姓名", default=None)
    before_value: Optional[Any] = Field(description="处置前值", default=None)
    after_value: Optional[Any] = Field(description="处置后值", default=None)
    materials_used: Optional[Any] = Field(description="使用材料列表", default=None)
    photos: Optional[Any] = Field(description="现场照片URL列表", default=None)
    notes: Optional[Any] = Field(description="备注", default=None)
    extra_info: Optional[Any] = Field(description="扩展信息", default=None)
