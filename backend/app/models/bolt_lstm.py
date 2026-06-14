"""
螺栓状态预测LSTM模型

基于LSTM神经网络的螺栓预紧力状态预测模型。

模型架构:
    输入层(100×2) → LSTM(128) → Dropout(0.2) 
    → LSTM(64) → Dropout(0.2) → FC(32) → 输出层(5类)

状态类别:
    0: 正常
    1: 关注级预警
    2: 检查级预警
    3: 紧急级预警
    4: 故障

使用示例:
    from app.models.bolt_lstm import BoltLSTMModel
    
    model = BoltLSTMModel()
    prediction = model.predict(input_sequence)
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
from collections import Counter
from loguru import logger

from app.utils.config import config
from app.utils.device import get_device, clear_gpu_cache


# 状态标签映射
STATUS_LABELS = {
    0: '正常',
    1: '关注级预警',
    2: '检查级预警',
    3: '紧急级预警',
    4: '故障'
}

# 故障类型映射
FAULT_TYPES = {
    'L': '松动',
    'O': '过载',
    'B': '断裂'
}


class LSTMNetwork(nn.Module):
    """
    LSTM神经网络模型
    
    多层LSTM网络，用于时间序列分类。
    
    Attributes:
        lstm1: 第一层LSTM
        dropout1: 第一层Dropout
        lstm2: 第二层LSTM
        dropout2: 第二层Dropout
        fc: 全连接层
        output: 输出层
    """
    
    def __init__(
        self,
        input_dim: int = 2,
        lstm_units_1: int = 128,
        lstm_units_2: int = 64,
        dropout_rate: float = 0.2,
        dense_units: int = 32,
        output_classes: int = 5
    ):
        """
        初始化LSTM网络
        
        Args:
            input_dim: 输入特征维度
            lstm_units_1: 第一层LSTM单元数
            lstm_units_2: 第二层LSTM单元数
            dropout_rate: Dropout率
            dense_units: 全连接层单元数
            output_classes: 输出类别数
        """
        super(LSTMNetwork, self).__init__()
        
        # 第一层LSTM
        self.lstm1 = nn.LSTM(
            input_size=input_dim,
            hidden_size=lstm_units_1,
            batch_first=True,
            bidirectional=False
        )
        self.dropout1 = nn.Dropout(dropout_rate)
        
        # 第二层LSTM
        self.lstm2 = nn.LSTM(
            input_size=lstm_units_1,
            hidden_size=lstm_units_2,
            batch_first=True,
            bidirectional=False
        )
        self.dropout2 = nn.Dropout(dropout_rate)
        
        # 全连接层
        self.fc = nn.Linear(lstm_units_2, dense_units)
        self.relu = nn.ReLU()
        
        # 输出层
        self.output = nn.Linear(dense_units, output_classes)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        Args:
            x: 输入张量，形状为 (batch_size, sequence_length, input_dim)
            
        Returns:
            torch.Tensor: 输出张量，形状为 (batch_size, output_classes)
        """
        # LSTM层1
        lstm_out1, _ = self.lstm1(x)
        lstm_out1 = self.dropout1(lstm_out1)
        
        # LSTM层2
        lstm_out2, _ = self.lstm2(lstm_out1)
        lstm_out2 = self.dropout2(lstm_out2)
        
        # 取最后一个时间步的输出
        last_output = lstm_out2[:, -1, :]
        
        # 全连接层
        fc_out = self.relu(self.fc(last_output))
        
        # 输出层
        output = self.output(fc_out)
        
        return output


