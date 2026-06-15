"""
联邦学习模块

实现跨厂区模型协作功能，支持各厂区本地训练，仅上传梯度或加密模型更新，
中心服务聚合全局模型并下发。支持差分隐私和安全聚合等隐私保护机制。

主要组件:
- privacy: 隐私保护模块（差分隐私、安全聚合）
- aggregator: 模型聚合器（FedAvg等）
- client: 联邦学习客户端（厂区端）
- server: 联邦学习服务器（中心端）

使用示例:
    from app.federated import FederatedClient, FederatedServer
    
    # 厂区端
    client = FederatedClient(factory_id='factory_001')
    client.local_train(model_type='bolt', node_id='B001')
    update = client.get_model_update()
    client.upload_update(update)
    
    # 中心端
    server = FederatedServer()
    server.start_round()
    server.collect_updates()
    global_model = server.aggregate_updates()
    server.distribute_model(global_model)
"""

from app.federated.privacy import PrivacyEngine, DifferentialPrivacy, SecureAggregator, create_privacy_engine
from app.federated.aggregator import (
    ModelAggregator,
    FedAvgAggregator,
    WeightedAvgAggregator,
    MedianAggregator,
    TrimmedMeanAggregator,
    create_aggregator
)
from app.federated.client import FederatedClient
from app.federated.server import FederatedServer

__all__ = [
    'PrivacyEngine',
    'DifferentialPrivacy',
    'SecureAggregator',
    'create_privacy_engine',
    'ModelAggregator',
    'FedAvgAggregator',
    'WeightedAvgAggregator',
    'MedianAggregator',
    'TrimmedMeanAggregator',
    'create_aggregator',
    'FederatedClient',
    'FederatedServer',
]
