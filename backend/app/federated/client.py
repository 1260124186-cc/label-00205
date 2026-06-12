"""
联邦学习客户端模块（厂区端）

实现各厂区的本地训练和模型更新功能。支持：
1. 接收全局模型并初始化本地模型
2. 本地训练（基于厂区私有数据）
3. 提取模型更新（权重差异或梯度）
4. 应用隐私保护（差分隐私/加密）
5. 上传更新到中心服务器
6. 本地微调（两层架构）

主要类:
- FederatedClient: 联邦学习客户端

使用示例:
    client = FederatedClient(factory_id='factory_001')
    client.receive_global_model(global_weights)
    client.local_train(model_type='bolt', node_id='B001')
    update = client.get_model_update()
    client.fine_tune()  # 本地微调
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

from app.models.bolt_lstm import BoltLSTMModel
from app.models.flange_attention import FlangeAttentionModel
from app.services.training_service import TrainingService
from app.services.preprocessing import DataPreprocessor
from app.federated.privacy import (
    PrivacyEngine,
    create_privacy_engine,
    PrivacyMechanism
)
from app.federated.aggregator import (
    ClientUpdate,
    extract_weights_from_model,
    compute_weight_difference,
    apply_weights_to_model
)
from app.utils.config import config


class UpdateType(str, Enum):
    """模型更新类型"""
    WEIGHTS = "weights"  # 上传完整权重
    GRADIENTS = "gradients"  # 上传梯度
    DIFFERENCE = "difference"  # 上传权重差异（本地权重 - 全局权重）


class TrainingMode(str, Enum):
    """训练模式"""
    FULL = "full"  # 全量训练
    FINE_TUNE = "fine_tune"  # 微调（冻结底层）
    TRANSFER = "transfer"  # 迁移学习


@dataclass
class ClientConfig:
    """客户端配置"""
    factory_id: str
    update_type: UpdateType = UpdateType.DIFFERENCE
    
    # 本地训练参数
    local_epochs: int = 5
    local_batch_size: int = 32
    local_learning_rate: float = 0.001
    
    # 隐私配置
    privacy_config: Optional[Dict[str, Any]] = None
    
    # 本地微调参数
    fine_tune_epochs: int = 3
    fine_tune_layers: List[str] = field(default_factory=lambda: ["output", "fc"])
    
    # 两层架构参数
    enable_two_level_arch: bool = True  # 是否启用全局+本地微调两层架构
    
    # 数据采样
    sample_ratio: float = 1.0  # 本地数据采样比例


@dataclass
class LocalTrainingResult:
    """本地训练结果"""
    client_id: str
    model_type: str
    node_id: str
    num_samples: int
    metrics: Dict[str, float]
    training_time: float
    epoch_metrics: List[Dict[str, float]] = field(default_factory=list)


class FederatedClient:
    """
    联邦学习客户端（厂区端）
    
    负责厂区本地的模型训练和更新上传。
    
    两层架构:
    1. 全局模型层: 从服务器接收，基于所有厂区数据聚合
    2. 本地微调层: 在全局模型基础上，使用本地数据微调
    """
    
    def __init__(
        self,
        factory_id: str,
        config: Optional[ClientConfig] = None
    ):
        """
        初始化联邦学习客户端
        
        Args:
            factory_id: 厂区ID
            config: 客户端配置
        """
        self.factory_id = factory_id
        
        if config is None:
            self.config = ClientConfig(factory_id=factory_id)
        else:
            self.config = config
            self.config.factory_id = factory_id
        
        # 初始化隐私引擎
        self.privacy_engine: Optional[PrivacyEngine] = None
        if self.config.privacy_config:
            self.privacy_engine = create_privacy_engine(self.config.privacy_config)
        
        # 模型相关
        self.global_weights: Optional[Dict[str, torch.Tensor]] = None
        self.local_model: Optional[nn.Module] = None
        self.model_wrapper: Optional[Any] = None
        self.current_model_type: Optional[str] = None
        self.current_node_id: Optional[str] = None
        
        # 训练服务
        self.training_service = TrainingService()
        
        # 本地训练历史
        self.training_history: List[LocalTrainingResult] = []
        
        # 最后更新时间
        self.last_update_time: Optional[float] = None
        self.current_round: int = 0
        
        logger.info(f"联邦学习客户端初始化完成: factory_id={factory_id}")
    
    # ==================== 模型管理 ====================
    
    def receive_global_model(
        self,
        global_weights: Dict[str, torch.Tensor],
        model_type: str,
        node_id: str,
        round_id: int = 0
    ) -> None:
        """
        接收全局模型（从中心服务器）
        
        Args:
            global_weights: 全局模型权重
            model_type: 模型类型 (bolt/flange)
            node_id: 节点ID
            round_id: 当前联邦学习轮次
        """
        self.global_weights = global_weights
        self.current_model_type = model_type
        self.current_node_id = node_id
        self.current_round = round_id
        
        # 创建或更新本地模型
        self._init_local_model(model_type, node_id)
        
        # 应用全局权重到本地模型
        if self.local_model is not None:
            apply_weights_to_model(self.local_model, global_weights)
        
        logger.info(
            f"[{self.factory_id}] 接收全局模型: "
            f"model_type={model_type}, node_id={node_id}, round={round_id}"
        )
    
    def _init_local_model(self, model_type: str, node_id: str) -> None:
        """
        初始化本地模型
        
        Args:
            model_type: 模型类型
            node_id: 节点ID
        """
        if model_type == 'bolt':
            self.model_wrapper = BoltLSTMModel(bolt_id=node_id)
            self.local_model = self.model_wrapper.model
        elif model_type == 'flange':
            self.model_wrapper = FlangeAttentionModel(flange_id=node_id)
            self.local_model = self.model_wrapper.model
        else:
            raise ValueError(f"未知模型类型: {model_type}")
    
    # ==================== 本地训练 ====================
    
    def local_train(
        self,
        model_type: Optional[str] = None,
        node_id: Optional[str] = None,
        train_data: Optional[np.ndarray] = None,
        train_labels: Optional[np.ndarray] = None,
        mode: TrainingMode = TrainingMode.FULL
    ) -> LocalTrainingResult:
        """
        本地训练
        
        Args:
            model_type: 模型类型（可选，使用当前模型）
            node_id: 节点ID（可选，使用当前节点）
            train_data: 训练数据（可选，自动加载）
            train_labels: 训练标签（可选，自动加载）
            mode: 训练模式
            
        Returns:
            训练结果
        """
        model_type = model_type or self.current_model_type
        node_id = node_id or self.current_node_id
        
        if model_type is None or node_id is None:
            raise ValueError("模型类型和节点ID不能为空")
        
        if self.local_model is None:
            self._init_local_model(model_type, node_id)
        
        start_time = time.time()
        logger.info(f"[{self.factory_id}] 开始本地训练: {model_type}/{node_id}, 模式={mode}")
        
        # 加载训练数据
        if train_data is None or train_labels is None:
            train_data, train_labels = self._load_training_data(model_type, node_id)
        
        if len(train_data) == 0:
            logger.warning(f"[{self.factory_id}] 训练数据为空，跳过训练")
            return LocalTrainingResult(
                client_id=self.factory_id,
                model_type=model_type,
                node_id=node_id,
                num_samples=0,
                metrics={},
                training_time=0
            )
        
        # 数据采样
        if self.config.sample_ratio < 1.0:
            sample_size = int(len(train_data) * self.config.sample_ratio)
            indices = np.random.choice(len(train_data), sample_size, replace=False)
            train_data = train_data[indices]
            train_labels = train_labels[indices]
        
        num_samples = len(train_data)
        
        # 设置训练模式
        self._set_training_mode(mode)
        
        # 执行训练
        epoch_metrics = []
        if model_type == 'bolt':
            history = self.model_wrapper.train(
                train_data=train_data,
                train_labels=train_labels,
                epochs=self.config.local_epochs,
                batch_size=self.config.local_batch_size,
                learning_rate=self.config.local_learning_rate
            )
        else:  # flange
            # 法兰面数据需要特殊处理
            processed_data = self._prepare_flange_data(train_data)
            history = self.model_wrapper.train(
                train_data=processed_data,
                train_labels=train_labels,
                epochs=self.config.local_epochs,
                batch_size=self.config.local_batch_size,
                learning_rate=self.config.local_learning_rate
            )
        
        # 记录每个epoch的指标
        for i in range(len(history.get('train_loss', []))):
            epoch_metrics.append({
                'epoch': i + 1,
                'train_loss': history['train_loss'][i] if i < len(history['train_loss']) else 0,
                'train_acc': history['train_acc'][i] if i < len(history['train_acc']) else 0,
                'val_loss': history['val_loss'][i] if i < len(history['val_loss']) else 0,
                'val_acc': history['val_acc'][i] if i < len(history['val_acc']) else 0
            })
        
        # 保存模型
        self.model_wrapper.save()
        
        training_time = time.time() - start_time
        
        metrics = {
            'final_train_loss': history['train_loss'][-1] if history['train_loss'] else 0,
            'final_train_acc': history['train_acc'][-1] if history['train_acc'] else 0,
            'final_val_loss': history['val_loss'][-1] if history['val_loss'] else 0,
            'final_val_acc': history['val_acc'][-1] if history['val_acc'] else 0
        }
        
        result = LocalTrainingResult(
            client_id=self.factory_id,
            model_type=model_type,
            node_id=node_id,
            num_samples=num_samples,
            metrics=metrics,
            training_time=training_time,
            epoch_metrics=epoch_metrics
        )
        
        self.training_history.append(result)
        self.last_update_time = time.time()
        
        logger.info(
            f"[{self.factory_id}] 本地训练完成: "
            f"samples={num_samples}, time={training_time:.2f}s, "
            f"val_acc={metrics['final_val_acc']:.4f}"
        )
        
        return result
    
    def _load_training_data(
        self,
        model_type: str,
        node_id: str
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        加载本地训练数据
        
        Args:
            model_type: 模型类型
            node_id: 节点ID
            
        Returns:
            (训练数据, 标签)
        """
        try:
            if model_type == 'bolt':
                return self.training_service._load_bolt_training_data(node_id)
            else:
                return self.training_service._load_flange_training_data(node_id)
        except Exception as e:
            logger.warning(f"[{self.factory_id}] 加载训练数据失败: {e}")
            # 返回空数据
            return np.array([]), np.array([])
    
    def _prepare_flange_data(
        self,
        raw_data: Any
    ) -> List[List[np.ndarray]]:
        """
        准备法兰面训练数据
        
        Args:
            raw_data: 原始数据
            
        Returns:
            格式化的法兰面数据
        """
        if isinstance(raw_data, list) and len(raw_data) > 0:
            if isinstance(raw_data[0], list):
                return raw_data
        
        # 转换为期望的格式
        samples = []
        for i in range(len(raw_data) // 10):
            sample = []
            for j in range(min(10, len(raw_data) - i * 10)):
                sample.append(raw_data[i * 10 + j])
            samples.append(sample)
        
        return samples if samples else [[raw_data]]
    
    def _set_training_mode(self, mode: TrainingMode) -> None:
        """
        设置训练模式（冻结/解冻层）
        
        Args:
            mode: 训练模式
        """
        if self.local_model is None:
            return
        
        if mode == TrainingMode.FULL:
            # 训练所有层
            for param in self.local_model.parameters():
                param.requires_grad = True
        elif mode == TrainingMode.FINE_TUNE:
            # 只训练指定层
            for name, param in self.local_model.named_parameters():
                param.requires_grad = any(
                    layer_name in name 
                    for layer_name in self.config.fine_tune_layers
                )
            logger.info(f"[{self.factory_id}] 微调模式，训练层: {self.config.fine_tune_layers}")
        elif mode == TrainingMode.TRANSFER:
            # 冻结底层，训练分类头
            for name, param in self.local_model.named_parameters():
                param.requires_grad = 'output' in name or 'fc' in name
    
    # ==================== 模型更新提取 ====================
    
    def get_model_update(
        self,
        apply_privacy: bool = True
    ) -> ClientUpdate:
        """
        获取模型更新（准备上传到服务器）
        
        Args:
            apply_privacy: 是否应用隐私保护
            
        Returns:
            客户端模型更新
        """
        if self.local_model is None or self.global_weights is None:
            raise ValueError("模型未初始化，无法提取更新")
        
        # 提取本地权重
        local_weights = extract_weights_from_model(self.local_model)
        
        # 根据更新类型处理
        if self.config.update_type == UpdateType.WEIGHTS:
            update_weights = local_weights
        elif self.config.update_type == UpdateType.DIFFERENCE:
            # 计算权重差异
            update_weights = compute_weight_difference(local_weights, self.global_weights)
        elif self.config.update_type == UpdateType.GRADIENTS:
            # 提取梯度（需要在训练时记录，这里简化为差异）
            update_weights = compute_weight_difference(local_weights, self.global_weights)
        else:
            update_weights = local_weights
        
        # 应用隐私保护
        if apply_privacy and self.privacy_engine is not None:
            logger.info(f"[{self.factory_id}] 应用隐私保护: {self.privacy_engine.config.mechanism}")
            processed = self.privacy_engine.process_update(update_weights)
            
            if isinstance(processed, bytes):
                # 加密更新
                return ClientUpdate(
                    client_id=self.factory_id,
                    weights=update_weights,  # 原始权重（用于调试）
                    num_samples=self.training_history[-1].num_samples if self.training_history else 0,
                    metrics=self.training_history[-1].metrics if self.training_history else {},
                    round_id=self.current_round,
                    timestamp=time.time(),
                    encrypted_update=processed
                )
            else:
                update_weights = processed
        
        # 获取训练指标
        num_samples = 0
        metrics = {}
        if self.training_history:
            last_result = self.training_history[-1]
            num_samples = last_result.num_samples
            metrics = last_result.metrics
        
        return ClientUpdate(
            client_id=self.factory_id,
            weights=update_weights,
            num_samples=num_samples,
            metrics=metrics,
            round_id=self.current_round,
            timestamp=time.time()
        )
    
    # ==================== 本地微调（两层架构） ====================
    
    def fine_tune(
        self,
        model_type: Optional[str] = None,
        node_id: Optional[str] = None,
        fine_tune_data: Optional[np.ndarray] = None,
        fine_tune_labels: Optional[np.ndarray] = None
    ) -> LocalTrainingResult:
        """
        本地微调（两层架构的第二层）
        
        在全局模型基础上，使用本地数据进行微调，以适应厂区特定分布。
        
        Args:
            model_type: 模型类型
            node_id: 节点ID
            fine_tune_data: 微调数据
            fine_tune_labels: 微调标签
            
        Returns:
            微调结果
        """
        if not self.config.enable_two_level_arch:
            logger.info(f"[{self.factory_id}] 两层架构未启用，跳过敏调")
            return LocalTrainingResult(
                client_id=self.factory_id,
                model_type=model_type or self.current_model_type or "",
                node_id=node_id or self.current_node_id or "",
                num_samples=0,
                metrics={},
                training_time=0
            )
        
        logger.info(f"[{self.factory_id}] 开始本地微调（第二层）")
        
        # 保存当前的epochs设置
        original_epochs = self.config.local_epochs
        self.config.local_epochs = self.config.fine_tune_epochs
        
        try:
            result = self.local_train(
                model_type=model_type,
                node_id=node_id,
                train_data=fine_tune_data,
                train_labels=fine_tune_labels,
                mode=TrainingMode.FINE_TUNE
            )
        finally:
            # 恢复原始设置
            self.config.local_epochs = original_epochs
        
        logger.info(
            f"[{self.factory_id}] 本地微调完成: "
            f"val_acc={result.metrics.get('final_val_acc', 0):.4f}"
        )
        
        return result
    
    # ==================== 推理（使用本地微调模型） ====================
    
    def predict(
        self,
        data: np.ndarray,
        use_fine_tuned: bool = True
    ) -> Tuple[int, float, Optional[np.ndarray]]:
        """
        使用本地模型进行预测
        
        Args:
            data: 输入数据
            use_fine_tuned: 是否使用微调后的模型
            
        Returns:
            (预测类别, 置信度, 概率分布)
        """
        if self.model_wrapper is None:
            raise ValueError("模型未初始化")
        
        if not use_fine_tuned and self.global_weights is not None:
            # 临时应用全局权重（不推荐，通常应使用微调模型）
            apply_weights_to_model(self.local_model, self.global_weights)
        
        return self.model_wrapper.predict(data)
    
    # ==================== 工具方法 ====================
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取客户端状态
        
        Returns:
            状态字典
        """
        return {
            'factory_id': self.factory_id,
            'model_type': self.current_model_type,
            'node_id': self.current_node_id,
            'current_round': self.current_round,
            'has_global_model': self.global_weights is not None,
            'has_local_model': self.local_model is not None,
            'last_update_time': self.last_update_time,
            'training_count': len(self.training_history),
            'privacy_mechanism': (
                self.privacy_engine.config.mechanism.value 
                if self.privacy_engine else PrivacyMechanism.NONE.value
            ),
            'update_type': self.config.update_type.value,
            'two_level_arch_enabled': self.config.enable_two_level_arch
        }
    
    def save_local_model(self, path: Optional[str] = None) -> str:
        """保存本地模型"""
        if self.model_wrapper is None:
            raise ValueError("模型未初始化")
        return self.model_wrapper.save(path)
    
    def load_local_model(self, path: str) -> None:
        """加载本地模型"""
        if self.model_wrapper is None:
            raise ValueError("模型未初始化")
        self.model_wrapper.load(path)
        self.local_model = self.model_wrapper.model
