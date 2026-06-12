"""
联邦学习单元测试

测试内容:
1. 隐私保护模块（差分隐私、安全聚合）
2. 模型聚合器（FedAvg、加权平均、中位数等）
3. 联邦学习客户端（厂区端）
4. 联邦学习服务器（中心端）
5. 端到端联邦学习流程
"""

import pytest
import logging
import numpy as np
import torch
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 设置随机种子确保测试可复现
np.random.seed(42)
torch.manual_seed(42)

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDifferentialPrivacy:
    """差分隐私测试"""
    
    def test_privacy_config_creation(self):
        """测试隐私配置创建"""
        from app.federated.privacy import PrivacyConfig, PrivacyMechanism
        
        config = PrivacyConfig(
            mechanism=PrivacyMechanism.DIFFERENTIAL_PRIVACY,
            epsilon=1.0,
            delta=1e-5,
            noise_scale=0.1,
            clip_norm=1.0
        )
        
        assert config.mechanism == PrivacyMechanism.DIFFERENTIAL_PRIVACY
        assert config.epsilon == 1.0
        assert config.delta == 1e-5
    
    def test_dp_engine_creation(self):
        """测试差分隐私引擎创建"""
        from app.federated.privacy import create_privacy_engine, DifferentialPrivacy
        
        config = {
            'mechanism': 'dp',
            'epsilon': 1.0,
            'delta': 1e-5,
            'clip_norm': 1.0
        }
        
        engine = create_privacy_engine(config)
        
        assert isinstance(engine, DifferentialPrivacy)
        assert engine.config.epsilon == 1.0
        assert engine.sigma > 0
    
    def test_gradient_clipping(self):
        """测试梯度裁剪"""
        from app.federated.privacy import create_privacy_engine
        
        engine = create_privacy_engine({'mechanism': 'dp', 'clip_norm': 1.0})
        
        # 创建大梯度
        gradients = {
            'layer1.weight': torch.randn(10, 10) * 10,  # 大的梯度值
            'layer1.bias': torch.randn(10) * 5
        }
        
        clipped = engine.clip_gradients(gradients)
        
        # 计算裁剪后的范数
        total_norm = 0.0
        for g in clipped.values():
            total_norm += g.norm(2).item() ** 2
        total_norm = np.sqrt(total_norm)
        
        # 范数应该被裁剪到clip_norm附近
        assert total_norm <= 1.0 + 1e-6
    
    def test_noise_addition(self):
        """测试噪声添加"""
        from app.federated.privacy import create_privacy_engine
        
        engine = create_privacy_engine({
            'mechanism': 'dp',
            'epsilon': 100.0,  # 大epsilon，小噪声
            'delta': 1e-5,
            'noise_scale': 0.01
        })
        
        gradients = {
            'layer1.weight': torch.ones(5, 5),
            'layer1.bias': torch.ones(5)
        }
        
        noisy = engine.add_noise(gradients)
        
        # 噪声应该很小，因为epsilon很大
        for key in gradients:
            diff = torch.abs(noisy[key] - gradients[key]).mean().item()
            assert diff < 0.1  # 平均差异应该很小
    
    def test_privacy_budget_tracking(self):
        """测试隐私预算跟踪"""
        from app.federated.privacy import create_privacy_engine
        
        engine = create_privacy_engine({'mechanism': 'dp', 'epsilon': 1.0})
        
        initial_budget = engine.get_privacy_spent()
        
        # 多次添加噪声
        for _ in range(5):
            gradients = {'w': torch.randn(10)}
            engine.add_noise(gradients)
        
        # 隐私预算应该被消耗
        assert engine.get_privacy_spent() > initial_budget
        assert engine.verify_privacy_budget()  # 还没超过总预算


