"""
模型聚合器模块

实现联邦学习中的模型聚合算法，支持多种聚合策略。

主要类:
- ModelAggregator: 聚合器基类
- FedAvgAggregator: FedAvg聚合（经典联邦平均）
- WeightedAvgAggregator: 加权平均聚合（按样本量加权）
- MedianAggregator: 中位数聚合（拜占庭鲁棒）
- TrimmedMeanAggregator: 修剪均值聚合（拜占庭鲁棒）

使用示例:
    aggregator = FedAvgAggregator()
    global_model = aggregator.aggregate(client_updates)
"""

import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import copy


class AggregationStrategy(str, Enum):
    """聚合策略类型"""
    FEDAVG = "fedavg"
    WEIGHTED_AVG = "weighted_avg"
    MEDIAN = "median"
    TRIMMED_MEAN = "trimmed_mean"
    FEDPROX = "fedprox"
    FEDOPT = "fedopt"


@dataclass
class AggregationConfig:
    """聚合配置"""
    strategy: AggregationStrategy = AggregationStrategy.FEDAVG
    
    # 修剪均值参数
    trim_ratio: float = 0.1  # 修剪比例（0-0.5）
    
    # FedProx参数
    mu: float = 0.01  # 近端项系数
    
    # FedOpt参数
    server_learning_rate: float = 1.0
    server_momentum: float = 0.9
    
    # 最小参与客户端比例
    min_clients_ratio: float = 0.5
    
    # 异常值检测
    enable_outlier_detection: bool = True
    outlier_threshold: float = 2.0  # 标准差倍数


@dataclass
class ClientUpdate:
    """客户端模型更新"""
    client_id: str
    weights: Dict[str, torch.Tensor]
    num_samples: int = 0
    metrics: Dict[str, float] = field(default_factory=dict)
    round_id: int = 0
    timestamp: float = 0.0
    
    # 可选：梯度更新（如果是上传梯度而非权重）
    gradients: Optional[Dict[str, torch.Tensor]] = None
    
    # 可选：加密后的更新
    encrypted_update: Optional[bytes] = None


class ModelAggregator:
    """
    模型聚合器基类
    
    定义联邦学习模型聚合的通用接口。
    """
    
    def __init__(self, config: AggregationConfig):
        """
        初始化聚合器
        
        Args:
            config: 聚合配置
        """
        self.config = config
        self.global_weights: Optional[Dict[str, torch.Tensor]] = None
        self.aggregation_count = 0
        
        # FedOpt动量
        self.momentum: Dict[str, torch.Tensor] = {}
        
        logger.info(f"模型聚合器初始化完成, 策略: {config.strategy}")
    
    def aggregate(
        self,
        updates: List[ClientUpdate],
        global_weights: Optional[Dict[str, torch.Tensor]] = None
    ) -> Dict[str, torch.Tensor]:
        """
        聚合客户端更新
        
        Args:
            updates: 客户端更新列表
            global_weights: 当前全局模型权重（可选）
            
        Returns:
            聚合后的全局模型权重
        """
        if len(updates) == 0:
            raise ValueError("客户端更新列表为空")
        
        self.global_weights = global_weights
        
        # 异常值检测
        if self.config.enable_outlier_detection:
            updates = self._detect_and_remove_outliers(updates)
        
        # 检查参与客户端数量
        min_clients = max(1, int(len(updates) * self.config.min_clients_ratio))
        if len(updates) < min_clients:
            raise ValueError(
                f"参与客户端数量不足: 需要至少{min_clients}个, 实际{len(updates)}个"
            )
        
        # 执行具体聚合策略
        aggregated = self._aggregate_impl(updates)
        
        self.aggregation_count += 1
        logger.info(f"模型聚合完成: {len(updates)}个客户端, 第{self.aggregation_count}次聚合")
        
        return aggregated
    
    def _aggregate_impl(
        self,
        updates: List[ClientUpdate]
    ) -> Dict[str, torch.Tensor]:
        """具体聚合实现，由子类重写"""
        raise NotImplementedError
    
    def _detect_and_remove_outliers(
        self,
        updates: List[ClientUpdate]
    ) -> List[ClientUpdate]:
        """
        检测并移除异常更新
        
        使用Z-score方法检测权重更新中的异常值。
        
        Args:
            updates: 客户端更新列表
            
        Returns:
            过滤后的更新列表
        """
        if len(updates) < 3:
            return updates
        
        # 计算每个客户端更新的范数
        norms = []
        for update in updates:
            total_norm = 0.0
            for name, weight in update.weights.items():
                if weight is not None:
                    total_norm += weight.norm(2).item() ** 2
            norms.append(np.sqrt(total_norm))
        
        # 计算Z-score
        mean_norm = np.mean(norms)
        std_norm = np.std(norms) + 1e-8
        z_scores = np.abs((np.array(norms) - mean_norm) / std_norm)
        
        # 过滤异常值
        filtered_updates = []
        for i, update in enumerate(updates):
            if z_scores[i] < self.config.outlier_threshold:
                filtered_updates.append(update)
            else:
                logger.warning(
                    f"移除异常更新: client={update.client_id}, "
                    f"norm={norms[i]:.4f}, z-score={z_scores[i]:.4f}"
                )
        
        return filtered_updates if filtered_updates else updates
    
    def _stack_weights(
        self,
        updates: List[ClientUpdate]
    ) -> Dict[str, torch.Tensor]:
        """
        将所有客户端的权重堆叠
        
        Args:
            updates: 客户端更新列表
            
        Returns:
            堆叠后的权重字典 {param_name: (num_clients, *param_shape)}
        """
        if not updates:
            return {}
        
        stacked = {}
        for key in updates[0].weights.keys():
            weights_list = []
            for update in updates:
                if key in update.weights and update.weights[key] is not None:
                    weights_list.append(update.weights[key].unsqueeze(0))
            
            if weights_list:
                stacked[key] = torch.cat(weights_list, dim=0)
        
        return stacked
    
    def compute_aggregation_weights(
        self,
        updates: List[ClientUpdate]
    ) -> np.ndarray:
        """
        计算聚合权重（默认按样本量加权）
        
        Args:
            updates: 客户端更新列表
            
        Returns:
            权重数组，和为1
        """
        total_samples = sum(u.num_samples for u in updates)
        if total_samples > 0:
            weights = np.array([u.num_samples / total_samples for u in updates])
        else:
            weights = np.ones(len(updates)) / len(updates)
        
        return weights


