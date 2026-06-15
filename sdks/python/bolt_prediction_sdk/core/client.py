"""
API 客户端基类
"""

import json
from typing import Optional, Dict, Any, Union
from urllib.parse import urljoin

import httpx
from loguru import logger

from .config import SDKConfig
from .auth import AuthManager
from .retry import RetryManager


class BaseAPIClient:
    """API 客户端基类"""

    def __init__(self, config: SDKConfig, auth: AuthManager, retry: RetryManager):
        self.config = config
        self.auth = auth
        self.retry = retry
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )
        return self._client

    async def close(self) -> None:
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """
        发送 HTTP 请求

        Args:
            method: HTTP 方法
            path: 请求路径
            params: 查询参数
            json: 请求体 JSON
            headers: 自定义请求头

        Returns:
            响应数据

        Raises:
            httpx.HTTPError: HTTP 请求错误
        """
        async def _do_request():
            client = await self._get_client()

            request_headers = self.auth.get_headers()
            if headers:
                request_headers.update(headers)

            request_headers.setdefault("Content-Type", "application/json")
            request_headers.setdefault("Accept", "application/json")

            url = urljoin(self.config.base_url, path)

            logger.debug(f"{method} {url}")

            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json,
                headers=request_headers,
            )

            response.raise_for_status()

            if response.content:
                return response.json()
            return None

        return await self.retry.execute(_do_request)