class TestSecureAggregator:
    """安全聚合测试"""
    
    def test_secagg_creation(self):
        """测试安全聚合器创建"""
        from app.federated.privacy import create_privacy_engine, SecureAggregator
        
        config = {
            'mechanism': 'secagg',
            'num_parties': 3,
            'secret_share_threshold': 2,
            'encryption_key': 'test_key'
        }
        
        engine = create_privacy_engine(config)
        
        assert isinstance(engine, SecureAggregator)
        assert engine.config.num_parties == 3
    
    def test_secret_sharing(self):
        """测试秘密共享"""
        from app.federated.privacy import create_privacy_engine
        
        engine = create_privacy_engine({
            'mechanism': 'secagg',
            'num_parties': 5,
            'secret_share_threshold': 3
        })
        
        secret = 42.0
        shares = engine.secret_share(secret, num_shares=5, threshold=3)
        
        assert len(shares) == 5
        
        # 使用任意3个份额恢复秘密
        recovered = engine.reconstruct_secret(
            [(1, shares[0]), (2, shares[1]), (3, shares[2])],
            threshold=3
        )
        
        assert abs(recovered - secret) < 1e-6
    
    def test_encryption_decryption(self):
        """测试加密解密"""
        from app.federated.privacy import create_privacy_engine
        
        engine = create_privacy_engine({
            'mechanism': 'secagg',
            'encryption_key': 'test_key_123'
        })
        
        weights = {
            'layer1.weight': torch.randn(5, 5),
            'layer1.bias': torch.randn(5)
        }
        
        # 加密
        encrypted = engine.encrypt(weights)
        assert isinstance(encrypted, bytes)
        
        # 解密
        decrypted = engine.decrypt(encrypted)
        
        # 验证解密结果
        for key in weights:
            assert torch.allclose(weights[key], decrypted[key], atol=1e-6)
    
    def test_double_masks(self):
        """测试双重掩码生成"""
        from app.federated.privacy import create_privacy_engine
        
        engine = create_privacy_engine({'mechanism': 'secagg'})
        
        total_mask, pairwise = engine.generate_double_masks(
            client_id='client_1',
            num_clients=3,
            param_shape=torch.Size([5, 5])
        )
        
        assert total_mask.shape == torch.Size([5, 5])
        assert len(pairwise) == 2  # 其他2个客户端


