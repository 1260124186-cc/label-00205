"""
螺栓预紧力机器学习预测系统 - 主入口

启动FastAPI应用和定时任务调度器。

使用方法:
    python main.py              # 启动API服务
    python main.py --train      # 训练模型
    python main.py --predict    # 执行一次预测

环境变量:
    CONFIG_PATH: 配置文件路径
    API_HOST: API服务主机
    API_PORT: API服务端口
"""

import os
import sys
import argparse
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app import __version__
from app.api.routes import router
from app.api.sso_routes import router as sso_router
from app.api.timeseries_routes import router as timeseries_router
from app.api.sync_routes import router as sync_router
from app.schedulers.scheduler import scheduler
from app.utils.config import config
from app.utils.database import db_manager
from app.utils.device import get_all_device_info
from app.middleware import RequestContextMiddleware, TenantContextMiddleware, setup_structured_logging
from app.core.prometheus import metrics
from app.core.redis_broadcast import config_sync
from app.core.event_bus import event_bus, EventType
from app.core.config_manager import config_manager


def setup_logging() -> None:
    """
    配置日志系统（结构化日志）
    """
    log_config = config.get('logging', {})
    log_level = log_config.get('level', 'INFO')
    log_file = log_config.get('file', './logs/app.log')

    # 确保日志目录存在
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 配置结构化日志
    setup_structured_logging()

    # 添加文件处理器
    log_format_file = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "request_id={extra[request_id]} | "
        "bolt_id={extra[bolt_id]} | "
        "{message}"
    )

    logger.add(
        log_file,
        format=log_format_file,
        level=log_level,
        rotation=log_config.get('max_size', 10485760),
        retention=log_config.get('backup_count', 5),
        encoding='utf-8'
    )

    logger.info(f"日志系统初始化完成，级别: {log_level}")


def setup_log_level_hot_reload() -> None:
    """
    注册日志级别热更新订阅（LOG_LEVEL_CHANGED 事件）。

    当收到 logging.level 变更时：
    1. 记录原有 stderr handler 的配置
    2. 移除所有 handlers
    3. 重新按新级别添加 stderr + file handler
    """
    def _on_log_level_changed(event) -> None:
        try:
            new_level = config_manager.get('logging.level', 'INFO')
            log_config = config_manager.get('logging', {})
            log_file = log_config.get('file', './logs/app.log')
            backup_count = log_config.get('backup_count', 5)
            max_size = log_config.get('max_size', 10485760)

            logger.remove()

            log_format_stdout = (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "{extra[request_id]} | "
                "<level>{message}</level>"
            )
            logger.add(
                sys.stderr,
                format=log_format_stdout,
                level=new_level,
                colorize=True,
            )

            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_format_file = (
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "{name}:{function}:{line} | "
                "request_id={extra[request_id]} | "
                "bolt_id={extra[bolt_id]} | "
                "{message}"
            )
            logger.add(
                log_file,
                format=log_format_file,
                level=new_level,
                rotation=max_size,
                retention=backup_count,
                encoding='utf-8'
            )

            logger.info(
                f"日志级别热更新成功: {event.data.get('changed_paths', [])}, "
                f"new_level={new_level}"
            )
        except Exception as e:
            logger.exception(f"日志级别热更新失败: {e}")

    event_bus.subscribe(
        EventType.LOG_LEVEL_CHANGED,
        _on_log_level_changed,
        priority=100,
    )
    logger.debug("日志级别热更新订阅已注册")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    # 启动时
    logger.info(f"螺栓预紧力预测系统启动中... 版本: {__version__}")

    setup_log_level_hot_reload()

    # 启动Redis配置同步（多实例广播）
    try:
        config_sync.start()
        logger.info("Redis配置同步模块已启动")
    except Exception as e:
        logger.warning(f"Redis配置同步启动失败: {e}")

    # 显示设备信息
    device_info = get_all_device_info()
    logger.info(f"计算设备: {device_info}")

    # 创建数据表
    try:
        db_manager.create_tables()
    except Exception as e:
        logger.warning(f"数据表创建失败（数据库可能未配置）: {e}")

    # 启动调度器
    scheduler.start()

    # 启动流式预测引擎（如果配置启用）
    try:
        stream_enabled = config.get('stream_prediction.enabled', False)
        if stream_enabled:
            from app.streaming import get_stream_engine
            stream_engine = get_stream_engine()
            stream_engine.start()
            logger.info("流式预测引擎已启动")
    except Exception as e:
        logger.warning(f"流式预测引擎启动失败: {e}")

    logger.info("系统启动完成")

    yield

    # 关闭时
    logger.info("系统关闭中...")

    # 停止流式预测引擎
    try:
        from app.streaming import get_stream_engine
        stream_engine = get_stream_engine()
        if stream_engine.is_running:
            stream_engine.stop()
            logger.info("流式预测引擎已停止")
    except Exception as e:
        logger.warning(f"流式预测引擎停止失败: {e}")

    scheduler.stop()
    db_manager.close()
    logger.info("系统已关闭")


