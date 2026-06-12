"""
联邦学习服务器模块（中心端）

实现中心服务器的联邦学习协调功能：
1. 管理联邦学习轮次
2. 分发全局模型给各厂区客户端
3. 收集各厂区的模型更新
4. 聚合并更新全局模型
5. 保存和管理全局模型版本
6. 监控联邦学习过程

主要类:
- FederatedServer: 联邦学习服务器
- GlobalModelManager: 全局模型管理器
- RoundManager: 轮次管理器

使用示例:
    server = FederatedServer()
    server.start_round(model_type='bolt', node_id='B001')
    server.broadcast_global_model()
    # ... 等待客户端上传更新 ...
    server.collect_update(client_update)
    global_model = server.aggregate_updates()
    server.distribute_model(global_model)
"""

import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import time
from pathlib import Path
import copy
import pickle
from datetime import datetime

from app.models.bolt_lstm import BoltLSTMModel, LSTMNetwork
from app.models.flange_attention import FlangeAttentionModel, FlangeAttentionNetwork
from app.federated.privacy import (
    PrivacyEngine,
    create_privacy_engine,
    PrivacyMechanism,
    SecureAggregator
)
from app.federated.aggregator import (
    ClientUpdate,
    ModelAggregator,
    create_aggregator,
    AggregationStrategy,
    extract_weights_from_model,
    apply_weights_to_model,
    add_weight_difference
)
from app.utils.config import config


class RoundStatus(str, Enum):
    """轮次状态"""
    NOT_STARTED = "not_started"
    WAITING = "waiting"  # 等待客户端更新
    AGGREGATING = "aggregating"  # 聚合中
    COMPLETED = "completed"  # 本轮完成
    FAILED = "failed"  # 本轮失败


@dataclass
class RoundInfo:
    """轮次信息"""
    round_id: int
    model_type: str
    node_id: str
    status: RoundStatus
    start_time: float
    end_time: Optional[float] = None
    expected_clients: List[str] = field(default_factory=list)
    received_updates: List[ClientUpdate] = field(default_factory=list)
    aggregated_weights: Optional[Dict[str, torch.Tensor]] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GlobalModelVersion:
    """全局模型版本"""
    version: int
    round_id: int
    model_type: str
    node_id: str
    weights: Dict[str, torch.Tensor]
    created_at: float
    metrics: Dict[str, Any] = field(default_factory=dict)
    num_clients: int = 0


@dataclass
class ServerConfig:
    """服务器配置"""
    # 聚合策略
    aggregation_strategy: AggregationStrategy = AggregationStrategy.WEIGHTED_AVG
    aggregation_config: Optional[Dict[str, Any]] = None
    
    # 隐私配置（服务器端，如需要解密）
    privacy_config: Optional[Dict[str, Any]] = None
    
    # 轮次配置
    max_rounds: int = 100
    round_timeout: int = 3600  # 秒
    min_clients_per_round: int = 2
    
    # 模型保存
    save_path: str = "./trained_models/federated"
    max_versions: int = 10
    
    # 客户端选择
    enable_client_selection: bool = False
    client_selection_ratio: float = 0.8  # 每轮选择的客户端比例
    
    # 两层架构
    enable_two_level_arch: bool = True


