"""
重试模块
"""

import asyncio
from typing import Callable, Awaitable, Any, List
from loguru import logger


class RetryManager:
    """重试管理器"""

    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        status_codes: List[int] = None,
    ):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.status_codes = status_codes or [429, 500, 502, 503, 504]

    async def execute(
        self,
        func: Callable[..., Awaitable[Any]],
        *args,
        **kwargs,
    ) -> Any:
        """
        执行带重试的异步函数

        Args:
            func: 要执行的异步函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数执行结果
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                status_code = getattr(e, "status_code", None)

                if status_code not in self.status_codes:
                    raise

                if attempt >= self.max_retries:
                    logger.warning(
                        f"Max retries ({self.max_retries}) reached, giving up"
                    )
                    raise

                wait_time = self.backoff_factor * (2 ** attempt)
                logger.warning(
                    f"Retry attempt {attempt + 1}/{self.max_retries}, "
                    f"waiting {wait_time}s before retry. Error: {e}"
                )
                await asyncio.sleep(wait_time)

        raise last_exception