class FedAvgAggregator(ModelAggregator):
    """
    FedAvg聚合器
    
    经典的联邦平均算法：
        w_global = (1/K) * sum(w_i)
    
    参考文献:
        Communication-Efficient Learning of Deep Networks from Decentralized Data
        https://arxiv.org/abs/1602.05629
    """
    
    def _aggregate_impl(
        self,
        updates: List[ClientUpdate]
    ) -> Dict[str, torch.Tensor]:
        """
        FedAvg聚合实现
        
        Args:
            updates: 客户端更新列表
            
        Returns:
            平均后的全局权重
        """
        stacked = self._stack_weights(updates)
        aggregated = {}
        
        for key, stacked_tensor in stacked.items():
            # 简单平均
            aggregated[key] = stacked_tensor.mean(dim=0)
        
        return aggregated


class WeightedAvgAggregator(ModelAggregator):
    """
    加权平均聚合器
    
    按样本量加权平均：
        w_global = sum(n_i * w_i) / sum(n_i)
    
    其中n_i是客户端i的样本数量。
    """
    
    def _aggregate_impl(
        self,
        updates: List[ClientUpdate]
    ) -> Dict[str, torch.Tensor]:
        """
        加权平均聚合实现
        
        Args:
            updates: 客户端更新列表
            
        Returns:
            加权平均后的全局权重
        """
        weights = self.compute_aggregation_weights(updates)
        
        aggregated = {}
        for key in updates[0].weights.keys():
            # 加权求和
            weighted_sum = None
            for i, update in enumerate(updates):
                if key in update.weights and update.weights[key] is not None:
                    if weighted_sum is None:
                        weighted_sum = update.weights[key] * weights[i]
                    else:
                        weighted_sum += update.weights[key] * weights[i]
            
            if weighted_sum is not None:
                aggregated[key] = weighted_sum
        
        return aggregated


