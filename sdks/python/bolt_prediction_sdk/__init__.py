"""
bolt_prediction_sdk - 螺栓预紧力预测系统 Python SDK

特性:
- 完整的 API 客户端覆盖
- 内置指数退避重试机制
- API Key 鉴权支持
- 游标分页同步封装
- 异步/同步双模式支持
"""

from .core.config import SDKConfig
from .core.auth import AuthManager
from .core.retry import RetryManager
from .core.pagination import CursorPaginator
from .models import *
from .api import *

__version__ = "v1"
__all__ = [
    "SDKConfig",
    "AuthManager",
    "RetryManager",
    "CursorPaginator",
]