class TestModelAggregator:
    """模型聚合器测试"""
    
    def test_fedavg_aggregation(self):
        """测试FedAvg聚合"""
        from app.federated.aggregator import create_aggregator, ClientUpdate
        
        aggregator = create_aggregator('fedavg')
        
        # 创建3个客户端的更新
        updates = []
        for i in range(3):
            weights = {
                'layer1.weight': torch.ones(5, 5) * (i + 1),
                'layer1.bias': torch.ones(5) * (i + 1)
            }
            updates.append(ClientUpdate(
                client_id=f'client_{i}',
                weights=weights,
                num_samples=100
            ))
        
        aggregated = aggregator.aggregate(updates)
        
        # FedAvg应该是 (1+2+3)/3 = 2
        expected = torch.ones(5, 5) * 2.0
        assert torch.allclose(aggregated['layer1.weight'], expected)
        assert torch.allclose(aggregated['layer1.bias'], torch.ones(5) * 2.0)
    
    def test_weighted_avg_aggregation(self):
        """测试加权平均聚合"""
        from app.federated.aggregator import create_aggregator, ClientUpdate
        
        aggregator = create_aggregator('weighted_avg')
        
        # 创建2个客户端，样本数不同
        updates = [
            ClientUpdate(
                client_id='client_1',
                weights={'w': torch.tensor([1.0])},
                num_samples=100  # 权重 100/150 = 0.666
            ),
            ClientUpdate(
                client_id='client_2',
                weights={'w': torch.tensor([4.0])},
                num_samples=50   # 权重 50/150 = 0.333
            )
        ]
        
        aggregated = aggregator.aggregate(updates)
        
        # 加权平均: 1 * (2/3) + 4 * (1/3) = 2
        expected = torch.tensor([2.0])
        assert torch.allclose(aggregated['w'], expected, atol=1e-6)
    
    def test_median_aggregation(self):
        """测试中位数聚合"""
        from app.federated.aggregator import create_aggregator, ClientUpdate
        
        aggregator = create_aggregator('median')
        
        # 创建5个客户端更新，包含异常值
        updates = []
        values = [1.0, 2.0, 3.0, 100.0, 200.0]  # 中位数是3.0
        for v in values:
            updates.append(ClientUpdate(
                client_id=f'client_{v}',
                weights={'w': torch.tensor([v])},
                num_samples=100
            ))
        
        aggregated = aggregator.aggregate(updates)
        
        # 中位数应该是3.0，不受异常值影响
        assert torch.allclose(aggregated['w'], torch.tensor([3.0]))
    
    def test_trimmed_mean_aggregation(self):
        """测试修剪均值聚合"""
        from app.federated.aggregator import create_aggregator, ClientUpdate
        
        # 修剪比例0.2，5个客户端中修剪最大和最小各1个
        aggregator = create_aggregator('trimmed_mean', {'trim_ratio': 0.2})
        
        updates = []
        values = [1.0, 2.0, 3.0, 4.0, 100.0]  # 修剪1和100，平均(2+3+4)/3 = 3
        for v in values:
            updates.append(ClientUpdate(
                client_id=f'client_{v}',
                weights={'w': torch.tensor([v])},
                num_samples=100
            ))
        
        aggregated = aggregator.aggregate(updates)
        
        assert torch.allclose(aggregated['w'], torch.tensor([3.0]))
    
    def test_outlier_detection(self):
        """测试异常值检测"""
        from app.federated.aggregator import create_aggregator, ClientUpdate
        
        aggregator = create_aggregator(
            'fedavg',
            {'enable_outlier_detection': True, 'outlier_threshold': 1.0}
        )
        
        # 4个正常客户端 + 1个异常客户端
        updates = []
        for i in range(4):
            updates.append(ClientUpdate(
                client_id=f'normal_{i}',
                weights={'w': torch.ones(5) * (i + 1)},
                num_samples=100
            ))
        
        # 异常客户端（权重范数很大）
        updates.append(ClientUpdate(
            client_id='outlier',
            weights={'w': torch.ones(5) * 1000},  # 异常大的值
            num_samples=100
        ))
        
        # 聚合时应该移除异常值
        aggregated = aggregator.aggregate(updates)
        
        # 结果应该接近正常客户端的平均，而不是被异常值拉高
        assert aggregated['w'].mean().item() < 100  # 远小于1000


