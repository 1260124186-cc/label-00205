"""
LabelImportCSVRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class LabelImportCsvRequest(SDKBaseModel):
    """CSV标注导入请求"""

    csv_path: str = Field(description="CSV文件路径")
    node_type: str = Field(description="节点类型: bolt/flange")
    label_column: Optional[Any] = Field(description="标签列名，自动检测", default=None)
    id_column: Optional[Any] = Field(description="节点ID列名，自动检测", default=None)
    data_column: Optional[Any] = Field(description="数据点列名", default=None)
    timestamp_column: Optional[Any] = Field(description="时间戳列名", default=None)
    labeler_name: Optional[Any] = Field(description="标注人姓名", default=None)
    auto_approve: Optional[bool] = Field(description="是否自动审核通过", default=True)
    skip_errors: Optional[bool] = Field(description="是否跳过错误行", default=True)
