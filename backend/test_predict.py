#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型预测测试脚本

用于测试训练好的模型的预测功能。

使用方法:
    python test_predict.py                          # 使用示例数据测试
    python test_predict.py --type bolt --id B001    # 测试指定螺栓
    python test_predict.py --type flange --id F001  # 测试指定法兰面
    python test_predict.py --risk                   # 测试风险评估
    python test_predict.py --forecast               # 测试月度预测
"""

import sys
import json
import argparse
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger

from app.services.prediction_service import PredictionService
from app.services.training_service import TrainingService
from app.models.bolt_lstm import BoltLSTMModel
from app.models.flange_attention import FlangeAttentionModel
from app.models.risk_model import BayesianRiskModel
from app.utils.device import get_device


def setup_logging():
    """配置日志"""
    logger.remove()
    logger.add(
        sys.stderr,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="INFO"
    )


def generate_sample_bolt_data(n_points: int = 100, pattern: str = 'normal') -> tuple:
    """
    生成示例螺栓数据
    
    Args:
        n_points: 数据点数量
        pattern: 数据模式 (normal/warning/fault)
    
    Returns:
        tuple: (数据数组, 时间戳列表)
    """
    np.random.seed(42)
    
    base_time = datetime.now() - timedelta(hours=n_points)
    timestamps = [
        (base_time + timedelta(minutes=i)).strftime('%Y%m%d %H:%M:%S')
        for i in range(n_points)
    ]
    
    if pattern == 'normal':
        # 正常数据：在正常范围内小幅波动
        data = 600 + np.random.randn(n_points) * 20
    elif pattern == 'warning':
        # 预警数据：逐渐下降
        data = 600 - np.linspace(0, 100, n_points) + np.random.randn(n_points) * 10
    elif pattern == 'fault':
        # 故障数据：骤降
        data = np.ones(n_points) * 600
        data[80:] = 300 + np.random.randn(20) * 10
    else:
        data = np.random.randn(n_points) * 100 + 500
    
    return data, timestamps


def generate_sample_flange_data(n_bolts: int = 5, n_points: int = 100) -> list:
    """
    生成示例法兰面数据
    
    Args:
        n_bolts: 螺栓数量
        n_points: 每个螺栓的数据点数量
    
    Returns:
        list: 多螺栓数据列表
    """
    np.random.seed(42)
    
    multi_bolt_data = []
    for i in range(n_bolts):
        # 每个螺栓稍有不同的基准值
        base = 580 + i * 10
        data = base + np.random.randn(n_points) * 15
        multi_bolt_data.append(data)
    
    return multi_bolt_data


def test_bolt_prediction(bolt_id: str = 'B001', pattern: str = 'normal'):
    """
    测试螺栓预测
    """
    logger.info(f"测试螺栓预测: {bolt_id}, 模式: {pattern}")
    
    # 生成测试数据
    data, timestamps = generate_sample_bolt_data(100, pattern)
    
    # 创建预测服务
    service = PredictionService()
    
    # 执行预测
    result = service.predict_bolt(
        bolt_id=bolt_id,
        data=data,
        timestamps=timestamps,
        save_to_db=False
    )
    
    # 输出结果
    logger.info("预测结果:")
    logger.info(f"  状态: {result['status']} (代码: {result['status_code']})")
    logger.info(f"  置信度: {result['confidence']:.2%}")
    logger.info(f"  风险评分: {result['risk_score']}/10")
    logger.info(f"  风险等级: {result['risk_level']}")
    logger.info(f"  诊断: {result['diagnosis']}")
    logger.info(f"  建议: {', '.join(result['recommendations'][:2])}")
    
    return result


def test_flange_prediction(flange_id: str = 'F001'):
    """
    测试法兰面预测
    """
    logger.info(f"测试法兰面预测: {flange_id}")
    
    # 生成测试数据
    multi_bolt_data = generate_sample_flange_data(5, 100)
    
    # 创建预测服务
    service = PredictionService()
    
    # 执行预测
    result = service.predict_flange(
        flange_id=flange_id,
        multi_bolt_data=multi_bolt_data,
        save_to_db=False
    )
    
    # 输出结果
    logger.info("预测结果:")
    logger.info(f"  状态: {result['status']} (代码: {result['status_code']})")
    logger.info(f"  置信度: {result['confidence']:.2%}")
    logger.info(f"  风险评分: {result['risk_score']}/10")
    logger.info(f"  风险等级: {result['risk_level']}")
    logger.info(f"  螺栓数量: {len(multi_bolt_data)}")
    logger.info(f"  诊断: {result['diagnosis']}")
    
    return result


def test_risk_assessment():
    """
    测试风险评估
    """
    logger.info("测试风险评估")
    
    risk_model = BayesianRiskModel()
    
    # 测试不同场景
    scenarios = [
        ("正常", np.random.randn(100) * 20 + 600),
        ("边界", np.random.randn(100) * 30 + 420),
        ("异常", np.random.randn(100) * 50 + 350),
    ]
    
    for name, data in scenarios:
        assessment = risk_model.assess_risk(data)
        logger.info(f"场景 [{name}]:")
        logger.info(f"  评分: {assessment.score}/10, 等级: {assessment.level.value}")
        logger.info(f"  因素: {assessment.factors[:2]}")
    
    return True


def test_api_format():
    """
    测试API格式的输入
    """
    logger.info("测试API格式输入")
    
    # 模拟API请求格式
    bolt_request = {
        "螺栓id": "B001",
        "data": [
            ["20250201 00:00:00", 400.00],
            ["20250201 00:01:00", 401.50],
            ["20250201 00:02:00", 399.80]
        ] + [
            [f"20250201 00:{i:02d}:00", 400 + np.random.randn() * 10]
            for i in range(3, 100)
        ]
    }
    
    # 解析数据
    timestamps = [item[0] for item in bolt_request['data']]
    values = np.array([item[1] for item in bolt_request['data']])
    
    # 预测
    service = PredictionService()
    result = service.predict_bolt(
        bolt_id=bolt_request['螺栓id'],
        data=values,
        timestamps=timestamps,
        save_to_db=False
    )
    
    logger.info(f"API格式测试结果: {result['status']}")
    
    return result


def test_model_loading():
    """
    测试模型加载
    """
    logger.info("测试模型加载")
    
    device = get_device()
    logger.info(f"使用设备: {device}")
    
    # 测试螺栓模型
    bolt_model = BoltLSTMModel(bolt_id='test')
    logger.info(f"螺栓模型已加载: is_trained={bolt_model.is_trained}")
    
    # 测试法兰面模型
    flange_model = FlangeAttentionModel(flange_id='test')
    logger.info(f"法兰面模型已加载: is_trained={flange_model.is_trained}")
    
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='螺栓预紧力预测模型测试工具'
    )
    
    parser.add_argument(
        '--type', '-t',
        type=str,
        choices=['bolt', 'flange', 'all'],
        default='all',
        help='测试类型'
    )
    
    parser.add_argument(
        '--id', '-i',
        type=str,
        default=None,
        help='节点ID'
    )
    
    parser.add_argument(
        '--pattern', '-p',
        type=str,
        choices=['normal', 'warning', 'fault'],
        default='normal',
        help='数据模式'
    )
    
    parser.add_argument(
        '--risk', '-r',
        action='store_true',
        help='测试风险评估'
    )
    
    parser.add_argument(
        '--api',
        action='store_true',
        help='测试API格式'
    )
    
    parser.add_argument(
        '--load',
        action='store_true',
        help='测试模型加载'
    )
    
    args = parser.parse_args()
    
    # 配置日志
    setup_logging()
    
    logger.info("=" * 60)
    logger.info("螺栓预紧力预测系统 - 测试工具")
    logger.info("=" * 60)
    
    try:
        if args.load:
            test_model_loading()
        elif args.risk:
            test_risk_assessment()
        elif args.api:
            test_api_format()
        elif args.type == 'bolt':
            test_bolt_prediction(args.id or 'B001', args.pattern)
        elif args.type == 'flange':
            test_flange_prediction(args.id or 'F001')
        else:
            # 测试所有
            logger.info("\n--- 测试螺栓预测 (正常) ---")
            test_bolt_prediction('B001', 'normal')
            
            logger.info("\n--- 测试螺栓预测 (预警) ---")
            test_bolt_prediction('B002', 'warning')
            
            logger.info("\n--- 测试螺栓预测 (故障) ---")
            test_bolt_prediction('B003', 'fault')
            
            logger.info("\n--- 测试法兰面预测 ---")
            test_flange_prediction('F001')
            
            logger.info("\n--- 测试风险评估 ---")
            test_risk_assessment()
        
        logger.info("\n测试完成!")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        raise


if __name__ == '__main__':
    main()