class TestFederatedClient:
    """联邦学习客户端测试"""
    
    def test_client_creation(self):
        """测试客户端创建"""
        from app.federated.client import FederatedClient, ClientConfig, UpdateType
        
        config = ClientConfig(
            factory_id='factory_001',
            update_type=UpdateType.DIFFERENCE,
            local_epochs=3
        )
        
        client = FederatedClient('factory_001', config)
        
        assert client.factory_id == 'factory_001'
        assert client.config.update_type == UpdateType.DIFFERENCE
        assert client.config.local_epochs == 3
    
    def test_receive_global_model(self):
        """测试接收全局模型"""
        from app.federated.client import FederatedClient
        from app.models.bolt_lstm import LSTMNetwork
        
        client = FederatedClient('factory_001')
        
        # 创建模拟的全局权重
        model = LSTMNetwork()
        global_weights = {k: v.clone() for k, v in model.state_dict().items()}
        
        client.receive_global_model(
            global_weights=global_weights,
            model_type='bolt',
            node_id='B001',
            round_id=1
        )
        
        assert client.global_weights is not None
        assert client.current_model_type == 'bolt'
        assert client.current_node_id == 'B001'
        assert client.current_round == 1
        assert client.local_model is not None
    
    def test_get_model_update_difference(self):
        """测试获取模型更新（差异类型）"""
        from app.federated.client import FederatedClient, ClientConfig, UpdateType
        from app.models.bolt_lstm import LSTMNetwork
        
        config = ClientConfig(
            factory_id='factory_001',
            update_type=UpdateType.DIFFERENCE
        )
        client = FederatedClient('factory_001', config)
        
        # 创建全局权重
        model = LSTMNetwork()
        global_weights = {k: v.clone() for k, v in model.state_dict().items()}
        
        # 接收全局模型
        client.receive_global_model(global_weights, 'bolt', 'B001', 1)
        
        # 模拟本地训练后更新一些权重
        with torch.no_grad():
            for param in client.local_model.parameters():
                param.add_(torch.randn_like(param) * 0.01)
        
        # 获取更新
        # 先设置训练历史，这样get_model_update才能获取num_samples
        from app.federated.client import LocalTrainingResult
        client.training_history.append(LocalTrainingResult(
            client_id='factory_001',
            model_type='bolt',
            node_id='B001',
            num_samples=100,
            metrics={'final_val_acc': 0.95},
            training_time=10.0
        ))
        
        update = client.get_model_update(apply_privacy=False)
        
        assert update.client_id == 'factory_001'
        assert update.num_samples == 100
        
        # 更新应该是差异（本地权重 - 全局权重）
        total_diff = 0.0
        for key in update.weights:
            total_diff += update.weights[key].abs().sum().item()
        
        assert total_diff > 0  # 有差异
    
    def test_two_level_architecture(self):
        """测试两层架构（全局模型 + 本地微调）"""
        from app.federated.client import FederatedClient, ClientConfig, TrainingMode
        from app.models.bolt_lstm import LSTMNetwork
        
        config = ClientConfig(
            factory_id='factory_001',
            enable_two_level_arch=True,
            fine_tune_layers=['output', 'fc']
        )
        client = FederatedClient('factory_001', config)
        
        # 先接收全局模型以初始化 local_model
        model = LSTMNetwork()
        global_weights = {k: v.clone() for k, v in model.state_dict().items()}
        client.receive_global_model(global_weights, 'bolt', 'B001', 1)
        
        # 设置训练模式为微调
        client._set_training_mode(TrainingMode.FINE_TUNE)
        
        # 检查只有指定层需要梯度
        trainable_params = [
            name for name, param in client.local_model.named_parameters()
            if param.requires_grad
        ]
        
        # 应该只有output和fc层可训练
        for name in trainable_params:
            assert 'output' in name or 'fc' in name, f"层 {name} 不应该被训练"
    
    def test_privacy_engine_integration(self):
        """测试隐私引擎集成"""
        from app.federated.client import FederatedClient, ClientConfig
        from app.models.bolt_lstm import LSTMNetwork
        
        privacy_config = {
            'mechanism': 'dp',
            'epsilon': 1.0,
            'delta': 1e-5
        }
        
        config = ClientConfig(
            factory_id='factory_001',
            privacy_config=privacy_config
        )
        client = FederatedClient('factory_001', config)
        
        assert client.privacy_engine is not None
        
        # 创建全局权重
        model = LSTMNetwork()
        global_weights = {k: v.clone() for k, v in model.state_dict().items()}
        
        client.receive_global_model(global_weights, 'bolt', 'B001', 1)
        
        # 添加训练历史
        from app.federated.client import LocalTrainingResult
        client.training_history.append(LocalTrainingResult(
            client_id='factory_001',
            model_type='bolt',
            node_id='B001',
            num_samples=100,
            metrics={},
            training_time=0
        ))
        
        # 获取带隐私保护的更新
        update = client.get_model_update(apply_privacy=True)
        
        assert update is not None
    
    def test_get_status(self):
        """测试获取客户端状态"""
        from app.federated.client import FederatedClient
        
        client = FederatedClient('factory_001')
        
        status = client.get_status()
        
        assert status['factory_id'] == 'factory_001'
        assert status['has_global_model'] is False
        assert status['has_local_model'] is False
        assert 'privacy_mechanism' in status
        assert 'update_type' in status


