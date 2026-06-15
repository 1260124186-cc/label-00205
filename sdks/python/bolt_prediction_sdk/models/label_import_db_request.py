"""
LabelImportDBRequest 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class LabelImportDbRequest(SDKBaseModel):
    """数据库标注导入请求"""

    source_table: str = Field(description="源表名")
    node_type: str = Field(description="节点类型: bolt/flange")
    id_field: str = Field(description="节点ID字段名")
    label_field: str = Field(description="标签字段名")
    data_field: Optional[Any] = Field(description="数据点字段名", default=None)
    timestamp_field: Optional[Any] = Field(description="时间戳字段名", default=None)
    where_clause: Optional[Any] = Field(description="WHERE条件，不带WHERE关键字", default=None)
    labeler_name: Optional[Any] = Field(description="标注人姓名", default=None)
    auto_approve: Optional[bool] = Field(description="是否自动审核通过", default=True)
