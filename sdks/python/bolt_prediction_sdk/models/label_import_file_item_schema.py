"""
LabelImportFileItemSchema 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class LabelImportFileItemSchema(SDKBaseModel):
    """可导入文件列表项"""

    filename: str = Field(description="文件名")
    path: str = Field(description="文件完整路径")
    size_bytes: Optional[int] = Field(description="文件大小（字节）", default=0)
    modified_time: Optional[Any] = Field(description="修改时间", default=None)
