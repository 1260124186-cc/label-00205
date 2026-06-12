"""
模型性能评估指标模块

提供模型性能评估的各种指标计算。

功能:
1. 分类指标（准确率、精确率、召回率、F1）
2. 回归指标（MAE、MSE、RMSE、R2）
3. 时间序列指标（MAPE、SMAPE）
4. 混淆矩阵和分类报告

使用示例:
    from app.core.metrics import ClassificationMetrics, RegressionMetrics
    
    metrics = ClassificationMetrics()
    result = metrics.evaluate(y_true, y_pred)
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
    mean_absolute_error, mean_squared_error, r2_score
)
from loguru import logger


@dataclass
class ClassificationResult:
    """
    分类评估结果
    
    Attributes:
        accuracy: 准确率
        precision: 精确率
        recall: 召回率
        f1: F1分数
        confusion_matrix: 混淆矩阵
        class_report: 分类报告
        per_class_metrics: 每个类别的指标
    """
    accuracy: float
    precision: float
    recall: float
    f1: float
    confusion_matrix: np.ndarray
    class_report: str
    per_class_metrics: Dict[str, Dict[str, float]]


@dataclass
class RegressionResult:
    """
    回归评估结果
    
    Attributes:
        mae: 平均绝对误差
        mse: 均方误差
        rmse: 均方根误差
        r2: 决定系数
        mape: 平均绝对百分比误差
    """
    mae: float
    mse: float
    rmse: float
    r2: float
    mape: Optional[float] = None


class ClassificationMetrics:
    """
    分类性能评估器
    
    计算多分类任务的各种评估指标。
    """
    
    def __init__(self, class_names: Optional[List[str]] = None):
        """
        初始化分类评估器
        
        Args:
            class_names: 类别名称列表
        """
        self.class_names = class_names or [
            '正常', '关注级预警', '检查级预警', '紧急级预警', '故障'
        ]
    
    def evaluate(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        average: str = 'weighted'
    ) -> ClassificationResult:
        """
        评估分类性能
        
        Args:
            y_true: 真实标签
            y_pred: 预测标签
            average: 平均方式 ('micro', 'macro', 'weighted')
            
        Returns:
            ClassificationResult: 评估结果
        """
        # 基本指标
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, average=average, zero_division=0)
        recall = recall_score(y_true, y_pred, average=average, zero_division=0)
        f1 = f1_score(y_true, y_pred, average=average, zero_division=0)
        
        # 混淆矩阵
        cm = confusion_matrix(y_true, y_pred)
        
        # 分类报告
        report = classification_report(
            y_true, y_pred,
            target_names=self.class_names[:len(np.unique(y_true))],
            zero_division=0
        )
        
        # 每个类别的指标
        per_class = {}
        for i, name in enumerate(self.class_names[:len(np.unique(y_true))]):
            y_true_binary = (y_true == i).astype(int)
            y_pred_binary = (y_pred == i).astype(int)
            
            per_class[name] = {
                'precision': precision_score(y_true_binary, y_pred_binary, zero_division=0),
                'recall': recall_score(y_true_binary, y_pred_binary, zero_division=0),
                'f1': f1_score(y_true_binary, y_pred_binary, zero_division=0),
                'support': int(np.sum(y_true == i))
            }
        
        return ClassificationResult(
            accuracy=float(accuracy),
            precision=float(precision),
            recall=float(recall),
            f1=float(f1),
            confusion_matrix=cm,
            class_report=report,
            per_class_metrics=per_class
        )
    
    def evaluate_with_probabilities(
        self,
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        使用概率进行评估
        
        Args:
            y_true: 真实标签
            y_pred_proba: 预测概率
            threshold: 分类阈值
            
        Returns:
            Dict: 评估结果
        """
        # 获取预测类别
        y_pred = np.argmax(y_pred_proba, axis=1)
        
        # 基本评估
        result = self.evaluate(y_true, y_pred)
        
        # 添加概率相关指标
        confidence = np.max(y_pred_proba, axis=1)
        
        return {
            'classification_result': result,
            'mean_confidence': float(np.mean(confidence)),
            'std_confidence': float(np.std(confidence)),
            'low_confidence_ratio': float(np.mean(confidence < threshold))
        }


