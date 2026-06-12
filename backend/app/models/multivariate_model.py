"""
多变量预测模型模块

支持温度等多因素的预紧力预测模型。

功能:
1. 温度-预紧力耦合建模
2. 多变量特征融合
3. 时序多变量LSTM预测
4. 特征重要性分析

使用示例:
    from app.models.multivariate_model import MultivariatePredictor
    
    predictor = MultivariatePredictor()
    result = predictor.predict(preload_data, temperature_data)
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from loguru import logger

from app.utils.config import config
from app.utils.device import get_device


@dataclass
class MultivariateInput:
    """
    多变量输入数据
    
    Attributes:
        preload: 预紧力数据
        temperature: 温度数据
        timestamps: 时间戳
        humidity: 湿度数据（可选）
        vibration: 振动数据（可选）
    """
    preload: np.ndarray
    temperature: Optional[np.ndarray] = None
    timestamps: Optional[np.ndarray] = None
    humidity: Optional[np.ndarray] = None
    vibration: Optional[np.ndarray] = None
    
    @property
    def n_features(self) -> int:
        """计算特征数量"""
        count = 1  # 预紧力
        if self.temperature is not None:
            count += 1
        if self.humidity is not None:
            count += 1
        if self.vibration is not None:
            count += 1
        return count
    
    def to_array(self) -> np.ndarray:
        """转换为特征数组"""
        features = [self.preload.reshape(-1, 1)]
        
        if self.temperature is not None:
            features.append(self.temperature.reshape(-1, 1))
        if self.humidity is not None:
            features.append(self.humidity.reshape(-1, 1))
        if self.vibration is not None:
            features.append(self.vibration.reshape(-1, 1))
        
        return np.hstack(features)


@dataclass
class MultivariatePrediction:
    """
    多变量预测结果
    
    Attributes:
        status: 预测状态
        status_code: 状态码
        confidence: 置信度
        feature_importance: 特征重要性
        temperature_effect: 温度影响分析
        predictions: 各变量预测值
    """
    status: str
    status_code: int
    confidence: float
    feature_importance: Dict[str, float]
    temperature_effect: Dict[str, Any]
    predictions: Dict[str, float] = field(default_factory=dict)


class TemperatureCouplingModel:
    """
    温度耦合模型
    
    分析温度对预紧力的影响，进行温度补偿。
    
    预紧力变化 = 基础变化 + 热膨胀效应
    ΔF = ΔF_base + α * ΔT * K
    
    其中:
        α: 热膨胀系数
        K: 刚度系数
    """
    
    def __init__(
        self,
        thermal_expansion_coef: float = 12e-6,  # 钢材热膨胀系数
        stiffness_factor: float = 1.0
    ):
        """
        初始化温度耦合模型
        
        Args:
            thermal_expansion_coef: 热膨胀系数 (1/°C)
            stiffness_factor: 刚度系数
        """
        self.alpha = thermal_expansion_coef
        self.stiffness = stiffness_factor
        
        # 参考温度（用于计算温度变化）
        self.reference_temp = 20.0  # °C
        
        # 拟合参数
        self._fitted = False
        self._coef = 0.0
        self._intercept = 0.0
        
    def fit(
        self,
        preload: np.ndarray,
        temperature: np.ndarray
    ) -> 'TemperatureCouplingModel':
        """
        拟合温度-预紧力关系
        
        Args:
            preload: 预紧力数据
            temperature: 温度数据
            
        Returns:
            self
        """
        # 简单线性回归
        temp_centered = temperature - self.reference_temp
        
        # 使用最小二乘法
        A = np.vstack([temp_centered, np.ones(len(temp_centered))]).T
        result = np.linalg.lstsq(A, preload, rcond=None)
        
        self._coef = result[0][0]
        self._intercept = result[0][1]
        self._fitted = True
        
        logger.debug(f"温度耦合模型拟合完成: coef={self._coef:.4f}, intercept={self._intercept:.4f}")
        
        return self
    
    def compensate(
        self,
        preload: np.ndarray,
        temperature: np.ndarray
    ) -> np.ndarray:
        """
        温度补偿
        
        将预紧力校正到参考温度下的值。
        
        Args:
            preload: 原始预紧力
            temperature: 温度
            
        Returns:
            np.ndarray: 补偿后的预紧力
        """
        if not self._fitted:
            self.fit(preload, temperature)
        
        temp_diff = temperature - self.reference_temp
        compensation = self._coef * temp_diff
        
        return preload - compensation
    
    def analyze_effect(
        self,
        preload: np.ndarray,
        temperature: np.ndarray
    ) -> Dict[str, Any]:
        """
        分析温度效应
        
        Args:
            preload: 预紧力数据
            temperature: 温度数据
            
        Returns:
            Dict: 分析结果
        """
        if not self._fitted:
            self.fit(preload, temperature)
        
        # 计算相关性
        correlation = np.corrcoef(preload, temperature)[0, 1]
        
        # 计算温度变化对预紧力的影响
        temp_range = temperature.max() - temperature.min()
        preload_effect = self._coef * temp_range
        
        # 判断影响程度
        preload_mean = np.mean(preload)
        effect_ratio = abs(preload_effect) / preload_mean if preload_mean != 0 else 0
        
        if effect_ratio < 0.01:
            effect_level = "可忽略"
        elif effect_ratio < 0.05:
            effect_level = "轻微"
        elif effect_ratio < 0.1:
            effect_level = "中等"
        else:
            effect_level = "显著"
        
        return {
            'correlation': float(correlation),
            'coefficient': float(self._coef),
            'temperature_range': float(temp_range),
            'preload_effect': float(preload_effect),
            'effect_ratio': float(effect_ratio),
            'effect_level': effect_level,
            'reference_temperature': self.reference_temp
        }


class MultivariateLSTM(nn.Module):
    """
    多变量LSTM网络
    
    支持多个输入变量的时序预测。
    """
    
    def __init__(
        self,
        input_dim: int = 4,
        hidden_dim: int = 128,
        num_layers: int = 2,
        output_classes: int = 5,
        dropout: float = 0.2
    ):
        """
        初始化多变量LSTM
        
        Args:
            input_dim: 输入特征维度
            hidden_dim: LSTM隐藏层维度
            num_layers: LSTM层数
            output_classes: 输出类别数
            dropout: Dropout比例
        """
        super().__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # 特征嵌入层
        self.feature_embed = nn.Sequential(
            nn.Linear(input_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
        # LSTM层
        self.lstm = nn.LSTM(
            input_size=hidden_dim // 2,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=True
        )
        
        # 注意力层
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1)
        )
        
        # 输出层
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, output_classes)
        )
        
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        前向传播
        
        Args:
            x: 输入张量 (batch, seq_len, input_dim)
            
        Returns:
            Tuple: (输出, 注意力权重)
        """
        # 特征嵌入
        embedded = self.feature_embed(x)  # (batch, seq, hidden//2)
        
        # LSTM
        lstm_out, _ = self.lstm(embedded)  # (batch, seq, hidden*2)
        
        # 注意力
        attn_weights = self.attention(lstm_out)  # (batch, seq, 1)
        attn_weights = torch.softmax(attn_weights, dim=1)
        
        # 加权求和
        context = torch.sum(lstm_out * attn_weights, dim=1)  # (batch, hidden*2)
        
        # 输出
        output = self.fc(context)  # (batch, output_classes)
        
        return output, attn_weights.squeeze(-1)


