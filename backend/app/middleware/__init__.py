"""
中间件模块

提供请求级别的中间件功能：
1. Request ID 生成和传递
2. 请求指标采集（Prometheus）
3. 结构化日志上下文

使用示例:
    from app.middleware import RequestContextMiddleware, get_request_id
    
    # 在 FastAPI 应用中添加中间件
    app.add_middleware(RequestContextMiddleware)
    
    # 获取当前请求 ID
    request_id = get_request_id()
"""

import time
import uuid
import contextvars
from typing import Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from loguru import logger

from app.core.prometheus import metrics

# 请求上下文变量
_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('request_id', default='')
_bolt_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('bolt_id', default='')
_request_start_time_var: contextvars.ContextVar[float] = contextvars.ContextVar('request_start_time', default=0.0)


def get_request_id() -> str:
    """获取当前请求的 request_id"""
    return _request_id_var.get()


def set_request_id(request_id: str) -> None:
    """设置当前请求的 request_id"""
    _request_id_var.set(request_id)


def get_bolt_id() -> str:
    """获取当前请求关联的 bolt_id"""
    return _bolt_id_var.get()


def set_bolt_id(bolt_id: str) -> None:
    """设置当前请求关联的 bolt_id"""
    _bolt_id_var.set(bolt_id)


def get_request_context() -> Dict[str, Any]:
    """获取请求上下文字典（用于日志）"""
    return {
        'request_id': get_request_id(),
        'bolt_id': get_bolt_id(),
    }


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    请求上下文中间件
    
    为每个请求生成唯一的 request_id，并记录请求指标。
    
    功能:
    1. 生成/传递 X-Request-ID
    2. 记录请求开始时间
    3. 采集 HTTP 请求指标（Prometheus）
    4. 计算请求耗时
    """
    
    async def dispatch(self, request: Request, call_next):
        # 从请求头获取或生成 request_id
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        _request_id_var.set(request_id)
        
        # 记录开始时间
        start_time = time.time()
        _request_start_time_var.set(start_time)
        
        # 获取请求路径（去掉查询参数）
        path = request.url.path
        method = request.method
        
        # 结构化日志 - 请求开始
        logger.bind(
            request_id=request_id,
            method=method,
            path=path,
            client_ip=request.client.host if request.client else 'unknown'
        ).info(f"Request started: {method} {path}")
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算耗时
            duration = time.time() - start_time
            
            # 获取状态码
            status_code = str(response.status_code)
            
            # 添加 request_id 到响应头
            response.headers['X-Request-ID'] = request_id
            
            # 记录 Prometheus 指标
            metrics.record_http_request(
                method=method,
                path=path,
                status_code=status_code,
                duration=duration
            )
            
            # 结构化日志 - 请求完成
            logger.bind(
                request_id=request_id,
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=round(duration * 1000, 2)
            ).info(f"Request completed: {method} {path} - {status_code}")
            
            return response
            
        except Exception as e:
            # 计算耗时
            duration = time.time() - start_time
            
            # 记录错误指标
            metrics.record_http_request(
                method=method,
                path=path,
                status_code="500",
                duration=duration
            )
            
            # 结构化日志 - 请求错误
            logger.bind(
                request_id=request_id,
                method=method,
                path=path,
                duration_ms=round(duration * 1000, 2),
                error=str(e)
            ).exception(f"Request failed: {method} {path}")
            
            raise


class StructuredLogFilter:
    """
    结构化日志过滤器
    
    为 loguru 日志添加上下文信息。
    """
    
    @staticmethod
    def patch(record: Dict[str, Any]) -> None:
        """
        为日志记录添加上下文信息
        
        Args:
            record: loguru 日志记录字典
        """
        # 添加 request_id
        request_id = get_request_id()
        if request_id:
            record['extra']['request_id'] = request_id
        
        # 添加 bolt_id
        bolt_id = get_bolt_id()
        if bolt_id:
            record['extra']['bolt_id'] = bolt_id


def setup_structured_logging() -> None:
    """
    配置结构化日志
    
    为 loguru 添加上下文信息。
    """
    import sys
    from loguru import logger
    
    # 移除默认处理器
    logger.remove()
    
    # 定义日志格式（包含结构化字段）
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<yellow>request_id={extra[request_id]}</yellow> | "
        "<yellow>bolt_id={extra[bolt_id]}</yellow> | "
        "<level>{message}</level>"
    )
    
    # 添加控制台处理器
    logger.add(
        sys.stderr,
        format=log_format,
        level="INFO",
        backtrace=True,
        diagnose=True
    )
    
    # 确保 extra 字段有默认值
    logger.configure(extra={"request_id": "", "bolt_id": ""})
    
    logger.info("Structured logging initialized")
