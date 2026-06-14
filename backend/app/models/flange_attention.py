"""
法兰面状态预测注意力模型

基于注意力机制和LSTM的多螺栓关联分析模型。

模型架构:
    螺栓特征提取 → 自注意力机制 → LSTM层 
    → 全连接层 → 输出层(5类)

多螺栓关系建模:
    - 皮尔逊相关系数矩阵
    - 格兰杰因果关系检验
    - 聚类分析识别模式
    - 自注意力机制捕捉长程依赖

使用示例:
    from app.models.flange_attention import FlangeAttentionModel
    
    model = FlangeAttentionModel(flange_id='F001')
    prediction = model.predict(multi_bolt_data)
"""

import os
import time
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler
from torch.optim.lr_scheduler import ReduceLROnPlateau, StepLR, CosineAnnealingLR
import numpy as np
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path
from scipy import stats
from collections import Counter
from loguru import logger

from app.utils.config import config
from app.utils.device import get_device


class MultiHeadSelfAttention(nn.Module):
    """
    多头自注意力机制
    
    用于捕捉螺栓之间的依赖关系。
    
    Attributes:
        num_heads: 注意力头数
        head_dim: 每个头的维度
        query: Query线性变换
        key: Key线性变换
        value: Value线性变换
        output: 输出线性变换
    """
    
    def __init__(self, embed_dim: int, num_heads: int = 8, dropout: float = 0.1):
        """
        初始化多头自注意力
        
        Args:
            embed_dim: 嵌入维度
            num_heads: 注意力头数
            dropout: Dropout率
        """
        super(MultiHeadSelfAttention, self).__init__()
        
        self.num_heads = num_heads
        self.head_dim = embed_dim // num_heads
        assert embed_dim % num_heads == 0, "embed_dim must be divisible by num_heads"
        
        self.query = nn.Linear(embed_dim, embed_dim)
        self.key = nn.Linear(embed_dim, embed_dim)
        self.value = nn.Linear(embed_dim, embed_dim)
        self.output = nn.Linear(embed_dim, embed_dim)
        
        self.dropout = nn.Dropout(dropout)
        self.scale = self.head_dim ** -0.5
        
    def forward(
        self, 
        x: torch.Tensor, 
        mask: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        前向传播
        
        Args:
            x: 输入张量，形状为 (batch_size, seq_len, embed_dim)
            mask: 注意力掩码，可选
            
        Returns:
            Tuple: (输出张量, 注意力权重)
        """
        batch_size, seq_len, embed_dim = x.size()
        
        # 线性变换
        Q = self.query(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        K = self.key(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        V = self.value(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        
        # 计算注意力分数
        scores = torch.matmul(Q, K.transpose(-2, -1)) * self.scale
        
        if mask is not None:
            scores = scores.masked_fill(mask == 0, float('-inf'))
        
        attention_weights = torch.softmax(scores, dim=-1)
        attention_weights = self.dropout(attention_weights)
        
        # 应用注意力
        context = torch.matmul(attention_weights, V)
        context = context.transpose(1, 2).contiguous().view(batch_size, seq_len, embed_dim)
        
        output = self.output(context)
        
        return output, attention_weights


class BoltFeatureExtractor(nn.Module):
    """
    螺栓特征提取器
    
    从单个螺栓的时间序列中提取特征。
    
    Attributes:
        lstm: LSTM层用于序列编码
        fc: 全连接层用于特征压缩
    """
    
    def __init__(
        self, 
        input_dim: int = 2, 
        hidden_dim: int = 64,
        output_dim: int = 32
    ):
        """
        初始化特征提取器
        
        Args:
            input_dim: 输入特征维度
            hidden_dim: LSTM隐藏层维度
            output_dim: 输出特征维度
        """
        super(BoltFeatureExtractor, self).__init__()
        
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            batch_first=True,
            bidirectional=True
        )
        
        self.fc = nn.Linear(hidden_dim * 2, output_dim)
        self.relu = nn.ReLU()
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        提取螺栓特征
        
        Args:
            x: 输入张量，形状为 (batch_size, seq_len, input_dim)
            
        Returns:
            torch.Tensor: 特征向量，形状为 (batch_size, output_dim)
        """
        lstm_out, (h_n, _) = self.lstm(x)
        
        # 连接双向LSTM的最后隐藏状态
        hidden = torch.cat((h_n[-2, :, :], h_n[-1, :, :]), dim=1)
        
        features = self.relu(self.fc(hidden))
        
        return features


class FlangeAttentionNetwork(nn.Module):
    """
    法兰面注意力网络
    
    集成多螺栓特征提取和注意力机制。
    
    Attributes:
        bolt_extractor: 螺栓特征提取器
        attention: 多头自注意力
        lstm: 时序建模LSTM
        fc: 全连接分类层
        output: 输出层
    """
    
    def __init__(
        self,
        max_bolts: int = 20,
        input_dim: int = 2,
        feature_dim: int = 32,
        attention_heads: int = 8,
        lstm_units: int = 64,
        output_classes: int = 5
    ):
        """
        初始化法兰面网络
        
        Args:
            max_bolts: 最大螺栓数量
            input_dim: 输入特征维度
            feature_dim: 螺栓特征维度
            attention_heads: 注意力头数
            lstm_units: LSTM单元数
            output_classes: 输出类别数
        """
        super(FlangeAttentionNetwork, self).__init__()
        
        self.max_bolts = max_bolts
        self.feature_dim = feature_dim
        
        # 螺栓特征提取器
        self.bolt_extractor = BoltFeatureExtractor(
            input_dim=input_dim,
            hidden_dim=64,
            output_dim=feature_dim
        )
        
        # 多头自注意力
        self.attention = MultiHeadSelfAttention(
            embed_dim=feature_dim,
            num_heads=attention_heads,
            dropout=0.1
        )
        
        # 跨螺栓LSTM
        self.lstm = nn.LSTM(
            input_size=feature_dim,
            hidden_size=lstm_units,
            batch_first=True,
            bidirectional=True
        )
        
        # 分类层
        self.fc = nn.Linear(lstm_units * 2, 64)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.2)
        self.output = nn.Linear(64, output_classes)
        
    def forward(
        self, 
        x: torch.Tensor, 
        bolt_mask: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        前向传播
        
        Args:
            x: 输入张量，形状为 (batch_size, num_bolts, seq_len, input_dim)
            bolt_mask: 螺栓掩码，用于处理不同数量的螺栓
            
        Returns:
            Tuple: (分类输出, 注意力权重)
        """
        batch_size, num_bolts, seq_len, input_dim = x.size()
        
        # 提取每个螺栓的特征
        bolt_features = []
        for i in range(num_bolts):
            bolt_seq = x[:, i, :, :]  # (batch_size, seq_len, input_dim)
            features = self.bolt_extractor(bolt_seq)  # (batch_size, feature_dim)
            bolt_features.append(features)
        
        # 堆叠螺栓特征
        bolt_features = torch.stack(bolt_features, dim=1)  # (batch_size, num_bolts, feature_dim)
        
        # 自注意力机制
        attended_features, attention_weights = self.attention(bolt_features, bolt_mask)
        
        # LSTM处理
        lstm_out, (h_n, _) = self.lstm(attended_features)
        
        # 取最后隐藏状态
        hidden = torch.cat((h_n[-2, :, :], h_n[-1, :, :]), dim=1)
        
        # 分类
        fc_out = self.relu(self.fc(hidden))
        fc_out = self.dropout(fc_out)
        output = self.output(fc_out)
        
        return output, attention_weights


class FlangeAttentionModel:
    """
    法兰面状态预测模型
    
    封装法兰面注意力网络，提供训练、预测、关系分析等功能。
    
    Attributes:
        model: 注意力网络模型
        device: 计算设备
        model_config: 模型配置
        flange_id: 法兰面ID
        is_trained: 是否已训练
        correlation_matrix: 螺栓相关性矩阵
    """
    
    def __init__(self, flange_id: Optional[str] = None):
        """
        初始化法兰面预测模型
        
        Args:
            flange_id: 法兰面ID
        """
        self.flange_id = flange_id
        self.device = get_device()
        self.model_config = config.get('model.flange_attention', {})
        self.training_config = config.get('model.training', {})
        
        # 创建网络
        self.model = FlangeAttentionNetwork(
            max_bolts=self.model_config.get('max_bolts', 20),
            input_dim=2,
            feature_dim=32,
            attention_heads=self.model_config.get('attention_heads', 8),
            lstm_units=self.model_config.get('lstm_units', 64),
            output_classes=self.model_config.get('output_classes', 5)
        ).to(self.device)
        
        self.is_trained = False
        self.correlation_matrix = None
        self.bolt_ids = []
        self.training_history = []
        
        logger.info(f"法兰面注意力模型初始化完成: flange_id={flange_id}")
    
    def analyze_bolt_correlations(self, bolt_data: Dict[str, np.ndarray]) -> np.ndarray:
        """
        分析螺栓间的相关性
        
        使用皮尔逊相关系数计算螺栓间的相关性矩阵。
        
        Args:
            bolt_data: 螺栓数据字典 {bolt_id: time_series}
            
        Returns:
            np.ndarray: 相关性矩阵
        """
        self.bolt_ids = list(bolt_data.keys())
        n_bolts = len(self.bolt_ids)
        
        correlation_matrix = np.zeros((n_bolts, n_bolts))
        
        for i, bolt_i in enumerate(self.bolt_ids):
            for j, bolt_j in enumerate(self.bolt_ids):
                if i == j:
                    correlation_matrix[i, j] = 1.0
                else:
                    data_i = bolt_data[bolt_i]
                    data_j = bolt_data[bolt_j]
                    
                    # 对齐长度
                    min_len = min(len(data_i), len(data_j))
                    corr, _ = stats.pearsonr(data_i[:min_len], data_j[:min_len])
                    correlation_matrix[i, j] = corr if not np.isnan(corr) else 0.0
        
        self.correlation_matrix = correlation_matrix
        logger.info(f"螺栓相关性分析完成: {n_bolts}个螺栓")
        
        return correlation_matrix
    
    def prepare_data(
        self,
        multi_bolt_data: List[np.ndarray],
        labels: Optional[np.ndarray] = None,
        sequence_length: int = 100
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], torch.Tensor]:
        """
        准备多螺栓数据
        
        Args:
            multi_bolt_data: 多螺栓数据列表，每个元素为单个螺栓的时序数据
            labels: 标签数据
            sequence_length: 序列长度
            
        Returns:
            Tuple: (输入张量, 标签张量, 螺栓掩码)
        """
        max_bolts = self.model_config.get('max_bolts', 20)
        n_bolts = len(multi_bolt_data)
        
        # 处理每个螺栓的数据
        processed_bolts = []
        for bolt_data in multi_bolt_data[:max_bolts]:
            # 确保是2D的
            if bolt_data.ndim == 1:
                n = len(bolt_data)
                time_index = np.arange(n) / n
                bolt_data = np.column_stack([bolt_data, time_index])
            
            # 调整长度
            if len(bolt_data) < sequence_length:
                # 填充
                padded = np.zeros((sequence_length, bolt_data.shape[1]))
                padded[-len(bolt_data):] = bolt_data
                bolt_data = padded
            else:
                # 截断
                bolt_data = bolt_data[-sequence_length:]
            
            processed_bolts.append(bolt_data)
        
        # 填充不足的螺栓位置
        while len(processed_bolts) < max_bolts:
            processed_bolts.append(np.zeros((sequence_length, 2)))
        
        # 转换为张量
        X = torch.FloatTensor(np.array(processed_bolts)).unsqueeze(0)  # (1, max_bolts, seq_len, 2)
        X = X.to(self.device)
        
        # 创建螺栓掩码
        mask = torch.zeros(max_bolts, dtype=torch.bool)
        mask[:n_bolts] = True
        mask = mask.to(self.device)
        
        if labels is not None:
            y = torch.LongTensor(labels).to(self.device)
            return X, y, mask
        
        return X, None, mask
    
    def train(
        self,
        train_data: List[List[np.ndarray]],
        train_labels: np.ndarray,
        val_data: Optional[List[List[np.ndarray]]] = None,
        val_labels: Optional[np.ndarray] = None,
        epochs: Optional[int] = None,
        batch_size: Optional[int] = None,
        learning_rate: Optional[float] = None,
        class_weights: Optional[np.ndarray] = None,
        training_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        增强版训练方法

        支持：
        - 可配置早停机制（patience/min_delta/mode）
        - 学习率调度（ReduceLROnPlateau/StepLR/CosineAnnealing）
        - 类别不平衡处理（加权损失 + 过采样 WeightedRandomSampler）
        - 增量训练（冻结指定层，fine-tune）
        - 完整评估指标（精确率/召回率/F1/混淆矩阵）

        Args:
            train_data: 训练数据，列表的列表，外层是样本，内层是螺栓
            train_labels: 训练标签
            val_data: 验证数据
            val_labels: 验证标签
            epochs: 训练轮数
            batch_size: 批次大小
            learning_rate: 学习率
            class_weights: 类别权重
            training_config: 增强训练配置字典，包含：
                - early_stopping: {enabled, patience, min_delta, mode}
                - lr_scheduler: {type, ...params}
                - class_imbalance: {strategy: weighted_loss/oversampling/none, oversampling_ratio}
                - incremental: {enabled, freeze_layers: [layer_names]}
                - focal_loss: {enabled, gamma, alpha}

        Returns:
            Dict: 包含训练历史和完整评估指标
        """
        if training_config is None:
            training_config = {}

        epochs = epochs or self.training_config.get('epochs', 100)
        batch_size = batch_size or self.training_config.get('batch_size', 32)
        learning_rate = learning_rate or self.training_config.get('learning_rate', 0.001)

        es_config = training_config.get('early_stopping', {})
        es_enabled = es_config.get('enabled', True)
        patience = es_config.get('patience', self.training_config.get('early_stopping_patience', 10))
        min_delta = es_config.get('min_delta', 0.001)
        es_mode = es_config.get('mode', 'min')

        lr_config = training_config.get('lr_scheduler', {})
        lr_scheduler_type = lr_config.get('type', self.training_config.get('lr_scheduler_type', 'none'))

        ci_config = training_config.get('class_imbalance', {})
        ci_strategy = ci_config.get('strategy', 'weighted_loss')
        oversampling_ratio = ci_config.get('oversampling_ratio', 1.0)

        inc_config = training_config.get('incremental', {})
        inc_enabled = inc_config.get('enabled', False)
        freeze_layers = inc_config.get('freeze_layers', [])

        fl_config = training_config.get('focal_loss', {})
        fl_enabled = fl_config.get('enabled', False)
        fl_gamma = fl_config.get('gamma', 2.0)
        fl_alpha = fl_config.get('alpha', None)

        sequence_length = self.model_config.get('sequence_length', 100)

        all_X = []
        all_masks = []
        for sample in train_data:
            X, _, mask = self.prepare_data(sample, sequence_length=sequence_length)
            all_X.append(X.squeeze(0))
            all_masks.append(mask)

        X_train = torch.stack(all_X).to(self.device)
        y_train = torch.LongTensor(train_labels).to(self.device)

        if val_data is not None and val_labels is not None:
            all_val_X = []
            for sample in val_data:
                X, _, _ = self.prepare_data(sample, sequence_length=sequence_length)
                all_val_X.append(X.squeeze(0))
            X_val = torch.stack(all_val_X).to(self.device)
            y_val = torch.LongTensor(val_labels).to(self.device)
        else:
            val_split = self.training_config.get('validation_split', 0.2)
            val_size = max(1, int(len(X_train) * val_split))
            X_val = X_train[-val_size:]
            y_val = y_train[-val_size:]
            X_train = X_train[:-val_size]
            y_train = y_train[:-val_size]

        if inc_enabled and freeze_layers:
            self._freeze_layers(freeze_layers)
            logger.info(f"增量训练模式: 冻结层 {freeze_layers}")

        train_dataset = TensorDataset(X_train, y_train)
        sampler = None
        shuffle = True

        if ci_strategy == 'oversampling':
            try:
                label_counts = Counter(y_train.cpu().numpy())
                num_samples = len(y_train)
                weights = []
                max_count = max(label_counts.values())
                for lbl in y_train.cpu().numpy():
                    weight = (max_count / label_counts[lbl]) * oversampling_ratio
                    weights.append(weight)
                sampler = WeightedRandomSampler(
                    weights=torch.DoubleTensor(weights),
                    num_samples=int(num_samples * oversampling_ratio),
                    replacement=True
                )
                shuffle = False
                logger.info(f"过采样模式: 原始样本数 {num_samples}, 采样后 {int(num_samples * oversampling_ratio)}")
            except Exception as e:
                logger.warning(f"过采样设置失败，回退到默认: {e}")

        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=shuffle,
            sampler=sampler
        )

        if fl_enabled:
            criterion = self._create_focal_loss(fl_gamma, fl_alpha, class_weights)
            logger.info(f"使用Focal Loss: gamma={fl_gamma}")
        elif class_weights is not None and ci_strategy in ('weighted_loss', 'none'):
            weights = torch.FloatTensor(class_weights).to(self.device)
            criterion = nn.CrossEntropyLoss(weight=weights)
            logger.info(f"使用加权交叉熵损失: 权重={class_weights.tolist()}")
        else:
            criterion = nn.CrossEntropyLoss()

        trainable_params = [p for p in self.model.parameters() if p.requires_grad]
        optimizer = optim.Adam(trainable_params, lr=learning_rate)

        scheduler = None
        if lr_scheduler_type == 'reduce_on_plateau':
            scheduler = ReduceLROnPlateau(
                optimizer,
                mode=es_mode,
                factor=lr_config.get('factor', 0.5),
                patience=lr_config.get('patience', 5),
                min_lr=lr_config.get('min_lr', 1e-6)
            )
            logger.info(f"学习率调度: ReduceLROnPlateau")
        elif lr_scheduler_type == 'step':
            scheduler = StepLR(
                optimizer,
                step_size=lr_config.get('step_size', 20),
                gamma=lr_config.get('gamma', 0.5)
            )
            logger.info(f"学习率调度: StepLR")
        elif lr_scheduler_type == 'cosine':
            scheduler = CosineAnnealingLR(
                optimizer,
                T_max=lr_config.get('t_max', epochs),
                eta_min=lr_config.get('eta_min', 1e-6)
            )
            logger.info(f"学习率调度: CosineAnnealing")

        best_value = float('inf') if es_mode == 'min' else float('-inf')
        patience_counter = 0
        best_model_state = None
        best_epoch = 0
        all_val_preds = []
        all_val_labels = []

        history = {
            'train_loss': [],
            'val_loss': [],
            'train_acc': [],
            'val_acc': [],
            'learning_rates': []
        }

        class_distribution = dict(Counter(y_train.cpu().numpy().tolist()))
        val_class_distribution = dict(Counter(y_val.cpu().numpy().tolist()))
        logger.info(f"训练集类别分布: {class_distribution}")
        logger.info(f"验证集类别分布: {val_class_distribution}")
        logger.info(f"开始训练: epochs={epochs}, batch_size={batch_size}, lr={learning_rate}")

        for epoch in range(epochs):
            epoch_start = time.time()
            self.model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0

            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs, _ = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()

                train_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                train_total += batch_y.size(0)
                train_correct += (predicted == batch_y).sum().item()

            avg_train_loss = train_loss / max(1, len(train_loader))
            train_acc = train_correct / max(1, train_total)

            self.model.eval()
            with torch.no_grad():
                val_outputs, _ = self.model(X_val)
                val_loss = criterion(val_outputs, y_val).item()
                _, val_predicted = torch.max(val_outputs.data, 1)
                val_acc = (val_predicted == y_val).sum().item() / max(1, len(y_val))
                all_val_preds = val_predicted.cpu().numpy().tolist()
                all_val_labels = y_val.cpu().numpy().tolist()

            current_lr = optimizer.param_groups[0]['lr']
            history['train_loss'].append(avg_train_loss)
            history['val_loss'].append(val_loss)
            history['train_acc'].append(train_acc)
            history['val_acc'].append(val_acc)
            history['learning_rates'].append(current_lr)

            if scheduler is not None:
                if lr_scheduler_type == 'reduce_on_plateau':
                    scheduler.step(val_loss if es_mode == 'min' else val_acc)
                else:
                    scheduler.step()

            monitor_value = val_loss if es_mode == 'min' else val_acc
            if es_mode == 'min':
                is_improved = monitor_value < (best_value - min_delta)
            else:
                is_improved = monitor_value > (best_value + min_delta)

            if is_improved:
                best_value = monitor_value
                patience_counter = 0
                best_model_state = {k: v.clone() for k, v in self.model.state_dict().items()}
                best_epoch = epoch + 1
            else:
                patience_counter += 1

            if (epoch + 1) % 10 == 0:
                epoch_duration = time.time() - epoch_start
                logger.info(
                    f"Epoch {epoch+1}/{epochs}: "
                    f"train_loss={avg_train_loss:.4f}, train_acc={train_acc:.4f}, "
                    f"val_loss={val_loss:.4f}, val_acc={val_acc:.4f}, "
                    f"lr={current_lr:.6f}, time={epoch_duration:.1f}s"
                )

            if es_enabled and patience_counter >= patience:
                logger.info(f"早停触发于 epoch {epoch+1}，最佳 epoch={best_epoch}")
                break

        if best_model_state is not None:
            self.model.load_state_dict(best_model_state)

        eval_metrics = self._evaluate_model(
            X_val, y_val, all_val_preds, all_val_labels
        )

        self.is_trained = True
        self.training_history = history

        logger.info(
            f"训练完成: 最佳{es_mode}={best_value:.4f} (epoch {best_epoch}), "
            f"F1={eval_metrics['f1_weighted']:.4f}"
        )

        return {
            'history': history,
            'evaluation': eval_metrics,
            'best_epoch': best_epoch,
            'best_value': best_value,
            'class_distribution': {str(k): v for k, v in class_distribution.items()},
            'val_class_distribution': {str(k): v for k, v in val_class_distribution.items()},
            'config_used': {
                'epochs': epochs,
                'batch_size': batch_size,
                'learning_rate': learning_rate,
                'early_stopping': es_config if es_enabled else None,
                'lr_scheduler': lr_config if lr_scheduler_type != 'none' else None,
                'class_imbalance': ci_config,
                'incremental': inc_config if inc_enabled else None,
                'focal_loss': fl_config if fl_enabled else None,
            }
        }

    def _freeze_layers(self, layer_names: List[str]) -> None:
        """
        冻结指定层的参数

        Args:
            layer_names: 要冻结的层名称列表
        """
        for name, param in self.model.named_parameters():
            for freeze_name in layer_names:
                if freeze_name in name:
                    param.requires_grad = False
                    logger.debug(f"冻结参数: {name}")
                    break

    def unfreeze_all(self) -> None:
        """解冻所有层参数"""
        for param in self.model.parameters():
            param.requires_grad = True

    def get_trainable_layer_names(self) -> List[str]:
        """获取所有可训练的层名称"""
        return [name for name, _ in self.model.named_parameters()]

    def _create_focal_loss(
        self,
        gamma: float = 2.0,
        alpha: Optional[List[float]] = None,
        class_weights: Optional[np.ndarray] = None
    ):
        """
        创建Focal Loss损失函数

        Args:
            gamma: 聚焦参数，难例加权系数
            alpha: 类别权重
            class_weights: 可选的类别权重

        Returns:
            可调用的Focal Loss函数
        """
        if alpha is None and class_weights is not None:
            alpha = class_weights.tolist()

        if alpha is not None:
            alpha_tensor = torch.FloatTensor(alpha).to(self.device)
        else:
            alpha_tensor = None

        def focal_loss(inputs, targets):
            ce_loss = nn.CrossEntropyLoss(
                weight=alpha_tensor, reduction='none'
            )(inputs, targets)

            pt = torch.exp(-ce_loss)
            focal_loss_value = ((1 - pt) ** gamma) * ce_loss

            return focal_loss_value.mean()

        return focal_loss

    def _evaluate_model(
        self,
        X_val: torch.Tensor,
        y_val: torch.Tensor,
        preds: List[int],
        labels: List[int]
    ) -> Dict[str, Any]:
        """
        计算完整评估指标

        Args:
            X_val: 验证数据
            y_val: 验证标签
            preds: 预测结果
            labels: 真实标签

        Returns:
            Dict: 包含 precision/recall/f1/confusion_matrix 等指标
        """
        num_classes = self.model_config.get('output_classes', 5)
        y_true = np.array(labels)
        y_pred = np.array(preds)

        confusion_matrix = np.zeros((num_classes, num_classes), dtype=int)
        for t, p in zip(y_true, y_pred):
            if 0 <= t < num_classes and 0 <= p < num_classes:
                confusion_matrix[t][p] += 1

        precision_per_class = []
        recall_per_class = []
        f1_per_class = []
        support_per_class = []

        for c in range(num_classes):
            tp = confusion_matrix[c][c]
            fp = confusion_matrix[:, c].sum() - tp
            fn = confusion_matrix[c, :].sum() - tp

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
            support = int(confusion_matrix[c, :].sum())

            precision_per_class.append(float(precision))
            recall_per_class.append(float(recall))
            f1_per_class.append(float(f1))
            support_per_class.append(support)

        total_support = sum(support_per_class)
        if total_support > 0:
            precision_weighted = sum(
                p * s for p, s in zip(precision_per_class, support_per_class)
            ) / total_support
            recall_weighted = sum(
                r * s for r, s in zip(recall_per_class, support_per_class)
            ) / total_support
            f1_weighted = sum(
                f * s for f, s in zip(f1_per_class, support_per_class)
            ) / total_support
        else:
            precision_weighted = recall_weighted = f1_weighted = 0.0

        accuracy = np.mean(y_true == y_pred) if len(y_true) > 0 else 0.0

        return {
            'accuracy': float(accuracy),
            'precision_weighted': float(precision_weighted),
            'recall_weighted': float(recall_weighted),
            'f1_weighted': float(f1_weighted),
            'precision_per_class': precision_per_class,
            'recall_per_class': recall_per_class,
            'f1_per_class': f1_per_class,
            'support_per_class': support_per_class,
            'confusion_matrix': confusion_matrix.tolist(),
            'num_samples': int(len(y_true))
        }

    def predict(
        self,
        multi_bolt_data: List[np.ndarray],
        return_attention: bool = False
    ) -> Tuple[int, float, Optional[np.ndarray]]:
        """
        预测法兰面状态
        
        Args:
            multi_bolt_data: 多螺栓数据列表
            return_attention: 是否返回注意力权重
            
        Returns:
            Tuple: (预测类别, 置信度, 注意力权重或None)
        """
        self.model.eval()
        
        sequence_length = self.model_config.get('sequence_length', 100)
        X, _, mask = self.prepare_data(multi_bolt_data, sequence_length=sequence_length)
        
        with torch.no_grad():
            outputs, attention_weights = self.model(X)
            probabilities = torch.softmax(outputs, dim=1)
            
            prob = probabilities[0].cpu().numpy()
            predicted_class = int(torch.argmax(probabilities[0]).item())
            confidence = float(prob[predicted_class])
        
        if return_attention:
            return predicted_class, confidence, attention_weights.cpu().numpy()
        
        return predicted_class, confidence, None
    
    def get_status_label(self, class_id: int) -> str:
        """获取状态标签"""
        labels = {0: '正常', 1: '关注级预警', 2: '检查级预警', 3: '紧急级预警', 4: '故障'}
        return labels.get(class_id, '未知')
    
    def get_recommendation(self, class_id: int, confidence: float) -> str:
        """获取推荐措施"""
        recommendations = {
            0: "法兰面整体状态良好，继续正常监测。",
            1: "部分螺栓出现异常趋势，建议加强监测频率。",
            2: "法兰面存在异常，建议组织检查并制定维护方案。",
            3: "法兰面状态紧急，需立即采取措施防止事故扩大。",
            4: "法兰面发生故障，需紧急停机处理。"
        }
        return recommendations.get(class_id, "请联系技术人员评估。")
    
    def save(self, path: Optional[str] = None) -> str:
        """保存模型"""
        if path is None:
            save_dir = Path(config.get('model.save_path', './trained_models'))
            save_dir.mkdir(parents=True, exist_ok=True)
            
            if self.flange_id:
                filename = f"flange_attention_{self.flange_id}.pt"
            else:
                filename = "flange_attention_default.pt"
            
            path = str(save_dir / filename)
        
        save_data = {
            'model_state_dict': self.model.state_dict(),
            'model_config': self.model_config,
            'flange_id': self.flange_id,
            'is_trained': self.is_trained,
            'correlation_matrix': self.correlation_matrix,
            'bolt_ids': self.bolt_ids,
            'training_history': self.training_history
        }
        
        torch.save(save_data, path)
        logger.info(f"法兰面模型已保存: {path}")
        
        return path
    
    def load(self, path: str) -> None:
        """加载模型"""
        if not os.path.exists(path):
            raise FileNotFoundError(f"模型文件不存在: {path}")
        
        save_data = torch.load(path, map_location=self.device)
        
        self.model.load_state_dict(save_data['model_state_dict'])
        self.model_config = save_data.get('model_config', self.model_config)
        self.flange_id = save_data.get('flange_id', self.flange_id)
        self.is_trained = save_data.get('is_trained', True)
        self.correlation_matrix = save_data.get('correlation_matrix')
        self.bolt_ids = save_data.get('bolt_ids', [])
        self.training_history = save_data.get('training_history', [])
        
        self.model.eval()
        logger.info(f"法兰面模型已加载: {path}")
    
    def granger_causality_test(
        self,
        bolt_data: Dict[str, np.ndarray],
        max_lag: int = 5,
        significance_level: float = 0.05
    ) -> Dict[str, Any]:
        """
        格兰杰因果检验

        检验螺栓之间的因果关系：如果螺栓X的历史值有助于预测螺栓Y的未来值，
        则称X Granger引起Y。

        Args:
            bolt_data: 螺栓数据字典 {bolt_id: time_series}
            max_lag: 最大滞后阶数
            significance_level: 显著性水平

        Returns:
            Dict: 包含因果矩阵、p值矩阵、F统计量矩阵的字典
        """
        self.bolt_ids = list(bolt_data.keys())
        n_bolts = len(self.bolt_ids)

        if n_bolts < 2:
            return {
                'causal_matrix': np.zeros((1, 1)),
                'p_value_matrix': np.ones((1, 1)),
                'f_stat_matrix': np.zeros((1, 1)),
                'optimal_lags': np.zeros((1, 1), dtype=int),
                'bolt_ids': self.bolt_ids
            }

        causal_matrix = np.zeros((n_bolts, n_bolts))
        p_value_matrix = np.ones((n_bolts, n_bolts))
        f_stat_matrix = np.zeros((n_bolts, n_bolts))
        optimal_lags = np.zeros((n_bolts, n_bolts), dtype=int)

        for i, bolt_i in enumerate(self.bolt_ids):
            for j, bolt_j in enumerate(self.bolt_ids):
                if i == j:
                    causal_matrix[i, j] = 1.0
                    p_value_matrix[i, j] = 0.0
                    continue

                data_i = bolt_data[bolt_i]
                data_j = bolt_data[bolt_j]

                min_len = min(len(data_i), len(data_j))
                x = data_i[-min_len:]
                y = data_j[-min_len:]

                best_p_value = 1.0
                best_f_stat = 0.0
                best_lag = 0

                for lag in range(1, min(max_lag, min_len // 4) + 1):
                    f_stat, p_value = self._granger_test_pair(x, y, lag)
                    if p_value < best_p_value:
                        best_p_value = p_value
                        best_f_stat = f_stat
                        best_lag = lag

                p_value_matrix[i, j] = best_p_value
                f_stat_matrix[i, j] = best_f_stat
                optimal_lags[i, j] = best_lag

                if best_p_value < significance_level:
                    causal_matrix[i, j] = 1.0

        self.causal_matrix = causal_matrix
        self.p_value_matrix = p_value_matrix
        self.f_stat_matrix = f_stat_matrix
        self.optimal_lags = optimal_lags

        logger.info(f"格兰杰因果检验完成: {n_bolts}个螺栓, 显著因果对: {int(np.sum(causal_matrix) - n_bolts)}")

        return {
            'causal_matrix': causal_matrix.tolist(),
            'p_value_matrix': p_value_matrix.tolist(),
            'f_stat_matrix': f_stat_matrix.tolist(),
            'optimal_lags': optimal_lags.tolist(),
            'bolt_ids': self.bolt_ids
        }

    def _granger_test_pair(
        self,
        x: np.ndarray,
        y: np.ndarray,
        lag: int
    ) -> Tuple[float, float]:
        """
        对两个时间序列进行Granger因果检验

        使用F检验比较受限模型（仅y自回归）和非受限模型（y自回归 + x滞后）

        Args:
            x: 原因变量序列
            y: 结果变量序列
            lag: 滞后阶数

        Returns:
            Tuple: (F统计量, p值)
        """
        n = len(y) - lag

        if n < lag * 2 + 2:
            return 0.0, 1.0

        y_future = y[lag:]

        Y_restricted = np.zeros((n, lag + 1))
        for i in range(lag):
            Y_restricted[:, i] = y[lag - i - 1:n + lag - i - 1]
        Y_restricted[:, lag] = 1.0

        Y_unrestricted = np.zeros((n, lag * 2 + 1))
        for i in range(lag):
            Y_unrestricted[:, i] = y[lag - i - 1:n + lag - i - 1]
        for i in range(lag):
            Y_unrestricted[:, lag + i] = x[lag - i - 1:n + lag - i - 1]
        Y_unrestricted[:, lag * 2] = 1.0

        try:
            beta_restricted = np.linalg.lstsq(Y_restricted, y_future, rcond=None)[0]
            residuals_restricted = y_future - Y_restricted @ beta_restricted
            ssr_restricted = np.sum(residuals_restricted ** 2)

            beta_unrestricted = np.linalg.lstsq(Y_unrestricted, y_future, rcond=None)[0]
            residuals_unrestricted = y_future - Y_unrestricted @ beta_unrestricted
            ssr_unrestricted = np.sum(residuals_unrestricted ** 2)

            df1 = lag
            df2 = n - lag * 2 - 1

            if df2 <= 0 or ssr_unrestricted <= 0:
                return 0.0, 1.0

            f_stat = ((ssr_restricted - ssr_unrestricted) / df1) / (ssr_unrestricted / df2)

            from scipy.stats import f as f_dist
            p_value = 1 - f_dist.cdf(f_stat, df1, df2)

            return f_stat, p_value
        except Exception:
            return 0.0, 1.0

    def build_causal_graph(
        self,
        bolt_data: Dict[str, np.ndarray],
        max_lag: int = 5,
        significance_level: float = 0.05,
        min_correlation: float = 0.3
    ) -> Dict[str, Any]:
        """
        构建螺栓因果关系图

        结合相关性和Granger因果关系，构建有向因果图。

        Args:
            bolt_data: 螺栓数据字典 {bolt_id: time_series}
            max_lag: 最大滞后阶数
            significance_level: Granger检验显著性水平
            min_correlation: 最小相关系数阈值

        Returns:
            Dict: 因果图数据，包含节点、边、邻接矩阵等
        """
        if self.correlation_matrix is None or self.bolt_ids != list(bolt_data.keys()):
            self.analyze_bolt_correlations(bolt_data)

        granger_result = self.granger_causality_test(bolt_data, max_lag, significance_level)
        causal_matrix = np.array(granger_result['causal_matrix'])
        p_value_matrix = np.array(granger_result['p_value_matrix'])
        f_stat_matrix = np.array(granger_result['f_stat_matrix'])
        optimal_lags = np.array(granger_result['optimal_lags'])

        n_bolts = len(self.bolt_ids)

        adjacency_matrix = np.zeros((n_bolts, n_bolts))
        edge_weights = np.zeros((n_bolts, n_bolts))

        edges = []
        for i in range(n_bolts):
            for j in range(n_bolts):
                if i == j:
                    continue

                corr = abs(self.correlation_matrix[i, j])
                is_causal = causal_matrix[i, j] == 1
                is_correlated = corr >= min_correlation

                if is_causal and is_correlated:
                    weight = corr * (1 - p_value_matrix[i, j])
                    adjacency_matrix[i, j] = 1
                    edge_weights[i, j] = weight

                    edges.append({
                        'source': self.bolt_ids[i],
                        'target': self.bolt_ids[j],
                        'source_idx': i,
                        'target_idx': j,
                        'weight': float(weight),
                        'correlation': float(self.correlation_matrix[i, j]),
                        'p_value': float(p_value_matrix[i, j]),
                        'f_stat': float(f_stat_matrix[i, j]),
                        'lag': int(optimal_lags[i, j]),
                        'type': 'causal'
                    })
                elif is_correlated and abs(self.correlation_matrix[j, i]) < min_correlation:
                    weight = corr * 0.5
                    adjacency_matrix[i, j] = 1
                    edge_weights[i, j] = weight

                    edges.append({
                        'source': self.bolt_ids[i],
                        'target': self.bolt_ids[j],
                        'source_idx': i,
                        'target_idx': j,
                        'weight': float(weight),
                        'correlation': float(self.correlation_matrix[i, j]),
                        'p_value': None,
                        'f_stat': None,
                        'lag': None,
                        'type': 'correlated'
                    })

        nodes = []
        in_degree = np.sum(adjacency_matrix, axis=0)
        out_degree = np.sum(adjacency_matrix, axis=1)

        for i, bolt_id in enumerate(self.bolt_ids):
            nodes.append({
                'id': bolt_id,
                'index': i,
                'in_degree': int(in_degree[i]),
                'out_degree': int(out_degree[i]),
                'total_degree': int(in_degree[i] + out_degree[i]),
                'centrality': float((in_degree[i] + out_degree[i]) / max(n_bolts - 1, 1))
            })

        self.causal_graph = {
            'nodes': nodes,
            'edges': edges,
            'adjacency_matrix': adjacency_matrix.tolist(),
            'edge_weights': edge_weights.tolist(),
            'bolt_ids': self.bolt_ids
        }

        logger.info(f"因果图构建完成: {n_bolts}个节点, {len(edges)}条边")

        return self.causal_graph

    def identify_leading_bolts(
        self,
        bolt_data: Dict[str, np.ndarray],
        max_lag: int = 5
    ) -> List[Dict[str, Any]]:
        """
        识别领先螺栓

        领先螺栓定义：
        1. 出度 > 入度（作为原因的次数多于作为结果的次数）
        2. Granger因果检验中显著影响多个其他螺栓
        3. 变化趋势领先于其他螺栓

        Args:
            bolt_data: 螺栓数据字典
            max_lag: 最大滞后阶数

        Returns:
            List[Dict]: 领先螺栓列表，按领先程度排序
        """
        if not hasattr(self, 'causal_graph') or self.causal_graph is None:
            self.build_causal_graph(bolt_data, max_lag)

        if self.correlation_matrix is None:
            self.analyze_bolt_correlations(bolt_data)

        adjacency_matrix = np.array(self.causal_graph['adjacency_matrix'])
        edge_weights = np.array(self.causal_graph['edge_weights'])

        in_degree = np.sum(adjacency_matrix, axis=0)
        out_degree = np.sum(adjacency_matrix, axis=1)

        out_strength = np.sum(edge_weights, axis=1)
        in_strength = np.sum(edge_weights, axis=0)

        leading_scores = []
        for i, bolt_id in enumerate(self.bolt_ids):
            net_out_degree = out_degree[i] - in_degree[i]
            net_out_strength = out_strength[i] - in_strength[i]

            trend_lead = self._calculate_trend_leadership(bolt_data, bolt_id, max_lag)

            score = (
                0.4 * net_out_degree / max(len(self.bolt_ids) - 1, 1) +
                0.3 * net_out_strength +
                0.3 * trend_lead
            )

            leading_scores.append({
                'bolt_id': bolt_id,
                'index': i,
                'leading_score': float(score),
                'out_degree': int(out_degree[i]),
                'in_degree': int(in_degree[i]),
                'net_degree': int(net_out_degree),
                'out_strength': float(out_strength[i]),
                'in_strength': float(in_strength[i]),
                'net_strength': float(net_out_strength),
                'trend_leadership': float(trend_lead),
                'is_leading': bool(score > 0)
            })

        leading_scores.sort(key=lambda x: x['leading_score'], reverse=True)

        self.leading_bolts = leading_scores
        logger.info(f"领先螺栓识别完成: {sum(1 for b in leading_scores if b['is_leading'])}个领先螺栓")

        return leading_scores

    def _calculate_trend_leadership(
        self,
        bolt_data: Dict[str, np.ndarray],
        target_bolt: str,
        max_lag: int
    ) -> float:
        """
        计算螺栓的趋势领先性

        通过交叉相关分析，判断该螺栓的趋势变化是否领先于其他螺栓。

        Args:
            bolt_data: 螺栓数据字典
            target_bolt: 目标螺栓ID
            max_lag: 最大滞后阶数

        Returns:
            float: 趋势领先性得分 [-1, 1]
        """
        target_data = bolt_data[target_bolt]
        leadership_scores = []

        for other_bolt, other_data in bolt_data.items():
            if other_bolt == target_bolt:
                continue

            min_len = min(len(target_data), len(other_data))
            x = target_data[-min_len:]
            y = other_data[-min_len:]

            x = (x - np.mean(x)) / (np.std(x) + 1e-6)
            y = (y - np.mean(y)) / (np.std(y) + 1e-6)

            best_corr = 0
            best_lag = 0

            for lag in range(-max_lag, max_lag + 1):
                if lag == 0:
                    continue
                if lag > 0:
                    x_slice = x[:-lag]
                    y_slice = y[lag:]
                else:
                    x_slice = x[-lag:]
                    y_slice = y[:lag]

                if len(x_slice) < max_lag:
                    continue

                corr = np.correlate(x_slice - np.mean(x_slice),
                                    y_slice - np.mean(y_slice),
                                    mode='valid')[0] / len(x_slice)
                corr = corr / (np.std(x_slice) * np.std(y_slice) + 1e-6)

                if abs(corr) > abs(best_corr):
                    best_corr = corr
                    best_lag = lag

            if best_lag < 0:
                leadership_scores.append(abs(best_corr))
            elif best_lag > 0:
                leadership_scores.append(-abs(best_corr))
            else:
                leadership_scores.append(0)

        if leadership_scores:
            return float(np.mean(leadership_scores))
        return 0.0

    def analyze_propagation_paths(
        self,
        bolt_data: Dict[str, np.ndarray],
        source_bolt: Optional[str] = None,
        max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        分析松动传播路径

        从领先螺栓或指定源螺栓出发，追踪松动的传播路径。

        Args:
            bolt_data: 螺栓数据字典
            source_bolt: 源螺栓ID，None则使用领先螺栓
            max_depth: 最大传播深度

        Returns:
            Dict: 传播路径分析结果
        """
        if not hasattr(self, 'causal_graph') or self.causal_graph is None:
            self.build_causal_graph(bolt_data)

        if source_bolt is None:
            if not hasattr(self, 'leading_bolts') or self.leading_bolts is None:
                self.identify_leading_bolts(bolt_data)
            if self.leading_bolts and self.leading_bolts[0]['is_leading']:
                source_bolt = self.leading_bolts[0]['bolt_id']
            else:
                source_bolt = self.bolt_ids[0]

        if source_bolt not in self.bolt_ids:
            raise ValueError(f"源螺栓 {source_bolt} 不在螺栓列表中")

        source_idx = self.bolt_ids.index(source_bolt)
        adjacency_matrix = np.array(self.causal_graph['adjacency_matrix'])
        edge_weights = np.array(self.causal_graph['edge_weights'])

        paths = []
        visited = set()

        def dfs(current_idx: int, path: List[int], depth: int, weight: float):
            if depth > max_depth:
                return

            if len(path) >= 2:
                paths.append({
                    'path': [self.bolt_ids[idx] for idx in path],
                    'path_indices': path.copy(),
                    'depth': depth,
                    'total_weight': weight,
                    'avg_weight': weight / max(depth, 1)
                })

            for next_idx in range(len(self.bolt_ids)):
                if next_idx not in visited and adjacency_matrix[current_idx, next_idx] > 0:
                    visited.add(next_idx)
                    path.append(next_idx)
                    dfs(next_idx, path, depth + 1, weight + edge_weights[current_idx, next_idx])
                    path.pop()
                    visited.remove(next_idx)

        visited.add(source_idx)
        dfs(source_idx, [source_idx], 0, 0.0)

        paths.sort(key=lambda p: p['total_weight'], reverse=True)

        reachable_bolts = set()
        for path in paths:
            for bolt_id in path['path']:
                reachable_bolts.add(bolt_id)

        propagation_distance = {}
        for bolt_id in self.bolt_ids:
            if bolt_id == source_bolt:
                propagation_distance[bolt_id] = 0
            else:
                shortest = None
                for path in paths:
                    if path['path'][-1] == bolt_id:
                        if shortest is None or path['depth'] < shortest:
                            shortest = path['depth']
                propagation_distance[bolt_id] = shortest

        self.propagation_paths = {
            'source_bolt': source_bolt,
            'source_idx': source_idx,
            'paths': paths[:20],
            'total_path_count': len(paths),
            'reachable_bolts': list(reachable_bolts),
            'propagation_distance': propagation_distance,
            'max_depth': max_depth
        }

        logger.info(f"传播路径分析完成: 源螺栓={source_bolt}, 路径数={len(paths)}, 可达螺栓数={len(reachable_bolts)}")

        return self.propagation_paths

    def identify_root_cause_bolt(
        self,
        bolt_data: Dict[str, np.ndarray],
        bolt_statuses: Optional[Dict[str, int]] = None,
        bolt_health_indices: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        定位根因螺栓

        当多个螺栓出现不均衡松动时，识别根因螺栓。
        综合考虑：
        1. 因果图中的出度和因果强度
        2. 趋势领先性
        3. 健康状况（最差的可能是根因）
        4. 传播路径的源头位置

        Args:
            bolt_data: 螺栓数据字典
            bolt_statuses: 螺栓状态字典 {bolt_id: status_code}
            bolt_health_indices: 螺栓健康度字典 {bolt_id: health_index}

        Returns:
            Dict: 根因螺栓分析结果
        """
        if not hasattr(self, 'leading_bolts') or self.leading_bolts is None:
            self.identify_leading_bolts(bolt_data)

        if not hasattr(self, 'propagation_paths') or self.propagation_paths is None:
            self.analyze_propagation_paths(bolt_data)

        n_bolts = len(self.bolt_ids)

        if bolt_statuses is None:
            bolt_statuses = {}
        if bolt_health_indices is None:
            bolt_health_indices = {}

        abnormal_bolts = []
        for bolt_id in self.bolt_ids:
            status = bolt_statuses.get(bolt_id, 0)
            hi = bolt_health_indices.get(bolt_id, 50.0)
            if status >= 2 or hi < 50:
                abnormal_bolts.append(bolt_id)

        is_unbalanced_loosening = len(abnormal_bolts) >= 2 and len(abnormal_bolts) < n_bolts

        root_cause_scores = []
        for i, bolt_id in enumerate(self.bolt_ids):
            score = 0.0

            leading_info = next((b for b in self.leading_bolts if b['bolt_id'] == bolt_id), None)
            if leading_info:
                score += 0.4 * leading_info['leading_score']

            status = bolt_statuses.get(bolt_id, 0)
            hi = bolt_health_indices.get(bolt_id, 50.0)

            if status >= 2:
                score += 0.3 * (status / 4.0)
            if hi < 70:
                score += 0.3 * ((100 - hi) / 100.0)

            prop_dist = self.propagation_paths['propagation_distance'].get(bolt_id)
            if prop_dist is not None and prop_dist > 0:
                score += 0.2 * (1.0 / (prop_dist + 1))
            elif prop_dist == 0:
                score += 0.2

            root_cause_scores.append({
                'bolt_id': bolt_id,
                'index': i,
                'root_cause_score': float(score),
                'status_code': status,
                'health_index': hi,
                'is_abnormal': bolt_id in abnormal_bolts
            })

        root_cause_scores.sort(key=lambda x: x['root_cause_score'], reverse=True)

        root_cause_bolt = root_cause_scores[0] if root_cause_scores else None

        result = {
            'root_cause_bolt': root_cause_bolt,
            'root_cause_ranking': root_cause_scores,
            'abnormal_bolts': abnormal_bolts,
            'is_unbalanced_loosening': is_unbalanced_loosening,
            'total_bolts': n_bolts,
            'abnormal_count': len(abnormal_bolts)
        }

        self.root_cause_analysis = result

        logger.info(
            f"根因螺栓定位完成: "
            f"根因={root_cause_bolt['bolt_id'] if root_cause_bolt else 'N/A'}, "
            f"异常螺栓数={len(abnormal_bolts)}, "
            f"不均衡松动={is_unbalanced_loosening}"
        )

        return result

    def generate_root_cause_measures(
        self,
        root_cause_result: Dict[str, Any],
        flange_id: Optional[str] = None
    ) -> str:
        """
        生成根因分析相关的推荐措施

        Args:
            root_cause_result: 根因分析结果
            flange_id: 法兰面ID

        Returns:
            str: 推荐措施文本
        """
        root_cause_bolt = root_cause_result.get('root_cause_bolt')
        abnormal_bolts = root_cause_result.get('abnormal_bolts', [])
        is_unbalanced = root_cause_result.get('is_unbalanced_loosening', False)

        measures = []

        if not root_cause_bolt:
            return "法兰面螺栓状态整体良好，继续正常监测。"

        bolt_id = root_cause_bolt['bolt_id']
        score = root_cause_bolt.get('root_cause_score', 0)

        if is_unbalanced and len(abnormal_bolts) >= 2:
            measures.append(
                f"检测到多螺栓不均衡松动现象，共 {len(abnormal_bolts)} 个螺栓状态异常。"
            )
            measures.append(
                f"根因螺栓初步判定为 {bolt_id}（根因评分: {score:.2f}），建议优先检查该螺栓。"
            )

            if hasattr(self, 'propagation_paths') and self.propagation_paths:
                paths = self.propagation_paths.get('paths', [])
                if paths:
                    top_path = paths[0]
                    path_str = ' → '.join(top_path['path'][:4])
                    measures.append(f"主要传播路径: {path_str}，建议沿路径依次检查。")

            measures.append(
                "建议按以下优先级处理："
                "1) 首先检查并紧固根因螺栓；"
                "2) 沿传播路径依次检查关联螺栓；"
                "3) 检查法兰面密封性能；"
                "4) 分析松动原因（振动、温度循环、安装工艺等）；"
                "5) 处理后进行复测验证。"
            )
        elif len(abnormal_bolts) == 1:
            measures.append(f"螺栓 {bolt_id} 状态异常，建议进行检查和紧固。")
            measures.append("检查完成后进行复测，确认状态恢复正常。")
        else:
            measures.append("法兰面整体状态良好，继续保持日常监测。")

        if not is_unbalanced and len(abnormal_bolts) == 0:
            if hasattr(self, 'leading_bolts') and self.leading_bolts:
                leaders = [b['bolt_id'] for b in self.leading_bolts if b.get('is_leading')]
                if leaders:
                    measures.append(
                        f"领先螺栓: {', '.join(leaders[:3])}，"
                        f"这些螺栓的状态变化可能预示整体趋势，建议重点关注。"
                    )

        return ' '.join(measures)

    def comprehensive_correlation_analysis(
        self,
        bolt_data: Dict[str, np.ndarray],
        bolt_ids: Optional[List[str]] = None,
        bolt_statuses: Optional[Dict[str, int]] = None,
        bolt_health_indices: Optional[Dict[str, float]] = None,
        max_lag: int = 5,
        significance_level: float = 0.05,
        min_correlation: float = 0.3
    ) -> Dict[str, Any]:
        """
        综合关联分析

        一次性执行所有关联分析：
        1. 相关性矩阵
        2. Granger因果检验
        3. 因果图构建
        4. 领先螺栓识别
        5. 传播路径分析
        6. 根因螺栓定位

        Args:
            bolt_data: 螺栓数据字典 {bolt_id: time_series}
            bolt_ids: 螺栓ID列表（可选）
            bolt_statuses: 螺栓状态字典
            bolt_health_indices: 螺栓健康度字典
            max_lag: 最大滞后阶数
            significance_level: Granger检验显著性水平
            min_correlation: 最小相关系数阈值

        Returns:
            Dict: 综合分析结果
        """
        if bolt_ids is not None:
            filtered_data = {bid: bolt_data[bid] for bid in bolt_ids if bid in bolt_data}
        else:
            filtered_data = bolt_data

        self.analyze_bolt_correlations(filtered_data)

        self.build_causal_graph(
            filtered_data,
            max_lag=max_lag,
            significance_level=significance_level,
            min_correlation=min_correlation
        )

        self.identify_leading_bolts(filtered_data, max_lag=max_lag)

        self.analyze_propagation_paths(filtered_data, max_depth=3)

        root_cause_result = self.identify_root_cause_bolt(
            filtered_data,
            bolt_statuses=bolt_statuses,
            bolt_health_indices=bolt_health_indices
        )

        root_cause_measures = self.generate_root_cause_measures(root_cause_result)

        result = {
            'flange_id': self.flange_id,
            'bolt_count': len(self.bolt_ids),
            'bolt_ids': self.bolt_ids,
            'correlation_matrix': self.correlation_matrix.tolist() if self.correlation_matrix is not None else None,
            'causal_graph': self.causal_graph,
            'leading_bolts': self.leading_bolts,
            'propagation_paths': self.propagation_paths,
            'root_cause_analysis': root_cause_result,
            'root_cause_measures': root_cause_measures,
            'analysis_params': {
                'max_lag': max_lag,
                'significance_level': significance_level,
                'min_correlation': min_correlation
            }
        }

        logger.info(f"综合关联分析完成: 法兰面={self.flange_id}, 螺栓数={len(self.bolt_ids)}")

        return result

    @classmethod
    def load_or_create(cls, flange_id: str) -> 'FlangeAttentionModel':
        """加载已有模型或创建新模型"""
        model = cls(flange_id=flange_id)
        
        save_dir = Path(config.get('model.save_path', './trained_models'))
        model_path = save_dir / f"flange_attention_{flange_id}.pt"
        
        if model_path.exists():
            model.load(str(model_path))
        
        return model
