"""
ReportGenerateRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class ReportGenerateRequest(SDKBaseModel):
    """周期报告生成请求（周报/月报）"""

    node_type: str = Field(description="节点类型：bolt/flange")
    node_id: str = Field(description="节点ID（螺栓ID或法兰面ID）")
    report_type: Optional[str] = Field(description="报告类型：weekly/monthly", default='weekly')
    use_llm: Optional[Any] = Field(description="是否使用LLM生成（默认True，不可用时自动降级）", default=True)
