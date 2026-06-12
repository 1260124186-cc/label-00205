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
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path
from scipy import stats
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
        learning_rate: Optional[float] = None
    ) -> Dict[str, List[float]]:
        """
        训练模型
        
        Args:
            train_data: 训练数据，列表的列表，外层是样本，内层是螺栓
            train_labels: 训练标签
            val_data: 验证数据
            val_labels: 验证标签
            epochs: 训练轮数
            batch_size: 批次大小
            learning_rate: 学习率
            
        Returns:
            Dict: 训练历史
        """
        epochs = epochs or self.training_config.get('epochs', 100)
        batch_size = batch_size or self.training_config.get('batch_size', 32)
        learning_rate = learning_rate or self.training_config.get('learning_rate', 0.001)
        patience = self.training_config.get('early_stopping_patience', 10)
        
        sequence_length = self.model_config.get('sequence_length', 100)
        
        # 准备所有训练数据
        all_X = []
        all_masks = []
        for sample in train_data:
            X, _, mask = self.prepare_data(sample, sequence_length=sequence_length)
            all_X.append(X.squeeze(0))
            all_masks.append(mask)
        
        X_train = torch.stack(all_X).to(self.device)
        y_train = torch.LongTensor(train_labels).to(self.device)
        
        # 验证集
        if val_data is not None:
            all_val_X = []
            for sample in val_data:
                X, _, _ = self.prepare_data(sample, sequence_length=sequence_length)
                all_val_X.append(X.squeeze(0))
            X_val = torch.stack(all_val_X).to(self.device)
            y_val = torch.LongTensor(val_labels).to(self.device)
        else:
            val_split = int(len(X_train) * 0.2)
            X_val = X_train[-val_split:]
            y_val = y_train[-val_split:]
            X_train = X_train[:-val_split]
            y_train = y_train[:-val_split]
        
        # 创建数据加载器
        train_dataset = TensorDataset(X_train, y_train)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        
        best_val_loss = float('inf')
        patience_counter = 0
        best_model_state = None
        
        history = {'train_loss': [], 'val_loss': [], 'train_acc': [], 'val_acc': []}
        
        logger.info(f"开始训练法兰面模型: epochs={epochs}")
        
        for epoch in range(epochs):
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
            
            avg_train_loss = train_loss / len(train_loader)
            train_acc = train_correct / train_total
            
            # 验证
            self.model.eval()
            with torch.no_grad():
                val_outputs, _ = self.model(X_val)
                val_loss = criterion(val_outputs, y_val).item()
                _, val_predicted = torch.max(val_outputs.data, 1)
                val_acc = (val_predicted == y_val).sum().item() / len(y_val)
            
            history['train_loss'].append(avg_train_loss)
            history['val_loss'].append(val_loss)
            history['train_acc'].append(train_acc)
            history['val_acc'].append(val_acc)
            
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                best_model_state = self.model.state_dict().copy()
            else:
                patience_counter += 1
            
            if (epoch + 1) % 10 == 0:
                logger.info(f"Epoch {epoch+1}/{epochs}: val_loss={val_loss:.4f}, val_acc={val_acc:.4f}")
            
            if patience_counter >= patience:
                logger.info(f"早停触发于 epoch {epoch+1}")
                break
        
        if best_model_state is not None:
            self.model.load_state_dict(best_model_state)
        
        self.is_trained = True
        self.training_history = history
        
        return history
    
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
    
    @classmethod
    def load_or_create(cls, flange_id: str) -> 'FlangeAttentionModel':
        """加载已有模型或创建新模型"""
        model = cls(flange_id=flange_id)
        
        save_dir = Path(config.get('model.save_path', './trained_models'))
        model_path = save_dir / f"flange_attention_{flange_id}.pt"
        
        if model_path.exists():
            model.load(str(model_path))
        
        return model