class GlobalModelManager:
    """
    全局模型管理器
    
    负责全局模型的初始化、保存、加载和版本管理。
    """
    
    def __init__(self, config: ServerConfig):
        """
        初始化全局模型管理器
        
        Args:
            config: 服务器配置
        """
        self.config = config
        self.save_path = Path(config.save_path)
        self.save_path.mkdir(parents=True, exist_ok=True)
        
        # 全局模型字典: key = f"{model_type}_{node_id}"
        self.global_models: Dict[str, nn.Module] = {}
        self.global_weights: Dict[str, Dict[str, torch.Tensor]] = {}
        self.model_versions: Dict[str, List[GlobalModelVersion]] = {}
        
        logger.info(f"全局模型管理器初始化完成, 保存路径: {self.save_path}")
    
    def init_global_model(
        self,
        model_type: str,
        node_id: str
    ) -> nn.Module:
        """
        初始化全局模型
        
        Args:
            model_type: 模型类型
            node_id: 节点ID
            
        Returns:
            初始化的模型
        """
        model_key = f"{model_type}_{node_id}"
        
        if model_type == 'bolt':
            model = LSTMNetwork()
        elif model_type == 'flange':
            model = FlangeAttentionNetwork()
        else:
            raise ValueError(f"未知模型类型: {model_type}")
        
        self.global_models[model_key] = model
        self.global_weights[model_key] = extract_weights_from_model(model)
        
        logger.info(f"全局模型初始化完成: {model_key}")
        
        return model
    
    def get_global_weights(
        self,
        model_type: str,
        node_id: str
    ) -> Dict[str, torch.Tensor]:
        """
        获取全局模型权重
        
        Args:
            model_type: 模型类型
            node_id: 节点ID
            
        Returns:
            模型权重字典
        """
        model_key = f"{model_type}_{node_id}"
        
        if model_key not in self.global_weights:
            # 初始化模型
            self.init_global_model(model_type, node_id)
        
        # 返回拷贝
        return {k: v.clone() for k, v in self.global_weights[model_key].items()}
    
    def update_global_weights(
        self,
        model_type: str,
        node_id: str,
        new_weights: Dict[str, torch.Tensor],
        round_id: int,
        metrics: Optional[Dict[str, Any]] = None,
        num_clients: int = 0
    ) -> GlobalModelVersion:
        """
        更新全局模型权重
        
        Args:
            model_type: 模型类型
            node_id: 节点ID
            new_weights: 新的权重
            round_id: 轮次ID
            metrics: 指标
            num_clients: 参与的客户端数量
            
        Returns:
            新版本信息
        """
        model_key = f"{model_type}_{node_id}"
        
        # 更新权重
        self.global_weights[model_key] = new_weights
        
        # 更新模型对象
        if model_key in self.global_models:
            apply_weights_to_model(self.global_models[model_key], new_weights)
        
        # 创建版本
        version_num = len(self.model_versions.get(model_key, [])) + 1
        version = GlobalModelVersion(
            version=version_num,
            round_id=round_id,
            model_type=model_type,
            node_id=node_id,
            weights={k: v.clone() for k, v in new_weights.items()},
            created_at=time.time(),
            metrics=metrics or {},
            num_clients=num_clients
        )
        
        if model_key not in self.model_versions:
            self.model_versions[model_key] = []
        self.model_versions[model_key].append(version)
        
        # 清理旧版本
        if len(self.model_versions[model_key]) > self.config.max_versions:
            self.model_versions[model_key] = self.model_versions[model_key][-self.config.max_versions:]
        
        # 保存
        self._save_version(version)
        
        logger.info(
            f"全局模型更新: {model_key}, version={version_num}, "
            f"round={round_id}, clients={num_clients}"
        )
        
        return version
    
    def _save_version(self, version: GlobalModelVersion) -> None:
        """保存模型版本到磁盘"""
        model_key = f"{version.model_type}_{version.node_id}"
        save_file = self.save_path / f"{model_key}_v{version.version}.pt"
        
        save_data = {
            'version': version.version,
            'round_id': version.round_id,
            'model_type': version.model_type,
            'node_id': version.node_id,
            'weights': {k: v.cpu() for k, v in version.weights.items()},
            'created_at': version.created_at,
            'metrics': version.metrics,
            'num_clients': version.num_clients
        }
        
        torch.save(save_data, save_file)
    
    def load_version(
        self,
        model_type: str,
        node_id: str,
        version: Optional[int] = None
    ) -> Optional[GlobalModelVersion]:
        """
        加载指定版本的全局模型
        
        Args:
            model_type: 模型类型
            node_id: 节点ID
            version: 版本号（None则加载最新）
            
        Returns:
            模型版本
        """
        model_key = f"{model_type}_{node_id}"
        
        if model_key not in self.model_versions:
            return None
        
        if version is None:
            return self.model_versions[model_key][-1]
        
        for v in self.model_versions[model_key]:
            if v.version == version:
                return v
        
        return None
    
    def get_latest_version(
        self,
        model_type: str,
        node_id: str
    ) -> Optional[GlobalModelVersion]:
        """获取最新版本"""
        return self.load_version(model_type, node_id)
    
    def get_model_performance_history(
        self,
        model_type: str,
        node_id: str
    ) -> List[Dict[str, Any]]:
        """
        获取模型性能历史
        
        Args:
            model_type: 模型类型
            node_id: 节点ID
            
        Returns:
            性能历史列表
        """
        model_key = f"{model_type}_{node_id}"
        versions = self.model_versions.get(model_key, [])
        
        history = []
        for v in versions:
            history.append({
                'version': v.version,
                'round_id': v.round_id,
                'created_at': datetime.fromtimestamp(v.created_at),
                'num_clients': v.num_clients,
                'metrics': v.metrics
            })
        
        return history