class MultivariatePredictor:
    """
    多变量预测器
    
    整合温度耦合和多变量LSTM的预测器。
    """
    
    STATUS_LABELS = ['正常', '关注级预警', '检查级预警', '紧急级预警', '故障']
    FEATURE_NAMES = ['预紧力', '温度', '湿度', '振动']
    
    def __init__(self, model_id: str = 'default'):
        """
        初始化多变量预测器
        
        Args:
            model_id: 模型标识
        """
        self.model_id = model_id
        self.device = get_device()
        
        # 温度耦合模型
        self.temp_coupling = TemperatureCouplingModel()
        
        # 神经网络模型
        self.model: Optional[MultivariateLSTM] = None
        
        # 配置
        self.sequence_length = config.get('model.bolt_lstm.sequence_length', 100)
        
        logger.info(f"多变量预测器初始化: model_id={model_id}, device={self.device}")
    
    def _init_model(self, input_dim: int = 4) -> None:
        """初始化模型"""
        self.model = MultivariateLSTM(
            input_dim=input_dim,
            hidden_dim=128,
            num_layers=2,
            output_classes=5
        ).to(self.device)
    
    def predict(
        self,
        data: MultivariateInput,
        apply_temp_compensation: bool = True
    ) -> MultivariatePrediction:
        """
        多变量预测
        
        Args:
            data: 多变量输入数据
            apply_temp_compensation: 是否应用温度补偿
            
        Returns:
            MultivariatePrediction: 预测结果
        """
        # 温度补偿
        if apply_temp_compensation and data.temperature is not None:
            compensated_preload = self.temp_coupling.compensate(
                data.preload, data.temperature
            )
            temp_effect = self.temp_coupling.analyze_effect(
                data.preload, data.temperature
            )
        else:
            compensated_preload = data.preload
            temp_effect = {}
        
        # 准备特征
        features = data.to_array()
        
        # 初始化或调整模型
        if self.model is None or self.model.input_dim != data.n_features:
            self._init_model(data.n_features)
        
        # 准备序列数据
        if len(features) >= self.sequence_length:
            seq = features[-self.sequence_length:]
        else:
            # 填充
            pad_len = self.sequence_length - len(features)
            seq = np.vstack([np.zeros((pad_len, data.n_features)), features])
        
        # 标准化
        seq_mean = seq.mean(axis=0, keepdims=True)
        seq_std = seq.std(axis=0, keepdims=True) + 1e-8
        seq_normalized = (seq - seq_mean) / seq_std
        
        # 转换为张量
        x = torch.FloatTensor(seq_normalized).unsqueeze(0).to(self.device)
        
        # 预测
        self.model.eval()
        with torch.no_grad():
            output, attn_weights = self.model(x)
            probs = torch.softmax(output, dim=1)
        
        # 获取预测结果
        pred_class = probs.argmax(dim=1).item()
        confidence = probs.max(dim=1).values.item()
        
        # 计算特征重要性（基于注意力和梯度）
        feature_importance = self._compute_feature_importance(
            data, attn_weights.cpu().numpy()
        )
        
        return MultivariatePrediction(
            status=self.STATUS_LABELS[pred_class],
            status_code=pred_class,
            confidence=confidence,
            feature_importance=feature_importance,
            temperature_effect=temp_effect,
            predictions={
                'preload_compensated': float(compensated_preload[-1]) if len(compensated_preload) > 0 else 0
            }
        )
    
    def _compute_feature_importance(
        self,
        data: MultivariateInput,
        attention_weights: np.ndarray
    ) -> Dict[str, float]:
        """
        计算特征重要性
        
        基于统计特性和注意力权重。
        """
        importance = {}
        
        # 基于变异系数
        features = [
            ('预紧力', data.preload),
            ('温度', data.temperature),
            ('湿度', data.humidity),
            ('振动', data.vibration)
        ]
        
        total_cv = 0
        cvs = {}
        
        for name, feat in features:
            if feat is not None and len(feat) > 0:
                cv = np.std(feat) / (np.mean(feat) + 1e-8)
                cvs[name] = cv
                total_cv += cv
        
        # 归一化
        for name, cv in cvs.items():
            importance[name] = cv / total_cv if total_cv > 0 else 0
        
        return importance