class MedianAggregator(ModelAggregator):
    """
    中位数聚合器
    
    对每个参数取所有客户端更新的中位数，具有拜占庭容错能力。
    
    参考文献:
        Byzantine-Robust Distributed Learning: Towards Optimal Statistical Rates
        https://arxiv.org/abs/1803.01498
    """
    
    def _aggregate_impl(
        self,
        updates: List[ClientUpdate]
    ) -> Dict[str, torch.Tensor]:
        """
        中位数聚合实现
        
        Args:
            updates: 客户端更新列表
            
        Returns:
            中位数聚合后的全局权重
        """
        stacked = self._stack_weights(updates)
        aggregated = {}
        
        for key, stacked_tensor in stacked.items():
            # 计算中位数
            aggregated[key] = torch.median(stacked_tensor, dim=0).values
        
        return aggregated


class TrimmedMeanAggregator(ModelAggregator):
    """
    修剪均值聚合器
    
    移除最大和最小的一定比例的更新，然后取平均。
    同样具有拜占庭容错能力。
    
    参考文献:
        Distributed Statistical Machine Learning in Adversarial Settings
        https://arxiv.org/abs/1705.05491
    """
    
    def _aggregate_impl(
        self,
        updates: List[ClientUpdate]
    ) -> Dict[str, torch.Tensor]:
        """
        修剪均值聚合实现
        
        Args:
            updates: 客户端更新列表
            
        Returns:
            修剪均值聚合后的全局权重
        """
        trim_ratio = self.config.trim_ratio
        num_clients = len(updates)
        trim_count = int(num_clients * trim_ratio)
        
        if trim_count <= 0 or trim_count >= num_clients // 2:
            # 回退到普通平均
            aggregator = FedAvgAggregator(self.config)
            return aggregator._aggregate_impl(updates)
        
        stacked = self._stack_weights(updates)
        aggregated = {}
        
        for key, stacked_tensor in stacked.items():
            # 排序后修剪
            sorted_tensor, _ = torch.sort(stacked_tensor, dim=0)
            
            # 修剪两端
            trimmed = sorted_tensor[trim_count:-trim_count]
            
            # 平均
            aggregated[key] = trimmed.mean(dim=0)
        
        return aggregated


class FedProxAggregator(ModelAggregator):
    """
    FedProx聚合器
    
    在FedAvg基础上加入近端项约束，处理异质性数据。
    
    目标函数:
        min_w [ F_i(w) + (mu/2) * ||w - w_global||^2 ]
    
    参考文献:
        Federated Optimization in Heterogeneous Networks
        https://arxiv.org/abs/1812.06127
    """
    
    def _aggregate_impl(
        self,
        updates: List[ClientUpdate]
    ) -> Dict[str, torch.Tensor]:
        """
        FedProx聚合实现
        
        Args:
            updates: 客户端更新列表
            
        Returns:
            聚合后的全局权重
        """
        # 先进行加权平均
        weighted_aggregator = WeightedAvgAggregator(self.config)
        avg_weights = weighted_aggregator._aggregate_impl(updates)
        
        # 如果有全局权重，应用近端项（这里简化处理）
        if self.global_weights is not None:
            mu = self.config.mu
            aggregated = {}
            for key in avg_weights.keys():
                if key in self.global_weights:
                    # 近端项收缩
                    aggregated[key] = (
                        (1 - mu) * avg_weights[key] + 
                        mu * self.global_weights[key]
                    )
                else:
                    aggregated[key] = avg_weights[key]
            return aggregated
        
        return avg_weights


class FedOptAggregator(ModelAggregator):
    """
    FedOpt聚合器
    
    服务器端使用自适应优化器（如Adam）来更新全局模型。
    
    参考文献:
        Adaptive Federated Optimization
        https://arxiv.org/abs/2003.00295
    """
    
    def _aggregate_impl(
        self,
        updates: List[ClientUpdate]
    ) -> Dict[str, torch.Tensor]:
        """
        FedOpt聚合实现（简化版，带动量）
        
        Args:
            updates: 客户端更新列表
            
        Returns:
            聚合后的全局权重
        """
        # 计算平均更新（全局权重 - 平均客户端权重 = 更新方向）
        stacked = self._stack_weights(updates)
        
        if self.global_weights is None:
            # 第一次聚合，直接平均
            aggregated = {}
            for key, stacked_tensor in stacked.items():
                aggregated[key] = stacked_tensor.mean(dim=0)
            return aggregated
        
        # 计算更新方向
        updates_direction = {}
        for key, stacked_tensor in stacked.items():
            if key in self.global_weights:
                avg_client = stacked_tensor.mean(dim=0)
                # 更新方向 = 全局权重 - 客户端平均（梯度下降方向）
                updates_direction[key] = self.global_weights[key] - avg_client
        
        # 应用动量和学习率
        lr = self.config.server_learning_rate
        momentum = self.config.server_momentum
        
        aggregated = {}
        for key in self.global_weights.keys():
            if key in updates_direction:
                # 更新动量
                if key not in self.momentum:
                    self.momentum[key] = torch.zeros_like(self.global_weights[key])
                
                self.momentum[key] = (
                    momentum * self.momentum[key] + 
                    (1 - momentum) * updates_direction[key]
                )
                
                # 更新全局权重
                aggregated[key] = (
                    self.global_weights[key] - lr * self.momentum[key]
                )
            else:
                aggregated[key] = self.global_weights[key].clone()
        
        return aggregated


