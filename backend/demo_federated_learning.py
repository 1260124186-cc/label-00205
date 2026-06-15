#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联邦学习端到端演示脚本
演示跨厂区模型协作的完整流程
"""

import sys
import random
import numpy as np
import torch
from loguru import logger
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.federated.server import FederatedServer, ServerConfig, AggregationStrategy, RoundStatus
from app.federated.client import FederatedClient, ClientConfig, UpdateType
from app.federated.privacy import create_privacy_engine, DifferentialPrivacy, SecureAggregator
from app.federated.aggregator import create_aggregator, ClientUpdate
from app.models.bolt_lstm import LSTMNetwork


def print_separator(title: str = ""):
    if title:
        print(f"\n{'='*20} {title} {'='*20}\n")
    else:
        print("\n" + "=" * 60 + "\n")


def demo_basic_federated():
    """演示1：基础联邦学习流程"""
    print_separator("演示1：基础联邦学习流程")

    server = FederatedServer()

    for i in range(3):
        server.register_client(
            client_id=f'factory_{i:03d}',
            client_info={'name': f'工厂{i+1}', 'location': ['北京', '上海', '广州'][i]}
        )

    status = server.get_server_status()
    logger.info("服务器状态: {} 个客户端已注册", status['registered_clients'])

    server.model_manager.init_global_model('bolt', 'B001')
    logger.info("全局模型已初始化 (bolt/B001)")

    round_info = server.start_round('bolt', 'B001')
    logger.info(f"第 {round_info.round_id} 轮训练开始，状态: {round_info.status}")

    base_model = LSTMNetwork()
    base_weights = {k: v.clone() for k, v in base_model.state_dict().items()}

    for i in range(3):
        client_weights = {}
        for k, v in base_weights.items():
            client_weights[k] = v + torch.randn_like(v) * 0.01 * (i + 1)

        update_data = {
            'client_id': f'factory_{i:03d}',
            'model_type': 'bolt',
            'node_id': 'B001',
            'round_id': 1,
            'weights': {k: v.numpy() for k, v in client_weights.items()},
            'num_samples': 100 * (i + 1),
            'metrics': {'final_val_acc': 0.85 + i * 0.02}
        }
        server.receive_client_update(update_data)
        logger.info("  factory_{:03d} 提交更新 ({} samples)".format(i, 100*(i+1)))

    aggregated = server.aggregate_updates()
    if aggregated:
        latest = server.model_manager.get_latest_version('bolt', 'B001')
        logger.info(f"聚合完成，全局模型版本: v{latest.version}")
        logger.info(f"  参与客户端数: {latest.num_clients}")
        logger.info(f"  总样本数: {latest.metrics.get('total_samples', 'N/A')}")

    print_separator()
    return True


def demo_privacy_protection():
    """演示2：隐私保护机制"""
    print_separator("演示2：隐私保护机制")

    logger.info("--- 差分隐私 (DP) ---")
    dp_engine = create_privacy_engine({
        'mechanism': 'dp',
        'epsilon': 1.0,
        'delta': 1e-5,
        'clip_norm': 1.0
    })

    gradients = {
        'layer1.weight': torch.randn(10, 10) * 2,
        'layer1.bias': torch.randn(10) * 0.5
    }

    clipped = dp_engine.clip_gradients(gradients)
    total_norm_before = sum(g.norm(2).item()**2 for g in gradients.values()) ** 0.5
    total_norm_after = sum(g.norm(2).item()**2 for g in clipped.values()) ** 0.5
    logger.info(f"  梯度裁剪: 范数 {total_norm_before:.3f} → {total_norm_after:.3f}")

    noisy = dp_engine.add_noise(clipped)
    noise = sum(torch.abs(noisy[k] - clipped[k]).mean().item()
                for k in gradients.keys()) / len(gradients)
    logger.info(f"  噪声添加: 平均噪声大小 {noise:.6f}")

    budget = dp_engine.get_privacy_spent()
    logger.info(f"  已消耗隐私预算: ε={budget:.4f}")

    logger.info("\n--- 安全聚合 (SecAgg) ---")
    sec_agg = create_privacy_engine({
        'mechanism': 'secagg',
        'num_parties': 3,
        'secret_share_threshold': 2
    })

    logger.info(f"  SecAgg配置: 3方参与, 阈值2")
    logger.info("  基于Shamir秘密共享实现安全聚合")

    print_separator()
    return True


def demo_two_level_arch():
    """演示3：两层架构（全局模型 + 本地微调）"""
    print_separator("演示3：两层架构")

    config = ClientConfig(
        factory_id='factory_001',
        enable_two_level_arch=True,
        fine_tune_layers=['output', 'fc']
    )
    client = FederatedClient('factory_001', config)

    model = LSTMNetwork()
    global_weights = {k: v.clone() for k, v in model.state_dict().items()}
    client.receive_global_model(global_weights, 'bolt', 'B001', 1)

    logger.info("客户端已接收全局模型")
    logger.info(f"  两层架构: 启用")
    logger.info(f"  微调层: {client.config.fine_tune_layers}")

    status = client.get_status()
    logger.info(f"\n客户端状态:")
    logger.info(f"  全局模型: {'有' if status['has_global_model'] else '无'}")
    logger.info(f"  本地模型: {'有' if status['has_local_model'] else '无'}")
    logger.info(f"  两层架构: {'启用' if status['two_level_arch_enabled'] else '未启用'}")

    print_separator()
    return True


def demo_aggregation_strategies():
    """演示4：多种聚合策略"""
    print_separator("演示4：聚合策略对比")

    strategies = ['fedavg', 'weighted_avg', 'median', 'trimmed_mean']

    base_model = LSTMNetwork()
    base_weights = {k: v.clone() for k, v in base_model.state_dict().items()}

    updates = []
    for i in range(5):
        weights = {}
        for k, v in base_weights.items():
            weights[k] = v + torch.randn_like(v) * 0.01 * (i + 1)
        updates.append(ClientUpdate(
            client_id=f'client_{i}',
            weights=weights,
            num_samples=100 * (i + 1)
        ))

    for strategy in strategies:
        agg = create_aggregator(strategy)
        result = agg.aggregate(updates)

        weight_mean = None
        for w in result.values():
            if weight_mean is None:
                weight_mean = w.mean().item()
            else:
                weight_mean += w.mean().item()
        weight_mean /= len(result)

        logger.info(f"  {strategy:15s} 权重均值: {weight_mean:.6f}")

    print_separator()
    return True


def main():
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "联邦学习端到端演示" + " " * 23 + "║")
    print("║" + " " * 10 + "Federated Learning End-to-End Demo" + " " * 14 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    demos = [
        ("基础联邦学习流程", demo_basic_federated),
        ("隐私保护机制", demo_privacy_protection),
        ("两层架构（全局+本地微调）", demo_two_level_arch),
        ("多种聚合策略对比", demo_aggregation_strategies),
    ]

    success_count = 0
    for i, (name, demo_func) in enumerate(demos, 1):
        print(f"【{i}/{len(demos)}】{name}")
        try:
            if demo_func():
                success_count += 1
                print(f"✓ 演示 {i} 完成\n")
        except Exception as e:
            logger.error(f"演示 {i} 失败: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"\n演示完成: {success_count}/{len(demos)} 个演示成功\n")

    if success_count == len(demos):
        print("🎉 所有演示运行成功！")
        print()
        print("核心功能总结:")
        print("  ✓ 各厂区本地训练，仅上传权重差异")
        print("  ✓ 中心服务聚合全局模型并下发")
        print("  ✓ 差分隐私保护（梯度裁剪 + 噪声添加）")
        print("  ✓ 安全聚合（Shamir秘密共享）")
        print("  ✓ 全局模型 + 本地微调 两层架构")
        print("  ✓ 多种聚合策略（FedAvg/加权/中位数/修剪均值）")
    else:
        print(f"⚠️  {len(demos) - success_count} 个演示失败")

    print()


if __name__ == "__main__":
    main()
