#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型训练脚本

用于训练螺栓和法兰面预测模型。

使用方法:
    python train.py                     # 训练所有模型
    python train.py --type bolt         # 只训练螺栓模型
    python train.py --type flange       # 只训练法兰面模型
    python train.py --id B001           # 训练指定节点的模型
    python train.py --force             # 强制重新训练
    python train.py --csv               # 从CSV文件训练

示例:
    # 从CSV文件训练所有螺栓模型
    python train.py --type bolt --csv
    
    # 训练指定螺栓的模型
    python train.py --type bolt --id B001 --force
"""

import sys
import argparse
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger

from app.services.training_service import TrainingService
from app.utils.config import config
from app.utils.device import get_all_device_info


def setup_logging():
    """配置日志"""
    logger.remove()
    logger.add(
        sys.stderr,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="INFO"
    )
    logger.add(
        "logs/training.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="DEBUG",
        rotation="10 MB"
    )


def print_banner():
    """打印横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║       螺栓预紧力机器学习预测系统 - 模型训练工具              ║
║                       Version 1.0.0                           ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_device_info():
    """打印设备信息"""
    device_info = get_all_device_info()
    logger.info("=" * 50)
    logger.info("设备信息:")
    logger.info(f"  CPU: {device_info['cpu']['device_name']}")
    logger.info(f"  CUDA可用: {device_info['cuda_available']}")
    if device_info['cuda_available']:
        for i, gpu in enumerate(device_info['gpus']):
            logger.info(f"  GPU {i}: {gpu['device_name']} ({gpu['total_memory']}GB)")
    logger.info("=" * 50)


def train_models(model_type: str, node_id: str = None, force: bool = False, use_csv: bool = False):
    """
    执行模型训练
    
    Args:
        model_type: 模型类型 (bolt/flange/all)
        node_id: 节点ID
        force: 是否强制重新训练
        use_csv: 是否从CSV训练
    """
    service = TrainingService()
    
    start_time = time.time()
    
    if use_csv:
        logger.info("从CSV文件训练模型...")
        results = service.train_from_csv()
        
        if results['bolt_results']:
            logger.info(f"螺栓模型: {results['bolt_results'].get('message', '')}")
        if results['flange_results']:
            logger.info(f"法兰面模型: {results['flange_results'].get('message', '')}")
    else:
        if model_type in ['bolt', 'all']:
            logger.info("训练螺栓模型...")
            bolt_result = service.train_model(
                model_type='bolt',
                node_id=node_id,
                force_retrain=force
            )
            logger.info(f"螺栓训练结果: {bolt_result.get('message', '')}")
            
            if 'metrics' in bolt_result:
                logger.info(f"  训练准确率: {bolt_result['metrics'].get('train_acc', 'N/A'):.4f}")
                logger.info(f"  验证准确率: {bolt_result['metrics'].get('val_acc', 'N/A'):.4f}")
        
        if model_type in ['flange', 'all']:
            logger.info("训练法兰面模型...")
            flange_result = service.train_model(
                model_type='flange',
                node_id=node_id,
                force_retrain=force
            )
            logger.info(f"法兰面训练结果: {flange_result.get('message', '')}")
            
            if 'metrics' in flange_result:
                logger.info(f"  训练准确率: {flange_result['metrics'].get('train_acc', 'N/A'):.4f}")
                logger.info(f"  验证准确率: {flange_result['metrics'].get('val_acc', 'N/A'):.4f}")
    
    elapsed = time.time() - start_time
    logger.info(f"训练完成，总耗时: {elapsed:.2f}秒")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='螺栓预紧力预测模型训练工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--type', '-t',
        type=str,
        choices=['bolt', 'flange', 'all'],
        default='all',
        help='模型类型: bolt(螺栓), flange(法兰面), all(全部)'
    )
    
    parser.add_argument(
        '--id', '-i',
        type=str,
        default=None,
        help='节点ID，不指定则训练所有'
    )
    
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='强制重新训练已存在的模型'
    )
    
    parser.add_argument(
        '--csv',
        action='store_true',
        help='从CSV文件训练'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='静默模式'
    )
    
    args = parser.parse_args()
    
    # 配置日志
    setup_logging()
    
    if not args.quiet:
        print_banner()
        print_device_info()
    
    # 确保目录存在
    Path('logs').mkdir(exist_ok=True)
    Path(config.get('model.save_path', './trained_models')).mkdir(parents=True, exist_ok=True)
    
    # 执行训练
    try:
        train_models(
            model_type=args.type,
            node_id=args.id,
            force=args.force,
            use_csv=args.csv
        )
    except KeyboardInterrupt:
        logger.warning("训练被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"训练失败: {e}")
        raise


if __name__ == '__main__':
    main()