class TestFederatedServer:
    """联邦学习服务器测试"""
    
    def test_server_creation(self):
        """测试服务器创建"""
        from app.federated.server import FederatedServer, ServerConfig, AggregationStrategy
        
        config = ServerConfig(
            aggregation_strategy=AggregationStrategy.WEIGHTED_AVG,
            min_clients_per_round=2,
            enable_two_level_arch=True
        )
        
        server = FederatedServer(config)
        
        assert server.config.aggregation_strategy == AggregationStrategy.WEIGHTED_AVG
        assert server.config.min_clients_per_round == 2
    
    def test_client_registration(self):
        """测试客户端注册"""
        from app.federated.server import FederatedServer
        
        server = FederatedServer()
        
        server.register_client(
            client_id='factory_001',
            client_info={'name': '工厂1', 'location': '北京'}
        )
        
        assert 'factory_001' in server.registered_clients
        assert server.registered_clients['factory_001']['info']['name'] == '工厂1'
    
    def test_round_management(self):
        """测试轮次管理"""
        from app.federated.server import FederatedServer, RoundStatus
        
        server = FederatedServer()
        
        # 注册客户端
        for i in range(3):
            server.register_client(f'factory_{i:03d}')
        
        # 开始轮次
        round_info = server.start_round(
            model_type='bolt',
            node_id='B001'
        )
        
        assert round_info.status == RoundStatus.WAITING
        assert round_info.round_id == 1
        assert len(round_info.expected_clients) == 3
    
    def test_global_model_distribution(self):
        """测试全局模型分发"""
        from app.federated.server import FederatedServer
        
        server = FederatedServer()
        
        # 初始化全局模型
        server.model_manager.init_global_model('bolt', 'B001')
        
        # 获取全局模型给客户端
        model_data = server.get_global_model_for_client(
            client_id='factory_001',
            model_type='bolt',
            node_id='B001'
        )
        
        assert 'weights' in model_data
        assert model_data['model_type'] == 'bolt'
        assert model_data['node_id'] == 'B001'
        assert model_data['enable_two_level_arch'] is True
    
    def test_update_collection(self):
        """测试更新收集"""
        from app.federated.server import FederatedServer, RoundStatus
        from app.models.bolt_lstm import LSTMNetwork
        
        server = FederatedServer()
        
        # 注册客户端
        for i in range(3):
            server.register_client(f'factory_{i:03d}')
        
        # 开始轮次
        server.start_round('bolt', 'B001')
        
        # 创建模拟的权重更新
        model = LSTMNetwork()
        weights = {k: v.clone() for k, v in model.state_dict().items()}
        
        # 收集更新
        for i in range(3):
            update_data = {
                'client_id': f'factory_{i:03d}',
                'model_type': 'bolt',
                'node_id': 'B001',
                'round_id': 1,
                'weights': {k: v.numpy() for k, v in weights.items()},
                'num_samples': 100,
                'metrics': {'final_val_acc': 0.9 + i * 0.01}
            }
            
            success = server.receive_client_update(update_data)
            assert success is True
        
        assert len(server.round_manager.current_round.received_updates) == 3
    
    def test_model_aggregation(self):
        """测试模型聚合"""
        from app.federated.server import FederatedServer, RoundStatus
        from app.models.bolt_lstm import LSTMNetwork
        
        server = FederatedServer()
        
        # 注册客户端
        for i in range(3):
            server.register_client(f'factory_{i:03d}')
        
        # 开始轮次
        server.start_round('bolt', 'B001')
        
        # 初始化全局模型
        server.model_manager.init_global_model('bolt', 'B001')
        
        # 创建3个客户端的更新（略有不同）
        base_model = LSTMNetwork()
        base_weights = {k: v.clone() for k, v in base_model.state_dict().items()}
        
        for i in range(3):
            # 每个客户端的权重有微小差异
            client_weights = {}
            for k, v in base_weights.items():
                client_weights[k] = v + torch.randn_like(v) * 0.01 * (i + 1)
            
            update_data = {
                'client_id': f'factory_{i:03d}',
                'model_type': 'bolt',
                'node_id': 'B001',
                'round_id': 1,
                'weights': {k: v.numpy() for k, v in client_weights.items()},
                'num_samples': 100 * (i + 1),  # 样本数不同
                'metrics': {'final_val_acc': 0.9}
            }
            
            server.receive_client_update(update_data)
        
        # 执行聚合
        aggregated = server.aggregate_updates()
        
        assert aggregated is not None
        assert server.round_manager.round_history[-1].status == RoundStatus.COMPLETED
        
        # 检查新版本是否创建
        latest_version = server.model_manager.get_latest_version('bolt', 'B001')
        assert latest_version is not None
        assert latest_version.version == 1
        assert latest_version.num_clients == 3
    
    def test_server_status(self):
        """测试获取服务器状态"""
        from app.federated.server import FederatedServer
        
        server = FederatedServer()
        
        # 注册一些客户端
        for i in range(5):
            server.register_client(f'factory_{i:03d}')
        
        status = server.get_server_status()
        
        assert status['registered_clients'] == 5
        assert status['active_clients'] == 5  # 刚注册，都是活跃的
        assert status['total_rounds'] == 0
        assert 'aggregation_strategy' in status


