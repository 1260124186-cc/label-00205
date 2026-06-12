"""
预测服务模块

提供螺栓和法兰面状态预测的核心服务。

主要功能:
1. 加载和管理模型
2. 执行预测并整合结果
3. 风险评估
4. 预测结果持久化

使用示例:
    from app.services.prediction_service import PredictionService
    
    service = PredictionService()
    result = service.predict_bolt('B001', data)
"""

import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from loguru import logger

from app.models.bolt_lstm import BoltLSTMModel, STATUS_LABELS
from app.models.flange_attention import FlangeAttentionModel
from app.models.risk_model import BayesianRiskModel, RiskLevel
from app.models.prophet_forecaster import ProphetForecaster
from app.services.preprocessing import DataPreprocessor
from app.services.feature_engineering import FeatureEngineer
from app.utils.config import config
from app.utils.database import (
    get_db, get_bolt_recent_data, get_flange_recent_data,
    AbnormalPrediction, MonthPrediction
)


class PredictionService:
    """
    预测服务类
    
    封装所有预测相关的业务逻辑。
    
    Attributes:
        preprocessor: 数据预处理器
        feature_engineer: 特征工程师
        risk_model: 风险评估模型
        prophet: Prophet预测器
        bolt_models: 螺栓模型缓存
        flange_models: 法兰面模型缓存
    """
    
    def __init__(self):
        """
        初始化预测服务
        """
        self.preprocessor = DataPreprocessor()
        self.feature_engineer = FeatureEngineer()
        self.risk_model = BayesianRiskModel()
        self.prophet = ProphetForecaster()
        
        # 模型缓存
        self.bolt_models: Dict[str, BoltLSTMModel] = {}
        self.flange_models: Dict[str, FlangeAttentionModel] = {}
        
        # 预警策略
        self.strategy = config.get('warning_strategy.strategy_type', 1)
        
        logger.info("预测服务初始化完成")
    
    def get_bolt_model(self, bolt_id: str) -> BoltLSTMModel:
        """
        获取或创建螺栓模型
        
        Args:
            bolt_id: 螺栓ID
            
        Returns:
            BoltLSTMModel: 螺栓预测模型
        """
        if bolt_id not in self.bolt_models:
            self.bolt_models[bolt_id] = BoltLSTMModel.load_or_create(bolt_id)
        return self.bolt_models[bolt_id]
    
    def get_flange_model(self, flange_id: str) -> FlangeAttentionModel:
        """
        获取或创建法兰面模型
        
        Args:
            flange_id: 法兰面ID
            
        Returns:
            FlangeAttentionModel: 法兰面预测模型
        """
        if flange_id not in self.flange_models:
            self.flange_models[flange_id] = FlangeAttentionModel.load_or_create(flange_id)
        return self.flange_models[flange_id]
    
    def predict_bolt(
        self,
        bolt_id: str,
        data: np.ndarray,
        timestamps: Optional[List[str]] = None,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        预测螺栓状态
        
        Args:
            bolt_id: 螺栓ID
            data: 预紧力数据
            timestamps: 时间戳列表
            save_to_db: 是否保存到数据库
            
        Returns:
            Dict: 预测结果
        """
        logger.info(f"开始螺栓预测: {bolt_id}, 数据点数: {len(data)}")
        
        # 数据预处理
        processed = self.preprocessor.process(
            data, 
            remove_anomalies=True,
            normalize=True,
            smooth=True
        )
        
        # 获取模型
        model = self.get_bolt_model(bolt_id)
        
        # 执行预测
        if model.is_trained:
            status_code, confidence, probs = model.predict(
                processed.data, 
                return_proba=True
            )
        else:
            # 模型未训练，使用规则判断
            status_code, confidence, probs = self._rule_based_prediction(data)
        
        # 获取状态标签
        status = STATUS_LABELS.get(status_code, '未知')
        
        # 风险评估
        risk_assessment = self.risk_model.assess_risk(
            data, 
            lstm_probs=probs,
            lstm_class=status_code
        )
        
        # 应用预警策略
        status_code, status = self._apply_warning_strategy(
            status_code, status, confidence
        )
        
        # 获取推荐措施
        recommendations = model.get_recommendation(status_code, confidence)
        
        result = {
            'bolt_id': bolt_id,
            'status': status,
            'status_code': status_code,
            'confidence': float(confidence),
            'risk_score': float(risk_assessment.score),
            'risk_level': risk_assessment.level.value,
            'diagnosis': risk_assessment.diagnosis,
            'recommendations': risk_assessment.recommendations,
            'recent_time': timestamps[-1] if timestamps else None
        }
        
        # 保存到数据库
        if save_to_db:
            self._save_bolt_prediction(bolt_id, result)
        
        logger.info(f"螺栓预测完成: {bolt_id} -> {status}")
        
        return result
    
    def predict_flange(
        self,
        flange_id: str,
        multi_bolt_data: List[np.ndarray],
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        预测法兰面状态
        
        Args:
            flange_id: 法兰面ID
            multi_bolt_data: 多螺栓数据列表
            save_to_db: 是否保存到数据库
            
        Returns:
            Dict: 预测结果
        """
        logger.info(f"开始法兰面预测: {flange_id}, 螺栓数: {len(multi_bolt_data)}")
        
        # 预处理每个螺栓的数据
        processed_bolts = []
        for bolt_data in multi_bolt_data:
            processed = self.preprocessor.process(
                bolt_data,
                remove_anomalies=True,
                normalize=True,
                smooth=True
            )
            processed_bolts.append(processed.data)
        
        # 获取模型
        model = self.get_flange_model(flange_id)
        
        # 执行预测
        if model.is_trained:
            status_code, confidence, attention = model.predict(
                processed_bolts,
                return_attention=True
            )
        else:
            # 模型未训练，使用聚合策略
            status_code, confidence = self._aggregate_bolt_predictions(multi_bolt_data)
            attention = None
        
        # 获取状态标签
        status = STATUS_LABELS.get(status_code, '未知')
        
        # 风险评估（使用所有螺栓数据）
        all_data = np.concatenate(multi_bolt_data)
        risk_assessment = self.risk_model.assess_risk(all_data, lstm_class=status_code)
        
        # 应用预警策略
        status_code, status = self._apply_warning_strategy(
            status_code, status, confidence
        )
        
        # 获取推荐措施
        recommendations = model.get_recommendation(status_code, confidence)
        
        result = {
            'flange_id': flange_id,
            'status': status,
            'status_code': status_code,
            'confidence': float(confidence),
            'risk_score': float(risk_assessment.score),
            'risk_level': risk_assessment.level.value,
            'attention_weights': attention.tolist() if attention is not None else None,
            'diagnosis': risk_assessment.diagnosis,
            'recommendations': risk_assessment.recommendations
        }
        
        # 保存到数据库
        if save_to_db:
            self._save_flange_prediction(flange_id, result)
        
        logger.info(f"法兰面预测完成: {flange_id} -> {status}")
        
        return result
    
    def assess_risk(
        self,
        node_id: str,
        node_type: str,
        data: np.ndarray
    ) -> Dict[str, Any]:
        """
        风险评估
        
        Args:
            node_id: 节点ID
            node_type: 节点类型
            data: 预紧力数据
            
        Returns:
            Dict: 风险评估结果
        """
        assessment = self.risk_model.assess_risk(data)
        
        return {
            'node_id': node_id,
            'node_type': node_type,
            'risk_score': float(assessment.score),
            'risk_level': assessment.level.value,
            'factors': assessment.factors,
            'diagnosis': assessment.diagnosis,
            'recommendations': assessment.recommendations,
            'confidence': float(assessment.confidence)
        }
    
    def forecast_monthly(
        self,
        node_id: str,
        node_type: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        月度预测
        
        Args:
            node_id: 节点ID
            node_type: 节点类型
            days: 预测天数
            
        Returns:
            Dict: 预测结果
        """
        logger.info(f"开始月度预测: {node_id}, 类型: {node_type}, 天数: {days}")
        
        # 从数据库获取历史数据
        if node_type == 'bolt':
            historical = self._get_bolt_history(node_id)
        else:
            historical = self._get_flange_history(node_id)
        
        if historical is None or len(historical['data']) < 10:
            logger.warning(f"历史数据不足: {node_id}")
            return {
                'pw_type': '正常',
                'fault_type': None,
                'begin_time': None,
                'end_time': None,
                'confidence': 0.5,
                'rec_measures': '历史数据不足，无法进行可靠预测。',
                'forecast_dates': [],
                'forecast_values': []
            }
        
        # 执行预测
        result = self.prophet.predict_status(
            historical_data=historical['data'],
            historical_timestamps=historical['timestamps'],
            days=days
        )
        
        # 保存到数据库
        self._save_monthly_prediction(node_id, node_type, result)
        
        return result
    
    def batch_predict_from_db(self, node_type: str) -> None:
        """
        从数据库批量读取数据并预测
        
        Args:
            node_type: 节点类型 (bolt/flange)
        """
        logger.info(f"开始批量预测: {node_type}")
        
        try:
            if node_type == 'bolt':
                self._batch_predict_bolts()
            elif node_type == 'flange':
                self._batch_predict_flanges()
            else:
                logger.error(f"未知节点类型: {node_type}")
        except Exception as e:
            logger.error(f"批量预测失败: {e}")
    
    def _batch_predict_bolts(self) -> None:
        """批量预测螺栓"""
        from sqlalchemy import text
        
        with get_db() as db:
            # 获取所有螺栓的最近100条数据
            query = text("""
                SELECT id, create_time, sensor_id, ptf
                FROM (
                    SELECT id, create_time, sensor_id, ptf,
                        @rank := IF(@current_sensor = sensor_id, @rank + 1, 1) AS sensor_rank,
                        @current_sensor := sensor_id
                    FROM sc_bolt_data
                    CROSS JOIN (SELECT @current_sensor := NULL, @rank := 0) AS vars
                    ORDER BY sensor_id, create_time DESC
                ) AS ranked_data
                WHERE sensor_rank <= 100
                ORDER BY sensor_id, create_time DESC
            """)
            
            result = db.execute(query)
            rows = result.fetchall()
        
        # 按螺栓分组
        bolt_data = {}
        for row in rows:
            sensor_id = str(row.sensor_id)
            if sensor_id not in bolt_data:
                bolt_data[sensor_id] = {'data': [], 'timestamps': []}
            bolt_data[sensor_id]['data'].append(row.ptf)
            bolt_data[sensor_id]['timestamps'].append(row.create_time)
        
        # 逐个预测
        for bolt_id, data_dict in bolt_data.items():
            try:
                self.predict_bolt(
                    bolt_id=bolt_id,
                    data=np.array(data_dict['data']),
                    timestamps=data_dict['timestamps'],
                    save_to_db=True
                )
            except Exception as e:
                logger.error(f"螺栓 {bolt_id} 预测失败: {e}")
        
        logger.info(f"批量螺栓预测完成，共 {len(bolt_data)} 个")
    
    def _batch_predict_flanges(self) -> None:
        """批量预测法兰面"""
        from sqlalchemy import text
        
        with get_db() as db:
            # 获取所有法兰面ID
            query = text("""
                SELECT DISTINCT CONCAT(collector_id, '-', splitter_num, '-', position) as flange_id
                FROM sc_bolt_data
            """)
            result = db.execute(query)
            flange_ids = [row.flange_id for row in result.fetchall()]
        
        for flange_id in flange_ids:
            try:
                # 获取法兰面数据
                flange_data = get_flange_recent_data(flange_id)
                
                if not flange_data:
                    continue
                
                # 按螺栓分组
                bolt_series = {}
                for row in flange_data:
                    sensor_id = row.sensor_id
                    if sensor_id not in bolt_series:
                        bolt_series[sensor_id] = []
                    bolt_series[sensor_id].append(row.ptf)
                
                multi_bolt_data = [np.array(v) for v in bolt_series.values()]
                
                self.predict_flange(
                    flange_id=flange_id,
                    multi_bolt_data=multi_bolt_data,
                    save_to_db=True
                )
            except Exception as e:
                logger.error(f"法兰面 {flange_id} 预测失败: {e}")
        
        logger.info(f"批量法兰面预测完成，共 {len(flange_ids)} 个")
    
    def _rule_based_prediction(
        self, 
        data: np.ndarray
    ) -> Tuple[int, float, Optional[np.ndarray]]:
        """
        基于规则的预测（模型未训练时使用）
        """
        thresholds = config.get('risk_assessment.preload_thresholds', {})
        min_normal = thresholds.get('min_normal', 400)
        max_normal = thresholds.get('max_normal', 800)
        
        mean_val = np.mean(data)
        std_val = np.std(data)
        
        # 简单规则判断
        if mean_val < min_normal * 0.5 or mean_val > max_normal * 1.5:
            return 4, 0.8, None  # 故障
        elif mean_val < min_normal * 0.8 or mean_val > max_normal * 1.2:
            return 3, 0.7, None  # 紧急预警
        elif mean_val < min_normal or mean_val > max_normal:
            return 2, 0.7, None  # 检查预警
        elif std_val > mean_val * 0.2:
            return 1, 0.6, None  # 关注预警
        else:
            return 0, 0.9, None  # 正常
    
    def _aggregate_bolt_predictions(
        self, 
        multi_bolt_data: List[np.ndarray]
    ) -> Tuple[int, float]:
        """
        聚合螺栓预测（模型未训练时使用）
        """
        statuses = []
        for bolt_data in multi_bolt_data:
            status, conf, _ = self._rule_based_prediction(bolt_data)
            statuses.append(status)
        
        # 取最严重的状态
        max_status = max(statuses)
        confidence = 0.7
        
        return max_status, confidence
    
    def _apply_warning_strategy(
        self,
        status_code: int,
        status: str,
        confidence: float
    ) -> Tuple[int, str]:
        """
        应用预警策略
        """
        strategy_config = config.get('warning_strategy', {})
        strategy_type = strategy_config.get('strategy_type', 1)
        
        if strategy_type == 1:
            # 策略一：应报尽报
            threshold = strategy_config.get('strategy_1', {}).get('confidence_threshold', 0.7)
            if confidence >= threshold:
                return status_code, status
            else:
                # 置信度不足，降一级
                new_code = max(0, status_code - 1)
                return new_code, STATUS_LABELS.get(new_code, '正常')
        else:
            # 策略二：精准报警
            threshold = strategy_config.get('strategy_2', {}).get('confidence_threshold', 0.95)
            if confidence >= threshold:
                return status_code, status
            else:
                # 置信度不足，仅报告正常
                return 0, '正常'
    
    def _get_bolt_history(self, bolt_id: str) -> Optional[Dict]:
        """获取螺栓历史数据"""
        from sqlalchemy import text
        
        with get_db() as db:
            query = text("""
                SELECT create_time, ptf
                FROM sc_bolt_data
                WHERE sensor_id = :sensor_id
                    AND create_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                ORDER BY create_time ASC
            """)
            result = db.execute(query, {'sensor_id': bolt_id})
            rows = result.fetchall()
        
        if not rows:
            return None
        
        return {
            'data': np.array([r.ptf for r in rows]),
            'timestamps': np.array([r.create_time for r in rows])
        }
    
    def _get_flange_history(self, flange_id: str) -> Optional[Dict]:
        """获取法兰面历史数据"""
        from sqlalchemy import text
        
        with get_db() as db:
            query = text("""
                SELECT create_time, AVG(ptf) as avg_ptf
                FROM sc_bolt_data
                WHERE CONCAT(collector_id, '-', splitter_num, '-', position) = :flange_id
                    AND create_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY create_time
                ORDER BY create_time ASC
            """)
            result = db.execute(query, {'flange_id': flange_id})
            rows = result.fetchall()
        
        if not rows:
            return None
        
        return {
            'data': np.array([r.avg_ptf for r in rows]),
            'timestamps': np.array([r.create_time for r in rows])
        }
    
    def _save_bolt_prediction(self, bolt_id: str, result: Dict) -> None:
        """保存螺栓预测结果到数据库"""
        try:
            with get_db() as db:
                prediction = AbnormalPrediction(
                    bolt_id=int(bolt_id) if bolt_id.isdigit() else None,
                    node_type='螺栓',
                    year_month=datetime.now().strftime('%Y%m'),
                    pw_type=result['status'],
                    confidence=result['confidence'],
                    rec_measures=', '.join(result['recommendations']),
                    recent_time=result.get('recent_time'),
                    create_time=datetime.now()
                )
                db.add(prediction)
                db.commit()
        except Exception as e:
            logger.error(f"保存螺栓预测失败: {e}")
    
    def _save_flange_prediction(self, flange_id: str, result: Dict) -> None:
        """保存法兰面预测结果到数据库"""
        try:
            with get_db() as db:
                prediction = AbnormalPrediction(
                    flm_id=flange_id,
                    node_type='法兰面',
                    year_month=datetime.now().strftime('%Y%m'),
                    pw_type=result['status'],
                    confidence=result['confidence'],
                    rec_measures=', '.join(result['recommendations']),
                    create_time=datetime.now()
                )
                db.add(prediction)
                db.commit()
        except Exception as e:
            logger.error(f"保存法兰面预测失败: {e}")
    
    def _save_monthly_prediction(
        self, 
        node_id: str, 
        node_type: str, 
        result: Dict
    ) -> None:
        """保存月度预测结果"""
        try:
            with get_db() as db:
                prediction = MonthPrediction(
                    bolt_id=int(node_id) if node_type == 'bolt' and node_id.isdigit() else None,
                    flm_id=node_id if node_type == 'flange' else None,
                    node_type='螺栓' if node_type == 'bolt' else '法兰面',
                    year_month=datetime.now().strftime('%Y%m'),
                    pw_type=result['pw_type'],
                    begin_time=result.get('begin_time'),
                    end_time=result.get('end_time'),
                    confidence=result['confidence'],
                    rec_measures=result['rec_measures'],
                    create_time=datetime.now()
                )
                db.add(prediction)
                db.commit()
        except Exception as e:
            logger.error(f"保存月度预测失败: {e}")
