"""
鉴权模块
"""

from typing import Optional, Dict, Any


class AuthManager:
    """认证管理器"""

    def __init__(self, api_key: Optional[str] = None, header_name: str = "X-API-Key"):
        self.api_key = api_key
        self.header_name = header_name

    def get_headers(self) -> Dict[str, str]:
        """获取认证请求头"""
        headers = {}
        if self.api_key:
            headers[self.header_name] = self.api_key
        return headers

    def set_api_key(self, api_key: str) -> None:
        """设置 API Key"""
        self.api_key = api_key
