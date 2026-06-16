"""
超参优化（HPO）服务模块

提供完整的自动超参优化能力：
1. 搜索空间定义：层数、hidden size、dropout、lr、sequence_length
2. 优化目标：验证 F1 + 误报惩罚 + 推理延迟约束
3. 多框架支持：Optuna、Ray Tune
4. 试验记录持久化到 sc_hpo_trials
5. 最优配置自动写入训练任务
6. Per-node 超参支持
"""

from app.services.hpo.search_space import (
    SearchSpace,
    SearchSpaceParam,
    ParamType,
    default_bolt_search_space,
    default_flange_search_space,
    build_search_space,
)
from app.services.hpo.objective import (
    ObjectiveConfig,
    HPOResult,
    compute_objective,
    evaluate_model_with_params,
)
from app.services.hpo.trial_storage import TrialStorageService
from app.services.hpo.best_config_applier import BestConfigApplier
from app.services.hpo.hpo_service import HPOService
from app.services.hpo.optuna_executor import OptunaExecutor
from app.services.hpo.ray_executor import RayTuneExecutor

__all__ = [
    "SearchSpace",
    "SearchSpaceParam",
    "ParamType",
    "default_bolt_search_space",
    "default_flange_search_space",
    "build_search_space",
    "ObjectiveConfig",
    "HPOResult",
    "compute_objective",
    "evaluate_model_with_params",
    "TrialStorageService",
    "BestConfigApplier",
    "HPOService",
    "OptunaExecutor",
    "RayTuneExecutor",
]
