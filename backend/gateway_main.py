"""
工业协议采集网关启动脚本

用法:
    python gateway_main.py [--config CONFIG_PATH] [--daemon]
"""

import os
import sys
import time
import signal
import argparse
from pathlib import Path
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.gateway.service import get_gateway_service
from app.gateway.models import GatewayStatus


def setup_logging(log_level: str = "INFO", log_file: str = "./logs/gateway.log") -> None:
    """
    设置日志

    Args:
        log_level: 日志级别
        log_file: 日志文件路径
    """
    logger.remove()

    # 控制台输出
    logger.add(
        sys.stdout,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    # 文件输出
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(log_path),
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
    )


def handle_shutdown(signum, frame):
    """
    处理关闭信号

    Args:
        signum: 信号编号
        frame: 帧对象
    """
    logger.info(f"收到信号 {signum}，正在关闭网关...")
    gateway = get_gateway_service()
    gateway.stop()
    logger.info("网关已安全关闭")
    sys.exit(0)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="工业协议采集网关")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="配置文件路径",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="日志级别 (DEBUG/INFO/WARNING/ERROR)",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="./logs/gateway.log",
        help="日志文件路径",
    )
    parser.add_argument(
        "--daemon",
        "-d",
        action="store_true",
        help="以守护进程运行",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="仅检查配置，不启动网关",
    )
    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="列出所有可用的PLC模板",
    )

    args = parser.parse_args()

    # 设置日志
    setup_logging(args.log_level, args.log_file)

    logger.info("工业协议采集网关启动中...")

    # 列出模板
    if args.list_templates:
        from app.gateway.templates import get_template_manager
        tmpl_mgr = get_template_manager()
        templates = tmpl_mgr.list_templates()
        print("\n可用 PLC 模板:")
        print("-" * 60)
        for t in templates:
            print(
                f"  {t['template_id']:<30} "
                f"{t['brand']:<15} "
                f"{t['model']:<20} "
                f"{t['protocol']}"
            )
        print()
        return

    # 初始化网关服务
    try:
        gateway = get_gateway_service(config_path=args.config)
    except Exception as e:
        logger.error(f"初始化网关失败: {e}")
        sys.exit(1)

    # 仅检查配置
    if args.check:
        errors = gateway.config_manager.validate_config()
        if errors:
            print("\n配置验证发现以下问题:")
            for err in errors:
                print(f"  - {err}")
            print()
            sys.exit(1)
        else:
            print("\n配置验证通过！")
            status = gateway.config_manager.get_config()
            print(f"  网关ID: {status.gateway_id}")
            print(f"  设备数量: {len(status.devices)}")
            print(f"  数据目标: {status.data_target.value}")
            print()
            sys.exit(0)

    # 注册信号处理
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # 启动网关
    if not gateway.start():
        logger.error("网关启动失败")
        sys.exit(1)

    # 打印启动信息
    status = gateway.get_status()
    logger.info(
        f"网关已启动 | 状态: {status['status']} | "
        f"设备: {status['connected_devices']}/{status['total_devices']} | "
        f"点位: {status['active_points']}/{status['total_points']}"
    )

    # 主循环
    try:
        while gateway.is_running:
            time.sleep(5)

            # 定期打印状态
            status = gateway.get_status()
            logger.info(
                f"运行状态 | 设备: {status['connected_devices']}/{status['total_devices']} | "
                f"点位: {status['active_points']}/{status['total_points']} | "
                f"总采样: {status['total_samples']} | "
                f"QPS: {status['samples_per_second']:.2f} | "
                f"缓存: {status['cache_size']}"
            )

    except KeyboardInterrupt:
        logger.info("收到中断信号")
    finally:
        gateway.stop()
        logger.info("网关已退出")


if __name__ == "__main__":
    main()
