"""
模型训练服务模块

提供模型训练和管理的核心服务。

主要功能:
1. 从数据库或CSV加载训练数据
2. 数据预处理和标签生成
3. 模型训练和验证
4. 模型保存和管理

使用示例:
    from app.services.training_service import TrainingService
    
    service = TrainingService()
    service.train_model('bolt', 'B001')
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import time
from loguru import logger

from app.models.bolt_lstm import BoltLSTMModel
from app.models.flange_attention import FlangeAttentionModel
from app.services.preprocessing import DataPreprocessor
from app.services.feature_engineering import FeatureEngineer
from app.api.validators import get_validator, ValidationMode, format_validation_errors
from app.utils.config import config
from app.utils.database import get_db, BoltData

_data_quality_engine = None


def get_data_quality_engine():
    """获取数据质量引擎实例（懒加载）"""
    global _data_quality_engine
    if _data_quality_engine is None:
        from app.services.data_quality import DataQualityEngine
        _data_quality_engine = DataQualityEngine()
    return _data_quality_engine


class TrainingService:
    """
    模型训练服务类
    
    封装所有模型训练相关的业务逻辑。
    
    Attributes:
        preprocessor: 数据预处理器
        feature_engineer: 特征工程师
        model_save_path: 模型保存路径
    """
    
    def __init__(self):
        """
        初始化训练服务
        """
        self.preprocessor = DataPreprocessor()
        self.feature_engineer = FeatureEngineer()
        self.model_save_path = Path(config.get('model.save_path', './trained_models'))
        self.model_save_path.mkdir(parents=True, exist_ok=True)
        
        # 训练历史记录
        self.training_history: Dict[str, Dict] = {}
        
        logger.info("训练服务初始化完成")
    
    def train_model(
        self,
        model_type: str,
        node_id: Optional[str] = None,
        force_retrain: bool = False
    ) -> Dict[str, Any]:
        """
        训练模型
        
        Args:
            model_type: 模型类型 (bolt/flange)
            node_id: 节点ID，None则训练所有
            force_retrain: 是否强制重新训练
            
        Returns:
            Dict: 训练结果
        """
        logger.info(f"开始训练: type={model_type}, node_id={node_id}")
        start_time = time.time()
        
        try:
            if model_type == 'bolt':
                result = self._train_bolt_model(node_id, force_retrain)
            elif model_type == 'flange':
                result = self._train_flange_model(node_id, force_retrain)
            else:
                raise ValueError(f"未知模型类型: {model_type}")
            
            elapsed = time.time() - start_time
            result['training_time'] = elapsed
            
            logger.info(f"训练完成: {model_type}, 耗时: {elapsed:.2f}秒")
            return result
            
        except Exception as e:
            logger.error(f"训练失败: {e}")
            return {
                'status': 'failed',
                'message': str(e),
                'training_time': time.time() - start_time
            }
    
    def _train_bolt_model(
        self,
        bolt_id: Optional[str],
        force_retrain: bool
    ) -> Dict[str, Any]:
        """
        训练螺栓模型
        """
        if bolt_id:
            # 训练单个螺栓模型
            return self._train_single_bolt(bolt_id, force_retrain)
        else:
            # 训练所有螺栓模型
            return self._train_all_bolts(force_retrain)
    
    def _train_single_bolt(
        self, 
        bolt_id: str, 
        force_retrain: bool
    ) -> Dict[str, Any]:
        """
        训练单个螺栓的模型
        """
        # 检查是否需要训练
        model_path = self.model_save_path / f"bolt_lstm_{bolt_id}.pt"
        if model_path.exists() and not force_retrain:
            logger.info(f"螺栓模型已存在，跳过: {bolt_id}")
            return {'status': 'skipped', 'message': '模型已存在'}
        
        # 获取训练数据
        data, labels = self._load_bolt_training_data(bolt_id)
        
        # 数据校验（宽松模式，允许自动修正）
        validator = get_validator()
        validation_result = validator.validate_training_data(
            data=data,
            labels=labels,
            min_samples=100,
            mode=ValidationMode.LENIENT
        )
        
        if not validation_result.is_valid:
            logger.warning(
                f"训练数据校验失败: {bolt_id}, "
                f"错误数: {len(validation_result.errors)}, "
                f"警告数: {len(validation_result.warnings)}"
            )
            for err in validation_result.errors:
                logger.warning(f"  {err.code}: {err.message}")
            
            error_info = format_validation_errors(validation_result)
            return {
                'status': 'failed',
                'message': '训练数据校验失败',
                'validation_errors': error_info
            }
        
        # 记录校验警告
        if validation_result.warnings:
            logger.info(
                f"训练数据校验警告 ({bolt_id}): {len(validation_result.warnings)} 条警告"
            )
            for warn in validation_result.warnings:
                logger.info(f"  警告: {warn}")
        
        if len(data) < 100:
            logger.warning(f"训练数据不足: {bolt_id}")
            return {'status': 'failed', 'message': '训练数据不足'}
        
        # 创建并训练模型
        model = BoltLSTMModel(bolt_id=bolt_id)
        
        # 计算类别权重（处理不平衡）
        unique, counts = np.unique(labels, return_counts=True)
        class_weights = len(labels) / (len(unique) * counts)
        
        # 训练
        history = model.train(
            train_data=data,
            train_labels=labels,
            class_weights=class_weights
        )
        
        # 保存模型
        model.save()
        
        # 记录训练历史
        self.training_history[f'bolt_{bolt_id}'] = {
            'trained_at': datetime.now(),
            'samples': len(data),
            'final_val_acc': history['val_acc'][-1] if history['val_acc'] else None
        }
        
        return {
            'status': 'success',
            'message': f'螺栓 {bolt_id} 模型训练完成',
            'metrics': {
                'train_acc': history['train_acc'][-1],
                'val_acc': history['val_acc'][-1],
                'train_loss': history['train_loss'][-1],
                'val_loss': history['val_loss'][-1]
            }
        }
    
    def _train_all_bolts(self, force_retrain: bool) -> Dict[str, Any]:
        """
        训练所有螺栓的模型
        """
        # 获取所有螺栓ID
        bolt_ids = self._get_all_bolt_ids()
        
        results = {
            'total': len(bolt_ids),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
        
        for bolt_id in bolt_ids:
            try:
                result = self._train_single_bolt(bolt_id, force_retrain)
                if result['status'] == 'success':
                    results['success'] += 1
                elif result['status'] == 'skipped':
                    results['skipped'] += 1
                else:
                    results['failed'] += 1
                results['details'].append({
                    'bolt_id': bolt_id,
                    **result
                })
            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'bolt_id': bolt_id,
                    'status': 'failed',
                    'message': str(e)
                })
        
        results['status'] = 'completed'
        results['message'] = f"完成: 成功{results['success']}, 失败{results['failed']}, 跳过{results['skipped']}"
        
        return results
    
    def _train_flange_model(
        self,
        flange_id: Optional[str],
        force_retrain: bool
    ) -> Dict[str, Any]:
        """
        训练法兰面模型
        """
        if flange_id:
            return self._train_single_flange(flange_id, force_retrain)
        else:
            return self._train_all_flanges(force_retrain)
    
    def _train_single_flange(
        self, 
        flange_id: str, 
        force_retrain: bool
    ) -> Dict[str, Any]:
        """
        训练单个法兰面的模型
        """
        model_path = self.model_save_path / f"flange_attention_{flange_id}.pt"
        if model_path.exists() and not force_retrain:
            logger.info(f"法兰面模型已存在，跳过: {flange_id}")
            return {'status': 'skipped', 'message': '模型已存在'}
        
        # 获取训练数据
        data, labels = self._load_flange_training_data(flange_id)
        
        if len(data) < 50:
            logger.warning(f"训练数据不足: {flange_id}")
            return {'status': 'failed', 'message': '训练数据不足'}
        
        # 创建并训练模型
        model = FlangeAttentionModel(flange_id=flange_id)
        
        # 训练
        history = model.train(
            train_data=data,
            train_labels=labels
        )
        
        # 保存模型
        model.save()
        
        # 记录训练历史
        self.training_history[f'flange_{flange_id}'] = {
            'trained_at': datetime.now(),
            'samples': len(data),
            'final_val_acc': history['val_acc'][-1] if history['val_acc'] else None
        }
        
        return {
            'status': 'success',
            'message': f'法兰面 {flange_id} 模型训练完成',
            'metrics': {
                'train_acc': history['train_acc'][-1],
                'val_acc': history['val_acc'][-1]
            }
        }
    
    def _train_all_flanges(self, force_retrain: bool) -> Dict[str, Any]:
        """
        训练所有法兰面的模型
        """
        flange_ids = self._get_all_flange_ids()
        
        results = {
            'total': len(flange_ids),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
        
        for flange_id in flange_ids:
            try:
                result = self._train_single_flange(flange_id, force_retrain)
                if result['status'] == 'success':
                    results['success'] += 1
                elif result['status'] == 'skipped':
                    results['skipped'] += 1
                else:
                    results['failed'] += 1
                results['details'].append({
                    'flange_id': flange_id,
                    **result
                })
            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'flange_id': flange_id,
                    'status': 'failed',
                    'message': str(e)
                })
        
        results['status'] = 'completed'
        results['message'] = f"完成: 成功{results['success']}, 失败{results['failed']}, 跳过{results['skipped']}"
        
        return results
    
    def _load_bolt_training_data(
        self, 
        bolt_id: str
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        加载螺栓训练数据
        
        尝试从数据库加载，如果没有则从CSV加载。
        自动应用数据质量过滤，低质量数据不参与训练。
        """
        # 检查是否启用数据质量过滤
        dq_enabled = config.get('data_quality.enabled', True)
        auto_filter = config.get(
            'data_quality.integration.auto_filter_training_data', True
        )

        # 尝试从数据库加载
        try:
            with get_db() as db:
                data = db.query(BoltData).filter(
                    BoltData.sensor_id == int(bolt_id) if bolt_id.isdigit() else BoltData.sensor_id == bolt_id
                ).order_by(BoltData.create_time.asc()).all()

            if data and len(data) >= 100:
                values = np.array([d.ptf for d in data])
                timestamps = np.array([d.create_time for d in data])

                # 应用数据质量过滤
                if dq_enabled and auto_filter:
                    try:
                        engine = get_data_quality_engine()
                        filter_result = engine.filter_training_data(
                            sensor_id=bolt_id,
                            values=values,
                            timestamps=timestamps,
                        )

                        filtered_values = filter_result.filtered_data
                        original_count = len(values)
                        filtered_count = len(filtered_values)

                        if filter_result.valid_for_training:
                            if filtered_count != original_count:
                                logger.info(
                                    f"训练数据过滤: 螺栓 {bolt_id}, "
                                    f"原始 {original_count} 条, 过滤后 {filtered_count} 条, "
                                    f"移除 {original_count - filtered_count} 条"
                                )
                            labels = self._generate_labels(filtered_values)
                            return filtered_values, labels
                        else:
                            logger.warning(
                                f"螺栓 {bolt_id} 数据质量过低，不适用于训练。"
                                f"质量评分: {filter_result.quality_score.overall_score:.1f}"
                            )
                    except Exception as e:
                        logger.warning(f"数据质量过滤失败，使用原始数据: {e}")

                labels = self._generate_labels(values)
                return values, labels
        except Exception as e:
            logger.warning(f"从数据库加载失败: {e}")

        # 从CSV加载
        return self._load_bolt_from_csv(bolt_id)

    def _filter_data_by_quality(
        self,
        bolt_id: str,
        values: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        根据数据质量过滤数据

        Args:
            bolt_id: 螺栓ID
            values: 数据值数组
            timestamps: 时间戳数组

        Returns:
            np.ndarray: 过滤后的数据
        """
        try:
            engine = get_data_quality_engine()
            filter_result = engine.filter_training_data(
                sensor_id=bolt_id,
                values=values,
                timestamps=timestamps,
            )

            if not filter_result.valid_for_training:
                logger.warning(
                    f"螺栓 {bolt_id} 数据质量评分 "
                    f"{filter_result.quality_score.overall_score:.1f}，"
                    f"不适合训练，但仍使用过滤后的数据"
                )

            return filter_result.filtered_data
        except Exception as e:
            logger.warning(f"数据质量过滤失败: {e}")
            return values
    
    def _load_bolt_from_csv(
        self, 
        bolt_id: str
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        从CSV文件加载螺栓数据
        """
        csv_path = Path('data/data_bolt.csv')
        if not csv_path.exists():
            logger.warning(f"CSV文件不存在: {csv_path}")
            return np.array([]), np.array([])
        
        try:
            df = pd.read_csv(csv_path)
            
            # 尝试匹配螺栓ID
            if '螺栓id' in df.columns:
                bolt_data = df[df['螺栓id'] == bolt_id]
            elif 'bolt_id' in df.columns:
                bolt_data = df[df['bolt_id'] == bolt_id]
            else:
                # 使用所有数据
                bolt_data = df
            
            if len(bolt_data) == 0:
                return np.array([]), np.array([])
            
            # 获取预紧力列
            if '预紧力' in bolt_data.columns:
                values = bolt_data['预紧力'].values
            elif 'ptf' in bolt_data.columns:
                values = bolt_data['ptf'].values
            else:
                return np.array([]), np.array([])
            
            labels = self._generate_labels(values)
            
            return values, labels
            
        except Exception as e:
            logger.error(f"读取CSV失败: {e}")
            return np.array([]), np.array([])
    
    def _load_flange_training_data(
        self, 
        flange_id: str
    ) -> Tuple[List[List[np.ndarray]], np.ndarray]:
        """
        加载法兰面训练数据
        """
        # 从CSV加载
        csv_path = Path('data/data_flm.csv')
        if not csv_path.exists():
            logger.warning(f"CSV文件不存在: {csv_path}")
            return [], np.array([])
        
        try:
            df = pd.read_csv(csv_path)
            
            # 尝试匹配法兰面ID
            if '法兰面' in df.columns:
                flange_data = df[df['法兰面'] == flange_id]
            else:
                flange_data = df
            
            if len(flange_data) == 0:
                return [], np.array([])
            
            # 按时间分组，创建样本
            samples = []
            labels = []
            
            # 这里简化处理，实际应该按时间窗口分组
            if '螺栓id' in flange_data.columns:
                for time_group in flange_data.groupby('采集时间'):
                    bolt_data = []
                    for bolt_id in time_group[1]['螺栓id'].unique():
                        bolt_df = time_group[1][time_group[1]['螺栓id'] == bolt_id]
                        if '预紧力' in bolt_df.columns:
                            bolt_data.append(bolt_df['预紧力'].values)
                    
                    if bolt_data:
                        samples.append(bolt_data)
                        # 简单标签生成
                        labels.append(0)
            
            return samples, np.array(labels)
            
        except Exception as e:
            logger.error(f"读取CSV失败: {e}")
            return [], np.array([])
    
    def _generate_labels(self, data: np.ndarray) -> np.ndarray:
        """
        根据规则生成训练标签
        
        基于预紧力值自动生成状态标签。
        """
        thresholds = config.get('risk_assessment.preload_thresholds', {})
        min_normal = thresholds.get('min_normal', 400)
        max_normal = thresholds.get('max_normal', 800)
        
        labels = np.zeros(len(data), dtype=int)
        
        for i, val in enumerate(data):
            if val < min_normal * 0.5 or val > max_normal * 1.5:
                labels[i] = 4  # 故障
            elif val < min_normal * 0.7 or val > max_normal * 1.3:
                labels[i] = 3  # 紧急预警
            elif val < min_normal * 0.9 or val > max_normal * 1.1:
                labels[i] = 2  # 检查预警
            elif val < min_normal or val > max_normal:
                labels[i] = 1  # 关注预警
            else:
                labels[i] = 0  # 正常
        
        return labels
    
    def _get_all_bolt_ids(self) -> List[str]:
        """获取所有螺栓ID"""
        try:
            with get_db() as db:
                from sqlalchemy import distinct
                result = db.query(distinct(BoltData.sensor_id)).all()
                return [str(r[0]) for r in result]
        except Exception:
            # 从CSV获取
            csv_path = Path('data/data_bolt.csv')
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                if '螺栓id' in df.columns:
                    return df['螺栓id'].unique().tolist()
            return []
    
    def _get_all_flange_ids(self) -> List[str]:
        """获取所有法兰面ID"""
        try:
            with get_db() as db:
                from sqlalchemy import text
                query = text("""
                    SELECT DISTINCT CONCAT(collector_id, '-', splitter_num, '-', position)
                    FROM sc_bolt_data
                """)
                result = db.execute(query)
                return [r[0] for r in result.fetchall()]
        except Exception:
            # 从CSV获取
            csv_path = Path('data/data_flm.csv')
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                if '法兰面' in df.columns:
                    return df['法兰面'].unique().tolist()
            return []
    
    def get_model_info(
        self, 
        model_type: str, 
        node_id: str
    ) -> Dict[str, Any]:
        """
        获取模型信息
        """
        if model_type == 'bolt':
            model_path = self.model_save_path / f"bolt_lstm_{node_id}.pt"
        else:
            model_path = self.model_save_path / f"flange_attention_{node_id}.pt"
        
        history_key = f"{model_type}_{node_id}"
        history = self.training_history.get(history_key, {})
        
        return {
            'is_trained': model_path.exists(),
            'last_training_time': history.get('trained_at'),
            'training_samples': history.get('samples'),
            'validation_accuracy': history.get('final_val_acc')
        }
    
    def train_from_csv(
        self,
        bolt_csv: Optional[str] = None,
        flange_csv: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        从CSV文件训练所有模型
        
        Args:
            bolt_csv: 螺栓数据CSV路径
            flange_csv: 法兰面数据CSV路径
        """
        results = {
            'bolt_results': None,
            'flange_results': None
        }
        
        if bolt_csv or Path('data/data_bolt.csv').exists():
            logger.info("开始训练螺栓模型...")
            results['bolt_results'] = self._train_all_bolts(force_retrain=True)
        
        if flange_csv or Path('data/data_flm.csv').exists():
            logger.info("开始训练法兰面模型...")
            results['flange_results'] = self._train_all_flanges(force_retrain=True)
        
        return results