class RoundManager:
    """
    轮次管理器
    
    负责联邦学习轮次的生命周期管理。
    """
    
    def __init__(self, config: ServerConfig):
        """
        初始化轮次管理器
        
        Args:
            config: 服务器配置
        """
        self.config = config
        self.current_round: Optional[RoundInfo] = None
        self.round_history: List[RoundInfo] = []
        self.round_counter = 0
        
        logger.info(f"轮次管理器初始化完成, 最大轮次: {config.max_rounds}")
    
    def start_round(
        self,
        model_type: str,
        node_id: str,
        expected_clients: Optional[List[str]] = None
    ) -> RoundInfo:
        """
        开始新的联邦学习轮次
        
        Args:
            model_type: 模型类型
            node_id: 节点ID
            expected_clients: 期望参与的客户端列表
            
        Returns:
            轮次信息
        """
        if self.current_round and self.current_round.status == RoundStatus.WAITING:
            logger.warning(f"已有进行中的轮次: round={self.current_round.round_id}")
            return self.current_round
        
        self.round_counter += 1
        round_id = self.round_counter
        
        round_info = RoundInfo(
            round_id=round_id,
            model_type=model_type,
            node_id=node_id,
            status=RoundStatus.WAITING,
            start_time=time.time(),
            expected_clients=expected_clients or []
        )
        
        self.current_round = round_info
        
        logger.info(
            f"轮次开始: round={round_id}, model={model_type}/{node_id}, "
            f"expected_clients={len(expected_clients or [])}"
        )
        
        return round_info
    
    def collect_update(
        self,
        update: ClientUpdate
    ) -> bool:
        """
        收集客户端更新
        
        Args:
            update: 客户端更新
            
        Returns:
            是否成功收集
        """
        if self.current_round is None:
            logger.warning("没有进行中的轮次")
            return False
        
        if self.current_round.status != RoundStatus.WAITING:
            logger.warning(f"当前轮次状态不接受更新: {self.current_round.status}")
            return False
        
        # 检查是否超时
        if time.time() - self.current_round.start_time > self.config.round_timeout:
            self.current_round.status = RoundStatus.FAILED
            logger.error(f"轮次超时: round={self.current_round.round_id}")
            return False
        
        self.current_round.received_updates.append(update)
        
        logger.info(
            f"收集更新: round={self.current_round.round_id}, "
            f"client={update.client_id}, "
            f"received={len(self.current_round.received_updates)}/"
            f"{len(self.current_round.expected_clients) or '?'}"
        )
        
        return True
    
    def check_round_complete(self) -> bool:
        """
        检查轮次是否可以聚合
        
        Returns:
            是否满足聚合条件
        """
        if self.current_round is None:
            return False
        
        num_received = len(self.current_round.received_updates)
        num_expected = len(self.current_round.expected_clients)
        
        # 条件1: 达到最少客户端数
        if num_received < self.config.min_clients_per_round:
            return False
        
        # 条件2: 达到期望客户端数的一定比例
        if num_expected > 0 and num_received < num_expected * 0.5:
            return False
        
        # 条件3: 超时
        if time.time() - self.current_round.start_time > self.config.round_timeout:
            logger.warning(f"轮次超时但仍进行聚合: {self.current_round.round_id}")
            return True
        
        return True
    
    def complete_round(
        self,
        aggregated_weights: Dict[str, torch.Tensor],
        metrics: Optional[Dict[str, Any]] = None
    ) -> RoundInfo:
        """
        完成轮次
        
        Args:
            aggregated_weights: 聚合后的权重
            metrics: 聚合指标
            
        Returns:
            轮次信息
        """
        if self.current_round is None:
            raise ValueError("没有进行中的轮次")
        
        self.current_round.status = RoundStatus.COMPLETED
        self.current_round.end_time = time.time()
        self.current_round.aggregated_weights = aggregated_weights
        self.current_round.metrics = metrics or {}
        
        # 加入历史
        self.round_history.append(self.current_round)
        
        # 清理旧历史
        if len(self.round_history) > 100:
            self.round_history = self.round_history[-100:]
        
        logger.info(
            f"轮次完成: round={self.current_round.round_id}, "
            f"clients={len(self.current_round.received_updates)}, "
            f"duration={self.current_round.end_time - self.current_round.start_time:.2f}s"
        )
        
        completed_round = self.current_round
        self.current_round = None
        
        return completed_round
    
    def fail_round(self, reason: str) -> None:
        """标记轮次失败"""
        if self.current_round is None:
            return
        
        self.current_round.status = RoundStatus.FAILED
        self.current_round.end_time = time.time()
        self.current_round.metrics['fail_reason'] = reason
        
        self.round_history.append(self.current_round)
        self.current_round = None
        
        logger.error(f"轮次失败: reason={reason}")
    
    def get_round_status(self) -> Optional[Dict[str, Any]]:
        """获取当前轮次状态"""
        if self.current_round is None:
            return None
        
        return {
            'round_id': self.current_round.round_id,
            'model_type': self.current_round.model_type,
            'node_id': self.current_round.node_id,
            'status': self.current_round.status.value,
            'start_time': datetime.fromtimestamp(self.current_round.start_time),
            'expected_clients': len(self.current_round.expected_clients),
            'received_updates': len(self.current_round.received_updates),
            'elapsed_time': time.time() - self.current_round.start_time
        }


