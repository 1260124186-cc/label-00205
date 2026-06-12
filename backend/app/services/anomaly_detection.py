"""
异常检测服务模块

提供完整的异常值检测和处理功能：
1. 孤立森林算法检测异常值
2. 异常数据存储到异常数据表
3. 多种异常检测策略支持
4. 异常数据分析和报告

使用示例:
    from app.services.anomaly_detection import AnomalyDetector
    
    detector = AnomalyDetector()
    result = detector.detect_and_store(data, sensor_id='B001')
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from scipy import stats
from loguru import logger

from app.utils.config import config
from app.utils.database import get_db, Base
from sqlalchemy import Column, BigInteger, String, Float, DateTime, Text, Index


class AnomalyType(Enum):
    """异常类型枚举"""
    ISOLATION_FOREST = "isolation_forest"
    ZSCORE = "zscore"
    IQR = "iqr"
    SUDDEN_CHANGE = "sudden_change"
    OUT_OF_RANGE = "out_of_range"


@dataclass
class AnomalyRecord:
    """
    异常记录数据类
    
    Attributes:
        index: 原始数据中的索引
        value: 异常值
        anomaly_type: 异常类型
        score: 异常评分
        timestamp: 时间戳
        details: 详细信息
    """
    index: int
    value: float
    anomaly_type: AnomalyType
    score: float
    timestamp: Optional[datetime] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyDetectionResult:
    """
    异常检测结果数据类
    
    Attributes:
        total_points: 总数据点数
        anomaly_count: 异常点数
        anomaly_ratio: 异常比例
        anomalies: 异常记录列表
        cleaned_data: 清洗后的数据
        cleaned_indices: 保留数据的原始索引
    """
    total_points: int
    anomaly_count: int
    anomaly_ratio: float
    anomalies: List[AnomalyRecord]
    cleaned_data: np.ndarray
    cleaned_indices: np.ndarray


class IsolationForestDetector:
    """
    孤立森林异常检测器
    
    使用孤立森林算法检测多维数据中的异常点。
    
    Attributes:
        contamination: 预期异常比例
        n_estimators: 树的数量
        max_samples: 每棵树的采样数
        random_state: 随机种子
        model: 孤立森林模型
    """
    
    def __init__(
        self,
        contamination: float = 0.1,
        n_estimators: int = 100,
        max_samples: str = 'auto',
        random_state: int = 42
    ):
        """
        初始化孤立森林检测器
        
        Args:
            contamination: 预期异常比例 (0, 0.5)
            n_estimators: 树的数量
            max_samples: 每棵树的采样数
            random_state: 随机种子
        """
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.random_state = random_state
        
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            max_samples=max_samples,
            random_state=random_state,
            n_jobs=-1,
            bootstrap=True
        )
        
        self.scaler = StandardScaler()
        self._is_fitted = False
        
    def fit(self, data: np.ndarray) -> 'IsolationForestDetector':
        """
        拟合模型
        
        Args:
            data: 训练数据，形状为 (n_samples,) 或 (n_samples, n_features)
            
        Returns:
            self
        """
        # 确保数据是2D的
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        
        # 标准化数据
        data_scaled = self.scaler.fit_transform(data)
        
        # 拟合孤立森林
        self.model.fit(data_scaled)
        self._is_fitted = True
        
        logger.debug(f"孤立森林模型拟合完成: {len(data)}个样本")
        
        return self
    
    def predict(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        预测异常
        
        Args:
            data: 待检测数据
            
        Returns:
            Tuple: (预测标签, 异常评分)
            - 标签: 1=正常, -1=异常
            - 评分: 越负越可能是异常
        """
        if not self._is_fitted:
            self.fit(data)
        
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        
        # 标准化
        data_scaled = self.scaler.transform(data)
        
        # 预测
        labels = self.model.predict(data_scaled)
        scores = self.model.decision_function(data_scaled)
        
        return labels, scores
    
    def detect(
        self,
        data: np.ndarray,
        timestamps: Optional[np.ndarray] = None
    ) -> AnomalyDetectionResult:
        """
        检测异常并返回详细结果
        
        Args:
            data: 预紧力数据
            timestamps: 时间戳数组
            
        Returns:
            AnomalyDetectionResult: 检测结果
        """
        original_data = data.copy()
        labels, scores = self.predict(data)
        
        # 找出异常点
        anomaly_mask = labels == -1
        anomaly_indices = np.where(anomaly_mask)[0]
        
        anomalies = []
        for idx in anomaly_indices:
            record = AnomalyRecord(
                index=int(idx),
                value=float(original_data[idx]),
                anomaly_type=AnomalyType.ISOLATION_FOREST,
                score=float(scores[idx]),
                timestamp=timestamps[idx] if timestamps is not None else None,
                details={
                    'decision_score': float(scores[idx]),
                    'method': 'isolation_forest'
                }
            )
            anomalies.append(record)
        
        # 清洗后的数据
        cleaned_data = original_data[~anomaly_mask]
        cleaned_indices = np.where(~anomaly_mask)[0]
        
        return AnomalyDetectionResult(
            total_points=len(original_data),
            anomaly_count=len(anomalies),
            anomaly_ratio=len(anomalies) / len(original_data) if len(original_data) > 0 else 0,
            anomalies=anomalies,
            cleaned_data=cleaned_data,
            cleaned_indices=cleaned_indices
        )