def create_app() -> FastAPI:
    """
    创建FastAPI应用

    Returns:
        FastAPI: 应用实例
    """
    app = FastAPI(
        title="螺栓预紧力机器学习预测系统",
        description="""
## 系统功能

基于机器学习的螺栓预紧力预测系统，提供:

- **螺栓状态预测**: 预测单个螺栓的状态（正常/预警/故障）
- **法兰面状态预测**: 预测法兰面整体状态
- **风险评估**: 评估螺栓/法兰面的风险等级
- **月度预测**: 预测未来30天的状态趋势
- **模型管理**: 训练和管理预测模型
- **下游增量同步 API**: 基于游标的数据增量同步（预测结果 & 原始数据）
- **监控指标**: Prometheus 格式的 /metrics 端点

## 下游增量同步 API

### 端点
- `GET /api/v1/sync/predictions?since_id=12345&limit=500` - 预测结果增量同步
- `GET /api/v1/sync/bolt-data?since_time=...` - 螺栓原始数据增量（支持脱敏）
- `GET /api/v1/sync/status` - 同步游标状态查询

### 核心特性
- 基于单调递增 `id` 或 `update_time` 游标拉取增量
- 支持 `If-None-Match` / `ETag` 减少带宽
- 租户级游标隔离（X-Tenant-API-Key / X-Tenant-Token）
- API Key 权限: `sync:read`（`read` 权限同样兼容）

### SLA
- **增量延迟 < 1 分钟**（批处理场景）
- 响应头包含 `X-SLA-Latency` 实时延迟指标

## 状态类别

| 代码 | 状态 | 说明 |
|------|------|------|
| 0 | 正常 | 预紧力稳定 |
| 1 | 关注级预警 | 需要关注 |
| 2 | 检查级预警 | 需要检查 |
| 3 | 紧急级预警 | 紧急处理 |
| 4 | 故障 | 已发生故障 |

## API使用

所有预测接口都支持中文字段名和英文字段名。

## 监控

访问 `/metrics` 获取 Prometheus 格式的监控指标。
        """,
        version=__version__,
        lifespan=lifespan
    )

    # 请求上下文中间件（必须放在最前面）
    app.add_middleware(RequestContextMiddleware)

    # 租户上下文中间件
    app.add_middleware(TenantContextMiddleware)

    # CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # 注册路由
    app.include_router(router, prefix="/api/v1")
    app.include_router(sso_router)
    app.include_router(timeseries_router, prefix="/api/v1")
    app.include_router(sync_router, prefix="/api/v1")

    from app.api.routes import public_router
    app.include_router(public_router, prefix="/api/v1")

    from app.services.webhook.routes import router as webhook_router
    app.include_router(webhook_router, prefix="/api/v1")

    from app.bff.schema import create_bff_router
    bff_router = create_bff_router()
    app.include_router(bff_router, prefix="/graphql")

    from app.api.schemas import HealthResponse, HealthComponentStatus

    @app.get("/health", response_model=HealthResponse, tags=["系统"], summary="健康检查（公开免鉴权）")
    async def health_check():
        from app.services.health_check_service import get_health_check_service
        health_service = get_health_check_service()
        components = health_service.check_all()
        all_healthy = all(
            comp.get('status') == 'healthy'
            for comp in components.values()
        )
        component_status = {}
        for name, comp in components.items():
            component_status[name] = HealthComponentStatus(
                status=comp.get('status', 'unknown'),
                message=comp.get('message')
            )
        return HealthResponse(
            status="healthy" if all_healthy else "unhealthy",
            version=__version__,
            timestamp=datetime.now(),
            components=component_status
        )

    # Prometheus metrics 端点
    @app.get("/metrics", tags=["监控"])
    async def get_metrics():
        """
        获取 Prometheus 格式的监控指标

        返回系统运行指标，包括：
        - HTTP 请求数和延迟
        - 预测请求数和延迟
        - 预测结果分布
        - GPU 利用率
        - 模型加载数
        - 任务成功率
        """
        metrics_text = metrics.generate_metrics_text()
        return Response(
            content=metrics_text,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )

    # ---------- 风险热力图 WebSocket 端点 ----------

    @app.websocket("/ws/risk/heatmap")
    async def websocket_risk_heatmap(
        websocket: WebSocket,
        tenant_id: int = Query(..., description="租户ID"),
        api_key: str = Query(..., description="API密钥"),
    ):
        """
        风险热力图 WebSocket 实时推送端点

        支持的消息类型：
        - **subscribe**: 订阅节点风险更新
        - **unsubscribe**: 取消订阅
        - **heartbeat**: 心跳检测
        - **request_full_graph**: 请求全量图数据
        - **start_time_playback**: 开始时间回放
        - **stop_time_playback**: 停止时间回放
        """
        from app.services.risk_visualization.websocket_manager import get_websocket_manager

        manager = get_websocket_manager()
        try:
            await manager.connect(websocket, tenant_id, api_key)

            while True:
                try:
                    data = await websocket.receive_json()
                    await manager.handle_message(websocket, data)
                except WebSocketDisconnect:
                    manager.disconnect(websocket)
                    break
                except Exception as e:
                    logger.error(f"WebSocket消息处理错误: {e}")
                    try:
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e),
                            "timestamp": datetime.now().isoformat()
                        })
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"WebSocket连接失败: {e}")
            try:
                await websocket.close(code=1008, reason=str(e))
            except Exception:
                pass

    return app