class FederatedServer:
    """
    联邦学习服务器（中心端）
    
    协调整个联邦学习过程，管理全局模型和训练轮次。
    
    工作流程:
    1. start_round() - 开始新的训练轮次
    2. broadcast_global_model() - 广播全局模型给客户端
    3. collect_update() - 收集各客户端的模型更新
    4. aggregate_updates() - 聚合更新得到新的全局模型
    5. distribute_model() - 分发新的全局模型
    """
    
    def __init__(
        self,
        config: Optional[ServerConfig] = None
    ):
        """
        初始化联邦学习服务器
        
        Args:
            config: 服务器配置
        """
        self.config = config or ServerConfig()
        
        # 初始化子管理器
        self.model_manager = GlobalModelManager(self.config)
        self.round_manager = RoundManager(self.config)
        
        # 初始化聚合器
        self.aggregator = create_aggregator(
            strategy=self.config.aggregation_strategy,
            config=self.config.aggregation_config
        )
        
        # 初始化隐私引擎（用于解密）
        self.privacy_engine: Optional[PrivacyEngine] = None
        if self.config.privacy_config:
            self.privacy_engine = create_privacy_engine(self.config.privacy_config)
        
        # 已注册的客户端
        self.registered_clients: Dict[str, Dict[str, Any]] = {}
        
        logger.info(
            f"联邦学习服务器初始化完成, "
            f"聚合策略: {self.config.aggregation_strategy.value}, "
            f"隐私机制: {self.config.privacy_config.get('mechanism', 'none') if self.config.privacy_config else 'none'}"
        )
    
    # ==================== 客户端管理 ====================
    
    def register_client(
        self,
        client_id: str,
        client_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        注册客户端
        
        Args:
            client_id: 客户端ID
            client_info: 客户端信息
        """
        self.registered_clients[client_id] = {
            'client_id': client_id,
            'registered_at': time.time(),
            'last_seen': time.time(),
            'info': client_info or {},
            'rounds_participated': 0,
            'total_samples': 0
        }
        
        logger.info(f"客户端注册: {client_id}")
    
    def unregister_client(self, client_id: str) -> None:
        """注销客户端"""
        if client_id in self.registered_clients:
            del self.registered_clients[client_id]
            logger.info(f"客户端注销: {client_id}")
    
    def select_clients(
        self,
        model_type: str,
        node_id: str
    ) -> List[str]:
        """
        选择参与本轮的客户端
        
        Args:
            model_type: 模型类型
            node_id: 节点ID
            
        Returns:
            选中的客户端ID列表
        """
        active_clients = [
            cid for cid, info in self.registered_clients.items()
            if time.time() - info['last_seen'] < 3600  # 1小时内活跃
        ]
        
        if not self.config.enable_client_selection:
            return active_clients
        
        # 按客户端选择比例采样
        num_select = max(
            self.config.min_clients_per_round,
            int(len(active_clients) * self.config.client_selection_ratio)
        )
        
        selected = np.random.choice(
            active_clients,
            size=min(num_select, len(active_clients)),
            replace=False
        ).tolist()
        
        logger.info(
            f"客户端选择: {len(selected)}/{len(active_clients)} "
            f"active clients selected for {model_type}/{node_id}"
        )
        
        return selected
    
    def update_client_heartbeat(self, client_id: str) -> None:
        """更新客户端心跳"""
        if client_id in self.registered_clients:
            self.registered_clients[client_id]['last_seen'] = time.time()
    
    # ==================== 轮次管理 ====================
    
    def start_round(
        self,
        model_type: str,
        node_id: str,
        expected_clients: Optional[List[str]] = None
    ) -> RoundInfo:
        """
        开始新的联邦学习轮次
        
        Args:
            model_type: 模型类型
            node_id: 节点ID
            expected_clients: 期望参与的客户端列表（None则自动选择）
            
        Returns:
            轮次信息
        """
        # 确保全局模型已初始化
        self.model_manager.init_global_model(model_type, node_id)
        
        # 自动选择客户端
        if expected_clients is None:
            expected_clients = self.select_clients(model_type, node_id)
        
        return self.round_manager.start_round(model_type, node_id, expected_clients)
    
    def get_current_round_status(self) -> Optional[Dict[str, Any]]:
        """获取当前轮次状态"""
        return self.round_manager.get_round_status()
    
    # ==================== 全局模型分发 ====================
    
    def get_global_model_for_client(
        self,
        client_id: str,
        model_type: str,
        node_id: str
    ) -> Dict[str, Any]:
        """
        获取要分发给客户端的全局模型
        
        Args:
            client_id: 客户端ID
            model_type: 模型类型
            node_id: 节点ID
            
        Returns:
            包含模型权重和元数据的字典
        """
        # 更新客户端心跳
        self.update_client_heartbeat(client_id)
        
        # 获取全局权重
        weights = self.model_manager.get_global_weights(model_type, node_id)
        
        # 获取当前轮次ID
        round_id = self.round_manager.current_round.round_id if self.round_manager.current_round else 0
        
        # 转换为numpy以便序列化
        weights_np = {k: v.cpu().numpy() for k, v in weights.items()}
        
        return {
            'weights': weights_np,
            'model_type': model_type,
            'node_id': node_id,
            'round_id': round_id,
            'server_time': time.time(),
            'enable_two_level_arch': self.config.enable_two_level_arch
        }
    
    # ==================== 模型更新收集 ====================
    
    def receive_client_update(
        self,
        update_data: Dict[str, Any]
    ) -> bool:
        """
        接收客户端的模型更新
        
        Args:
            update_data: 更新数据（从API接收）
            
        Returns:
            是否成功接收
        """
        try:
            client_id = update_data['client_id']
            model_type = update_data['model_type']
            node_id = update_data['node_id']
            round_id = update_data['round_id']
            
            # 转换权重
            weights = {
                k: torch.from_numpy(np.array(v)).float()
                for k, v in update_data['weights'].items()
            }
            
            # 解密（如果需要）
            if update_data.get('encrypted') and self.privacy_engine:
                if isinstance(self.privacy_engine, SecureAggregator):
                    # 处理加密更新
                    encrypted = update_data['encrypted_update']
                    # 这里应该是在聚合时统一解密，先存储
                    pass
            
            # 创建ClientUpdate对象
            update = ClientUpdate(
                client_id=client_id,
                weights=weights,
                num_samples=update_data.get('num_samples', 0),
                metrics=update_data.get('metrics', {}),
                round_id=round_id,
                timestamp=time.time()
            )
            
            # 更新客户端统计
            if client_id in self.registered_clients:
                self.registered_clients[client_id]['rounds_participated'] += 1
                self.registered_clients[client_id]['total_samples'] += update.num_samples
                self.registered_clients[client_id]['last_seen'] = time.time()
            
            # 收集更新
            return self.round_manager.collect_update(update)
            
        except Exception as e:
            logger.error(f"接收客户端更新失败: {e}")
            return False
    
    # ==================== 模型聚合 ====================
    
    def aggregate_updates(self) -> Optional[Dict[str, torch.Tensor]]:
        """
        聚合收集到的客户端更新
        
        Returns:
            聚合后的全局模型权重
        """
        if self.round_manager.current_round is None:
            logger.warning("没有进行中的轮次")
            return None
        
        if not self.round_manager.check_round_complete():
            logger.warning("轮次尚未满足聚合条件")
            return None
        
        self.round_manager.current_round.status = RoundStatus.AGGREGATING
        
        updates = self.round_manager.current_round.received_updates
        model_type = self.round_manager.current_round.model_type
        node_id = self.round_manager.current_round.node_id
        
        logger.info(
            f"开始聚合: round={self.round_manager.current_round.round_id}, "
            f"num_updates={len(updates)}"
        )
        
        try:
            # 获取当前全局权重
            current_global = self.model_manager.get_global_weights(model_type, node_id)
            
            # 如果更新是差异，则先还原为完整权重
            processed_updates = self._process_updates(updates, current_global)
            
            # 执行聚合
            aggregated = self.aggregator.aggregate(processed_updates, current_global)
            
            # 计算聚合指标
            metrics = self._compute_aggregation_metrics(processed_updates, aggregated)
            
            # 更新全局模型
            version = self.model_manager.update_global_weights(
                model_type=model_type,
                node_id=node_id,
                new_weights=aggregated,
                round_id=self.round_manager.current_round.round_id,
                metrics=metrics,
                num_clients=len(processed_updates)
            )
            
            # 完成轮次
            self.round_manager.complete_round(aggregated, metrics)
            
            logger.info(
                f"聚合完成: version={version.version}, "
                f"avg_val_acc={metrics.get('avg_val_acc', 0):.4f}"
            )
            
            return aggregated
            
        except Exception as e:
            logger.error(f"聚合失败: {e}")
            self.round_manager.fail_round(str(e))
            return None
    
    def _process_updates(
        self,
        updates: List[ClientUpdate],
        current_global: Dict[str, torch.Tensor]
    ) -> List[ClientUpdate]:
        """
        处理更新（如果是差异则还原为完整权重）
        
        Args:
            updates: 客户端更新列表
            current_global: 当前全局权重
            
        Returns:
            处理后的更新列表
        """
        processed = []
        for update in updates:
            # 检查是否是差异更新（权重的范数较小）
            total_norm = sum(
                w.norm(2).item() ** 2 
                for w in update.weights.values() 
                if w is not None
            )
            total_norm = np.sqrt(total_norm)
            
            if total_norm < 10.0:  # 阈值判断是否为差异
                # 还原为完整权重
                full_weights = add_weight_difference(
                    current_global,
                    update.weights,
                    lr=1.0
                )
                processed_update = ClientUpdate(
                    client_id=update.client_id,
                    weights=full_weights,
                    num_samples=update.num_samples,
                    metrics=update.metrics,
                    round_id=update.round_id,
                    timestamp=update.timestamp
                )
                processed.append(processed_update)
            else:
                processed.append(update)
        
        return processed
    
    def _compute_aggregation_metrics(
        self,
        updates: List[ClientUpdate],
        aggregated: Dict[str, torch.Tensor]
    ) -> Dict[str, Any]:
        """
        计算聚合指标
        
        Args:
            updates: 客户端更新
            aggregated: 聚合后的权重
            
        Returns:
            指标字典
        """
        if not updates:
            return {}
        
        metrics = {}
        
        # 平均验证准确率
        val_accs = [u.metrics.get('final_val_acc', 0) for u in updates]
        metrics['avg_val_acc'] = float(np.mean(val_accs))
        metrics['std_val_acc'] = float(np.std(val_accs))
        metrics['min_val_acc'] = float(np.min(val_accs))
        metrics['max_val_acc'] = float(np.max(val_accs))
        
        # 总样本数
        metrics['total_samples'] = sum(u.num_samples for u in updates)
        
        # 客户端统计
        metrics['num_clients'] = len(updates)
        metrics['client_ids'] = [u.client_id for u in updates]
        
        # 权重变化（相对于上一轮）
        # 这里可以计算权重差异的范数
        
        return metrics
    
    # ==================== 模型分发 ====================
    
    def distribute_model(
        self,
        model_type: str,
        node_id: str
    ) -> Dict[str, Any]:
        """
        分发新的全局模型
        
        Args:
            model_type: 模型类型
            node_id: 节点ID
            
        Returns:
            模型分发信息
        """
        latest_version = self.model_manager.get_latest_version(model_type, node_id)
        
        if latest_version is None:
            raise ValueError(f"全局模型不存在: {model_type}/{node_id}")
        
        weights_np = {
            k: v.cpu().numpy() 
            for k, v in latest_version.weights.items()
        }
        
        return {
            'model_type': model_type,
            'node_id': node_id,
            'version': latest_version.version,
            'round_id': latest_version.round_id,
            'weights': weights_np,
            'metrics': latest_version.metrics,
            'created_at': datetime.fromtimestamp(latest_version.created_at),
            'num_clients': latest_version.num_clients,
            'enable_two_level_arch': self.config.enable_two_level_arch
        }
    
    # ==================== 工具方法 ====================
    
    def get_server_status(self) -> Dict[str, Any]:
        """
        获取服务器状态
        
        Returns:
            状态字典
        """
        return {
            'registered_clients': len(self.registered_clients),
            'active_clients': sum(
                1 for info in self.registered_clients.values()
                if time.time() - info['last_seen'] < 3600
            ),
            'current_round': self.round_manager.get_round_status(),
            'total_rounds': self.round_manager.round_counter,
            'completed_rounds': sum(
                1 for r in self.round_manager.round_history
                if r.status == RoundStatus.COMPLETED
            ),
            'failed_rounds': sum(
                1 for r in self.round_manager.round_history
                if r.status == RoundStatus.FAILED
            ),
            'aggregation_strategy': self.config.aggregation_strategy.value,
            'managed_models': list(self.model_manager.model_versions.keys())
        }
    
    def get_model_history(
        self,
        model_type: str,
        node_id: str
    ) -> List[Dict[str, Any]]:
        """获取模型性能历史"""
        return self.model_manager.get_model_performance_history(model_type, node_id)
    
    def get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """获取客户端信息"""
        return self.registered_clients.get(client_id)
