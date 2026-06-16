"""
最优配置自动应用模块

将 HPO 找到的最优超参自动写入训练任务配置，
支持 per-node 超参配置。
"""

import json
from typing import Any, Dict, Optional
from datetime import datetime
from loguru import logger

from app.utils.database import get_db, MultivariateTrainingConfig
from app.services.hpo.trial_storage import TrialStorageService
from app.utils.config import config


class BestConfigApplier:
    """最优配置自动应用器"""

    def __init__(
        self,
        storage_service: Optional[TrialStorageService] = None,
    ):
        self.storage_service = storage_service or TrialStorageService()

    def apply_best_config_to_training(
        self,
        study_id: str,
        model_type: str,
        node_id: Optional[str] = None,
        node_type: Optional[str] = None,
        auto_save: bool = True,
    ) -> Dict[str, Any]:
        """
        将最优配置应用到训练任务

        Args:
            study_id: 研究ID
            model_type: 模型类型
            node_id: 节点ID（None表示全局）
            node_type: 节点类型
            auto_save: 是否自动保存到数据库

        Returns:
            Dict[str, Any]: 应用结果
        """
        logger.info(
            f"开始应用最优配置: study_id={study_id}, "
            f"model_type={model_type}, node_id={node_id or 'global'}"
        )

        best_trial = self.storage_service.get_best_trial(study_id)

        if not best_trial:
            return {
                "success": False,
                "message": "未找到最佳试验",
            }

        best_params = best_trial.get("params", {})
        objective_value = best_trial.get("objective_value", 0.0)
        trial_id = best_trial.get("trial_id")

        training_config = self._convert_params_to_training_config(
            best_params,
            model_type,
        )

        training_config["hpo_optimized"] = True
        training_config["hpo_study_id"] = study_id
        training_config["hpo_trial_id"] = trial_id
        training_config["hpo_objective_value"] = objective_value
        training_config["hpo_search_space"] = {
            "val_f1_score": best_trial.get("val_f1_score"),
            "false_positive_rate": best_trial.get("false_positive_rate"),
            "inference_latency_ms": best_trial.get("inference_latency_ms"),
        }

        if auto_save:
            saved = self._save_training_config(
                model_type=model_type,
                node_id=node_id,
                node_type=node_type,
                config=training_config,
            )
        else:
            saved = True

        if saved and node_id:
            self.storage_service.mark_node_override_applied(study_id, node_id)

        logger.info(
            f"最优配置已应用: model_type={model_type}, "
            f"node_id={node_id or 'global'}, "
            f"objective={objective_value:.4f}, "
            f"saved={saved}"
        )

        return {
            "success": True,
            "message": "最优配置已应用",
            "model_type": model_type,
            "node_id": node_id,
            "node_type": node_type,
            "best_trial_id": trial_id,
            "best_params": best_params,
            "objective_value": objective_value,
            "training_config": training_config,
            "saved_to_db": saved,
        }

    def _convert_params_to_training_config(
        self,
        params: Dict[str, Any],
        model_type: str,
    ) -> Dict[str, Any]:
        """
        将 HPO 超参转换为训练配置格式

        Args:
            params: HPO 超参
            model_type: 模型类型

        Returns:
            Dict[str, Any]: 训练配置
        """
        num_layers = params.get("num_layers", 2)
        hidden_size = params.get("hidden_size", 128)
        dropout_rate = params.get("dropout_rate", 0.2)
        learning_rate = params.get("learning_rate", 0.001)
        sequence_length = params.get("sequence_length", 100)

        base_config = {
            "learning_rate": learning_rate,
            "sequence_length": sequence_length,
            "dropout_rate": dropout_rate,
            "epochs": 50,
            "batch_size": 32,
            "early_stopping": {
                "enabled": True,
                "patience": 8,
                "min_delta": 0.001,
                "mode": "max",
            },
            "hpo_params": {
                "num_layers": num_layers,
                "hidden_size": hidden_size,
                "dropout_rate": dropout_rate,
                "learning_rate": learning_rate,
                "sequence_length": sequence_length,
            },
        }

        if model_type == "bolt":
            lstm_units = [hidden_size] * num_layers
            base_config.update({
                "lstm_units_1": lstm_units[0] if num_layers >= 1 else 64,
                "lstm_units_2": lstm_units[1] if num_layers >= 2 else 32,
                "dense_units": max(16, hidden_size // 4),
                "num_layers": num_layers,
            })

        elif model_type == "flange":
            base_config.update({
                "lstm_units": hidden_size,
                "num_attention_layers": num_layers,
                "attention_heads": max(2, hidden_size // 32),
            })

        return base_config

    def _save_training_config(
        self,
        model_type: str,
        config: Dict[str, Any],
        node_id: Optional[str] = None,
        node_type: Optional[str] = None,
    ) -> bool:
        """
        保存训练配置到数据库

        Args:
            model_type: 模型类型
            config: 配置字典
            node_id: 节点ID
            node_type: 节点类型

        Returns:
            bool: 是否成功
        """
        try:
            with get_db() as db:
                if db is None:
                    logger.warning("数据库不可用，无法保存训练配置")
                    return False

                existing = db.query(MultivariateTrainingConfig).filter(
                    MultivariateTrainingConfig.model_type == model_type,
                    (MultivariateTrainingConfig.node_id == node_id) if node_id else (MultivariateTrainingConfig.node_id.is_(None)),
                ).first()

                config_json = json.dumps(config, ensure_ascii=False)

                if existing:
                    existing.config = config_json
                    existing.is_active = True
                    existing.update_time = datetime.now()
                    logger.info(f"训练配置已更新: model_type={model_type}, node_id={node_id or 'global'}")
                else:
                    new_config = MultivariateTrainingConfig(
                        model_type=model_type,
                        node_id=node_id,
                        node_type=node_type,
                        config=config_json,
                        is_active=True,
                        description=f"HPO 优化配置 - {datetime.now().strftime('%Y%m%d%H%M%S')}",
                        create_time=datetime.now(),
                        update_time=datetime.now(),
                    )
                    db.add(new_config)
                    logger.info(f"训练配置已创建: model_type={model_type}, node_id={node_id or 'global'}")

                return True

        except Exception as e:
            logger.error(f"保存训练配置失败: {e}")
            return False

    def get_current_training_config(
        self,
        model_type: str,
        node_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        获取当前的训练配置

        Args:
            model_type: 模型类型
            node_id: 节点ID

        Returns:
            Optional[Dict[str, Any]]: 训练配置
        """
        try:
            with get_db() as db:
                if db is None:
                    return None

                query = db.query(MultivariateTrainingConfig).filter(
                    MultivariateTrainingConfig.model_type == model_type,
                    MultivariateTrainingConfig.is_active == True,
                )

                if node_id:
                    query = query.filter(MultivariateTrainingConfig.node_id == node_id)
                else:
                    query = query.filter(MultivariateTrainingConfig.node_id.is_(None))

                config_record = query.first()

                if not config_record:
                    return None

                return json.loads(config_record.config)

        except Exception as e:
            logger.error(f"获取训练配置失败: {e}")
            return None

    def compare_with_current(
        self,
        study_id: str,
        model_type: str,
        node_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        比较最优配置与当前配置

        Args:
            study_id: 研究ID
            model_type: 模型类型
            node_id: 节点ID

        Returns:
            Dict[str, Any]: 比较结果
        """
        best_trial = self.storage_service.get_best_trial(study_id)
        current_config = self.get_current_training_config(model_type, node_id)

        if not best_trial:
            return {
                "success": False,
                "message": "未找到最佳试验",
            }

        best_params = best_trial.get("params", {})
        best_metrics = {
            "val_f1_score": best_trial.get("val_f1_score"),
            "false_positive_rate": best_trial.get("false_positive_rate"),
            "inference_latency_ms": best_trial.get("inference_latency_ms"),
            "objective_value": best_trial.get("objective_value"),
        }

        current_hpo_params = None
        current_metrics = None
        if current_config and current_config.get("hpo_params"):
            current_hpo_params = current_config["hpo_params"]
            current_metrics = current_config.get("hpo_search_space")

        param_changes = {}
        for param_name in ["num_layers", "hidden_size", "dropout_rate", "learning_rate", "sequence_length"]:
            best_val = best_params.get(param_name)
            current_val = current_hpo_params.get(param_name) if current_hpo_params else None

            if best_val != current_val:
                param_changes[param_name] = {
                    "from": current_val,
                    "to": best_val,
                    "change": (best_val - current_val) if current_val is not None and isinstance(best_val, (int, float)) else None,
                }

        metric_changes = {}
        if best_metrics and current_metrics:
            for metric_name in ["val_f1_score", "false_positive_rate", "inference_latency_ms"]:
                best_val = best_metrics.get(metric_name)
                current_val = current_metrics.get(metric_name)

                if best_val is not None and current_val is not None:
                    metric_changes[metric_name] = {
                        "from": current_val,
                        "to": best_val,
                        "change": best_val - current_val,
                        "change_percent": ((best_val - current_val) / current_val * 100) if current_val != 0 else None,
                    }

        return {
            "success": True,
            "best_params": best_params,
            "best_metrics": best_metrics,
            "current_params": current_hpo_params,
            "current_metrics": current_metrics,
            "param_changes": param_changes,
            "metric_changes": metric_changes,
            "has_changes": len(param_changes) > 0,
            "improvement": best_metrics.get("objective_value", 0) - (current_metrics.get("objective_value", 0) if current_metrics else 0),
        }

    def apply_per_node_configs(
        self,
        study_id: str,
        model_type: str,
        node_ids: list,
    ) -> Dict[str, Any]:
        """
        批量应用 per-node 最优配置

        Args:
            study_id: 研究ID
            model_type: 模型类型
            node_ids: 节点ID列表

        Returns:
            Dict[str, Any]: 应用结果
        """
        results = {
            "success": [],
            "failed": [],
            "total": len(node_ids),
        }

        for node_id in node_ids:
            try:
                result = self.apply_best_config_to_training(
                    study_id=study_id,
                    model_type=model_type,
                    node_id=node_id,
                    node_type=model_type,
                )
                if result.get("success"):
                    results["success"].append(node_id)
                else:
                    results["failed"].append({
                        "node_id": node_id,
                        "error": result.get("message"),
                    })
            except Exception as e:
                results["failed"].append({
                    "node_id": node_id,
                    "error": str(e),
                })

        results["success_count"] = len(results["success"])
        results["failed_count"] = len(results["failed"])

        return results
