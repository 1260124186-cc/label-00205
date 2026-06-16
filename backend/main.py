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

import uvicorn
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app import __version__
from app.api.routes import router
from app.api.sso_routes import router as sso_router
from app.schedulers.scheduler import scheduler
from app.utils.config import config
from app.utils.database import db_manager
from app.utils.device import get_all_device_info
from app.middleware import RequestContextMiddleware, setup_structured_logging
from app.core.prometheus import metrics


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    # 启动时
    logger.info(f"螺栓预紧力预测系统启动中... 版本: {__version__}")

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
- **监控指标**: Prometheus 格式的 /metrics 端点

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