class StatisticalAnomalyDetector:
    """
    统计方法异常检测器
    
    使用Z-Score和IQR方法检测异常值。
    """
    
    def __init__(
        self,
        zscore_threshold: float = 3.0,
        iqr_multiplier: float = 1.5
    ):
        """
        初始化统计检测器
        
        Args:
            zscore_threshold: Z-Score阈值
            iqr_multiplier: IQR倍数
        """
        self.zscore_threshold = zscore_threshold
        self.iqr_multiplier = iqr_multiplier
    
    def detect_zscore(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        使用Z-Score检测异常
        
        Args:
            data: 数据数组
            
        Returns:
            Tuple: (异常掩码, Z-Score值)
        """
        z_scores = np.abs(stats.zscore(data))
        anomaly_mask = z_scores > self.zscore_threshold
        return anomaly_mask, z_scores
    
    def detect_iqr(self, data: np.ndarray) -> Tuple[np.ndarray, Tuple[float, float]]:
        """
        使用IQR方法检测异常
        
        Args:
            data: 数据数组
            
        Returns:
            Tuple: (异常掩码, (下界, 上界))
        """
        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - self.iqr_multiplier * iqr
        upper_bound = q3 + self.iqr_multiplier * iqr
        
        anomaly_mask = (data < lower_bound) | (data > upper_bound)
        
        return anomaly_mask, (lower_bound, upper_bound)
    
    def detect_sudden_change(
        self,
        data: np.ndarray,
        threshold_ratio: float = 0.3
    ) -> np.ndarray:
        """
        检测突变点
        
        Args:
            data: 数据数组
            threshold_ratio: 变化阈值比例
            
        Returns:
            np.ndarray: 突变点掩码
        """
        if len(data) < 2:
            return np.zeros(len(data), dtype=bool)
        
        mean_val = np.mean(data)
        threshold = mean_val * threshold_ratio
        
        changes = np.abs(np.diff(data))
        sudden_changes = changes > threshold
        
        # 扩展到原始长度
        anomaly_mask = np.zeros(len(data), dtype=bool)
        anomaly_mask[1:] = sudden_changes
        
        return anomaly_mask


class AnomalyDetector:
    """
    综合异常检测器
    
    集成多种异常检测方法，提供完整的异常处理流程。
    
    Attributes:
        isolation_forest: 孤立森林检测器
        statistical: 统计检测器
        config: 配置参数
    """
    
    def __init__(self):
        """
        初始化综合异常检测器
        """
        iso_config = config.get('preprocessing.isolation_forest', {})
        
        self.isolation_forest = IsolationForestDetector(
            contamination=iso_config.get('contamination', 0.1),
            n_estimators=iso_config.get('n_estimators', 100),
            random_state=iso_config.get('random_state', 42)
        )
        
        self.statistical = StatisticalAnomalyDetector(
            zscore_threshold=3.0,
            iqr_multiplier=1.5
        )
        
        # 预紧力阈值
        self.preload_thresholds = config.get('risk_assessment.preload_thresholds', {})
        
        logger.info("综合异常检测器初始化完成")
    
    def detect(
        self,
        data: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        methods: Optional[List[str]] = None
    ) -> AnomalyDetectionResult:
        """
        使用多种方法检测异常
        
        Args:
            data: 预紧力数据
            timestamps: 时间戳
            methods: 使用的检测方法列表，默认使用所有方法
            
        Returns:
            AnomalyDetectionResult: 检测结果
        """
        if methods is None:
            methods = ['isolation_forest', 'zscore', 'iqr', 'range', 'sudden_change']
        
        all_anomalies = []
        anomaly_indices = set()
        
        # 孤立森林检测
        if 'isolation_forest' in methods:
            iso_result = self.isolation_forest.detect(data, timestamps)
            for anomaly in iso_result.anomalies:
                if anomaly.index not in anomaly_indices:
                    all_anomalies.append(anomaly)
                    anomaly_indices.add(anomaly.index)
        
        # Z-Score检测
        if 'zscore' in methods:
            zscore_mask, zscores = self.statistical.detect_zscore(data)
            for idx in np.where(zscore_mask)[0]:
                if idx not in anomaly_indices:
                    all_anomalies.append(AnomalyRecord(
                        index=int(idx),
                        value=float(data[idx]),
                        anomaly_type=AnomalyType.ZSCORE,
                        score=float(zscores[idx]),
                        timestamp=timestamps[idx] if timestamps is not None else None,
                        details={'zscore': float(zscores[idx])}
                    ))
                    anomaly_indices.add(idx)
        
        # IQR检测
        if 'iqr' in methods:
            iqr_mask, bounds = self.statistical.detect_iqr(data)
            for idx in np.where(iqr_mask)[0]:
                if idx not in anomaly_indices:
                    all_anomalies.append(AnomalyRecord(
                        index=int(idx),
                        value=float(data[idx]),
                        anomaly_type=AnomalyType.IQR,
                        score=abs(data[idx] - np.median(data)),
                        timestamp=timestamps[idx] if timestamps is not None else None,
                        details={'lower_bound': bounds[0], 'upper_bound': bounds[1]}
                    ))
                    anomaly_indices.add(idx)
        
        # 范围检测
        if 'range' in methods:
            min_normal = self.preload_thresholds.get('min_normal', 400)
            max_normal = self.preload_thresholds.get('max_normal', 800)
            range_mask = (data < min_normal * 0.5) | (data > max_normal * 1.5)
            
            for idx in np.where(range_mask)[0]:
                if idx not in anomaly_indices:
                    all_anomalies.append(AnomalyRecord(
                        index=int(idx),
                        value=float(data[idx]),
                        anomaly_type=AnomalyType.OUT_OF_RANGE,
                        score=abs(data[idx] - (min_normal + max_normal) / 2),
                        timestamp=timestamps[idx] if timestamps is not None else None,
                        details={'min_threshold': min_normal * 0.5, 'max_threshold': max_normal * 1.5}
                    ))
                    anomaly_indices.add(idx)
        
        # 突变检测
        if 'sudden_change' in methods:
            sudden_mask = self.statistical.detect_sudden_change(data)
            for idx in np.where(sudden_mask)[0]:
                if idx not in anomaly_indices:
                    change = abs(data[idx] - data[idx-1]) if idx > 0 else 0
                    all_anomalies.append(AnomalyRecord(
                        index=int(idx),
                        value=float(data[idx]),
                        anomaly_type=AnomalyType.SUDDEN_CHANGE,
                        score=float(change),
                        timestamp=timestamps[idx] if timestamps is not None else None,
                        details={'change_amount': float(change)}
                    ))
                    anomaly_indices.add(idx)
        
        # 生成清洗后的数据
        normal_mask = np.ones(len(data), dtype=bool)
        for idx in anomaly_indices:
            normal_mask[idx] = False
        
        cleaned_data = data[normal_mask]
        cleaned_indices = np.where(normal_mask)[0]
        
        # 按索引排序异常记录
        all_anomalies.sort(key=lambda x: x.index)
        
        result = AnomalyDetectionResult(
            total_points=len(data),
            anomaly_count=len(all_anomalies),
            anomaly_ratio=len(all_anomalies) / len(data) if len(data) > 0 else 0,
            anomalies=all_anomalies,
            cleaned_data=cleaned_data,
            cleaned_indices=cleaned_indices
        )
        
        logger.info(
            f"异常检测完成: 总数据{result.total_points}, "
            f"异常{result.anomaly_count} ({result.anomaly_ratio:.1%})"
        )
        
        return result
    
    def detect_and_store(
        self,
        data: np.ndarray,
        sensor_id: str,
        timestamps: Optional[np.ndarray] = None,
        methods: Optional[List[str]] = None
    ) -> AnomalyDetectionResult:
        """
        检测异常并存储到数据库
        
        Args:
            data: 预紧力数据
            sensor_id: 传感器/螺栓ID
            timestamps: 时间戳
            methods: 检测方法
            
        Returns:
            AnomalyDetectionResult: 检测结果
        """
        result = self.detect(data, timestamps, methods)
        
        # 存储异常数据到数据库
        if result.anomalies:
            self._store_anomalies(sensor_id, result.anomalies)
        
        return result
    
    def _store_anomalies(self, sensor_id: str, anomalies: List[AnomalyRecord]) -> None:
        """
        存储异常数据到异常数据表
        
        Args:
            sensor_id: 传感器ID
            anomalies: 异常记录列表
        """
        try:
            with get_db() as db:
                if db is None:
                    logger.warning("数据库不可用，跳过异常数据存储")
                    return
                
                from sqlalchemy import text
                
                for anomaly in anomalies:
                    insert_sql = text("""
                        INSERT INTO sc_anomaly_data 
                        (sensor_id, anomaly_value, anomaly_type, anomaly_score, 
                         original_time, details, create_time)
                        VALUES 
                        (:sensor_id, :value, :type, :score, :original_time, :details, NOW())
                    """)
                    
                    db.execute(insert_sql, {
                        'sensor_id': sensor_id,
                        'value': anomaly.value,
                        'type': anomaly.anomaly_type.value,
                        'score': anomaly.score,
                        'original_time': anomaly.timestamp,
                        'details': str(anomaly.details)
                    })
                
                db.commit()
                logger.info(f"已存储{len(anomalies)}条异常数据: sensor_id={sensor_id}")
                
        except Exception as e:
            logger.error(f"存储异常数据失败: {e}")
