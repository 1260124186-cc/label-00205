"""
FederatedPrivacyConfig 模型
"""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import Field

from .base import SDKBaseModel


class FederatedPrivacyConfig(SDKBaseModel):
    """隐私保护配置"""

    mechanism: Optional[str] = Field(description="隐私机制: none/dp/secagg/combined", default='none')
    epsilon: Optional[float] = Field(description="差分隐私epsilon", default=1.0)
    delta: Optional[float] = Field(description="差分隐私delta", default=1e-05)
    noise_scale: Optional[float] = Field(description="噪声缩放系数", default=0.1)
    clip_norm: Optional[float] = Field(description="梯度裁剪范数", default=1.0)
    num_parties: Optional[int] = Field(description="安全聚合参与方数量", default=3)
    secret_share_threshold: Optional[int] = Field(description="秘密共享阈值", default=2)
