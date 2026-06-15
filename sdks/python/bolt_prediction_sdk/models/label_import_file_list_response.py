"""
LabelImportFileListResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class LabelImportFileListResponse(SDKBaseModel):
    """可导入文件列表响应"""

    total: int = Field(description="文件数量")
    items: Optional[List[LabelImportFileItemSchema]] = Field(description="文件列表", default=None)
