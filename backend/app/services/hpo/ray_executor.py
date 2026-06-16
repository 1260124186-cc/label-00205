"""
Ray Tune 优化执行器模块

基于 Ray Tune 的分布式超参优化执行器。
作为 Optuna 的可选替代后端。
"""

import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from loguru import logger

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


class RayTuneExecutor:
    """Ray Tune 超参优化执行器"""

    def __init__(
        self,
        study_id: str,
        search_space: SearchSpace,
        objective_config: ObjectiveConfig,
        model_type: str,
        storage_service: Optional[TrialStorageService] = None,
        node_id: Optional[str] = None,
        node_type: Optional[str] = None,
        max_trials: int = 50,
        max_concurrent_trials: int = 2,
        optimizer: str = "asha",
        tenant_id: int = 0,
    ):
        self.study_id = study_id
        self.search_space = search_space
        self.objective_config = objective_config
        self.model_type = model_type
        self.node_id = node_id
        self.node_type = node_type
        self.max_trials = max_trials
        self.max_concurrent_trials = max_concurrent_trials
        self.optimizer = optimizer
        self.tenant_id = tenant_id
        self.storage_service = storage_service or TrialStorageService()

        self._ray_available = self._check_ray_available()
        self._tune_config = None
        self._scheduler = None

    def _check_ray_available(self) -> bool:
        """检查 Ray 是否可用"""
        try:
            import ray
            from ray import tune

            return True
        except ImportError:
            logger.warning("Ray Tune 不可用，将使用回退模式")
            return False

    def _build_ray_search_space(self) -> Dict[str, Any]:
        """将 SearchSpace 转换为 Ray Tune 搜索空间格式"""
        if not self._ray_available:
            return {}

        from ray import tune

        ray_space = {}

        for param_name, param in self.search_space.params.items():
            param_type = param.param_type

            if param_type == "INT":
                ray_space[param_name] = tune.randint(
                    param.low, param.high + 1
                )
            elif param_type == "FLOAT":
                ray_space[param_name] = tune.uniform(param.low, param.high)
            elif param_type == "LOG_UNIFORM":
                ray_space[param_name] = tune.loguniform(param.low, param.high)
            elif param_type == "CATEGORICAL":
                ray_space[param_name] = tune.choice(param.choices)
            elif param_type == "DISCRETE_UNIFORM":
                ray_space[param_name] = tune.quniform(
                    param.low, param.high, param.q
                )
            elif param_type == "UNIFORM":
                ray_space[param_name] = tune.uniform(param.low, param.high)

        return ray_space

    def _create_scheduler(self):
        """创建 Ray Tune 调度器"""
        if not self._ray_available:
            return None

        from ray.tune.schedulers import ASHAScheduler, HyperBandScheduler, MedianStoppingRule

        optimizer = self.optimizer.lower()

        if optimizer == "asha":
            return ASHAScheduler(
                max_t=100,
                grace_period=5,
                reduction_factor=3,
                brackets=1,
            )
        elif optimizer == "hyperband":
            return HyperBandScheduler(
                max_t=100,
                reduction_factor=3,
            )
        elif optimizer == "median":
            return MedianStoppingRule(
                min_samples_required=5,
                min_time_slice=5,
            )
        else:
            return None

    def _create_search_alg(self):
        """创建搜索算法"""
        if not self._ray_available:
            return None

        optimizer = self.optimizer.lower()

        try:
            from ray.tune.search.bayesopt import BayesOptSearch
            from ray.tune.search.optuna import OptunaSearch
            from ray.tune.search.basic_variant import BasicVariantGenerator

            if optimizer == "bayesopt":
                return BayesOptSearch(metric="objective_value", mode="max")
            elif optimizer == "optuna":
                return OptunaSearch(metric="objective_value", mode="max")
            elif optimizer == "random":
                return BasicVariantGenerator(max_concurrent=self.max_concurrent_trials)
            else:
                return BasicVariantGenerator(max_concurrent=self.max_concurrent_trials)

        except ImportError as e:
            logger.warning(f"搜索算法导入失败: {e}")
            return None

    def _ray_objective(self, config: Dict[str, Any]):
        """Ray Tune 目标函数（在远程 worker 中执行）"""
        from ray import tune

        trial_id = f"ray_{uuid.uuid4().hex[:16]}"

        self.storage_service.create_trial(
            trial_id=trial_id,
            study_id=self.study_id,
            model_type=self.model_type,
            framework="ray_tune",
            trial_number=0,
            params=config,
            node_id=self.node_id,
            node_type=self.node_type,
            status="running",
            tenant_id=self.tenant_id,
        )

        hpo_result = evaluate_model_with_params(
            params=config,
            model_type=self.model_type,
            objective_config=self.objective_config,
            node_id=self.node_id,
            node_type=self.node_type,
            trial_id=trial_id,
            framework="ray_tune",
            storage_service=self.storage_service,
        )

        self.storage_service.complete_trial(
            trial_id=trial_id,
            hpo_result=hpo_result,
            params=config,
        )

        if hpo_result.latency_constraint_violated or hpo_result.f1_constraint_violated:
            self.storage_service.update_trial_status(
                trial_id=trial_id,
                status="constraint_violated",
                error_message="违反约束条件",
            )

        tune.report(
            objective_value=hpo_result.objective_value,
            val_f1_score=hpo_result.val_f1_score,
            false_positive_rate=hpo_result.false_positive_rate,
            inference_latency_ms=hpo_result.inference_latency_ms,
        )

    def _fallback_optimize(self) -> Dict[str, Any]:
        """Ray 不可用时的回退优化（使用本地执行）"""
        logger.info(
            f"Ray 不可用，使用回退模式执行优化: study_id={self.study_id}, "
            f"max_trials={self.max_trials}"
        )

        best_value = float("-inf")
        best_params = None
        best_trial_id = None

        for i in range(self.max_trials):
            trial_id = f"fb_{uuid.uuid4().hex[:16]}"
            params = sample_from_search_space(self.search_space, framework="optuna")

            logger.info(
                f"回退试验 [{i+1}/{self.max_trials}]: trial_id={trial_id}, "
                f"params={params}"
            )

            self.storage_service.create_trial(
                trial_id=trial_id,
                study_id=self.study_id,
                model_type=self.model_type,
                framework="fallback",
                trial_number=i + 1,
                params=params,
                node_id=self.node_id,
                node_type=self.node_type,
                status="running",
                tenant_id=self.tenant_id,
            )

            hpo_result = evaluate_model_with_params(
                params=params,
                model_type=self.model_type,
                objective_config=self.objective_config,
                node_id=self.node_id,
                node_type=self.node_type,
                trial_id=trial_id,
                framework="fallback",
                storage_service=self.storage_service,
            )

            self.storage_service.complete_trial(
                trial_id=trial_id,
                hpo_result=hpo_result,
                params=params,
            )

            logger.info(
                f"试验 [{i+1}/{self.max_trials}] 完成: "
                f"objective={hpo_result.objective_value:.4f}, "
                f"f1={hpo_result.val_f1_score:.4f}, "
                f"fp_rate={hpo_result.false_positive_rate:.4f}, "
                f"latency={hpo_result.inference_latency_ms:.2f}ms"
            )

            if hpo_result.objective_value > best_value and \
               not hpo_result.latency_constraint_violated and \
               not hpo_result.f1_constraint_violated:
                best_value = hpo_result.objective_value
                best_params = params
                best_trial_id = trial_id

        return {
            "study_id": self.study_id,
            "status": "completed",
            "mode": "fallback",
            "best_params": best_params,
            "best_value": best_value,
            "best_trial_id": best_trial_id,
            "total_trials": self.max_trials,
        }

    def optimize(self) -> Dict[str, Any]:
        """执行超参优化"""
        if not self._ray_available:
            return self._fallback_optimize()

        try:
            import ray
            from ray import tune
            from ray.tune import Tuner

            logger.info(
                f"开始 Ray Tune 优化: study_id={self.study_id}, "
                f"max_trials={self.max_trials}, "
                f"max_concurrent={self.max_concurrent_trials}, "
                f"optimizer={self.optimizer}"
            )

            if not ray.is_initialized():
                ray.init(
                    ignore_reinit_error=True,
                    num_cpus=self.max_concurrent_trials * 2,
                    _temp_dir="/tmp/ray_hpo",
                )

            search_space = self._build_ray_search_space()
            scheduler = self._create_scheduler()
            search_alg = self._create_search_alg()

            tune_config = tune.TuneConfig(
                metric="objective_value",
                mode="max",
                num_samples=self.max_trials,
                scheduler=scheduler,
                search_alg=search_alg,
                max_concurrent_trials=self.max_concurrent_trials,
            )

            tuner = Tuner(
                tune.with_resources(
                    self._ray_objective,
                    {"cpu": 2},
                ),
                param_space=search_space,
                tune_config=tune_config,
            )

            results = tuner.fit()

            best_result = results.get_best_result(
                metric="objective_value",
                mode="max",
            )

            best_params = None
            best_value = float("-inf")
            best_trial_id = None

            if best_result:
                best_params = best_result.config
                best_value = best_result.metrics.get("objective_value", float("-inf"))

                for result in results:
                    if result.metrics.get("objective_value") == best_value:
                        best_trial_id = result.trial_id
                        break

            return {
                "study_id": self.study_id,
                "status": "completed",
                "mode": "ray_tune",
                "best_params": best_params,
                "best_value": best_value,
                "best_trial_id": best_trial_id,
                "total_trials": len(results),
            }

        except Exception as e:
            logger.error(f"Ray Tune 优化失败: {e}")
            return self._fallback_optimize()
