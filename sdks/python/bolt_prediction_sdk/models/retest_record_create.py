"""
RetestRecordCreate 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class RetestRecordCreate(SDKBaseModel):
    """创建复测记录请求"""

    work_order_id: int = Field(description="关联工单ID")
    retest_time: Optional[Any] = Field(description="复测时间", default=None)
    retester_id: Optional[Any] = Field(description="复测人ID", default=None)
    retester_name: Optional[Any] = Field(description="复测人姓名", default=None)
    retest_result: Optional[str] = Field(description="复测结果 pass/fail/pending", default='pending')
    measured_value: Optional[Any] = Field(description="复测测量值", default=None)
    data_points: Optional[Any] = Field(description="复测数据点 时序数据", default=None)
    before_risk_score: Optional[Any] = Field(description="复测前风险评分", default=None)
    after_risk_score: Optional[Any] = Field(description="复测后风险评分", default=None)
    status_after_retest: Optional[Any] = Field(description="复测后状态 normal/warning/critical", default=None)
    confidence: Optional[Any] = Field(description="复测置信度", default=None)
    retest_notes: Optional[Any] = Field(description="复测备注", default=None)
    photos: Optional[Any] = Field(description="复测照片URL列表", default=None)
    extra_info: Optional[Any] = Field(description="扩展信息", default=None)
    auto_repredict: Optional[Any] = Field(description="是否自动再预测", default=True)