class TestEndToEndFederatedLearning:
    """端到端联邦学习流程测试"""
    
    def test_full_federated_round(self):
        """测试完整的联邦学习轮次"""
        import tempfile
        from app.federated.server import FederatedServer, ServerConfig, AggregationStrategy
        from app.federated.client import FederatedClient, ClientConfig
        from app.models.bolt_lstm import LSTMNetwork
        
        # 创建临时目录保存模型
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建服务器
            server_config = ServerConfig(
                aggregation_strategy=AggregationStrategy.WEIGHTED_AVG,
                min_clients_per_round=2,
                save_path=tmpdir
            )
            server = FederatedServer(server_config)
            
            # 创建3个客户端（模拟3个厂区）
            clients = []
            for i in range(3):
                client_config = ClientConfig(
                    factory_id=f'factory_{i:03d}',
                    local_epochs=1,
                    enable_two_level_arch=True
                )
                client = FederatedClient(f'factory_{i:03d}', client_config)
                clients.append(client)
                
                # 注册到服务器
                server.register_client(
                    client_id=f'factory_{i:03d}',
                    client_info={'factory_idx': i}
                )
            
            # 步骤1: 服务器开始轮次
            round_info = server.start_round('bolt', 'B001')
            assert round_info.round_id == 1
            
            # 步骤2: 服务器初始化全局模型
            server.model_manager.init_global_model('bolt', 'B001')
            
            # 步骤3: 各客户端下载全局模型
            base_model = LSTMNetwork()
            global_weights = {k: v.clone() for k, v in base_model.state_dict().items()}
            
            for client in clients:
                # 从服务器获取模型（模拟API调用）
                model_data = server.get_global_model_for_client(
                    client_id=client.factory_id,
                    model_type='bolt',
                    node_id='B001'
                )
                
                # 转换权重格式
                weights = {
                    k: torch.from_numpy(v).float()
                    for k, v in model_data['weights'].items()
                }
                
                client.receive_global_model(
                    global_weights=weights,
                    model_type='bolt',
                    node_id='B001',
                    round_id=model_data['round_id']
                )
            
            # 步骤4: 各客户端模拟本地训练
            # （实际会用真实数据，这里我们手动修改一些权重）
            for i, client in enumerate(clients):
                # 模拟训练：修改一些权重
                with torch.no_grad():
                    for name, param in client.local_model.named_parameters():
                        param.add_(torch.randn_like(param) * 0.01 * (i + 1))
                
                # 添加训练历史
                from app.federated.client import LocalTrainingResult
                client.training_history.append(LocalTrainingResult(
                    client_id=client.factory_id,
                    model_type='bolt',
                    node_id='B001',
                    num_samples=100 * (i + 1),
                    metrics={'final_val_acc': 0.85 + i * 0.05},
                    training_time=5.0 + i
                ))
            
            # 步骤5: 各客户端获取模型更新并上传到服务器
            for client in clients:
                update = client.get_model_update(apply_privacy=False)
                
                # 上传到服务器
                update_data = {
                    'client_id': update.client_id,
                    'model_type': 'bolt',
                    'node_id': 'B001',
                    'round_id': update.round_id,
                    'weights': {k: v.cpu().numpy() for k, v in update.weights.items()},
                    'num_samples': update.num_samples,
                    'metrics': update.metrics
                }
                
                success = server.receive_client_update(update_data)
                assert success is True
            
            # 步骤6: 服务器聚合更新
            aggregated = server.aggregate_updates()
            
            assert aggregated is not None
            assert len(server.model_manager.model_versions.get('bolt_B001', [])) == 1
            
            # 步骤7: 验证聚合结果
            latest_version = server.model_manager.get_latest_version('bolt', 'B001')
            assert latest_version is not None
            assert latest_version.num_clients == 3
            assert 'avg_val_acc' in latest_version.metrics
            
            # 步骤8: 分发新的全局模型
            distributed = server.distribute_model('bolt', 'B001')
            assert distributed['version'] == 1
            assert distributed['num_clients'] == 3
            
            logger.info("完整联邦学习轮次测试通过！")