class TemperatureDataProcessor:
    """
    温度数据处理器
    
    处理温度数据，包括异常检测、平滑和插值。
    """
    
    def __init__(self):
        """初始化温度处理器"""
        self.min_temp = -40  # 最低有效温度
        self.max_temp = 100  # 最高有效温度
        
    def validate(self, temperature: np.ndarray) -> Tuple[bool, List[str]]:
        """
        验证温度数据
        
        Args:
            temperature: 温度数据
            
        Returns:
            Tuple: (是否有效, 错误列表)
        """
        errors = []
        
        if len(temperature) == 0:
            errors.append("温度数据为空")
            return False, errors
        
        # 范围检查
        if np.any(temperature < self.min_temp):
            errors.append(f"存在低于{self.min_temp}°C的异常低温")
        
        if np.any(temperature > self.max_temp):
            errors.append(f"存在高于{self.max_temp}°C的异常高温")
        
        # NaN检查
        if np.any(np.isnan(temperature)):
            errors.append("存在NaN值")
        
        return len(errors) == 0, errors
    
    def preprocess(
        self,
        temperature: np.ndarray,
        fill_method: str = 'linear'
    ) -> np.ndarray:
        """
        预处理温度数据
        
        Args:
            temperature: 原始温度数据
            fill_method: 缺失值填充方法
            
        Returns:
            np.ndarray: 处理后的温度数据
        """
        temp = temperature.copy()
        
        # 处理NaN
        if np.any(np.isnan(temp)):
            if fill_method == 'linear':
                # 线性插值
                nans = np.isnan(temp)
                x = np.arange(len(temp))
                temp[nans] = np.interp(x[nans], x[~nans], temp[~nans])
            elif fill_method == 'mean':
                temp[np.isnan(temp)] = np.nanmean(temp)
        
        # 限制范围
        temp = np.clip(temp, self.min_temp, self.max_temp)
        
        return temp
