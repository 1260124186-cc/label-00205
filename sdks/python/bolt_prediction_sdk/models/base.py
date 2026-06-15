"""
基础模型
"""

from typing import Optional, Any, Dict, List
from pydantic import BaseModel, ConfigDict


class SDKBaseModel(BaseModel):
    """SDK 基础模型"""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
        use_attribute_docstrings=True,
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump(by_alias=True, exclude_none=True)

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return self.model_dump_json(by_alias=True, exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SDKBaseModel":
        """从字典创建模型"""
        return cls(**data)
