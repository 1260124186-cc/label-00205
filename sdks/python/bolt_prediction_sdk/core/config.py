"""
SDK 配置
"""

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class SDKConfig:
    """SDK 配置"""

    base_url: str = "https://api.example.com"
    api_key: Optional[str] = None
    api_version: str = "v1"
    timeout: int = 30

    max_retries: int = 3
    retry_backoff_factor: float = 0.5
    retry_status_codes: List[int] = field(
        default_factory=lambda: [429, 500, 502, 503, 504]
    )

    api_key_header: str = "X-API-Key"

    pagination_cursor_param: str = "cursor"
    pagination_limit_param: str = "limit"
    pagination_default_limit: int = 20
    pagination_max_limit: int = 100

    def validate(self) -> None:
        """验证配置"""
        if not self.base_url:
            raise ValueError("base_url is required")
