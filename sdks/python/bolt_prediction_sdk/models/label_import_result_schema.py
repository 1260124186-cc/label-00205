"""
LabelImportResultSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class LabelImportResultSchema(SDKBaseModel):
    """标注导入结果"""

    total: Optional[int] = Field(description="总行数", default=0)
    imported: Optional[int] = Field(description="成功导入数", default=0)
    skipped: Optional[int] = Field(description="跳过数", default=0)
    duplicates: Optional[int] = Field(description="重复数", default=0)
    errors: Optional[int] = Field(description="错误数", default=0)
    error_details: Optional[Any] = Field(description="错误详情", default=None)
