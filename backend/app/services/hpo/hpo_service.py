"""
HPO 主服务模块

整合超参优化的所有功能，提供统一的服务接口。
"""

import uuid
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

from app.services.hpo.search_space import (
    SearchSpace,
    build_search_space,
)
from app.services.hpo.objective import (
    ObjectiveConfig,
    HPOResult,
    evaluate_model_with_params,
)
from app.services.hpo.trial_storage import TrialStorageService
from app.services.hpo.best_config_applier import BestConfigApplier
from app.services.hpo.optuna_executor import OptunaExecutor
from app.utils.database import get_db, HPOStudy, HPONodeOverride, OrganizationNode


class HPOService:
    """HPO 主服务类"""

    def __init__(
        self,
        storage_service: Optional[TrialStorageService] = None,
        config_applier: Optional[BestConfigApplier] = None,
    ):
        self.storage_service = storage_service or TrialStorageService()
        self.config_applier = config_applier or BestConfigApplier(self.storage_service)
        self._active_studies: Dict[str, Any] = {}

    def create_study(
        self,
        study_name: str,
        model_type: str,
        node_id: Optional[str] = None,
        node_type: Optional[str] = None,
        custom_search_space: Optional[Dict[str, Any]] = None,
        fixed_params: Optional[Dict[str, Any]] = None,
        objective_config: Optional[Dict[str, Any]] = None,
        framework: str = "optuna",
        optimizer: str = "tpe",
        max_trials: int = 50,
        max_concurrent_trials: int = 2,
        min_trials_to_prune: int = 5,
        pruner_type: str = "median",
        per_node_hpo_enabled: bool = False,
        node_scope: str = "global",
        tenant_id: int = 0,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        创建 HPO 研究

        Args:
            study_name: 研究名称
            model_type: 模型类型 (bolt/flange)
            node_id: 节点ID
            node_type: 节点类型
            custom_search_space: 自定义搜索空间覆盖
            fixed_params: 固定参数
            objective_config: 优化目标配置
            framework: 优化框架 (optuna/ray_tune)
            optimizer: 优化算法
            max_trials: 最大试验次数
            max_concurrent_trials: 最大并发试验数
            min_trials_to_prune: 最小试验数后开启剪枝
            pruner_type: 剪枝类型
            per_node_hpo_enabled: 是否启用per-node超参
            node_scope: 节点范围
            tenant_id: 租户ID
            created_by: 创建人

        Returns:
            Dict[str, Any]: 创建结果
        """
        study_id = f"hpo_{uuid.uuid4().hex[:16]}"

        logger.info(
            f"创建 HPO 研究: study_name={study_name}, "
            f"model_type={model_type}, framework={framework}"
        )

        search_space = build_search_space(
            model_type=model_type,
            custom_params=custom_search_space,
            fixed_params=fixed_params,
        )

        obj_config = ObjectiveConfig.from_dict(objective_config or {})

        study = self.storage_service.create_study(
            study_id=study_id,
            study_name=study_name,
            model_type=model_type,
            search_space_json=search_space.to_json(),
            objective_config_json=obj_config.to_json(),
            node_id=node_id,
            node_type=node_type,
            framework=framework,
            optimizer=optimizer,
            max_trials=max_trials,
            max_concurrent_trials=max_concurrent_trials,
            f1_weight=obj_config.f1_weight,
            false_positive_penalty=obj_config.false_positive_penalty,
            latency_threshold_ms=obj_config.latency_threshold_ms,
            latency_weight=obj_config.latency_weight,
            per_node_hpo_enabled=per_node_hpo_enabled,
            node_scope=node_scope,
            tenant_id=tenant_id,
            created_by=created_by,
        )

        if not study:
            return {
                "success": False,
                "message": "创建研究失败",
            }

        return {
            "success": True,
            "message": "研究创建成功",
            "study_id": study_id,
            "study_name": study_name,
            "model_type": model_type,
            "node_id": node_id,
            "node_type": node_type,
            "framework": framework,
            "search_space": search_space.to_dict(),
            "objective_config": obj_config.to_dict(),
            "max_trials": max_trials,
            "per_node_hpo_enabled": per_node_hpo_enabled,
        }

    def start_study(
        self,
        study_id: str,
        auto_apply_best: bool = True,
    ) -> Dict[str, Any]:
        """
        开始 HPO 研究

        Args:
            study_id: 研究ID
            auto_apply_best: 是否自动应用最优配置

        Returns:
            Dict[str, Any]: 启动结果
        """
        study_data = self.storage_service.get_study(study_id)

        if not study_data:
            return {
                "success": False,
                "message": f"研究不存在: {study_id}",
            }

        if study_data["status"] == "running":
            return {
                "success": False,
                "message": "研究已在运行中",
            }

        model_type = study_data["model_type"]
        node_id = study_data["node_id"]
        node_type = study_data["node_type"]
        framework = study_data["framework"]
        optimizer = study_data["optimizer"]
        max_trials = study_data["max_trials"]
        max_concurrent_trials = study_data["max_concurrent_trials"]
        min_trials_to_prune = study_data["min_trials_to_prune"]
        pruner_type = study_data["pruner_type"]
        per_node_hpo_enabled = study_data["per_node_hpo_enabled"]

        search_space = SearchSpace.from_dict(study_data["search_space"])
        objective_config = ObjectiveConfig.from_dict(study_data["objective_config"])

        self.storage_service.update_study_status(
            study_id=study_id,
            status="running",
            start_time=datetime.now(),
        )

        logger.info(f"开始 HPO 研究: study_id={study_id}, framework={framework}")

        try:
            if per_node_hpo_enabled:
                result = self._run_per_node_optimization(
                    study_id=study_id,
                    model_type=model_type,
                    node_scope=study_data["node_scope"],
                    search_space=search_space,
                    objective_config=objective_config,
                    framework=framework,
                    optimizer=optimizer,
                    max_trials=max_trials,
                    max_concurrent_trials=max_concurrent_trials,
                    min_trials_to_prune=min_trials_to_prune,
                    pruner_type=pruner_type,
                    tenant_id=study_data.get("tenant_id", 0),
                )
            else:
                result = self._run_single_optimization(
                    study_id=study_id,
                    model_type=model_type,
                    node_id=node_id,
                    node_type=node_type,
                    search_space=search_space,
                    objective_config=objective_config,
                    framework=framework,
                    optimizer=optimizer,
                    max_trials=max_trials,
                    max_concurrent_trials=max_concurrent_trials,
                    min_trials_to_prune=min_trials_to_prune,
                    pruner_type=pruner_type,
                    tenant_id=study_data.get("tenant_id", 0),
                )

            self.storage_service.update_study_status(
                study_id=study_id,
                status=result["status"],
                best_trial_id=result.get("best_trial_id"),
                best_params=result.get("best_params"),
                best_objective_value=result.get("best_value"),
                end_time=datetime.now(),
            )

            if auto_apply_best and result["status"] == "completed":
                apply_result = self.config_applier.apply_best_config_to_training(
                    study_id=study_id,
                    model_type=model_type,
                    node_id=node_id,
                    node_type=node_type,
                )
                result["auto_apply_result"] = apply_result

            logger.info(
                f"HPO 研究完成: study_id={study_id}, "
                f"status={result['status']}, "
                f"best_value={result.get('best_value')}"
            )

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"HPO 研究失败: study_id={study_id}, error={error_msg}")

            self.storage_service.update_study_status(
                study_id=study_id,
                status="failed",
                end_time=datetime.now(),
            )

            return {
                "study_id": study_id,
                "status": "failed",
                "error": error_msg,
            }

    def _run_single_optimization(
        self,
        study_id: str,
        model_type: str,
        search_space: SearchSpace,
        objective_config: ObjectiveConfig,
        framework: str = "optuna",
        node_id: Optional[str] = None,
        node_type: Optional[str] = None,
        optimizer: str = "tpe",
        max_trials: int = 50,
        max_concurrent_trials: int = 2,
        min_trials_to_prune: int = 5,
        pruner_type: str = "median",
        tenant_id: int = 0,
    ) -> Dict[str, Any]:
        """执行单节点优化"""
        if framework == "optuna":
            executor = OptunaExecutor(
                study_id=study_id,
                search_space=search_space,
                objective_config=objective_config,
                model_type=model_type,
                node_id=node_id,
                node_type=node_type,
                storage_service=self.storage_service,
                max_trials=max_trials,
                max_concurrent_trials=max_concurrent_trials,
                min_trials_to_prune=min_trials_to_prune,
                pruner_type=pruner_type,
                optimizer=optimizer,
                tenant_id=tenant_id,
            )

            self._active_studies[study_id] = executor
            result = executor.optimize()

        elif framework == "ray_tune":
            from app.services.hpo.ray_executor import RayTuneExecutor

            executor = RayTuneExecutor(
                study_id=study_id,
                search_space=search_space,
                objective_config=objective_config,
                model_type=model_type,
                node_id=node_id,
                node_type=node_type,
                storage_service=self.storage_service,
                max_trials=max_trials,
                max_concurrent_trials=max_concurrent_trials,
                optimizer=optimizer,
                tenant_id=tenant_id,
            )

            self._active_studies[study_id] = executor
            result = executor.optimize()

        else:
            raise ValueError(f"不支持的优化框架: {framework}")

        return result

    def _run_per_node_optimization(
        self,
        study_id: str,
        model_type: str,
        node_scope: str,
        search_space: SearchSpace,
        objective_config: ObjectiveConfig,
        framework: str = "optuna",
        optimizer: str = "tpe",
        max_trials: int = 50,
        max_concurrent_trials: int = 2,
        min_trials_to_prune: int = 5,
        pruner_type: str = "median",
        tenant_id: int = 0,
    ) -> Dict[str, Any]:
        """执行 per-node 优化"""
        node_ids = self._get_nodes_for_optimization(model_type, node_scope)

        if not node_ids:
            return {
                "study_id": study_id,
                "status": "failed",
                "message": "没有找到需要优化的节点",
            }

        logger.info(
            f"开始 per-node 优化: study_id={study_id}, "
            f"node_count={len(node_ids)}, "
            f"node_scope={node_scope}"
        )

        node_results = []
        overall_best_value = float("-inf")
        overall_best_params = None
        overall_best_trial_id = None

        for node_id in node_ids:
            try:
                node_override = self._get_or_create_node_override(
                    study_id=study_id,
                    node_id=node_id,
                    node_type=model_type,
                    tenant_id=tenant_id,
                )

                node_search_space = self._merge_node_search_space(
                    base_search_space=search_space,
                    node_override=node_override,
                )

                node_fixed_params = None
                if node_override and node_override.fixed_params:
                    try:
                        node_fixed_params = json.loads(node_override.fixed_params)
                    except Exception:
                        pass

                logger.info(
                    f"优化节点: study_id={study_id}, node_id={node_id}, "
                    f"params_count={len(node_search_space)}"
                )

                result = self._run_single_optimization(
                    study_id=f"{study_id}_node_{node_id}",
                    model_type=model_type,
                    node_id=node_id,
                    node_type=model_type,
                    search_space=node_search_space,
                    objective_config=objective_config,
                    framework=framework,
                    optimizer=optimizer,
                    max_trials=max_trials,
                    max_concurrent_trials=1,
                    min_trials_to_prune=min_trials_to_prune,
                    pruner_type=pruner_type,
                    tenant_id=tenant_id,
                )

                if result.get("status") == "completed":
                    node_results.append({
                        "node_id": node_id,
                        "success": True,
                        "best_value": result.get("best_value"),
                        "best_params": result.get("best_params"),
                        "best_trial_id": result.get("best_trial_id"),
                    })

                    self.storage_service.update_node_override_best(
                        study_id=study_id,
                        node_id=node_id,
                        best_params=result.get("best_params", {}),
                        best_trial_id=result.get("best_trial_id", ""),
                        best_objective_value=result.get("best_value", 0.0),
                    )

                    if result.get("best_value", float("-inf")) > overall_best_value:
                        overall_best_value = result.get("best_value")
                        overall_best_params = result.get("best_params")
                        overall_best_trial_id = result.get("best_trial_id")
                else:
                    node_results.append({
                        "node_id": node_id,
                        "success": False,
                        "error": result.get("message", result.get("error")),
                    })

            except Exception as e:
                logger.error(f"节点优化失败: node_id={node_id}, error={e}")
                node_results.append({
                    "node_id": node_id,
                    "success": False,
                    "error": str(e),
                })

        success_count = sum(1 for r in node_results if r["success"])

        return {
            "study_id": study_id,
            "status": "completed" if success_count > 0 else "failed",
            "node_scope": node_scope,
            "total_nodes": len(node_ids),
            "success_nodes": success_count,
            "failed_nodes": len(node_ids) - success_count,
            "node_results": node_results,
            "best_value": overall_best_value,
            "best_params": overall_best_params,
            "best_trial_id": overall_best_trial_id,
        }

    def _get_nodes_for_optimization(
        self,
        model_type: str,
        node_scope: str,
    ) -> List[str]:
        """获取需要优化的节点列表"""
        try:
            with get_db() as db:
                if db is None:
                    return []

                if node_scope == "global":
                    return []

                node_type_filter = "bolt" if model_type == "bolt" else "flange"

                query = db.query(OrganizationNode).filter(
                    OrganizationNode.node_type == node_type_filter,
                    OrganizationNode.status == "active",
                )

                nodes = query.all()
                return [str(n.node_code or n.id) for n in nodes]

        except Exception as e:
            logger.error(f"获取优化节点列表失败: {e}")
            return []

    def _get_or_create_node_override(
        self,
        study_id: str,
        node_id: str,
        node_type: str,
        tenant_id: int = 0,
    ) -> Optional[HPONodeOverride]:
        """获取或创建节点超参覆盖"""
        override = self.storage_service.get_node_override(study_id, node_id)

        if override:
            try:
                with get_db() as db:
                    if db is None:
                        return None
                    return db.query(HPONodeOverride).filter(
                        HPONodeOverride.study_id == study_id,
                        HPONodeOverride.node_id == node_id,
                    ).first()
            except Exception:
                return None

        return self.storage_service.create_node_override(
            study_id=study_id,
            node_id=node_id,
            node_type=node_type,
            tenant_id=tenant_id,
        )

    def _merge_node_search_space(
        self,
        base_search_space: SearchSpace,
        node_override: Optional[HPONodeOverride],
    ) -> SearchSpace:
        """合并节点搜索空间覆盖"""
        if not node_override or not node_override.search_space_override:
            return base_search_space

        try:
            override_dict = json.loads(node_override.search_space_override)
            return build_search_space(
                model_type="bolt",
                custom_params=override_dict,
            )
        except Exception as e:
            logger.warning(f"合并节点搜索空间失败: {e}")
            return base_search_space

    def get_study_status(self, study_id: str) -> Dict[str, Any]:
        """获取研究状态"""
        study_data = self.storage_service.get_study(study_id)

        if not study_data:
            return {
                "success": False,
                "message": f"研究不存在: {study_id}",
            }

        trials = self.storage_service.list_trials(
            study_id=study_id,
            limit=1000,
        )

        status_counts = {}
        for trial in trials:
            status = trial["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

        best_trial = self.storage_service.get_best_trial(study_id)

        return {
            "success": True,
            "study": study_data,
            "trials": {
                "total": len(trials),
                "status_counts": status_counts,
                "latest_10": trials[:10],
            },
            "best_trial": best_trial,
        }

    def list_studies(
        self,
        model_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """列出研究"""
        studies = self.storage_service.list_studies(
            model_type=model_type,
            status=status,
            limit=limit,
            offset=offset,
        )

        return {
            "success": True,
            "total": len(studies),
            "studies": studies,
        }

    def list_trials(
        self,
        study_id: Optional[str] = None,
        model_type: Optional[str] = None,
        node_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """列出试验"""
        trials = self.storage_service.list_trials(
            study_id=study_id,
            model_type=model_type,
            node_id=node_id,
            status=status,
            limit=limit,
            offset=offset,
        )

        return {
            "success": True,
            "total": len(trials),
            "trials": trials,
        }

    def apply_best_config(
        self,
        study_id: str,
        node_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """应用最优配置"""
        study_data = self.storage_service.get_study(study_id)

        if not study_data:
            return {
                "success": False,
                "message": f"研究不存在: {study_id}",
            }

        model_type = study_data["model_type"]
        node_type = study_data["node_type"]

        if node_ids:
            return self.config_applier.apply_per_node_configs(
                study_id=study_id,
                model_type=model_type,
                node_ids=node_ids,
            )

        return self.config_applier.apply_best_config_to_training(
            study_id=study_id,
            model_type=model_type,
            node_id=study_data["node_id"],
            node_type=node_type,
        )

    def compare_configs(
        self,
        study_id: str,
    ) -> Dict[str, Any]:
        """比较最优配置与当前配置"""
        study_data = self.storage_service.get_study(study_id)

        if not study_data:
            return {
                "success": False,
                "message": f"研究不存在: {study_id}",
            }

        return self.config_applier.compare_with_current(
            study_id=study_id,
            model_type=study_data["model_type"],
            node_id=study_data["node_id"],
        )

    def set_node_override(
        self,
        study_id: str,
        node_id: str,
        node_type: str,
        search_space_override: Optional[Dict[str, Any]] = None,
        fixed_params: Optional[Dict[str, Any]] = None,
        tenant_id: int = 0,
    ) -> Dict[str, Any]:
        """设置节点超参覆盖"""
        override = self.storage_service.get_node_override(study_id, node_id)

        if override:
            try:
                with get_db() as db:
                    if db is None:
                        return {"success": False, "message": "数据库不可用"}

                    existing = db.query(HPONodeOverride).filter(
                        HPONodeOverride.study_id == study_id,
                        HPONodeOverride.node_id == node_id,
                    ).first()

                    if existing:
                        if search_space_override is not None:
                            existing.search_space_override = json.dumps(
                                search_space_override, ensure_ascii=False
                            )
                        if fixed_params is not None:
                            existing.fixed_params = json.dumps(
                                fixed_params, ensure_ascii=False
                            )
                        existing.update_time = datetime.now()
                        return {"success": True, "message": "节点覆盖已更新"}
            except Exception as e:
                logger.error(f"更新节点覆盖失败: {e}")
                return {"success": False, "message": str(e)}

        created = self.storage_service.create_node_override(
            study_id=study_id,
            node_id=node_id,
            node_type=node_type,
            search_space_override=search_space_override,
            fixed_params=fixed_params,
            tenant_id=tenant_id,
        )

        if created:
            return {"success": True, "message": "节点覆盖已创建"}

        return {"success": False, "message": "创建节点覆盖失败"}