def create_aggregator(
    strategy: Union[str, AggregationStrategy] = "fedavg",
    config: Optional[Dict[str, Any]] = None
) -> ModelAggregator:
    """
    工厂函数：创建聚合器
    
    Args:
        strategy: 聚合策略
        config: 配置字典
        
    Returns:
        聚合器实例
    """
    if config is None:
        config = {}
    
    if isinstance(strategy, str):
        strategy = AggregationStrategy(strategy.lower())
    
    agg_config = AggregationConfig(
        strategy=strategy,
        trim_ratio=config.get('trim_ratio', 0.1),
        mu=config.get('mu', 0.01),
        server_learning_rate=config.get('server_learning_rate', 1.0),
        server_momentum=config.get('server_momentum', 0.9),
        min_clients_ratio=config.get('min_clients_ratio', 0.5),
        enable_outlier_detection=config.get('enable_outlier_detection', True),
        outlier_threshold=config.get('outlier_threshold', 2.0)
    )
    
    if strategy == AggregationStrategy.FEDAVG:
        return FedAvgAggregator(agg_config)
    elif strategy == AggregationStrategy.WEIGHTED_AVG:
        return WeightedAvgAggregator(agg_config)
    elif strategy == AggregationStrategy.MEDIAN:
        return MedianAggregator(agg_config)
    elif strategy == AggregationStrategy.TRIMMED_MEAN:
        return TrimmedMeanAggregator(agg_config)
    elif strategy == AggregationStrategy.FEDPROX:
        return FedProxAggregator(agg_config)
    elif strategy == AggregationStrategy.FEDOPT:
        return FedOptAggregator(agg_config)
    else:
        return FedAvgAggregator(agg_config)


def apply_weights_to_model(
    model: nn.Module,
    weights: Dict[str, torch.Tensor]
) -> None:
    """
    将权重应用到模型
    
    Args:
        model: PyTorch模型
        weights: 权重字典
    """
    model_dict = model.state_dict()
    
    # 只更新存在的参数
    filtered_weights = {k: v for k, v in weights.items() if k in model_dict}
    
    model_dict.update(filtered_weights)
    model.load_state_dict(model_dict)


def extract_weights_from_model(
    model: nn.Module
) -> Dict[str, torch.Tensor]:
    """
    从模型中提取权重
    
    Args:
        model: PyTorch模型
        
    Returns:
        权重字典
    """
    return {k: v.clone().detach() for k, v in model.state_dict().items()}


def compute_weight_difference(
    weights1: Dict[str, torch.Tensor],
    weights2: Dict[str, torch.Tensor]
) -> Dict[str, torch.Tensor]:
    """
    计算两个权重集的差异
    
    Args:
        weights1: 权重字典1
        weights2: 权重字典2
        
    Returns:
        差异字典 (weights1 - weights2)
    """
    diff = {}
    for key in weights1.keys():
        if key in weights2:
            diff[key] = weights1[key] - weights2[key]
    return diff


def add_weight_difference(
    base_weights: Dict[str, torch.Tensor],
    diff: Dict[str, torch.Tensor],
    lr: float = 1.0
) -> Dict[str, torch.Tensor]:
    """
    将差异应用到基础权重
    
    Args:
        base_weights: 基础权重
        diff: 差异
        lr: 学习率
        
    Returns:
        更新后的权重
    """
    updated = {}
    for key in base_weights.keys():
        if key in diff:
            updated[key] = base_weights[key] + lr * diff[key]
        else:
            updated[key] = base_weights[key].clone()
    return updated
