"""
EdgeModelExportRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EdgeModelExportRequest(SDKBaseModel):
    """EdgeModelExportRequest"""

    model_type: str = Field(description="模型类型 bolt/flange")
    node_id: Optional[Any] = Field(description="节点ID", default=None)
    export_format: Optional[str] = Field(description="导出格式 onnx/torchscript", default='onnx')
    version: Optional[Any] = Field(description="指定版本，None则使用最新", default=None)