def train_models() -> None:
    """
    训练所有模型
    """
    logger.info("开始训练模型...")

    from app.services.training_service import TrainingService

    service = TrainingService()
    results = service.train_from_csv()

    logger.info(f"训练完成: {results}")


def run_prediction() -> None:
    """
    执行一次预测
    """
    logger.info("开始执行预测...")

    from app.services.prediction_service import PredictionService

    service = PredictionService()

    # 批量预测
    service.batch_predict_from_db('bolt')
    service.batch_predict_from_db('flange')

    logger.info("预测完成")


def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(
        description='螺栓预紧力机器学习预测系统'
    )
    parser.add_argument(
        '--train',
        action='store_true',
        help='训练模型'
    )
    parser.add_argument(
        '--predict',
        action='store_true',
        help='执行一次预测'
    )
    parser.add_argument(
        '--host',
        type=str,
        default=None,
        help='API服务主机'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=None,
        help='API服务端口'
    )

    args = parser.parse_args()

    # 配置日志
    setup_logging()

    if args.train:
        train_models()
        return

    if args.predict:
        run_prediction()
        return

    # 启动API服务
    api_config = config.get('api', {})
    host = args.host or api_config.get('host', '0.0.0.0')
    port = args.port or api_config.get('port', 8000)
    debug = api_config.get('debug', False)

    logger.info(f"启动API服务: {host}:{port}")

    app = create_app()

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == '__main__':
    main()
