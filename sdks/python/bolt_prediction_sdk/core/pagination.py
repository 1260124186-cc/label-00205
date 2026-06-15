"""
游标分页模块
"""

from typing import Any, Dict, List, Optional, AsyncIterator
from loguru import logger


class CursorPaginator:
    """游标分页器

    支持同步迭代和异步迭代两种方式遍历所有数据。
    """

    def __init__(
        self,
        client: Any,
        path: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Any] = None,
        cursor_param: str = "cursor",
        limit_param: str = "limit",
        default_limit: int = 20,
        response_cursor_field: str = "next_cursor",
        response_items_field: str = "items",
    ):
        self.client = client
        self.path = path
        self.method = method
        self.params = params or {}
        self.body = body
        self.cursor_param = cursor_param
        self.limit_param = limit_param
        self.default_limit = default_limit
        self.response_cursor_field = response_cursor_field
        self.response_items_field = response_items_field

        self._cursor: Optional[str] = None
        self._has_more: bool = True
        self._buffer: List[Any] = []

    async def next_page(self, limit: Optional[int] = None) -> List[Any]:
        """
        获取下一页数据

        Args:
            limit: 每页数量

        Returns:
            本页数据列表
        """
        if not self._has_more:
            return []

        params = dict(self.params)
        params[self.limit_param] = limit or self.default_limit

        if self._cursor:
            params[self.cursor_param] = self._cursor

        request_kwargs = {
            "method": self.method,
            "path": self.path,
            "params": params,
        }

        if self.body is not None:
            request_kwargs["json"] = self.body

        response = await self.client._request(**request_kwargs)

        if isinstance(response, dict):
            items = response.get(self.response_items_field, [])
            self._cursor = response.get(self.response_cursor_field)
            self._has_more = self._cursor is not None
        else:
            items = response
            self._has_more = False

        return items

    async def all(self, limit: Optional[int] = None) -> List[Any]:
        """
        获取所有数据

        Args:
            limit: 每页数量

        Returns:
            所有数据的列表
        """
        all_items: List[Any] = []
        while self._has_more:
            items = await self.next_page(limit)
            all_items.extend(items)
        return all_items

    async def __aiter__(self) -> AsyncIterator[Any]:
        """异步迭代器支持"""
        while self._has_more:
            items = await self.next_page()
            for item in items:
                yield item