class BoltLSTMModel:
    """
    螺栓状态预测模型
    
    封装LSTM网络，提供训练、预测、保存、加载等功能。
    
    Attributes:
        model: LSTM网络模型
        device: 计算设备
        model_config: 模型配置
        bolt_id: 螺栓ID
        is_trained: 是否已训练
    """
    
    def __init__(self, bolt_id: Optional[str] = None):
        """
        初始化螺栓预测模型
        
        Args:
            bolt_id: 螺栓ID，用于区分不同螺栓的模型
        """
        self.bolt_id = bolt_id
        self.device = get_device()
        self.model_config = config.get('model.bolt_lstm', {})
        self.training_config = config.get('model.training', {})
        
        # 创建网络
        self.model = LSTMNetwork(
            input_dim=self.model_config.get('input_dim', 2),
            lstm_units_1=self.model_config.get('lstm_units_1', 128),
            lstm_units_2=self.model_config.get('lstm_units_2', 64),
            dropout_rate=self.model_config.get('dropout_rate', 0.2),
            dense_units=self.model_config.get('dense_units', 32),
            output_classes=self.model_config.get('output_classes', 5)
        ).to(self.device)
        
        self.is_trained = False
        self.training_history = []
        
        logger.info(f"螺栓LSTM模型初始化完成: bolt_id={bolt_id}, device={self.device}")
    
    def prepare_data(
        self, 
        data: np.ndarray, 
        labels: Optional[np.ndarray] = None,
        sequence_length: int = 100
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """
        准备训练/推理数据
        
        将原始数据转换为模型输入格式。
        
        Args:
            data: 原始数据，形状为 (n_samples, 2) 或 (n_samples,)
            labels: 标签数据，可选
            sequence_length: 序列长度
            
        Returns:
            Tuple: (输入张量, 标签张量或None)
        """
        # 确保数据是2D的
        if data.ndim == 1:
            # 添加时间索引作为第二个特征
            n = len(data)
            time_index = np.arange(n) / n
            data = np.column_stack([data, time_index])
        
        # 创建序列
        n_samples = len(data) - sequence_length + 1
        
        if n_samples <= 0:
            # 数据不足，进行填充
            padded_data = np.zeros((sequence_length, data.shape[1]))
            padded_data[-len(data):] = data
            sequences = padded_data.reshape(1, sequence_length, -1)
        else:
            sequences = np.zeros((n_samples, sequence_length, data.shape[1]))
            for i in range(n_samples):
                sequences[i] = data[i:i + sequence_length]
        
        # 转换为张量
        X = torch.FloatTensor(sequences).to(self.device)
        
        if labels is not None:
            # 调整标签以匹配序列数
            if len(labels) > n_samples:
                labels = labels[-n_samples:]
            y = torch.LongTensor(labels).to(self.device)
            return X, y
        
        return X, None
    
    def train(
        self,
        train_data: np.ndarray,
        train_labels: np.ndarray,
        val_data: Optional[np.ndarray] = None,
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
            train_data: 训练数据
            train_labels: 训练标签
            val_data: 验证数据，可选
            val_labels: 验证标签，可选
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
        X_train, y_train = self.prepare_data(train_data, train_labels, sequence_length)

        if val_data is not None and val_labels is not None:
            X_val, y_val = self.prepare_data(val_data, val_labels, sequence_length)
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
                outputs = self.model(batch_X)
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
            all_val_preds = []
            all_val_labels = []
            with torch.no_grad():
                val_outputs = self.model(X_val)
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
        data: np.ndarray,
        return_proba: bool = False
    ) -> Tuple[int, float, Optional[np.ndarray]]:
        """
        预测螺栓状态
        
        Args:
            data: 输入数据，形状为 (sequence_length, 2) 或 (sequence_length,)
            return_proba: 是否返回概率分布
            
        Returns:
            Tuple: (预测类别, 置信度, 概率分布或None)
        """
        self.model.eval()
        
        sequence_length = self.model_config.get('sequence_length', 100)
        X, _ = self.prepare_data(data, sequence_length=sequence_length)
        
        with torch.no_grad():
            outputs = self.model(X)
            probabilities = torch.softmax(outputs, dim=1)
            
            # 取最后一个序列的预测结果
            prob = probabilities[-1].cpu().numpy()
            predicted_class = int(torch.argmax(probabilities[-1]).item())
            confidence = float(prob[predicted_class])
        
        if return_proba:
            return predicted_class, confidence, prob
        
        return predicted_class, confidence, None
    
    def predict_batch(
        self, 
        data_list: List[np.ndarray]
    ) -> List[Tuple[int, float]]:
        """
        批量预测
        
        Args:
            data_list: 输入数据列表
            
        Returns:
            List: 预测结果列表 [(类别, 置信度), ...]
        """
        results = []
        for data in data_list:
            pred_class, confidence, _ = self.predict(data)
            results.append((pred_class, confidence))
        return results
    
    def get_status_label(self, class_id: int) -> str:
        """
        获取状态标签文本
        
        Args:
            class_id: 类别ID
            
        Returns:
            str: 状态标签
        """
        return STATUS_LABELS.get(class_id, '未知')
    
    def get_recommendation(self, class_id: int, confidence: float) -> str:
        """
        获取推荐措施
        
        Args:
            class_id: 预测类别
            confidence: 置信度
            
        Returns:
            str: 推荐措施文本
        """
        recommendations = {
            0: "继续正常监测，保持当前维护计划。",
            1: "加强监测频率，记录异常特征，关注后续变化趋势。",
            2: "组织专业检查，判定异常类型，制定维护方案。",
            3: "立即实施处理措施，防止事故扩大，考虑临时停机检修。",
            4: "紧急停机处理，排查故障原因，更换损坏部件。"
        }
        
        base_rec = recommendations.get(class_id, "请联系技术人员进行评估。")
        
        if confidence < 0.7:
            base_rec += f" 注意：预测置信度较低({confidence:.1%})，建议人工复核。"
        
        return base_rec
    
    def save(self, path: Optional[str] = None) -> str:
        """
        保存模型
        
        Args:
            path: 保存路径，可选
            
        Returns:
            str: 实际保存路径
        """
        if path is None:
            save_dir = Path(config.get('model.save_path', './trained_models'))
            save_dir.mkdir(parents=True, exist_ok=True)
            
            if self.bolt_id:
                filename = f"bolt_lstm_{self.bolt_id}.pt"
            else:
                filename = "bolt_lstm_default.pt"
            
            path = str(save_dir / filename)
        
        save_data = {
            'model_state_dict': self.model.state_dict(),
            'model_config': self.model_config,
            'bolt_id': self.bolt_id,
            'is_trained': self.is_trained,
            'training_history': self.training_history
        }
        
        torch.save(save_data, path)
        logger.info(f"模型已保存: {path}")
        
        return path
    
    def load(self, path: str) -> None:
        """
        加载模型
        
        Args:
            path: 模型文件路径
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"模型文件不存在: {path}")
        
        save_data = torch.load(path, map_location=self.device)
        
        self.model.load_state_dict(save_data['model_state_dict'])
        self.model_config = save_data.get('model_config', self.model_config)
        self.bolt_id = save_data.get('bolt_id', self.bolt_id)
        self.is_trained = save_data.get('is_trained', True)
        self.training_history = save_data.get('training_history', [])
        
        self.model.eval()
        logger.info(f"模型已加载: {path}")
    
    @classmethod
    def load_or_create(cls, bolt_id: str) -> 'BoltLSTMModel':
        """
        加载已有模型或创建新模型
        
        Args:
            bolt_id: 螺栓ID
            
        Returns:
            BoltLSTMModel: 模型实例
        """
        model = cls(bolt_id=bolt_id)
        
        save_dir = Path(config.get('model.save_path', './trained_models'))
        model_path = save_dir / f"bolt_lstm_{bolt_id}.pt"
        
        if model_path.exists():
            model.load(str(model_path))
            logger.info(f"已加载螺栓模型: {bolt_id}")
        else:
            logger.info(f"创建新的螺栓模型: {bolt_id}")
        
        return model