class RegressionMetrics:
    """
    回归性能评估器
    
    计算回归任务的各种评估指标。
    """
    
    def evaluate(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> RegressionResult:
        """
        评估回归性能
        
        Args:
            y_true: 真实值
            y_pred: 预测值
            
        Returns:
            RegressionResult: 评估结果
        """
        mae = mean_absolute_error(y_true, y_pred)
        mse = mean_squared_error(y_true, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_true, y_pred)
        
        # MAPE（避免除零）
        mask = y_true != 0
        if np.any(mask):
            mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
        else:
            mape = None
        
        return RegressionResult(
            mae=float(mae),
            mse=float(mse),
            rmse=float(rmse),
            r2=float(r2),
            mape=float(mape) if mape is not None else None
        )


class TimeSeriesMetrics:
    """
    时间序列性能评估器
    
    计算时间序列预测任务的评估指标。
    """
    
    @staticmethod
    def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """平均绝对百分比误差"""
        mask = y_true != 0
        if not np.any(mask):
            return 0.0
        return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)
    
    @staticmethod
    def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """对称平均绝对百分比误差"""
        denominator = (np.abs(y_true) + np.abs(y_pred)) / 2
        mask = denominator != 0
        if not np.any(mask):
            return 0.0
        return float(np.mean(np.abs(y_true[mask] - y_pred[mask]) / denominator[mask]) * 100)
    
    @staticmethod
    def directional_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """方向准确率"""
        if len(y_true) < 2:
            return 0.0
        
        true_direction = np.sign(np.diff(y_true))
        pred_direction = np.sign(np.diff(y_pred))
        
        return float(np.mean(true_direction == pred_direction))
    
    def evaluate(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> Dict[str, float]:
        """
        评估时间序列预测性能
        
        Args:
            y_true: 真实值
            y_pred: 预测值
            
        Returns:
            Dict: 评估指标
        """
        return {
            'mae': float(mean_absolute_error(y_true, y_pred)),
            'rmse': float(np.sqrt(mean_squared_error(y_true, y_pred))),
            'mape': self.mape(y_true, y_pred),
            'smape': self.smape(y_true, y_pred),
            'directional_accuracy': self.directional_accuracy(y_true, y_pred),
            'r2': float(r2_score(y_true, y_pred)) if len(y_true) > 1 else 0.0
        }


class ModelEvaluator:
    """
    模型综合评估器
    
    提供统一的模型评估接口。
    """
    
    def __init__(self):
        """初始化评估器"""
        self.classification_metrics = ClassificationMetrics()
        self.regression_metrics = RegressionMetrics()
        self.timeseries_metrics = TimeSeriesMetrics()
    
    def evaluate_classification(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_pred_proba: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """评估分类模型"""
        result = self.classification_metrics.evaluate(y_true, y_pred)
        
        output = {
            'accuracy': result.accuracy,
            'precision': result.precision,
            'recall': result.recall,
            'f1': result.f1,
            'per_class': result.per_class_metrics
        }
        
        if y_pred_proba is not None:
            confidence = np.max(y_pred_proba, axis=1)
            output['mean_confidence'] = float(np.mean(confidence))
        
        return output
    
    def evaluate_regression(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> Dict[str, float]:
        """评估回归模型"""
        result = self.regression_metrics.evaluate(y_true, y_pred)
        
        return {
            'mae': result.mae,
            'mse': result.mse,
            'rmse': result.rmse,
            'r2': result.r2,
            'mape': result.mape
        }
    
    def evaluate_timeseries(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> Dict[str, float]:
        """评估时间序列模型"""
        return self.timeseries_metrics.evaluate(y_true, y_pred)
    
    def generate_report(
        self,
        model_type: str,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_pred_proba: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        生成评估报告
        
        Args:
            model_type: 模型类型 ('classification', 'regression', 'timeseries')
            y_true: 真实值
            y_pred: 预测值
            y_pred_proba: 预测概率
            
        Returns:
            Dict: 评估报告
        """
        if model_type == 'classification':
            metrics = self.evaluate_classification(y_true, y_pred, y_pred_proba)
        elif model_type == 'regression':
            metrics = self.evaluate_regression(y_true, y_pred)
        elif model_type == 'timeseries':
            metrics = self.evaluate_timeseries(y_true, y_pred)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        return {
            'model_type': model_type,
            'sample_count': len(y_true),
            'metrics': metrics,
            'evaluated_at': np.datetime64('now').astype(str)
        }


# 全局评估器
model_evaluator = ModelEvaluator()
