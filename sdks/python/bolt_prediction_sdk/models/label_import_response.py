"""
LabelImportResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class LabelImportResponse(SDKBaseModel):
    """标注导入响应"""

    status: str = Field(description="状态: success/error")
    message: str = Field(description="描述信息")
    result: Optional[Any] = Field(description="导入结果统计", default=None)
