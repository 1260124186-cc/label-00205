"""
EnhancedTrainingResponse 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class EnhancedTrainingResponse(SDKBaseModel):
    """增强版模型训练响应"""

    session_id: str = Field(description="训练会话ID，用于查询状态")
    model_type: str = Field()
    node_id: Any = Field()
    status: str = Field(description="启动状态: started/error")
    message: str = Field(description="描述信息")
    is_incremental: Optional[bool] = Field(description="是否增量训练", default=False)
