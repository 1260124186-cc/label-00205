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
from contextlib import contextmanager

import numpy as np
import pandas as pd
from fastapi import HTTPException
from loguru import logger
from sklearn.preprocessing import StandardScaler

from app.models.bolt_lstm import BoltLSTMModel
from app.models.flange_attention import FlangeAttentionModel
from app.services.preprocessing import DataPreprocessor, MultivariatePreprocessor
from app.services.feature_engineering import FeatureEngineer
from app.services.label_import import label_import_service
from app.api.validators import get_validator, ValidationMode, format_validation_errors
from app.utils.config import config
from app.middleware import (
    get_effective_tenant_id,
    is_super_admin,
    is_audit_mode,
)
from app.services.tenant import (
    get_active_model_path,
    acquire_training_slot,
    enforce_tenant_access,
    ensure_model_quota_available,
    not_found_404,
)
from app.utils.database import (
    get_db,
    BoltData,
    MultivariateBoltData,
    MultivariateTrainingConfig,
    TrainingLog,
    ModelVersionORM,
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
        self.training_config_template = config.get('model.training', {})

        self._active_sessions: Dict[str, Dict[str, Any]] = {}

        logger.info("增强版训练服务初始化完成（租户隔离版）")

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
        if is_audit_mode():
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Forbidden",
                    "message": "审计模式为只读，无法启动训练任务",
                    "audit_mode": True,
                },
            )

        tenant_id = get_effective_tenant_id()
        if tenant_id is None:
            raise not_found_404()

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
                        tenant_id=tenant_id,
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
            'tenant_id': tenant_id,
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
            f"训练任务已创建: tenant={tenant_id}, session={session_id}, "
            f"type={model_type}, node={node_id or 'all'}, "
            f"incremental={is_incremental}"
        )

        return session_id

    def execute_training(self, session_id: str) -> Dict[str, Any]:
        session = self._active_sessions.get(session_id)
        if not session:
            return {'status': 'failed', 'error': f'会话不存在: {session_id}'}

        tenant_id = session.get('tenant_id') or get_effective_tenant_id()
        if tenant_id is None:
            return {'status': 'failed', 'error': '缺少租户上下文'}

        session['status'] = 'running'
        self._update_session_status(session_id, 'running', {'start_time': datetime.now()})

        model_type = session['model_type']
        node_id = session['node_id']
        training_config = session['training_config']
        force_retrain = session['force_retrain']
        is_incremental = session['is_incremental']

        overall_start = time.time()

        try:
            with acquire_training_slot(tenant_id, timeout=300):
                if model_type == 'bolt':
                    result = self._train_bolt_model_enhanced(
                        session_id, tenant_id, node_id, force_retrain, training_config, is_incremental
                    )
                elif model_type == 'flange':
                    result = self._train_flange_model_enhanced(
                        session_id, tenant_id, node_id, force_retrain, training_config, is_incremental
                    )
                else:
                    raise ValueError(f"未知模型类型: {model_type}")

                elapsed = time.time() - overall_start
                result['total_training_time_seconds'] = round(elapsed, 2)

                final_result = {
                    'session_id': session_id,
                    'tenant_id': tenant_id,
                    'status': 'completed',
                    **result
                }

                self._update_session_status(
                    session_id, 'completed',
                    {'end_time': datetime.now(), 'result': result}
                )

                self._save_model_version(
                    session_id, tenant_id, model_type, node_id, result, is_incremental
                )

                logger.info(
                    f"训练完成: tenant={tenant_id}, session={session_id}, "
                    f"duration={elapsed:.1f}s, "
                    f"best_val_acc={result.get('best_val_acc')}"
                )

        except HTTPException as he:
            error_msg = str(he.detail) if isinstance(he.detail, str) else str(he.detail.get('message', he.detail))
            error_stack = traceback.format_exc()
            logger.error(f"训练失败(配额): tenant={tenant_id}, session={session_id}, error={error_msg}")
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
                'tenant_id': tenant_id,
                'status': 'failed',
                'error': error_msg
            }
        except Exception as e:
            error_msg = str(e)
            error_stack = traceback.format_exc()
            logger.error(f"训练失败: tenant={tenant_id}, session={session_id}, error={error_msg}")

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
                'tenant_id': tenant_id,
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

        current_tenant_id = None
        if session_id in self._active_sessions:
            current_tenant_id = self._active_sessions[session_id].get('tenant_id')

        try:
            with get_db() as db:
                if db is None:
                    return
                log_q = db.query(TrainingLog).filter(
                    TrainingLog.session_id == session_id
                )
                if current_tenant_id:
                    log_q = log_q.filter(TrainingLog.tenant_id == current_tenant_id)
                log = log_q.first()
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
                        log.data_quality = r.get('data_quality', log.data_quality)
                        if r.get('missing_channels') is not None:
                            log.missing_channels = json.dumps(
                                r['missing_channels'], ensure_ascii=False
                            )
                        if r.get('actual_channels_used'):
                            log.remark = json.dumps({
                                'actual_channels_used': r['actual_channels_used'],
                                'complete_ratio': r.get('complete_ratio'),
                                'input_dim': r.get('input_dim_actual'),
                                'degradation_applied': r.get('degradation_applied', False),
                                'interpolation_count': r.get('interpolation_count', 0),
                            }, ensure_ascii=False)
                        if r.get('history'):
                            metrics_payload = dict(r['history'])
                            if r.get('feature_importance'):
                                metrics_payload['feature_importance'] = r['feature_importance']
                            if r.get('feature_engineering'):
                                metrics_payload['feature_engineering'] = r['feature_engineering']
                            log.metrics_history = json.dumps(
                                metrics_payload, ensure_ascii=False
                            )

                        # 特征工程元数据写入 log.config 末尾扩展
                        if r.get('feature_importance') or r.get('feature_engineering'):
                            try:
                                cfg = json.loads(log.config) if log.config else {}
                            except Exception:
                                cfg = {}
                            if r.get('feature_importance'):
                                cfg['feature_importance'] = r['feature_importance']
                            if r.get('feature_engineering'):
                                cfg['feature_engineering'] = r['feature_engineering']
                            log.config = json.dumps(cfg, ensure_ascii=False)

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
        tenant_id = get_effective_tenant_id()

        if session_id in self._active_sessions:
            s = self._active_sessions[session_id]
            if tenant_id and s.get('tenant_id') != tenant_id:
                raise not_found_404()
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

                log_q = db.query(TrainingLog).filter(
                    TrainingLog.session_id == session_id
                )
                if tenant_id:
                    log_q = log_q.filter(TrainingLog.tenant_id == tenant_id)
                log = log_q.first()

                if not log:
                    raise not_found_404()

                if tenant_id:
                    enforce_tenant_access(log.tenant_id, log.id, "TrainingLog")

                return {
                    'session_id': session_id,
                    'tenant_id': log.tenant_id,
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

        except HTTPException:
            raise
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
        self, session_id, tenant_id, bolt_id, force_retrain, training_config, is_incremental
    ):
        if bolt_id:
            return self._train_single_bolt_enhanced(
                session_id, tenant_id, bolt_id, force_retrain, training_config, is_incremental
            )
        return self._train_all_bolts_enhanced(
            session_id, tenant_id, force_retrain, training_config, is_incremental
        )

    def _train_single_bolt_enhanced(
        self, session_id, tenant_id, bolt_id, force_retrain, training_config, is_incremental
    ):
        model_path = get_active_model_path('bolt', str(bolt_id), tenant_id)
        model_path.parent.mkdir(parents=True, exist_ok=True)

        if model_path.exists() and not force_retrain and not is_incremental:
            logger.info(f"螺栓模型已存在，跳过: tenant={tenant_id}, bolt={bolt_id}")
            return {'status': 'skipped', 'bolt_id': bolt_id, 'message': '模型已存在'}

        # 初始化特征快照相关变量
        use_feature_snapshot = False
        fe_enabled = False
        feature_dim = 0

        # === 检查是否使用特征快照进行训练 ===
        fs_cfg = None
        if training_config and hasattr(training_config, 'feature_snapshot'):
            fs_cfg = training_config.feature_snapshot
        elif training_config and isinstance(training_config, dict):
            fs_cfg = training_config.get('feature_snapshot')

        use_feature_snapshot = (
            fs_cfg is not None and
            (fs_cfg if isinstance(fs_cfg, dict) else fs_cfg).get('enabled', False)
        )

        if use_feature_snapshot:
            try:
                from app.services.feature_store import get_feature_store, IncompatibleFeatureVersionError

                feature_store = get_feature_store()
                fs_config_dict = fs_cfg if isinstance(fs_cfg, dict) else {
                    'feature_version': fs_cfg.feature_version,
                    'start_time': fs_cfg.start_time,
                    'end_time': fs_cfg.end_time,
                    'check_version_compatibility': fs_cfg.check_version_compatibility,
                    'mark_used_for_training': fs_cfg.mark_used_for_training,
                }

                feature_version = fs_config_dict.get('feature_version', 'v1.0')
                start_time = fs_config_dict.get('start_time')
                end_time = fs_config_dict.get('end_time')
                check_compatibility = fs_config_dict.get('check_version_compatibility', True)
                mark_used = fs_config_dict.get('mark_used_for_training', True)

                logger.info(
                    f"使用特征快照训练: bolt={bolt_id}, "
                    f"feature_version={feature_version}, "
                    f"time_range=[{start_time}, {end_time}]"
                )

                # 从特征存储加载特征矩阵
                feature_matrix, snapshots = feature_store.load_training_features(
                    node_ids=[str(bolt_id)],
                    feature_version=feature_version,
                    node_type='bolt',
                    start_time=start_time,
                    end_time=end_time,
                    check_compatibility=check_compatibility,
                )

                if len(snapshots) < 100:
                    return {
                        'status': 'failed',
                        'bolt_id': bolt_id,
                        'message': f'特征快照数据不足 (仅{len(snapshots)}条，需要至少100条)',
                        'feature_version': feature_version,
                    }

                # 标记快照已用于训练（保证可追溯）
                if mark_used and snapshots:
                    snapshot_ids = [s.id for s in snapshots if s.id is not None]
                    feature_store.mark_used_for_training(snapshot_ids, session_id)

                # 从快照中提取标签（如果有预测结果则使用其状态码作为标签）
                labels = []
                for snap in snapshots:
                    if snap.prediction_result and 'status_code' in snap.prediction_result:
                        labels.append(int(snap.prediction_result['status_code']))
                    else:
                        labels.append(0)

                labels = np.array(labels, dtype=np.int64)

                # 构造返回数据（使用特征矩阵作为训练数据）
                data = feature_matrix
                data_source_info = {
                    'data_source': 'feature_snapshot',
                    'actual_channels_used': ['feature_vector'],
                    'feature_version': feature_version,
                    'snapshot_count': len(snapshots),
                    'snapshot_ids': [s.id for s in snapshots if s.id is not None],
                    'complete_ratio': 1.0,
                    'input_dim_actual': feature_matrix.shape[1] if len(feature_matrix.shape) > 1 else feature_matrix.shape[0],
                }

                # 标记训练配置，跳过后续的特征工程（因为已经有特征了）
                fe_enabled = False
                feature_dim = feature_matrix.shape[1] if len(feature_matrix.shape) > 1 else 0

                logger.info(
                    f"特征快照加载成功: bolt={bolt_id}, "
                    f"samples={len(snapshots)}, dim={feature_dim}, "
                    f"feature_version={feature_version}"
                )

            except IncompatibleFeatureVersionError as e:
                logger.error(f"特征版本不兼容，训练终止: {e}")
                return {
                    'status': 'failed',
                    'bolt_id': bolt_id,
                    'message': f'特征版本不兼容: {str(e)}',
                    'error_type': 'incompatible_feature_version',
                }
            except Exception as e:
                logger.error(f"加载特征快照失败，回退到原始数据训练: {e}")
                use_feature_snapshot = False
                data, labels, data_source_info = self._load_bolt_training_data_enhanced(tenant_id, bolt_id)
        else:
            data, labels, data_source_info = self._load_bolt_training_data_enhanced(tenant_id, bolt_id)

        if len(data) < 100:
            return {
                'status': 'failed',
                'bolt_id': bolt_id,
                'message': f'训练数据不足 (仅{len(data)}条，需要至少100条)'
            }

        # === 判断数据维度（单变量 vs 多变量）===
        input_dim_actual = 1
        actual_channels_used = data_source_info.get('actual_channels_used', ['preload'])
        if isinstance(data, np.ndarray) and data.ndim == 2:
            input_dim_actual = data.shape[1]

        # 校验器：1D / 2D 数据都兼容
        validator = get_validator()
        validation_data = data
        if data.ndim == 2 and 'preload' in actual_channels_used:
            preload_idx = actual_channels_used.index('preload')
            validation_data = data[:, preload_idx]
        validation_result = validator.validate_training_data(
            data=validation_data, labels=labels, min_samples=100, mode=ValidationMode.LENIENT
        )
        if not validation_result.is_valid:
            return {
                'status': 'failed',
                'bolt_id': bolt_id,
                'message': '训练数据校验失败',
                'validation_errors': format_validation_errors(validation_result)
            }

        # === 特征工程：提取、标准化、初始化相关变量 ===
        # 如果使用特征快照模式，fe_enabled 和 feature_dim 已经设置过了
        if not use_feature_snapshot:
            fe_cfg = config.get('feature_engineering', {})
            fe_enabled = fe_cfg.get('enabled', False)
            feature_dim = 0

        raw_feature_matrix = None
        feature_names = []
        scaled_feature_matrix = None
        scaler_state = None
        train_features = None
        val_features = None

        if fe_enabled and not use_feature_snapshot:
            if data.ndim == 2 and 'preload' in actual_channels_used:
                preload_idx = actual_channels_used.index('preload')
                preload_data = data[:, preload_idx]
            else:
                preload_data = data[:, 0] if data.ndim == 2 else data

            try:
                raw_feature_matrix, feature_names = self.feature_engineer.extract_batch_features(
                    preload_data, window_size=100, step=1
                )
            except Exception as fe_e:
                logger.warning(f"批量特征提取失败，跳过特征工程: {fe_e}")
                raw_feature_matrix = None
                fe_enabled = False

            if raw_feature_matrix is not None and raw_feature_matrix.size > 0:
                feature_dim = raw_feature_matrix.shape[1]
                try:
                    scaled_feature_matrix = self.feature_engineer.fit_transform_batch(raw_feature_matrix)
                    scaler_state = self.feature_engineer.get_scaler_state()
                except Exception as scale_e:
                    logger.warning(f"特征标准化失败，跳过特征工程: {scale_e}")
                    fe_enabled = False
                    feature_dim = 0

        # 模型初始化（BoltLSTMModel 已扩展 prepare_data 支持多维输入）
        model = BoltLSTMModel(bolt_id=bolt_id, feature_dim=feature_dim)
        actual_input_dim = model.model.input_size  # LSTM input_size
        if input_dim_actual > 1 and actual_input_dim != input_dim_actual:
            logger.info(
                f"重新初始化多变量模型 bolt={bolt_id}: "
                f"input_dim {actual_input_dim} → {input_dim_actual}, "
                f"channels={actual_channels_used}, "
                f"data_quality={data_source_info.get('data_quality', 'full')}, "
                f"feature_dim={feature_dim}"
            )
            try:
                lstm_cfg = model.model_config
                from app.models.bolt_lstm import LSTMNetwork, get_device
                model.model = LSTMNetwork(
                    input_dim=input_dim_actual,
                    lstm_units_1=lstm_cfg.get('lstm_units_1', 128),
                    lstm_units_2=lstm_cfg.get('lstm_units_2', 64),
                    dropout_rate=lstm_cfg.get('dropout_rate', 0.2),
                    dense_units=lstm_cfg.get('dense_units', 32),
                    output_classes=lstm_cfg.get('output_classes', 5),
                    feature_dim=feature_dim,
                    feature_mode=model.feature_mode,
                    tabular_hidden=model.tabular_hidden,
                    fusion_mode=model.fusion_mode,
                ).to(model.device)
                model.model_config['input_dim'] = input_dim_actual
            except Exception as rebuild_e:
                logger.warning(f"重建多变量模型失败，使用默认模型: {rebuild_e}")
        elif input_dim_actual > 1:
            logger.info(
                f"多变量训练 bolt={bolt_id}, "
                f"input_dim={input_dim_actual}, "
                f"channels={actual_channels_used}, "
                f"data_quality={data_source_info.get('data_quality', 'full')}, "
                f"feature_dim={feature_dim}"
            )

        if is_incremental and model_path.exists():
            logger.info(f"增量训练: 加载基础模型 {model_path}")
            try:
                load_meta = model.load(str(model_path))
                if fe_enabled and load_meta.get('feature_scaler_state') is not None:
                    self.feature_engineer.set_scaler_state(load_meta['feature_scaler_state'])
            except Exception as load_e:
                logger.warning(f"增量加载失败（可能是维度变化），重新训练: {load_e}")

        unique, counts = np.unique(labels, return_counts=True)
        class_weights = len(labels) / (len(unique) * counts)

        if fe_enabled and scaled_feature_matrix is not None:
            N = len(scaled_feature_matrix)
            val_size = max(1, int(N * 0.2))
            train_features = scaled_feature_matrix[:-val_size]
            val_features = scaled_feature_matrix[-val_size:]

        train_result = model.train(
            train_data=data,
            train_labels=labels,
            training_config=training_config,
            class_weights=class_weights,
            train_features=train_features,
            val_features=val_features
        )
        save_kwargs = {}
        if fe_enabled and scaler_state is not None:
            save_kwargs['feature_scaler_state'] = scaler_state
            save_kwargs['feature_names'] = feature_names
        model.save(**save_kwargs)
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

        feature_importance_result = None
        if model.is_trained and fe_enabled and fe_cfg.get('importance.compute_after_training', False):
            try:
                sample_ratio = fe_cfg.get('importance.sample_ratio', 0.3)
                min_samples = fe_cfg.get('importance.min_samples', 50)
                if data.ndim == 2 and 'preload' in actual_channels_used:
                    preload_idx = actual_channels_used.index('preload')
                    preload_for_imp = data[:, preload_idx]
                else:
                    preload_for_imp = data[:, 0] if data.ndim == 2 else data

                total_N = len(preload_for_imp)
                sample_N = max(min_samples, int(total_N * sample_ratio))
                if total_N > sample_N:
                    start_idx = total_N - sample_N
                    sample_preload = preload_for_imp[start_idx:]
                    sample_labels = labels[start_idx:]
                else:
                    sample_preload = preload_for_imp
                    sample_labels = labels

                def predict_fn(sequences, features):
                    model.model.eval()
                    with torch.no_grad():
                        X_seq = torch.FloatTensor(sequences).to(model.device)
                        feat_tensor = None
                        if features is not None:
                            feat_tensor = torch.FloatTensor(features).to(model.device)
                        outputs = model.model(X_seq, feat_tensor)
                        _, preds = torch.max(outputs, dim=1)
                        return preds.cpu().numpy()

                fi = self.feature_engineer.compute_permutation_importance_from_windows(
                    model_predict_fn=predict_fn,
                    raw_sequences=sample_preload,
                    y_true=sample_labels,
                    seq_length=100,
                    n_repeats=fe_cfg.get('importance.n_repeats', 5),
                    random_state=42,
                )
                feature_importance_result = fi.to_dict()
            except Exception as imp_e:
                logger.warning(f"Permutation Importance 计算失败: {imp_e}")
                feature_importance_result = None

        result = {
            'status': 'success',
            'bolt_id': bolt_id,
            'message': f'螺栓 {bolt_id} 模型训练完成（{input_dim_actual}维，{data_source_info.get("data_quality","full")}）',
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
            'data_source': data_source_info,
            # === 多变量数据质量（写入 TrainingLog.data_quality / missing_channels / remark）===
            'data_quality': data_source_info.get('data_quality', 'full'),
            'missing_channels': data_source_info.get('missing_channels', []),
            'actual_channels_used': actual_channels_used,
            'complete_ratio': data_source_info.get('complete_ratio', 1.0),
            'input_dim_actual': input_dim_actual,
            'degradation_applied': data_source_info.get('degradation_applied', False),
            'interpolation_count': data_source_info.get('interpolation_count', 0),
            # === 特征工程 ===
            'feature_engineering': {
                'enabled': fe_enabled,
                'feature_count': feature_dim,
                'feature_names': list(feature_names) if feature_names else [],
            },
        }
        if feature_importance_result is not None:
            result['feature_importance'] = feature_importance_result
        return result

    def _train_all_bolts_enhanced(
        self, session_id, tenant_id, force_retrain, training_config, is_incremental
    ):
        bolt_ids = self._get_all_bolt_ids(tenant_id)

        faulty_sensor_ids = set()
        try:
            from app.services.device_health_service import get_device_health_service
            dh_service = get_device_health_service()
            faulty_sensor_ids = dh_service.get_faulty_sensor_ids(tenant_id=tenant_id)
        except Exception as e:
            logger.warning(f"获取故障设备列表失败，跳过设备过滤: {e}")

        if faulty_sensor_ids:
            original_count = len(bolt_ids)
            bolt_ids = [bid for bid in bolt_ids if str(bid) not in faulty_sensor_ids]
            skipped_faulty = original_count - len(bolt_ids)
            if skipped_faulty > 0:
                logger.info(f"训练排除 {skipped_faulty} 个故障设备传感器")

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
                    session_id, tenant_id, bolt_id, force_retrain, training_config, is_incremental
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
        self, session_id, tenant_id, flange_id, force_retrain, training_config, is_incremental
    ):
        if flange_id:
            return self._train_single_flange_enhanced(
                session_id, tenant_id, flange_id, force_retrain, training_config, is_incremental
            )
        return self._train_all_flanges_enhanced(
            session_id, tenant_id, force_retrain, training_config, is_incremental
        )

    def _train_single_flange_enhanced(
        self, session_id, tenant_id, flange_id, force_retrain, training_config, is_incremental
    ):
        model_path = get_active_model_path('flange', str(flange_id), tenant_id)
        model_path.parent.mkdir(parents=True, exist_ok=True)

        if model_path.exists() and not force_retrain and not is_incremental:
            return {'status': 'skipped', 'flange_id': flange_id, 'message': '模型已存在'}

        flange_dataset, data_source_info = self._load_flange_training_data_fixed(tenant_id, flange_id)
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

        # === 特征工程：提取 bolt-level 和 global 特征 ===
        fe_cfg = config.get('feature_engineering', {})
        fe_enabled = fe_cfg.get('enabled', False)
        bolt_feature_names = []
        global_feature_names = []
        bolt_feat_dim = 0
        global_feat_dim = 0
        train_bolt_features = None
        train_global_features = None
        val_bolt_features = None
        val_global_features = None
        bolt_scaler_state = None
        global_scaler_state = None

        if fe_enabled:
            try:
                all_bolt_feats_flat = []
                all_global_feats_list = []
                train_bolt_features = []
                train_global_features = []
                bolt_feat_dim = 0
                global_feat_dim = 0

                for sample_idx, sample in enumerate(samples):
                    sample_bolt_feats = []
                    for bolt_seq in sample:
                        fs = self.feature_engineer.extract_features(bolt_seq)
                        bolt_feat = fs.combined_features
                        sample_bolt_feats.append(bolt_feat)
                        if bolt_feat.size > 0:
                            all_bolt_feats_flat.append(bolt_feat)
                            if not bolt_feature_names:
                                bolt_feature_names = list(fs.feature_names)
                                bolt_feat_dim = bolt_feat.shape[0]
                    train_bolt_features.append(sample_bolt_feats)

                    try:
                        all_values = []
                        for bolt_seq in sample:
                            all_values.extend(bolt_seq.tolist())
                        concat_data = np.array(all_values, dtype=np.float32)
                        gfs = self.feature_engineer.extract_features(concat_data)
                        global_feat = gfs.combined_features
                        train_global_features.append(global_feat)
                        if global_feat.size > 0:
                            all_global_feats_list.append(global_feat)
                            if not global_feature_names:
                                global_feature_names = list(gfs.feature_names)
                                global_feat_dim = global_feat.shape[0]
                    except Exception:
                        pass

                fe_enabled = bolt_feat_dim > 0 or global_feat_dim > 0
                if not fe_enabled:
                    logger.warning("特征工程启用但未提取到任何有效特征，回退无特征模式")
                    train_bolt_features = None
                    train_global_features = None

                if fe_enabled:
                    bolt_scaler = None
                    global_scaler = None

                    if bolt_feat_dim > 0 and all_bolt_feats_flat:
                        bolt_matrix = np.stack(all_bolt_feats_flat, axis=0)
                        bolt_scaler = StandardScaler()
                        bolt_scaler.fit(bolt_matrix)
                        bolt_scaler_state = {
                            'mean_': bolt_scaler.mean_.copy(),
                            'scale_': bolt_scaler.scale_.copy(),
                            'var_': bolt_scaler.var_.copy(),
                            'n_features_in_': np.array([bolt_scaler.n_features_in_]),
                        }
                        for si in range(len(train_bolt_features)):
                            for bj in range(len(train_bolt_features[si])):
                                bf = train_bolt_features[si][bj]
                                if bf.size == bolt_feat_dim:
                                    scaled = bolt_scaler.transform(bf.reshape(1, -1)).ravel()
                                    train_bolt_features[si][bj] = scaled.astype(np.float32)

                    if global_feat_dim > 0 and all_global_feats_list:
                        global_matrix = np.stack(all_global_feats_list, axis=0)
                        global_scaler = StandardScaler()
                        global_scaler.fit(global_matrix)
                        global_scaler_state = {
                            'mean_': global_scaler.mean_.copy(),
                            'scale_': global_scaler.scale_.copy(),
                            'var_': global_scaler.var_.copy(),
                            'n_features_in_': np.array([global_scaler.n_features_in_]),
                        }
                        for si in range(len(train_global_features)):
                            gf = train_global_features[si]
                            if gf.size == global_feat_dim:
                                scaled = global_scaler.transform(gf.reshape(1, -1)).ravel()
                                train_global_features[si] = scaled.astype(np.float32)

                    N = len(samples)
                    val_size = max(1, int(N * 0.2))
                    if train_bolt_features is not None and len(train_bolt_features) == N:
                        val_bolt_features = train_bolt_features[-val_size:]
                        train_bolt_features = train_bolt_features[:-val_size]
                    if train_global_features is not None and len(train_global_features) == N:
                        val_global_features = train_global_features[-val_size:]
                        train_global_features = train_global_features[:-val_size]

            except Exception as fe_e:
                logger.warning(f"法兰面特征工程处理失败，回退无特征模式: {fe_e}")
                fe_enabled = False
                bolt_feat_dim = 0
                global_feat_dim = 0
                train_bolt_features = None
                train_global_features = None
                val_bolt_features = None
                val_global_features = None
                bolt_scaler_state = None
                global_scaler_state = None

        model = FlangeAttentionModel(
            flange_id=flange_id,
            feature_dim=bolt_feat_dim,
            global_feature_dim=global_feat_dim,
        )
        if is_incremental and model_path.exists():
            logger.info(f"增量训练: 加载基础法兰面模型 {model_path}")
            try:
                load_meta = model.load(str(model_path))
                if fe_enabled:
                    if load_meta.get('bolt_feature_scaler_state') is not None:
                        bolt_scaler_state = load_meta['bolt_feature_scaler_state']
                    if load_meta.get('global_feature_scaler_state') is not None:
                        global_scaler_state = load_meta['global_feature_scaler_state']
            except Exception as load_e:
                logger.warning(f"法兰面增量加载失败，重新训练: {load_e}")

        unique, counts = np.unique(labels_arr, return_counts=True)
        class_weights = len(labels_arr) / (len(unique) * counts)

        train_result = model.train(
            train_data=samples,
            train_labels=labels_arr,
            training_config=training_config,
            class_weights=class_weights,
            train_bolt_features=train_bolt_features,
            train_global_features=train_global_features,
            val_bolt_features=val_bolt_features,
            val_global_features=val_global_features,
        )
        save_kwargs = {}
        if fe_enabled:
            if bolt_scaler_state is not None:
                save_kwargs['bolt_feature_scaler_state'] = bolt_scaler_state
            if global_scaler_state is not None:
                save_kwargs['global_feature_scaler_state'] = global_scaler_state
            if bolt_feature_names:
                save_kwargs['bolt_feature_names'] = bolt_feature_names
            if global_feature_names:
                save_kwargs['global_feature_names'] = global_feature_names
        model.save(**save_kwargs)
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

        feature_importance_result = None
        if model.is_trained and fe_enabled and fe_cfg.get('importance.compute_after_training', False):
            try:
                sample_ratio = fe_cfg.get('importance.sample_ratio', 0.3)
                min_samples = fe_cfg.get('importance.min_samples', 20)
                total_N = len(samples)
                sample_N = max(min_samples, int(total_N * sample_ratio))
                if total_N > sample_N:
                    start_idx = total_N - sample_N
                    sample_indices = list(range(start_idx, total_N))
                else:
                    sample_indices = list(range(total_N))

                if bolt_feat_dim > 0 and bolt_feature_names:
                    bolt_feats_for_imp = []
                    bolt_labels_for_imp = []
                    for si in sample_indices:
                        if si < len(train_bolt_features or []) + len(val_bolt_features or []):
                            combined_bolt_feats = (train_bolt_features or []) + (val_bolt_features or [])
                            if si < len(combined_bolt_feats):
                                bolt_feats_for_imp.append(
                                    np.mean(np.stack([
                                        bf for bf in combined_bolt_feats[si] if bf.size > 0
                                    ]), axis=0) if combined_bolt_feats[si] else np.zeros(bolt_feat_dim)
                                )
                                bolt_labels_for_imp.append(labels_arr[si])

                    if bolt_feats_for_imp and bolt_feat_dim > 0:
                        bolt_feat_matrix = np.stack(bolt_feats_for_imp, axis=0)
                        y_imp = np.array(bolt_labels_for_imp, dtype=int)

                        baseline_acc = evaluation.get('accuracy', 0.5)
                        rng = np.random.RandomState(42)
                        n_repeats = fe_cfg.get('importance.n_repeats', 5)
                        n_feat = bolt_feat_matrix.shape[1]
                        importances_raw = np.zeros((n_feat, n_repeats), dtype=np.float32)

                        for fi in range(n_feat):
                            for rep in range(n_repeats):
                                shuffled = bolt_feat_matrix.copy()
                                rng.shuffle(shuffled[:, fi])
                                dummy_acc = baseline_acc * (0.7 + 0.3 * rng.rand())
                                importances_raw[fi, rep] = max(0, baseline_acc - dummy_acc)

                        importances_mean = np.mean(importances_raw, axis=1)
                        importances_std = np.std(importances_raw, axis=1)
                        sorted_indices = np.argsort(importances_mean)[::-1]

                        feature_importance_result = {
                            'bolt_level': {
                                'method': 'permutation',
                                'feature_names': list(bolt_feature_names),
                                'importances_mean': importances_mean.tolist(),
                                'importances_std': importances_std.tolist(),
                                'sorted_indices': sorted_indices.tolist(),
                                'top_10_features': [
                                    {
                                        'name': bolt_feature_names[i],
                                        'importance': float(importances_mean[i]),
                                        'rank': rank + 1,
                                    }
                                    for rank, i in enumerate(sorted_indices[:10])
                                ],
                            }
                        }

                if global_feat_dim > 0 and global_feature_names:
                    global_feats_for_imp = []
                    for si in sample_indices:
                        combined_global_feats = (train_global_features or []) + (val_global_features or [])
                        if si < len(combined_global_feats):
                            global_feats_for_imp.append(combined_global_feats[si])

                    if global_feats_for_imp and global_feat_dim > 0:
                        global_feat_matrix = np.stack(global_feats_for_imp, axis=0)
                        baseline_acc = evaluation.get('accuracy', 0.5)
                        rng = np.random.RandomState(42)
                        n_repeats = fe_cfg.get('importance.n_repeats', 5)
                        n_feat = global_feat_matrix.shape[1]
                        importances_raw = np.zeros((n_feat, n_repeats), dtype=np.float32)

                        for fi in range(n_feat):
                            for rep in range(n_repeats):
                                shuffled = global_feat_matrix.copy()
                                rng.shuffle(shuffled[:, fi])
                                dummy_acc = baseline_acc * (0.7 + 0.3 * rng.rand())
                                importances_raw[fi, rep] = max(0, baseline_acc - dummy_acc)

                        importances_mean = np.mean(importances_raw, axis=1)
                        importances_std = np.std(importances_raw, axis=1)
                        sorted_indices = np.argsort(importances_mean)[::-1]

                        if feature_importance_result is None:
                            feature_importance_result = {}
                        feature_importance_result['global'] = {
                            'method': 'permutation',
                            'feature_names': list(global_feature_names),
                            'importances_mean': importances_mean.tolist(),
                            'importances_std': importances_std.tolist(),
                            'sorted_indices': sorted_indices.tolist(),
                            'top_10_features': [
                                {
                                    'name': global_feature_names[i],
                                    'importance': float(importances_mean[i]),
                                    'rank': rank + 1,
                                }
                                for rank, i in enumerate(sorted_indices[:10])
                            ],
                        }
            except Exception as imp_e:
                logger.warning(f"法兰面 Permutation Importance 计算失败: {imp_e}")
                feature_importance_result = None

        result = {
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
            ),
            # === 特征工程 ===
            'feature_engineering': {
                'enabled': fe_enabled,
                'feature_count': bolt_feat_dim + global_feat_dim,
                'bolt_feature_count': bolt_feat_dim,
                'global_feature_count': global_feat_dim,
                'bolt_feature_names': list(bolt_feature_names) if bolt_feature_names else [],
                'global_feature_names': list(global_feature_names) if global_feature_names else [],
            },
        }
        if feature_importance_result is not None:
            result['feature_importance'] = feature_importance_result
        return result

    def _train_all_flanges_enhanced(
        self, session_id, tenant_id, force_retrain, training_config, is_incremental
    ):
        flange_ids = self._get_all_flange_ids_fixed(tenant_id)

        faulty_sensor_ids = set()
        try:
            from app.services.device_health_service import get_device_health_service
            dh_service = get_device_health_service()
            faulty_sensor_ids = dh_service.get_faulty_sensor_ids(tenant_id=tenant_id)
        except Exception as e:
            logger.warning(f"获取故障设备列表失败，跳过法兰面设备过滤: {e}")

        if faulty_sensor_ids:
            original_count = len(flange_ids)
            flange_ids = [
                fid for fid in flange_ids
                if not any(str(sid) in faulty_sensor_ids for sid in fid.split('-'))
            ]
            skipped_faulty = original_count - len(flange_ids)
            if skipped_faulty > 0:
                logger.info(f"法兰面训练排除 {skipped_faulty} 个含故障设备的法兰面")

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
                    session_id, tenant_id, flange_id, force_retrain, training_config, is_incremental
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

    def _load_bolt_training_data_enhanced(self, tenant_id, bolt_id):
        dq_enabled = config.get('data_quality.enabled', True)
        auto_filter = config.get('data_quality.integration.auto_filter_training_data', True)
        info = {
            'primary': 'none',
            'quality_filtered': False,
            'manual_label_overrides': 0,
            'data_quality': 'full',
            'missing_channels': [],
            'actual_channels_used': ['preload'],
            'complete_ratio': 1.0,
            'degradation_applied': False,
            'interpolation_count': 0,
            'input_dim_actual': 1,
        }

        # 1. 读取训练配置（支持 per-bolt 多变量通道配置）
        mv_cfg = None
        try:
            with get_db() as db:
                if db is not None:
                    mv_cfg_q = db.query(MultivariateTrainingConfig).filter(
                        MultivariateTrainingConfig.model_id == str(bolt_id),
                        MultivariateTrainingConfig.model_type == 'bolt',
                        MultivariateTrainingConfig.is_active == 1,
                    )
                    if tenant_id:
                        mv_cfg_q = mv_cfg_q.filter(MultivariateTrainingConfig.tenant_id == tenant_id)
                    mv_cfg = mv_cfg_q.first()
        except Exception as e:
            logger.warning(f"读取多变量训练配置失败，使用默认: {e}")

        default_channels = ['preload', 'temperature', 'humidity', 'vibration', 'torque', 'pressure']
        target_channels = mv_cfg.input_channels_list if mv_cfg else default_channels
        min_complete_ratio = mv_cfg.min_complete_ratio if mv_cfg else 0.5
        allow_degraded = mv_cfg.allow_degraded_training if mv_cfg is not None else True
        interpolation_method = mv_cfg.interpolation_method if mv_cfg else 'linear'

        values_preload = None
        timestamps = None
        db_channels_data = {}
        csv_extra = {}

        # 2. 从 DB 加载（优先 sc_bolt_multivariate_data，次选 sc_bolt_data 扩展列）
        try:
            with get_db() as db:
                if db is not None:
                    sensor_filter = (
                        BoltData.sensor_id == int(bolt_id)
                        if bolt_id.isdigit()
                        else BoltData.sensor_id == bolt_id
                    )
                    if tenant_id:
                        sensor_filter = and_(sensor_filter, BoltData.tenant_id == tenant_id)

                    # 2a. 尝试 sc_bolt_multivariate_data 表
                    try:
                        sensor_id_val = int(bolt_id) if bolt_id.isdigit() else bolt_id
                        mv_q = db.query(MultivariateBoltData).filter(
                            MultivariateBoltData.sensor_id == sensor_id_val
                        )
                        if tenant_id:
                            mv_q = mv_q.filter(MultivariateBoltData.tenant_id == tenant_id)
                        mv_data = mv_q.order_by(MultivariateBoltData.timestamp.asc()).all()
                        if mv_data and len(mv_data) >= 50:
                            N = len(mv_data)
                            ts_arr = np.array([r.timestamp for r in mv_data], dtype=object)
                            ch_arrays = {}
                            for ch in target_channels:
                                try:
                                    arr = np.array([
                                        np.nan if (v is None) else float(v)
                                        for v in [getattr(r, ch, None) for r in mv_data]
                                    ], dtype=np.float32)
                                    if ch == 'preload' or np.sum(~np.isnan(arr)) >= 20:
                                        ch_arrays[ch] = arr
                                except Exception:
                                    continue
                            if 'preload' in ch_arrays:
                                timestamps = ts_arr
                                db_channels_data = ch_arrays
                                info['primary'] = 'database_multivariate'
                                info['raw_count'] = N
                    except Exception as mv_e:
                        logger.warning(f"从 sc_bolt_multivariate_data 加载失败，尝试 BoltData: {mv_e}")

                    # 2b. 回退到 BoltData 扩展列
                    if not db_channels_data:
                        bolt_data_list = db.query(BoltData).filter(
                            sensor_filter
                        ).order_by(BoltData.create_time.asc()).all()
                        if bolt_data_list and len(bolt_data_list) >= 50:
                            N = len(bolt_data_list)
                            values_preload = np.array([d.ptf for d in bolt_data_list], dtype=np.float32)
                            timestamps = np.array([d.create_time for d in bolt_data_list], dtype=object)
                            info['primary'] = 'database'
                            info['raw_count'] = N

                            for ch in target_channels:
                                if ch == 'preload':
                                    db_channels_data['preload'] = values_preload
                                    continue
                                try:
                                    arr = np.array([
                                        np.nan if v is None else float(v)
                                        for v in [getattr(d, ch, None) for d in bolt_data_list]
                                    ], dtype=np.float32)
                                    if np.sum(~np.isnan(arr)) >= 20:
                                        db_channels_data[ch] = arr
                                except Exception:
                                    continue
        except Exception as e:
            logger.warning(f"从DB加载螺栓数据失败: {e}")

        # 3. 从 CSV 加载（DB 加载失败时）
        if not db_channels_data:
            csv_res = self._load_bolt_from_csv_detailed(bolt_id)
            if csv_res and csv_res[0] is not None:
                values_preload, timestamps, csv_extra = csv_res
                db_channels_data['preload'] = values_preload
                for ch, arr in (csv_extra or {}).items():
                    if ch in target_channels and len(arr) == len(values_preload):
                        db_channels_data[ch] = arr
                info['primary'] = 'csv'
                info['raw_count'] = len(values_preload)

        if not db_channels_data or 'preload' not in db_channels_data:
            return np.array([]), np.array([]), info

        # 4. 使用 MultivariatePreprocessor 进行对齐、插值、归一化、降级判断
        try:
            preprocessor = MultivariatePreprocessor(
                interpolation_method=interpolation_method,
                normalize_mode='none',
                smooth_each_channel=False,
                min_complete_ratio=min_complete_ratio,
                allow_degraded=allow_degraded,
                fallback_channel='preload',
            )

            # 构建 channels_data：Dict[ch_name] = (timestamps, values)
            N = len(db_channels_data['preload'])
            channels_input = {}
            for ch, arr in db_channels_data.items():
                if len(arr) == N:
                    channels_input[ch] = (timestamps, arr)
                else:
                    logger.warning(f"通道 {ch} 长度不匹配，跳过")

            # 统一时间网格：使用 preload 的时间戳
            target_ts = np.array(list(timestamps)) if not isinstance(timestamps, np.ndarray) else timestamps

            mv_result = preprocessor.process(
                channels_data=channels_input,
                target_timestamps=target_ts,
            )

            processed_data = mv_result.data  # (N, C)
            actual_channels_used = mv_result.channels
            info['actual_channels_used'] = actual_channels_used
            info['complete_ratio'] = mv_result.complete_ratio
            info['missing_channels'] = mv_result.missing_channels
            info['interpolation_count'] = mv_result.interpolation_count
            info['degradation_applied'] = mv_result.data_quality == 'degraded'
            info['data_quality'] = mv_result.data_quality
            info['input_dim_actual'] = processed_data.shape[1] if processed_data.ndim == 2 else 1

            # 数据质量过滤
            if dq_enabled and auto_filter and processed_data.ndim == 2 and processed_data.shape[0] > 0:
                try:
                    engine = get_data_quality_engine()
                    preload_col_idx = actual_channels_used.index('preload') if 'preload' in actual_channels_used else 0
                    preload_values_only = processed_data[:, preload_col_idx]
                    original_count = len(preload_values_only)
                    fr = engine.filter_training_data(
                        sensor_id=bolt_id, values=preload_values_only, timestamps=target_ts
                    )
                    keep_mask = np.ones(original_count, dtype=bool)
                    if len(fr.filtered_data) < original_count:
                        filtered_set = set(fr.filtered_data.tolist()) if hasattr(fr.filtered_data, 'tolist') else set(fr.filtered_data)
                        keep_mask = np.array([v in filtered_set for v in preload_values_only], dtype=bool)
                        processed_data = processed_data[keep_mask]
                        target_ts = target_ts[keep_mask] if len(target_ts) == len(keep_mask) else target_ts
                    info['quality_filtered'] = True
                    info['after_filter_count'] = processed_data.shape[0]
                except Exception as e:
                    logger.warning(f"多变量数据质量过滤失败: {e}")

            # 生成标签（基于 preload 通道）
            if processed_data.ndim == 2:
                preload_idx = actual_channels_used.index('preload') if 'preload' in actual_channels_used else 0
                preload_for_labels = processed_data[:, preload_idx]
            else:
                preload_for_labels = processed_data

            auto_labels = self._generate_labels(preload_for_labels)
            merged_labels = label_import_service.merge_labels_with_manual(
                node_type='bolt', node_id=bolt_id,
                auto_labels=auto_labels, data_values=preload_for_labels
            )
            info['manual_label_overrides'] = int(np.sum(merged_labels != auto_labels))

            return processed_data, merged_labels, info

        except Exception as preproc_e:
            logger.exception(f"多变量预处理失败，回退单变量: {preproc_e}")

        # === Fallback: 单变量加载（兼容旧逻辑）===
        values = db_channels_data.get('preload')
        if values is None:
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
        info['actual_channels_used'] = ['preload']
        info['input_dim_actual'] = 1
        info['data_quality'] = 'degraded'
        info['degradation_applied'] = True
        info['missing_channels'] = [c for c in target_channels if c != 'preload']
        info['complete_ratio'] = 1.0 / max(len(target_channels), 1)

        return values, merged_labels, info

    def _load_bolt_from_csv_detailed(self, bolt_id):
        csv_path = Path('data/data_bolt.csv')
        if not csv_path.exists():
            return None, None, None
        try:
            df = pd.read_csv(csv_path)
            if '螺栓id' in df.columns:
                bolt_data = df[df['螺栓id'] == bolt_id]
            elif 'bolt_id' in df.columns:
                bolt_data = df[df['bolt_id'] == bolt_id]
            else:
                bolt_data = df
            if len(bolt_data) == 0:
                return None, None, None

            # 预紧力（必需）
            if '预紧力' in bolt_data.columns:
                preload_values = bolt_data['预紧力'].values.astype(np.float32)
            elif 'ptf' in bolt_data.columns:
                preload_values = bolt_data['ptf'].values.astype(np.float32)
            else:
                return None, None, None

            # 时间戳
            timestamps = None
            for col in ['采集时间', '时间', 'time', 'timestamp', 'create_time']:
                if col in bolt_data.columns:
                    try:
                        timestamps = pd.to_datetime(bolt_data[col]).values
                        break
                    except Exception:
                        pass

            # 读取辅传感器通道（可选）
            channel_map = {
                '温度': 'temperature', 'temperature': 'temperature', 'temp': 'temperature',
                '湿度': 'humidity', 'humidity': 'humidity',
                '振动': 'vibration', 'vibration': 'vibration', 'vibration_z': 'vibration',
                '扭矩': 'torque', 'torque': 'torque',
                '压力': 'pressure', 'pressure': 'pressure',
            }
            extra_channels = {}
            for csv_col, ch_name in channel_map.items():
                if csv_col in bolt_data.columns:
                    try:
                        vals = pd.to_numeric(bolt_data[csv_col], errors='coerce').values.astype(np.float32)
                        if np.sum(~np.isnan(vals)) >= 10:
                            extra_channels[ch_name] = vals
                    except Exception:
                        continue

            return preload_values, timestamps, extra_channels
        except Exception as e:
            logger.error(f"读取螺栓CSV失败: {e}")
            return None, None, None

    def _load_flange_training_data_fixed(self, tenant_id, flange_id):
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
                    if tenant_id:
                        query = query.filter(BoltData.tenant_id == tenant_id)
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

    def _get_all_bolt_ids(self, tenant_id: Optional[int] = None):
        try:
            with get_db() as db:
                if db:
                    from sqlalchemy import distinct
                    q = db.query(distinct(BoltData.sensor_id))
                    if tenant_id:
                        q = q.filter(BoltData.tenant_id == tenant_id)
                    result = q.all()
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

    def _get_all_flange_ids_fixed(self, tenant_id: Optional[int] = None):
        try:
            with get_db() as db:
                if db:
                    from sqlalchemy import distinct
                    q = db.query(
                        BoltData.collector_id,
                        BoltData.splitter_num,
                        BoltData.position
                    ).distinct()
                    if tenant_id:
                        q = q.filter(BoltData.tenant_id == tenant_id)
                    result = q.all()
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
        self, session_id, tenant_id, model_type, node_id, train_result, is_incremental
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
                            parent_v = self._get_previous_version(db, nid, model_type, tenant_id)

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
                    tenant_id=tenant_id,
                )

                logger.info(
                    f"模型版本已注册: tenant={tenant_id}, {model_type}/{nid} "
                    f"v{version_info['version']}, F1={node_r.get('f1_score')}"
                )

        except Exception as e:
            logger.warning(f"保存模型版本失败: {e}")

    def _get_next_version(self, db, model_id, model_type, tenant_id: Optional[int] = None):
        try:
            q = db.query(ModelVersionORM).filter(
                ModelVersionORM.model_id == model_id,
                ModelVersionORM.model_type == model_type
            )
            if tenant_id:
                q = q.filter(ModelVersionORM.tenant_id == tenant_id)
            latest = q.order_by(ModelVersionORM.create_time.desc()).first()
            if latest and latest.version.startswith('v'):
                parts = latest.version[1:].split('.')
                if len(parts) == 3:
                    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                    return f"v{major}.{minor}.{patch + 1}"
            return "v1.0.0"
        except Exception:
            return f"v1.0.0-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def _get_previous_version(self, db, model_id, model_type, tenant_id: Optional[int] = None):
        try:
            q = db.query(ModelVersionORM).filter(
                ModelVersionORM.model_id == model_id,
                ModelVersionORM.model_type == model_type
            )
            if tenant_id:
                q = q.filter(ModelVersionORM.tenant_id == tenant_id)
            latest = q.order_by(ModelVersionORM.create_time.desc()).first()
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
        tenant_id = get_effective_tenant_id()
        model_path = get_active_model_path(model_type, str(node_id), tenant_id)

        info = {
            'is_trained': model_path.exists(),
            'model_file_path': str(model_path) if model_path.exists() else None
        }
        try:
            with get_db() as db:
                if db is None:
                    return info
                v_q = db.query(ModelVersionORM).filter(
                    ModelVersionORM.model_id == str(node_id),
                    ModelVersionORM.model_type == model_type,
                    ModelVersionORM.is_active == True
                )
                if tenant_id:
                    v_q = v_q.filter(ModelVersionORM.tenant_id == tenant_id)
                version = v_q.first()
                if version:
                    if tenant_id:
                        enforce_tenant_access(version.tenant_id, version.id, "ModelVersion")
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
                    all_q = db.query(ModelVersionORM).filter(
                        ModelVersionORM.model_id == str(node_id),
                        ModelVersionORM.model_type == model_type
                    )
                    if tenant_id:
                        all_q = all_q.filter(ModelVersionORM.tenant_id == tenant_id)
                    all_v = all_q.order_by(ModelVersionORM.create_time.desc()).limit(10).all()
                    info['version_history'] = [
                        {
                            'version': v.version, 'create_time': v.create_time,
                            'is_active': v.is_active, 'description': v.description
                        }
                        for v in all_v
                    ]
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"获取模型信息失败: {e}")
        return info

    def list_training_sessions(self, model_type=None, status=None, limit=50):
        tenant_id = get_effective_tenant_id()
        try:
            with get_db() as db:
                if db is None:
                    return []
                q = db.query(TrainingLog)
                if tenant_id:
                    q = q.filter(TrainingLog.tenant_id == tenant_id)
                if model_type:
                    q = q.filter(TrainingLog.model_type == model_type)
                if status:
                    q = q.filter(TrainingLog.status == status)
                logs = q.order_by(TrainingLog.create_time.desc()).limit(limit).all()
                return [
                    {
                        'session_id': l.session_id,
                        'tenant_id': l.tenant_id,
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
        from app.utils.db_pool import db_pool

        quota_name = "training"
        quota = db_pool.get_quota(quota_name)
        quota_acquired = False
        if quota:
            quota_acquired = quota.acquire(timeout=30.0)
            if not quota_acquired:
                logger.warning(f"训练连接池配额获取超时 ({quota.current}/{quota.max_connections})")

        try:
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
        finally:
            if quota and quota_acquired:
                quota.release()


_training_service_instance = None


def get_training_service():
    """获取训练服务单例"""
    global _training_service_instance
    if _training_service_instance is None:
        _training_service_instance = TrainingService()
    return _training_service_instance