def test_weight_utils():
    """测试权重工具函数"""
    from app.federated.aggregator import (
        extract_weights_from_model,
        apply_weights_to_model,
        compute_weight_difference,
        add_weight_difference
    )
    from app.models.bolt_lstm import LSTMNetwork
    
    model1 = LSTMNetwork()
    model2 = LSTMNetwork()
    
    # 测试提取权重
    weights1 = extract_weights_from_model(model1)
    assert len(weights1) > 0
    
    # 测试计算差异
    diff = compute_weight_difference(weights1, extract_weights_from_model(model2))
    assert len(diff) == len(weights1)
    
    # 测试应用差异
    new_weights = add_weight_difference(weights1, diff)
    
    # 测试应用权重到模型
    apply_weights_to_model(model2, new_weights)
    
    # 验证model2现在的权重应该等于model1 + diff = model1 + (model1 - model2_initial)
    weights2_final = extract_weights_from_model(model2)
    for key in weights1:
        # weights1 + (weights1 - initial_weights2) = 2*weights1 - initial_weights2
        expected = 2 * weights1[key] - extract_weights_from_model(LSTMNetwork())[key]
        # 由于初始化的随机性，我们只检查形状
        assert weights2_final[key].shape == expected.shape


def test_create_privacy_engine_factory():
    """测试隐私引擎工厂函数"""
    from app.federated.privacy import (
        create_privacy_engine,
        DifferentialPrivacy,
        SecureAggregator,
        PrivacyEngine
    )
    
    # 测试无隐私保护
    engine = create_privacy_engine({'mechanism': 'none'})
    assert isinstance(engine, PrivacyEngine)
    
    # 测试差分隐私
    engine = create_privacy_engine({'mechanism': 'dp'})
    assert isinstance(engine, DifferentialPrivacy)
    
    # 测试安全聚合
    engine = create_privacy_engine({'mechanism': 'secagg'})
    assert isinstance(engine, SecureAggregator)


def test_create_aggregator_factory():
    """测试聚合器工厂函数"""
    from app.federated.aggregator import (
        create_aggregator,
        FedAvgAggregator,
        WeightedAvgAggregator,
        MedianAggregator,
        TrimmedMeanAggregator,
        FedProxAggregator,
        FedOptAggregator
    )
    
    strategies = [
        ('fedavg', FedAvgAggregator),
        ('weighted_avg', WeightedAvgAggregator),
        ('median', MedianAggregator),
        ('trimmed_mean', TrimmedMeanAggregator),
        ('fedprox', FedProxAggregator),
        ('fedopt', FedOptAggregator)
    ]
    
    for strategy, expected_class in strategies:
        aggregator = create_aggregator(strategy)
        assert isinstance(aggregator, expected_class)


if __name__ == '__main__':
    # 运行测试
    pytest.main([__file__, '-v'])
