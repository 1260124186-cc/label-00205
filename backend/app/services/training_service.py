"""
模型训练服务模块（增强版）

提供完整的模型训练管理能力：
1. 训练状态机管理（pending → running → completed/failed）
2. 训练日志持久化到 sc_training_logs 表
3. 人工标注数据导入和标签覆盖
4. 法兰面按 collector_id-splitter_num-position 正确分组
5. 训练完成自动验证评估，指标写入 sc_model_versions.metrics
6. 增量训练支持（冻结指定层 + fine-tune）
7. 可配置的早停、学习率调度、类别不平衡处理
"""

import os
import uuid
import json
import hashlib
import time
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
from loguru import logger

from app.models.bolt_lstm import BoltLSTMModel
from app.models.flange_attention import FlangeAttentionModel
from app.services.preprocessing import DataPreprocessor
from app.services.feature_engineering import FeatureEngineer
from app.services.label_import import label_import_service
from app.api.validators import get_validator, ValidationMode, format_validation_errors
from app.utils.config import config
from app.utils.database import (
    get_db,
    BoltData,
    TrainingLog,
    ModelVersionORM
)

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
    增强版模型训练服务

    支持训练状态机、人工标注覆盖、增量训练、自动模型版本管理等。
    """

    def __init__(self):
        self.preprocessor = DataPreprocessor()
        self.feature_engineer = FeatureEngineer()
        self.model_save_path = Path(config.get('model.save_path', './trained_models'))
        self.model_save_path.mkdir(parents=True, exist_ok=True)

        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self.training_config_template = config.get('model.training', {})

        logger.info("增强版训练服务初始化完成")

    def _generate_session_id(self) -> str:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_str = uuid.uuid4().hex[:8]
        return f"train_{timestamp}_{random_str}"

    def _parse_flange_id(self, flange_id: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        try:
            parts = flange_id.split('-')
            if len(parts) >= 3:
                return parts[0], parts[1], '-'.join(parts[2:])
            return None, None, None
        except Exception:
            return None, None, None

    def start_training(
        self,
        model_type: str,
        node_id: Optional[str] = None,
        force_retrain: bool = False,
        training_config: Optional[Dict[str, Any]] = None,
        data_source: str = 'db',
        is_incremental: bool = False,
        base_model_version: Optional[str] = None,
        freeze_layers: Optional[List[str]] = None
    ) -> str:
        session_id = self._generate_session_id()
        merged_config = dict(self.training_config_template)
        if training_config:
            merged_config.update(training_config)

        if is_incremental:
            if 'incremental' not in merged_config:
                merged_config['incremental'] = {}
            merged_config['incremental']['enabled'] = True
            merged_config['incremental']['freeze_layers'] = freeze_layers or ['lstm1', 'lstm2']

        try:
            with get_db() as db:
                if db is not None:
                    log = TrainingLog(
                        session_id=session_id,
                        model_id=node_id or 'all',
                        model_type=model_type,
                        status='pending',
                        config=json.dumps(merged_config, ensure_ascii=False),
                        data_source=data_source,
                        is_incremental=is_incremental,
                        base_model_version=base_model_version,
                        freeze_layers=json.dumps(freeze_layers or []) if freeze_layers else None,
                        start_time=datetime.now(),
                        create_time=datetime.now()
                    )
                    db.add(log)
        except Exception as e:
            logger.warning(f"写入训练日志(pending)失败: {e}")

        self._active_sessions[session_id] = {
            'session_id': session_id,
            'model_type': model_type,
            'node_id': node_id,
            'status': 'pending',
            'training_config': merged_config,
            'force_retrain': force_retrain,
            'data_source': data_source,
            'is_incremental': is_incremental,
            'base_model_version': base_model_version,
            'freeze_layers': freeze_layers,
            'start_time': datetime.now(),
            'progress': {
                'current_epoch': 0,
                'total_epochs': merged_config.get('epochs', 100),
                'current_loss': None,
                'current_acc': None
            }
        }

        logger.info(
            f"训练任务已创建: session={session_id}, "
            f"type={model_type}, node={node_id or 'all'}, "
            f"incremental={is_incremental}"
        )

        return session_id

    def execute_training(self, session_id: str) -> Dict[str, Any]:
        session = self._active_sessions.get(session_id)
        if not session:
            return {'status': 'failed', 'error': f'会话不存在: {session_id}'}

        session['status'] = 'running'
        self._update_session_status(session_id, 'running', {'start_time': datetime.now()})

        model_type = session['model_type']
        node_id = session['node_id']
        training_config = session['training_config']
        force_retrain = session['force_retrain']
        is_incremental = session['is_incremental']

        overall_start = time.time()

        try:
            if model_type == 'bolt':
                result = self._train_bolt_model_enhanced(
                    session_id, node_id, force_retrain, training_config, is_incremental
                )
            elif model_type == 'flange':
                result = self._train_flange_model_enhanced(
                    session_id, node_id, force_retrain, training_config, is_incremental
                )
            else:
                raise ValueError(f"未知模型类型: {model_type}")

            elapsed = time.time() - overall_start
            result['total_training_time_seconds'] = round(elapsed, 2)

            final_result = {
                'session_id': session_id,
                'status': 'completed',
                **result
            }

            self._update_session_status(
                session_id, 'completed',
                {'end_time': datetime.now(), 'result': result}
            )

            self._save_model_version(
                session_id, model_type, node_id, result, is_incremental
            )

            logger.info(
                f"训练完成: session={session_id}, "
                f"duration={elapsed:.1f}s, "
                f"best_val_acc={result.get('best_val_acc')}"
            )

        except Exception as e:
            error_msg = str(e)
            error_stack = traceback.format_exc()
            logger.error(f"训练失败: session={session_id}, error={error_msg}")

            self._update_session_status(
                session_id, 'failed',
                {
                    'end_time': datetime.now(),
                    'error_message': error_msg,
                    'error_stack': error_stack
                }
            )

            final_result = {
                'session_id': session_id,
                'status': 'failed',
                'error': error_msg
            }

        if session_id in self._active_sessions:
            del self._active_sessions[session_id]

        return final_result

    def _update_session_status(
        self, session_id: str, status: str,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> None:
        if session_id in self._active_sessions:
            self._active_sessions[session_id]['status'] = status
            if extra_data:
                self._active_sessions[session_id].update(extra_data)

        try:
            with get_db() as db:
                if db is None:
                    return
                log = db.query(TrainingLog).filter(
                    TrainingLog.session_id == session_id
                ).first()
                if not log:
                    return

                log.status = status
                log.update_time = datetime.now()

                if extra_data:
                    if 'result' in extra_data:
                        r = extra_data['result']
                        log.end_time = extra_data.get('end_time', log.end_time)
                        log.best_val_acc = r.get('best_val_acc')
                        log.best_val_loss = r.get('best_val_loss')
                        log.best_epoch = r.get('best_epoch')
                        log.total_epochs = r.get('total_epochs')
                        log.final_train_acc = r.get('final_train_acc')
                        log.final_train_loss = r.get('final_train_loss')
                        log.final_val_acc = r.get('final_val_acc')
                        log.final_val_loss = r.get('final_val_loss')
                        log.precision = r.get('precision')
                        log.recall = r.get('recall')
                        log.f1_score = r.get('f1_score')
                        if r.get('confusion_matrix'):
                            log.confusion_matrix = json.dumps(
                                r['confusion_matrix'], ensure_ascii=False
                            )
                        if r.get('class_distribution'):
                            log.class_distribution = json.dumps(
                                r['class_distribution'], ensure_ascii=False
                            )
                        log.samples_count = r.get('samples_count')
                        log.val_samples_count = r.get('val_samples_count')
                        if r.get('history'):
                            log.metrics_history = json.dumps(
                                r['history'], ensure_ascii=False
                            )

                    if 'error_message' in extra_data:
                        log.error_message = extra_data['error_message']
                        log.error_stack = extra_data.get('error_stack')
                        log.end_time = extra_data.get('end_time', log.end_time)

                    if 'progress' in extra_data:
                        prog = extra_data['progress']
                        log.current_epoch = prog.get('current_epoch', log.current_epoch)

        except Exception as e:
            logger.warning(f"更新训练日志状态失败: {e}")

    def get_training_status(self, session_id: str) -> Dict[str, Any]:
        if session_id in self._active_sessions:
            s = self._active_sessions[session_id]
            return {
                'session_id': session_id,
                'model_type': s['model_type'],
                'node_id': s['node_id'],
                'status': s['status'],
                'start_time': s.get('start_time'),
                'is_incremental': s.get('is_incremental', False),
                'progress': s.get('progress', {}),
                'message': self._status_message(s['status'])
            }

        try:
            with get_db() as db:
                if db is None:
                    return {
                        'session_id': session_id,
                        'status': 'not_found',
                        'error': '数据库不可用且内存中无会话'
                    }

                log = db.query(TrainingLog).filter(
                    TrainingLog.session_id == session_id
                ).first()

                if not log:
                    return {
                        'session_id': session_id,
                        'status': 'not_found',
                        'error': '会话不存在'
                    }

                return {
                    'session_id': session_id,
                    'model_type': log.model_type,
                    'node_id': log.model_id,
                    'status': log.status,
                    'start_time': log.start_time,
                    'end_time': log.end_time,
                    'is_incremental': log.is_incremental,
                    'data_source': log.data_source,
                    'total_epochs': log.total_epochs,
                    'current_epoch': log.current_epoch,
                    'best_epoch': log.best_epoch,
                    'best_val_acc': log.best_val_acc,
                    'best_val_loss': log.best_val_loss,
                    'final_train_acc': log.final_train_acc,
                    'final_train_loss': log.final_train_loss,
                    'final_val_acc': log.final_val_acc,
                    'final_val_loss': log.final_val_loss,
                    'precision': log.precision,
                    'recall': log.recall,
                    'f1_score': log.f1_score,
                    'samples_count': log.samples_count,
                    'val_samples_count': log.val_samples_count,
                    'error_message': log.error_message,
                    'message': self._status_message(log.status)
                }

        except Exception as e:
            logger.error(f"查询训练状态失败: {e}")
            return {'session_id': session_id, 'status': 'error', 'error': str(e)}

    def _status_message(self, status: str) -> str:
        messages = {
            'pending': '任务已创建，等待执行',
            'running': '正在训练中',
            'completed': '训练完成',
            'failed': '训练失败',
            'stopped': '训练已停止'
        }
        return messages.get(status, f'未知状态: {status}')

    def _train_bolt_model_enhanced(
        self, session_id, bolt_id, force_retrain, training_config, is_incremental
    ):
        if bolt_id:
            return self._train_single_bolt_enhanced(
                session_id, bolt_id, force_retrain, training_config, is_incremental
            )
        return self._train_all_bolts_enhanced(
            session_id, force_retrain, training_config, is_incremental
        )

    def _train_single_bolt_enhanced(
        self, session_id, bolt_id, force_retrain, training_config, is_incremental
    ):
        model_path = self.model_save_path / f"bolt_lstm_{bolt_id}.pt"
        if model_path.exists() and not force_retrain and not is_incremental:
            logger.info(f"螺栓模型已存在，跳过: {bolt_id}")
            return {'status': 'skipped', 'bolt_id': bolt_id, 'message': '模型已存在'}

        data, labels, data_source_info = self._load_bolt_training_data_enhanced(bolt_id)

        if len(data) < 100:
            return {
                'status': 'failed',
                'bolt_id': bolt_id,
                'message': f'训练数据不足 (仅{len(data)}条，需要至少100条)'
            }

        validator = get_validator()
        validation_result = validator.validate_training_data(
            data=data, labels=labels, min_samples=100, mode=ValidationMode.LENIENT
        )
        if not validation_result.is_valid:
            return {
                'status': 'failed',
                'bolt_id': bolt_id,
                'message': '训练数据校验失败',
                'validation_errors': format_validation_errors(validation_result)
            }

        model = BoltLSTMModel(bolt_id=bolt_id)
        if is_incremental and model_path.exists():
            logger.info(f"增量训练: 加载基础模型 {model_path}")
            model.load(str(model_path))

        unique, counts = np.unique(labels, return_counts=True)
        class_weights = len(labels) / (len(unique) * counts)

        train_result = model.train(
            train_data=data,
            train_labels=labels,
            training_config=training_config,
            class_weights=class_weights
        )
        model.save()
        file_hash, file_size = self._get_file_info(model_path)

        history = train_result.get('history', {})
        evaluation = train_result.get('evaluation', {})
        es_mode = training_config.get('early_stopping', {}).get('mode', 'min')

        final_val_acc = history.get('val_acc', [0])[-1] if history.get('val_acc') else 0
        final_val_loss = history.get('val_loss', [0])[-1] if history.get('val_loss') else 0
        final_train_acc = history.get('train_acc', [0])[-1] if history.get('train_acc') else 0
        final_train_loss = history.get('train_loss', [0])[-1] if history.get('train_loss') else 0

        best_val_acc = float(train_result.get('best_value', 0)) if es_mode == 'max' else final_val_acc
        best_val_loss = float(train_result.get('best_value', 0)) if es_mode == 'min' else final_val_loss

        return {
            'status': 'success',
            'bolt_id': bolt_id,
            'message': f'螺栓 {bolt_id} 模型训练完成',
            'total_epochs': len(history.get('val_loss', [])),
            'best_epoch': train_result.get('best_epoch'),
            'best_val_acc': float(best_val_acc),
            'best_val_loss': float(best_val_loss),
            'final_train_acc': float(final_train_acc),
            'final_train_loss': float(final_train_loss),
            'final_val_acc': float(final_val_acc),
            'final_val_loss': float(final_val_loss),
            'precision': float(evaluation.get('precision_weighted', 0)),
            'recall': float(evaluation.get('recall_weighted', 0)),
            'f1_score': float(evaluation.get('f1_weighted', 0)),
            'confusion_matrix': evaluation.get('confusion_matrix'),
            'precision_per_class': evaluation.get('precision_per_class'),
            'recall_per_class': evaluation.get('recall_per_class'),
            'f1_per_class': evaluation.get('f1_per_class'),
            'support_per_class': evaluation.get('support_per_class'),
            'class_distribution': train_result.get('class_distribution'),
            'val_class_distribution': train_result.get('val_class_distribution'),
            'samples_count': len(data),
            'val_samples_count': evaluation.get('num_samples', 0),
            'history': history,
            'config_used': train_result.get('config_used'),
            'model_file_path': str(model_path),
            'model_file_hash': file_hash,
            'model_file_size': file_size,
            'data_source': data_source_info
        }

    def _train_all_bolts_enhanced(
        self, session_id, force_retrain, training_config, is_incremental
    ):
        bolt_ids = self._get_all_bolt_ids()
        results = {
            'total': len(bolt_ids), 'success': 0, 'failed': 0,
            'skipped': 0, 'details': [], 'combined_metrics': defaultdict(list)
        }

        for idx, bolt_id in enumerate(bolt_ids):
            try:
                self._update_session_status(
                    session_id, 'running',
                    {'progress': {'phase': f'训练螺栓 {idx+1}/{len(bolt_ids)}', 'bolt_id': bolt_id}}
                )
                result = self._train_single_bolt_enhanced(
                    session_id, bolt_id, force_retrain, training_config, is_incremental
                )
                status = result.get('status', 'failed')
                if status == 'success':
                    results['success'] += 1
                    for k in ['final_val_acc', 'f1_score', 'precision', 'recall']:
                        if k in result:
                            results['combined_metrics'][k].append(result[k])
                elif status == 'skipped':
                    results['skipped'] += 1
                else:
                    results['failed'] += 1
                results['details'].append({'bolt_id': bolt_id, **result})
            except Exception as e:
                results['failed'] += 1
                results['details'].append({'bolt_id': bolt_id, 'status': 'failed', 'error': str(e)})

        for k, values in results['combined_metrics'].items():
            if values:
                results[f'avg_{k}'] = float(np.mean(values))
        del results['combined_metrics']

        first_success = next(
            (d for d in results['details'] if d.get('status') == 'success'), None
        )
        if first_success:
            results['samples_count'] = first_success.get('samples_count')
            results['val_samples_count'] = first_success.get('val_samples_count')
            results['final_val_acc'] = results.get('avg_final_val_acc')
            results['f1_score'] = results.get('avg_f1_score')

        results['status'] = 'completed'
        results['message'] = (
            f"完成: 成功{results['success']}, 失败{results['failed']}, 跳过{results['skipped']}"
        )
        return results

    def _train_flange_model_enhanced(
        self, session_id, flange_id, force_retrain, training_config, is_incremental
    ):
        if flange_id:
            return self._train_single_flange_enhanced(
                session_id, flange_id, force_retrain, training_config, is_incremental
            )
        return self._train_all_flanges_enhanced(
            session_id, force_retrain, training_config, is_incremental
        )

    def _train_single_flange_enhanced(
        self, session_id, flange_id, force_retrain, training_config, is_incremental
    ):
        model_path = self.model_save_path / f"flange_attention_{flange_id}.pt"
        if model_path.exists() and not force_retrain and not is_incremental:
            return {'status': 'skipped', 'flange_id': flange_id, 'message': '模型已存在'}

        flange_dataset, data_source_info = self._load_flange_training_data_fixed(flange_id)
        if not flange_dataset or len(flange_dataset) < 20:
            return {
                'status': 'failed', 'flange_id': flange_id,
                'message': f'训练数据不足 (仅{len(flange_dataset)}个时间点，需要至少20个)'
            }

        samples = []
        labels = []
        for tp in flange_dataset:
            if len(tp['bolt_sequences']) >= 2:
                samples.append(tp['bolt_sequences'])
                labels.append(tp['flange_label'])

        if len(samples) < 10:
            return {
                'status': 'failed', 'flange_id': flange_id,
                'message': f'有效样本不足 (仅{len(samples)}个)'
            }

        labels_arr = np.array(labels, dtype=int)
        model = FlangeAttentionModel(flange_id=flange_id)
        if is_incremental and model_path.exists():
            logger.info(f"增量训练: 加载基础法兰面模型 {model_path}")
            model.load(str(model_path))

        unique, counts = np.unique(labels_arr, return_counts=True)
        class_weights = len(labels_arr) / (len(unique) * counts)

        train_result = model.train(
            train_data=samples,
            train_labels=labels_arr,
            training_config=training_config,
            class_weights=class_weights
        )
        model.save()
        file_hash, file_size = self._get_file_info(model_path)

        history = train_result.get('history', {})
        evaluation = train_result.get('evaluation', {})
        es_mode = training_config.get('early_stopping', {}).get('mode', 'min')
        final_val_acc = history.get('val_acc', [0])[-1] if history.get('val_acc') else 0
        final_val_loss = history.get('val_loss', [0])[-1] if history.get('val_loss') else 0
        final_train_acc = history.get('train_acc', [0])[-1] if history.get('train_acc') else 0
        final_train_loss = history.get('train_loss', [0])[-1] if history.get('train_loss') else 0
        best_val_acc = float(train_result.get('best_value', 0)) if es_mode == 'max' else final_val_acc
        best_val_loss = float(train_result.get('best_value', 0)) if es_mode == 'min' else final_val_loss

        return {
            'status': 'success',
            'flange_id': flange_id,
            'message': f'法兰面 {flange_id} 模型训练完成',
            'total_epochs': len(history.get('val_loss', [])),
            'best_epoch': train_result.get('best_epoch'),
            'best_val_acc': float(best_val_acc),
            'best_val_loss': float(best_val_loss),
            'final_train_acc': float(final_train_acc),
            'final_train_loss': float(final_train_loss),
            'final_val_acc': float(final_val_acc),
            'final_val_loss': float(final_val_loss),
            'precision': float(evaluation.get('precision_weighted', 0)),
            'recall': float(evaluation.get('recall_weighted', 0)),
            'f1_score': float(evaluation.get('f1_weighted', 0)),
            'confusion_matrix': evaluation.get('confusion_matrix'),
            'precision_per_class': evaluation.get('precision_per_class'),
            'recall_per_class': evaluation.get('recall_per_class'),
            'f1_per_class': evaluation.get('f1_per_class'),
            'support_per_class': evaluation.get('support_per_class'),
            'class_distribution': train_result.get('class_distribution'),
            'val_class_distribution': train_result.get('val_class_distribution'),
            'samples_count': len(samples),
            'val_samples_count': evaluation.get('num_samples', 0),
            'history': history,
            'config_used': train_result.get('config_used'),
            'model_file_path': str(model_path),
            'model_file_hash': file_hash,
            'model_file_size': file_size,
            'data_source': data_source_info,
            'num_bolts_per_flange': max(
                (len(tp['bolt_sequences']) for tp in flange_dataset), default=0
            )
        }

    def _train_all_flanges_enhanced(
        self, session_id, force_retrain, training_config, is_incremental
    ):
        flange_ids = self._get_all_flange_ids_fixed()
        results = {
            'total': len(flange_ids), 'success': 0, 'failed': 0,
            'skipped': 0, 'details': []
        }
        for idx, flange_id in enumerate(flange_ids):
            try:
                self._update_session_status(
                    session_id, 'running',
                    {'progress': {'phase': f'训练法兰面 {idx+1}/{len(flange_ids)}', 'flange_id': flange_id}}
                )
                result = self._train_single_flange_enhanced(
                    session_id, flange_id, force_retrain, training_config, is_incremental
                )
                s = result.get('status', 'failed')
                if s == 'success':
                    results['success'] += 1
                elif s == 'skipped':
                    results['skipped'] += 1
                else:
                    results['failed'] += 1
                results['details'].append({'flange_id': flange_id, **result})
            except Exception as e:
                results['failed'] += 1
                results['details'].append({'flange_id': flange_id, 'status': 'failed', 'error': str(e)})

        results['status'] = 'completed'
        results['message'] = (
            f"完成: 成功{results['success']}, 失败{results['failed']}, 跳过{results['skipped']}"
        )
        return results

    def _load_bolt_training_data_enhanced(self, bolt_id):
        dq_enabled = config.get('data_quality.enabled', True)
        auto_filter = config.get('data_quality.integration.auto_filter_training_data', True)
        info = {'primary': 'none', 'quality_filtered': False, 'manual_label_overrides': 0}

        values = None
        timestamps = None
        try:
            with get_db() as db:
                if db is not None:
                    sensor_filter = (
                        BoltData.sensor_id == int(bolt_id)
                        if bolt_id.isdigit()
                        else BoltData.sensor_id == bolt_id
                    )
                    data = db.query(BoltData).filter(
                        sensor_filter
                    ).order_by(BoltData.create_time.asc()).all()
                    if data and len(data) >= 50:
                        values = np.array([d.ptf for d in data])
                        timestamps = np.array([d.create_time for d in data])
                        info['primary'] = 'database'
                        info['raw_count'] = len(data)
        except Exception as e:
            logger.warning(f"从DB加载螺栓数据失败: {e}")

        if values is None:
            values, timestamps = self._load_bolt_from_csv_detailed(bolt_id)
            if values is not None:
                info['primary'] = 'csv'
                info['raw_count'] = len(values)

        if values is None or len(values) < 1:
            return np.array([]), np.array([]), info

        if dq_enabled and auto_filter:
            try:
                engine = get_data_quality_engine()
                fr = engine.filter_training_data(
                    sensor_id=bolt_id, values=values, timestamps=timestamps
                )
                original_count = len(values)
                values = fr.filtered_data
                info['quality_filtered'] = True
                info['after_filter_count'] = len(values)
            except Exception as e:
                logger.warning(f"数据质量过滤失败: {e}")

        auto_labels = self._generate_labels(values)
        merged_labels = label_import_service.merge_labels_with_manual(
            node_type='bolt', node_id=bolt_id,
            auto_labels=auto_labels, data_values=values
        )
        info['manual_label_overrides'] = int(np.sum(merged_labels != auto_labels))

        return values, merged_labels, info

    def _load_bolt_from_csv_detailed(self, bolt_id):
        csv_path = Path('data/data_bolt.csv')
        if not csv_path.exists():
            return None, None
        try:
            df = pd.read_csv(csv_path)
            if '螺栓id' in df.columns:
                bolt_data = df[df['螺栓id'] == bolt_id]
            elif 'bolt_id' in df.columns:
                bolt_data = df[df['bolt_id'] == bolt_id]
            else:
                bolt_data = df
            if len(bolt_data) == 0:
                return None, None
            if '预紧力' in bolt_data.columns:
                values = bolt_data['预紧力'].values
            elif 'ptf' in bolt_data.columns:
                values = bolt_data['ptf'].values
            else:
                return None, None
            timestamps = None
            for col in ['采集时间', '时间', 'time', 'timestamp', 'create_time']:
                if col in bolt_data.columns:
                    try:
                        timestamps = pd.to_datetime(bolt_data[col]).values
                        break
                    except Exception:
                        pass
            return values, timestamps
        except Exception as e:
            logger.error(f"读取螺栓CSV失败: {e}")
            return None, None

    def _load_flange_training_data_fixed(self, flange_id):
        info = {
            'primary': 'none', 'flange_grouping': 'collector-splitter-position',
            'bolt_count': 0, 'time_points': 0
        }
        collector_id, splitter_num, position = self._parse_flange_id(flange_id)
        bolt_datasets = {}
        bolt_ids_list = []

        try:
            with get_db() as db:
                if db is not None:
                    query = db.query(BoltData)
                    if collector_id and splitter_num and position:
                        query = query.filter(
                            BoltData.collector_id == collector_id,
                            BoltData.splitter_num == int(splitter_num) if splitter_num.isdigit() else BoltData.splitter_num == splitter_num,
                            BoltData.position == position
                        )
                    else:
                        query = query.filter(BoltData.flange_id == flange_id)
                    all_data = query.order_by(BoltData.create_time.asc()).all()
                    if all_data:
                        grouped = defaultdict(list)
                        for r in all_data:
                            grouped[str(r.sensor_id)].append(r)
                        for bid, recs in grouped.items():
                            bolt_ids_list.append(bid)
                            bolt_datasets[bid] = [
                                (r.create_time, r.ptf)
                                for r in sorted(recs, key=lambda x: x.create_time)
                            ]
                        info['primary'] = 'database'
        except Exception as e:
            logger.warning(f"从DB加载法兰面数据失败: {e}")

        if not bolt_datasets:
            csv_res = self._load_flange_from_csv_fixed(flange_id)
            if csv_res:
                bolt_datasets, bolt_ids_list = csv_res
                info['primary'] = 'csv'

        if not bolt_datasets:
            return [], info

        aligned = self._align_bolt_data_by_time(bolt_datasets, bolt_ids_list)
        labeled = []
        for tp in aligned:
            if not tp['bolt_values']:
                continue
            bolt_labels = [self._generate_single_label(v) for v in tp['bolt_values']]
            avg_v = float(np.mean(tp['bolt_values']))
            min_v = float(np.min(tp['bolt_values']))
            max_v = float(np.max(tp['bolt_values']))
            flange_label = self._compute_flange_label(bolt_labels, avg_v, min_v, max_v)
            labeled.append({
                'timestamp': tp['timestamp'],
                'bolt_ids': bolt_ids_list,
                'bolt_sequences': tp['bolt_sequences'],
                'bolt_values': tp['bolt_values'],
                'flange_label': flange_label,
                'bolt_labels': bolt_labels
            })

        info['bolt_count'] = len(bolt_ids_list)
        info['time_points'] = len(labeled)
        info['flange_id_parsed'] = {
            'collector_id': collector_id, 'splitter_num': splitter_num, 'position': position
        }
        return labeled, info

    def _load_flange_from_csv_fixed(self, flange_id):
        csv_path = Path('data/data_flm.csv')
        if not csv_path.exists():
            csv_path = Path('data/data_bolt.csv')
            if not csv_path.exists():
                return None
        try:
            df = pd.read_csv(csv_path)
            collector_id, splitter_num, position = self._parse_flange_id(flange_id)
            flange_df = None
            if '法兰面' in df.columns:
                flange_df = df[df['法兰面'] == flange_id]
            elif all(f in df.columns for f in ['collector_id', 'splitter_num', 'position']):
                flange_df = df[
                    (df['collector_id'].astype(str) == str(collector_id)) &
                    (df['splitter_num'].astype(str) == str(splitter_num)) &
                    (df['position'].astype(str) == str(position))
                ]
            elif '螺栓id' in df.columns:
                flange_df = df
            if flange_df is None or len(flange_df) == 0:
                return None

            bolt_col = '螺栓id' if '螺栓id' in flange_df.columns else 'bolt_id'
            value_col = '预紧力' if '预紧力' in flange_df.columns else 'ptf'
            if bolt_col not in flange_df.columns or value_col not in flange_df.columns:
                return None

            time_col = None
            for col in ['采集时间', '时间', 'time', 'timestamp']:
                if col in flange_df.columns:
                    time_col = col
                    break

            bolt_datasets = defaultdict(list)
            for _, row in flange_df.iterrows():
                bid = str(row[bolt_col])
                try:
                    val = float(row[value_col])
                except (ValueError, TypeError):
                    continue
                if time_col:
                    try:
                        ts = pd.to_datetime(row[time_col]).to_pydatetime()
                    except Exception:
                        ts = datetime.now()
                else:
                    ts = datetime.now()
                bolt_datasets[bid].append((ts, val))

            for bid in bolt_datasets:
                bolt_datasets[bid].sort(key=lambda x: x[0])

            return dict(bolt_datasets), sorted(list(bolt_datasets.keys()))
        except Exception as e:
            logger.error(f"读取法兰面CSV失败: {e}")
            return None

    def _align_bolt_data_by_time(self, bolt_datasets, bolt_ids):
        if len(bolt_datasets) < 2:
            result = []
            for bid, data in bolt_datasets.items():
                for ts, val in data:
                    result.append({
                        'timestamp': ts,
                        'bolt_sequences': [np.array([val])],
                        'bolt_values': [val]
                    })
            return result

        time_indexed = defaultdict(dict)
        all_timestamps = set()
        for bid in bolt_ids:
            if bid not in bolt_datasets:
                continue
            for ts, val in bolt_datasets[bid]:
                ts_key = self._normalize_timestamp(ts)
                time_indexed[ts_key][bid] = val
                all_timestamps.add(ts_key)

        sorted_timestamps = sorted(all_timestamps)
        sequence_length = config.get('model.bolt_lstm.sequence_length', 100)
        bolt_history = defaultdict(list)
        result = []

        for ts_key in sorted_timestamps:
            current_values = time_indexed[ts_key]
            for bid in bolt_ids:
                if bid in current_values:
                    bolt_history[bid].append(current_values[bid])
                elif bolt_history[bid]:
                    bolt_history[bid].append(bolt_history[bid][-1])

            sequences = []
            point_values = []
            for bid in bolt_ids:
                h = bolt_history[bid]
                if not h:
                    continue
                if len(h) >= sequence_length:
                    seq = np.array(h[-sequence_length:], dtype=np.float32)
                else:
                    seq = np.pad(
                        np.array(h, dtype=np.float32),
                        (sequence_length - len(h), 0), mode='edge'
                    )
                sequences.append(seq)
                point_values.append(h[-1])

            if len(sequences) >= 2:
                result.append({
                    'timestamp': ts_key,
                    'bolt_sequences': sequences,
                    'bolt_values': point_values
                })
        return result

    def _normalize_timestamp(self, ts):
        try:
            if isinstance(ts, datetime):
                return ts.replace(second=0, microsecond=0)
            if isinstance(ts, str):
                return pd.to_datetime(ts).to_pydatetime().replace(second=0, microsecond=0)
            if hasattr(ts, 'to_pydatetime'):
                return ts.to_pydatetime().replace(second=0, microsecond=0)
        except Exception:
            pass
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(float(ts)).replace(second=0, microsecond=0)
        return datetime.now()

    def _compute_flange_label(self, bolt_labels, avg_value, min_value, max_value):
        if not bolt_labels:
            return 0
        worst = max(bolt_labels)
        avg_label = self._generate_single_label(avg_value)
        if worst >= 4:
            return 4
        if worst >= 3:
            if bolt_labels.count(3) + bolt_labels.count(4) >= 2:
                return 3
            return 3
        if worst >= 2:
            return 2
        if worst >= 1:
            return max(avg_label, 1)
        return max(avg_label, 0)

    def _generate_single_label(self, value):
        thresholds = config.get('risk_assessment.preload_thresholds', {})
        min_normal = thresholds.get('min_normal', 400)
        max_normal = thresholds.get('max_normal', 800)
        if value < min_normal * 0.5 or value > max_normal * 1.5:
            return 4
        elif value < min_normal * 0.7 or value > max_normal * 1.3:
            return 3
        elif value < min_normal * 0.9 or value > max_normal * 1.1:
            return 2
        elif value < min_normal or value > max_normal:
            return 1
        else:
            return 0

    def _generate_labels(self, data):
        thresholds = config.get('risk_assessment.preload_thresholds', {})
        min_normal = thresholds.get('min_normal', 400)
        max_normal = thresholds.get('max_normal', 800)
        labels = np.zeros(len(data), dtype=int)
        for i, val in enumerate(data):
            if val < min_normal * 0.5 or val > max_normal * 1.5:
                labels[i] = 4
            elif val < min_normal * 0.7 or val > max_normal * 1.3:
                labels[i] = 3
            elif val < min_normal * 0.9 or val > max_normal * 1.1:
                labels[i] = 2
            elif val < min_normal or val > max_normal:
                labels[i] = 1
            else:
                labels[i] = 0
        return labels

    def _get_all_bolt_ids(self):
        try:
            with get_db() as db:
                if db:
                    from sqlalchemy import distinct
                    result = db.query(distinct(BoltData.sensor_id)).all()
                    ids = [str(r[0]) for r in result]
                    if ids:
                        return ids
        except Exception:
            pass
        csv_path = Path('data/data_bolt.csv')
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path)
                if '螺栓id' in df.columns:
                    return df['螺栓id'].unique().tolist()
            except Exception:
                pass
        return []

    def _get_all_flange_ids_fixed(self):
        try:
            with get_db() as db:
                if db:
                    from sqlalchemy import distinct
                    result = db.query(
                        BoltData.collector_id,
                        BoltData.splitter_num,
                        BoltData.position
                    ).distinct().all()
                    flange_ids = set()
                    for cid, sn, pos in result:
                        if cid and sn is not None and pos:
                            flange_ids.add(f"{cid}-{sn}-{pos}")
                    if flange_ids:
                        return sorted(list(flange_ids))
        except Exception as e:
            logger.warning(f"从DB获取法兰面ID失败: {e}")

        csv_path = Path('data/data_flm.csv')
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path)
                if '法兰面' in df.columns:
                    return df['法兰面'].unique().tolist()
            except Exception:
                pass
        csv_path = Path('data/data_bolt.csv')
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path)
                if all(c in df.columns for c in ['collector_id', 'splitter_num', 'position']):
                    combined = (
                        df['collector_id'].astype(str) + '-' +
                        df['splitter_num'].astype(str) + '-' +
                        df['position'].astype(str)
                    )
                    return combined.unique().tolist()
            except Exception:
                pass
        return []

    def _get_file_info(self, path):
        try:
            if not path.exists():
                return None, None
            size = path.stat().st_size
            md5 = hashlib.md5()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    md5.update(chunk)
            return md5.hexdigest(), size
        except Exception as e:
            logger.warning(f"计算文件信息失败: {e}")
            return None, None

    def _save_model_version(
        self, session_id, model_type, node_id, train_result, is_incremental
    ):
        try:
            from app.services.model_version_service import get_model_version_service

            service = get_model_version_service()

            nodes_to_save = []
            if node_id:
                nodes_to_save.append(node_id)
            elif 'details' in train_result:
                for detail in train_result['details']:
                    if detail.get('status') == 'success':
                        nid = detail.get('bolt_id') or detail.get('flange_id')
                        if nid:
                            nodes_to_save.append(nid)

            for nid in nodes_to_save:
                node_r = train_result
                if 'details' in train_result and len(nodes_to_save) > 1:
                    node_r = next(
                        (d for d in train_result['details']
                         if (d.get('bolt_id') or d.get('flange_id')) == nid),
                        train_result
                    )

                arch = self._get_architecture_summary(model_type, node_r)

                metrics_data = {
                    'best_epoch': node_r.get('best_epoch'),
                    'best_val_acc': node_r.get('best_val_acc'),
                    'best_val_loss': node_r.get('best_val_loss'),
                    'final_train_acc': node_r.get('final_train_acc'),
                    'final_train_loss': node_r.get('final_train_loss'),
                    'final_val_acc': node_r.get('final_val_acc'),
                    'final_val_loss': node_r.get('final_val_loss'),
                    'precision': node_r.get('precision'),
                    'recall': node_r.get('recall'),
                    'f1_score': node_r.get('f1_score'),
                    'precision_per_class': node_r.get('precision_per_class'),
                    'recall_per_class': node_r.get('recall_per_class'),
                    'f1_per_class': node_r.get('f1_per_class'),
                    'support_per_class': node_r.get('support_per_class'),
                    'confusion_matrix': node_r.get('confusion_matrix'),
                    'class_distribution': node_r.get('class_distribution'),
                    'val_class_distribution': node_r.get('val_class_distribution'),
                    'samples_count': node_r.get('samples_count'),
                    'val_samples_count': node_r.get('val_samples_count'),
                    'history': node_r.get('history'),
                    'training_time_seconds': train_result.get('total_training_time_seconds')
                }
                cfg = node_r.get('config_used', {})
                cfg['data_source'] = node_r.get('data_source')

                parent_v = None
                if is_incremental:
                    with get_db() as db:
                        if db:
                            parent_v = self._get_previous_version(db, nid, model_type)

                freeze_layers_list = None
                if is_incremental:
                    freeze_layers_list = cfg.get('incremental', {}).get('freeze_layers', [])

                description = f"训练会话 {session_id} - {'增量训练' if is_incremental else '完整训练'}"

                model_file_path = node_r.get('model_file_path')
                if not model_file_path or not os.path.exists(model_file_path):
                    logger.warning(f"模型文件不存在，跳过版本注册: {model_file_path}")
                    continue

                version_info = service.register_version(
                    model_type=model_type,
                    node_id=nid,
                    model_file_path=model_file_path,
                    metrics=metrics_data,
                    training_config=cfg,
                    description=description,
                    training_session_id=session_id,
                    parent_version=parent_v,
                    training_samples=node_r.get('samples_count'),
                    validation_samples=node_r.get('val_samples_count'),
                    training_duration_seconds=train_result.get('total_training_time_seconds'),
                    architecture_summary=arch,
                    freeze_layers=freeze_layers_list,
                )

                logger.info(
                    f"模型版本已注册: {model_type}/{nid} "
                    f"v{version_info['version']}, F1={node_r.get('f1_score')}"
                )

        except Exception as e:
            logger.warning(f"保存模型版本失败: {e}")

    def _get_next_version(self, db, model_id, model_type):
        try:
            latest = db.query(ModelVersionORM).filter(
                ModelVersionORM.model_id == model_id,
                ModelVersionORM.model_type == model_type
            ).order_by(ModelVersionORM.create_time.desc()).first()
            if latest and latest.version.startswith('v'):
                parts = latest.version[1:].split('.')
                if len(parts) == 3:
                    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                    return f"v{major}.{minor}.{patch + 1}"
            return "v1.0.0"
        except Exception:
            return f"v1.0.0-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def _get_previous_version(self, db, model_id, model_type):
        try:
            latest = db.query(ModelVersionORM).filter(
                ModelVersionORM.model_id == model_id,
                ModelVersionORM.model_type == model_type
            ).order_by(ModelVersionORM.create_time.desc()).first()
            return latest.version if latest else None
        except Exception:
            return None

    def _get_architecture_summary(self, model_type, result):
        if model_type == 'bolt':
            return {
                'type': 'BoltLSTM',
                'lstm_layers': 2, 'fc_layers': 2,
                'sequence_length': config.get('model.bolt_lstm.sequence_length', 100),
                'hidden_size': config.get('model.bolt_lstm.hidden_size', 128),
                'output_classes': 5
            }
        return {
            'type': 'FlangeAttention',
            'bolt_extractor': 'BiLSTM',
            'attention_heads': config.get('model.flange_attention.num_heads', 4),
            'output_classes': 5
        }

    def get_model_info(self, model_type, node_id):
        if model_type == 'bolt':
            model_path = self.model_save_path / f"bolt_lstm_{node_id}.pt"
        else:
            model_path = self.model_save_path / f"flange_attention_{node_id}.pt"
        info = {
            'is_trained': model_path.exists(),
            'model_file_path': str(model_path) if model_path.exists() else None
        }
        try:
            with get_db() as db:
                if db is None:
                    return info
                version = db.query(ModelVersionORM).filter(
                    ModelVersionORM.model_id == node_id,
                    ModelVersionORM.model_type == model_type,
                    ModelVersionORM.is_active == True
                ).first()
                if version:
                    info.update({
                        'version': version.version,
                        'file_hash': version.file_hash,
                        'create_time': version.create_time,
                        'training_session_id': version.training_session_id,
                        'description': version.description,
                        'training_samples': version.training_samples,
                        'validation_samples': version.validation_samples,
                        'is_incremental': version.freeze_layers is not None,
                        'parent_version': version.parent_version,
                    })
                    if version.metrics:
                        try:
                            m = json.loads(version.metrics)
                            info['metrics'] = {k: m.get(k) for k in [
                                'precision', 'recall', 'f1_score', 'final_val_acc',
                                'best_val_acc', 'samples_count'
                            ]}
                        except Exception:
                            pass
                    all_v = db.query(ModelVersionORM).filter(
                        ModelVersionORM.model_id == node_id,
                        ModelVersionORM.model_type == model_type
                    ).order_by(ModelVersionORM.create_time.desc()).limit(10).all()
                    info['version_history'] = [
                        {
                            'version': v.version, 'create_time': v.create_time,
                            'is_active': v.is_active, 'description': v.description
                        }
                        for v in all_v
                    ]
        except Exception as e:
            logger.warning(f"获取模型信息失败: {e}")
        return info

    def list_training_sessions(self, model_type=None, status=None, limit=50):
        try:
            with get_db() as db:
                if db is None:
                    return []
                q = db.query(TrainingLog)
                if model_type:
                    q = q.filter(TrainingLog.model_type == model_type)
                if status:
                    q = q.filter(TrainingLog.status == status)
                logs = q.order_by(TrainingLog.create_time.desc()).limit(limit).all()
                return [
                    {
                        'session_id': l.session_id,
                        'model_type': l.model_type,
                        'model_id': l.model_id,
                        'status': l.status,
                        'start_time': l.start_time,
                        'end_time': l.end_time,
                        'best_val_acc': l.best_val_acc,
                        'f1_score': l.f1_score,
                        'samples_count': l.samples_count,
                        'error_message': l.error_message
                    }
                    for l in logs
                ]
        except Exception as e:
            logger.warning(f"列出训练会话失败: {e}")
            return []

    def train_model(self, model_type, node_id=None, force_retrain=False):
        """兼容旧接口的同步训练方法"""
        session_id = self.start_training(
            model_type=model_type, node_id=node_id, force_retrain=force_retrain
        )
        result = self.execute_training(session_id)
        status = result.get('status', 'unknown')
        if status == 'completed':
            return {'status': 'success', 'session_id': session_id, **result}
        if status == 'failed':
            return {'status': 'failed', 'session_id': session_id, 'error': result.get('error')}
        return {'status': status, 'session_id': session_id, **result}


_training_service_instance = None


def get_training_service():
    """获取训练服务单例"""
    global _training_service_instance
    if _training_service_instance is None:
        _training_service_instance = TrainingService()
    return _training_service_instance
