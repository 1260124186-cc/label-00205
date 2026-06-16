"""
Optuna 执行器模块

集成 Optuna 框架实现超参优化。
支持 TPE、Random、Grid、Bayesian Optimization 等多种优化算法。
"""

import uuid
import json
from datetime import datetime
from typing import Any, Callable, Dict, Optional, List
from loguru import logger

try:
    import optuna
    from optuna.pruners import MedianPruner, NopPruner, HyperbandPruner
    from optuna.samplers import TPESampler, RandomSampler, GridSampler, CmaEsSampler
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    logger.warning("Optuna 未安装，将无法使用 Optuna 优化框架")

from app.services.hpo.search_space import (
    SearchSpace,
    sample_from_search_space,
)
from app.services.hpo.objective import (
    ObjectiveConfig,
    HPOResult,
    evaluate_model_with_params,
)
from app.services.hpo.trial_storage import TrialStorageService
from app.utils.database import get_db, HPOStudy, HPONodeOverride


class OptunaExecutor:
    """Optuna 优化执行器"""

    def __init__(
        self,
        study_id: str,
        search_space: SearchSpace,
        objective_config: ObjectiveConfig,
        model_type: str,
        node_id: Optional[str] = None,
        node_type: Optional[str] = None,
        storage_service: Optional[TrialStorageService] = None,
        max_trials: int = 50,
        max_concurrent_trials: int = 2,
        min_trials_to_prune: int = 5,
        pruner_type: str = "median",
        optimizer: str = "tpe",
        fixed_params: Optional[Dict[str, Any]] = None,
        node_override: Optional[HPONodeOverride] = None,
        tenant_id: int = 0,
    ):
        if not OPTUNA_AVAILABLE:
            raise RuntimeError("Optuna 未安装，请先安装 optuna 包")

        self.study_id = study_id
        self.search_space = search_space
        self.objective_config = objective_config
        self.model_type = model_type
        self.node_id = node_id
        self.node_type = node_type
        self.storage_service = storage_service or TrialStorageService()
        self.max_trials = max_trials
        self.max_concurrent_trials = max_concurrent_trials
        self.min_trials_to_prune = min_trials_to_prune
        self.pruner_type = pruner_type
        self.optimizer = optimizer
        self.fixed_params = fixed_params or {}
        self.node_override = node_override
        self.tenant_id = tenant_id

        self._study: Optional[optuna.Study] = None
        self._trial_number = 0

        if node_override and node_override.fixed_params:
            try:
                override_fixed = json.loads(node_override.fixed_params)
                self.fixed_params.update(override_fixed)
            except Exception as e:
                logger.warning(f"解析节点固定参数失败: {e}")

    def _create_sampler(self) -> Any:
        """创建采样器"""
        if self.optimizer == "tpe":
            return TPESampler(seed=42)
        elif self.optimizer == "random":
            return RandomSampler(seed=42)
        elif self.optimizer == "cmaes":
            return CmaEsSampler(seed=42)
        elif self.optimizer == "grid":
            search_grid = {}
            for param in self.search_space:
                if param.choices:
                    search_grid[param.name] = param.choices
                elif param.low is not None and param.high is not None:
                    step = param.step or 1 if param.param_type == "int" else 0.1
                    if param.param_type == "int":
                        search_grid[param.name] = list(range(
                            int(param.low),
                            int(param.high) + 1,
                            int(step),
                        ))
                    else:
                        values = []
                        v = param.low
                        while v <= param.high:
                            values.append(round(v, 6))
                            v += step
                        search_grid[param.name] = values
            return GridSampler(search_grid)
        else:
            logger.warning(f"未知优化器: {self.optimizer}，使用 TPE")
            return TPESampler(seed=42)

    def _create_pruner(self) -> Any:
        """创建剪枝器"""
        if self.pruner_type == "median":
            return MedianPruner(
                n_startup_trials=self.min_trials_to_prune,
                n_warmup_steps=3,
                interval_steps=1,
            )
        elif self.pruner_type == "hyperband":
            return HyperbandPruner(
                min_resource=1,
                max_resource=self.max_trials,
                reduction_factor=3,
            )
        elif self.pruner_type == "none":
            return NopPruner()
        else:
            logger.warning(f"未知剪枝器: {self.pruner_type}，使用 MedianPruner")
            return MedianPruner(
                n_startup_trials=self.min_trials_to_prune,
                n_warmup_steps=3,
            )

    def _objective(self, trial: Any) -> float:
        """Optuna 目标函数"""
        self._trial_number += 1
        trial_id = f"{self.study_id}_trial_{self._trial_number}_{uuid.uuid4().hex[:8]}"

        logger.info(
            f"开始试验: trial_id={trial_id}, "
            f"number={self._trial_number}/{self.max_trials}"
        )

        try:
            params = sample_from_search_space(
                trial=trial,
                search_space=self.search_space,
                framework="optuna",
            )

            self.storage_service.create_trial(
                trial_id=trial_id,
                study_id=self.study_id,
                model_type=self.model_type,
                node_id=self.node_id,
                node_type=self.node_type,
                framework="optuna",
                trial_number=self._trial_number,
                params=params,
                status="running",
                tenant_id=self.tenant_id,
            )

            hpo_result = evaluate_model_with_params(
                params=params,
                model_type=self.model_type,
                node_id=self.node_id,
                objective_config=self.objective_config,
                fixed_params=self.fixed_params,
            )

            self.storage_service.complete_trial(
                trial_id=trial_id,
                hpo_result=hpo_result,
                params=params,
            )

            if hpo_result.latency_constraint_violated or hpo_result.f1_constraint_violated:
                logger.warning(
                    f"试验违反约束: trial_id={trial_id}, "
                    f"latency_violated={hpo_result.latency_constraint_violated}, "
                    f"f1_violated={hpo_result.f1_constraint_violated}"
                )

            logger.info(
                f"试验完成: trial_id={trial_id}, "
                f"objective={hpo_result.objective_value:.4f}, "
                f"f1={hpo_result.val_f1_score:.4f}"
            )

            return hpo_result.objective_value

        except optuna.TrialPruned as e:
            pruned_reason = str(e) or "被 MedianPruner 剪枝"
            logger.info(f"试验被剪枝: trial_id={trial_id}, reason={pruned_reason}")

            self.storage_service.update_trial_status(
                trial_id=trial_id,
                status="pruned",
                pruned_reason=pruned_reason,
            )
            raise

        except Exception as e:
            error_msg = str(e)
            logger.error(f"试验失败: trial_id={trial_id}, error={error_msg}")

            self.storage_service.update_trial_status(
                trial_id=trial_id,
                status="failed",
                error_message=error_msg,
            )
            raise

    def _get_or_create_study(self) -> Any:
        """获取或创建 Optuna Study"""
        if self._study is not None:
            return self._study

        study_name = f"hpo_{self.study_id}"

        sampler = self._create_sampler()
        pruner = self._create_pruner()

        self._study = optuna.create_study(
            study_name=study_name,
            direction="maximize",
            sampler=sampler,
            pruner=pruner,
            load_if_exists=True,
        )

        return self._study

    def optimize(
        self,
        callbacks: Optional[List[Callable[[Any, Any], None]]] = None,
    ) -> Dict[str, Any]:
        """
        执行超参优化

        Args:
            callbacks: 回调函数列表

        Returns:
            Dict[str, Any]: 优化结果
        """
        study = self._get_or_create_study()

        logger.info(
            f"开始 Optuna 优化: study_id={self.study_id}, "
            f"model_type={self.model_type}, "
            f"max_trials={self.max_trials}, "
            f"optimizer={self.optimizer}"
        )

        try:
            study.optimize(
                self._objective,
                n_trials=self.max_trials,
                n_jobs=self.max_concurrent_trials,
                callbacks=callbacks,
                show_progress_bar=False,
            )
        except Exception as e:
            logger.error(f"优化过程出错: {e}")

        best_trial = study.best_trial if study.trials else None

        if best_trial is None:
            return {
                "study_id": self.study_id,
                "status": "failed",
                "message": "没有成功的试验",
                "total_trials": len(study.trials),
            }

        best_params = best_trial.params
        best_value = best_trial.value

        logger.info(
            f"优化完成: study_id={self.study_id}, "
            f"best_value={best_value:.4f}, "
            f"best_params={best_params}"
        )

        return {
            "study_id": self.study_id,
            "status": "completed",
            "best_trial_id": f"{self.study_id}_trial_{best_trial.number}",
            "best_params": best_params,
            "best_value": best_value,
            "total_trials": len(study.trials),
            "completed_trials": len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]),
            "pruned_trials": len([t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED]),
            "failed_trials": len([t for t in study.trials if t.state == optuna.trial.TrialState.FAIL]),
        }

    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """获取优化历史"""
        if self._study is None:
            return []

        history = []
        for trial in self._study.trials:
            if trial.state == optuna.trial.TrialState.COMPLETE:
                history.append({
                    "trial_number": trial.number,
                    "params": trial.params,
                    "value": trial.value,
                    "datetime_start": trial.datetime_start.isoformat() if trial.datetime_start else None,
                    "datetime_complete": trial.datetime_complete.isoformat() if trial.datetime_complete else None,
                })

        return history
