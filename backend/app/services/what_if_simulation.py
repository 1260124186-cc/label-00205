"""
What-if 情景仿真引擎

基于历史HI序列（或预紧力序列），在不同情景假设下模拟未来劣化轨迹，
计算首次触阈时间、风险等级时间线、建议干预时间点，支持批量情景对比。

与RUL模块输出口径对齐：
- HI 0-100 健康度指数
- 劣化模型: linear/exponential/polynomial
- 阈值: failure=30, warning=50（默认）
- RUL天数、置信度
- 风险等级: low/medium/high/critical

复检排程模块输出口径对齐：
- 风险评分 0-100
- 状态: normal/warning/critical
- 推荐措施列表

主要类:
- WhatIfSimulator: 仿真引擎主类
    - run_simulation: 执行批量情景仿真
"""

import numpy as np
import json
import uuid
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from app.utils.config import config
from app.utils.database import get_db, BoltHealthHistory, FlangeHealthHistory


class DegradationModelType(Enum):
    """劣化模型类型（与health_service一致）"""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    POLYNOMIAL = "polynomial"


class HealthLevel(Enum):
    """健康等级（与health_service一致）"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class RiskLevel(Enum):
    """风险等级（与risk_model一致：中文，低/中/高）"""
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"


class RiskStatus(Enum):
    """风险状态（与复检排程模块一致：英文，normal/warning/critical）"""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class FittedModel:
    """拟合后的劣化模型"""
    model_type: str
    params: Dict[str, float]
    r_squared: Optional[float]
    residuals_std: float


@dataclass
class ParsedHistory:
    """解析后的历史数据"""
    dates: List[datetime]
    day_offsets: np.ndarray
    hi_values: np.ndarray
    base_date: datetime
    current_hi: float


class WhatIfSimulator:
    """
    What-if 情景仿真引擎

    核心算法流程:
    1. 解析历史序列 → 拟合劣化模型
    2. 对每个情景:
       a. 应用斜率调整 (slope_adjustment)
       b. 叠加阶跃变化 (step_changes)
       c. 注入噪声 (noise_level)
       d. 应用温度/湿度/振动场景修正
       e. 应用维护策略（正常/延迟）
    3. 逐日生成模拟轨迹
    4. 计算首次触阈
    5. 生成风险时间线
    6. 推荐干预点
    7. 批量情景时生成跨情景对比
    """

    TEMP_ACCEL_FACTOR = 0.002
    TEMP_BASELINE = 25.0
    HUMIDITY_ACCEL_FACTOR = 0.001
    HUMIDITY_BASELINE = 50.0
    VIBRATION_ACCEL_FACTOR = 0.003

    def __init__(self):
        logger.info("What-if 情景仿真引擎初始化完成")

    # ==================== 公共入口 ====================

    def run_simulation(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行 What-if 情景仿真"""
        thresholds_cfg = request_data.get("thresholds") or {}
        thresholds = {
            "failure_threshold": float(thresholds_cfg.get("failure_threshold", 30.0)),
            "warning_threshold": float(thresholds_cfg.get("warning_threshold", 50.0)),
            "intervention_threshold": float(thresholds_cfg.get("intervention_threshold", 60.0)),
            "excellent_threshold": float(thresholds_cfg.get("excellent_threshold", 90.0)),
            "good_threshold": float(thresholds_cfg.get("good_threshold", 70.0)),
            "fair_threshold": float(thresholds_cfg.get("fair_threshold", 50.0)),
            "poor_threshold": float(thresholds_cfg.get("poor_threshold", 30.0)),
        }

        parsed_history, data_quality_note = self._prepare_history(
            node_id=request_data["node_id"],
            node_type=request_data["node_type"],
            history_sequence=request_data["history_sequence"],
            history_type=request_data.get("history_type", "hi"),
            nominal_preload=request_data.get("nominal_preload", 600.0),
            use_db_history=request_data.get("use_db_history", False),
            use_history_days=request_data.get("use_history_days", 90),
        )

        fitted_model = self._select_and_fit_model(
            parsed_history=parsed_history,
            preferred_model=request_data.get("degradation_model"),
        )

        current_hi = parsed_history.current_hi
        current_hi_level = self._hi_to_level(current_hi, thresholds)
        current_risk_score = self._hi_to_risk_score(current_hi, thresholds)
        current_risk_level = self._risk_score_to_level(current_risk_score)
        current_risk_score_100 = self._risk_score_10_to_100(current_risk_score)
        current_risk_status = self._risk_level_to_status(current_risk_level)

        scenarios_request = request_data["scenarios"]
        scenario_results = []
        baseline_scenario_id = None

        for idx, scen_req in enumerate(scenarios_request):
            scen_id = scen_req.get("scenario_id") or f"scenario_{idx + 1}"
            scen_name = scen_req.get("scenario_name") or f"情景{idx + 1}"
            hypothesis = scen_req.get("hypothesis") or {}
            forecast_days = int(scen_req.get("forecast_days", 180))
            seed = int(scen_req.get("seed", 42))

            if idx == 0:
                baseline_scenario_id = scen_id

            scen_result = self._simulate_single_scenario(
                scen_id=scen_id,
                scen_name=scen_name,
                hypothesis=hypothesis,
                forecast_days=forecast_days,
                seed=seed,
                parsed_history=parsed_history,
                fitted_model=fitted_model,
                thresholds=thresholds,
                working_condition=request_data.get("working_condition"),
            )
            scenario_results.append(scen_result)

        comparison = None
        if len(scenario_results) >= 2:
            comparison = self._generate_scenario_comparison(
                scenario_results=scenario_results,
                baseline_scenario_id=baseline_scenario_id,
                thresholds=thresholds,
            )

        response = {
            "node_id": request_data["node_id"],
            "node_type": request_data["node_type"],
            "simulation_time": datetime.now(),
            "base_date": parsed_history.base_date,
            "current_hi": round(float(current_hi), 2),
            "current_hi_level": current_hi_level,
            "current_risk_level": current_risk_level,
            "current_risk_score": round(current_risk_score, 2),
            "current_risk_status": current_risk_status,
            "current_risk_score_100": round(current_risk_score_100, 2),
            "thresholds": thresholds,
            "scenarios": scenario_results,
            "comparison": comparison,
            "data_quality_note": data_quality_note,
        }

        return response

    # ==================== 历史数据准备 ====================

    def _prepare_history(
        self,
        node_id: str,
        node_type: str,
        history_sequence: List[List[Any]],
        history_type: str,
        nominal_preload: float,
        use_db_history: bool,
        use_history_days: int,
    ) -> Tuple[ParsedHistory, Optional[str]]:
        """准备历史数据"""
        data_quality_note = None

        req_dates = []
        req_values = []
        for item in history_sequence:
            if len(item) < 2:
                continue
            ts_raw, val_raw = item[0], item[1]
            try:
                if isinstance(ts_raw, str):
                    dt = self._parse_timestamp(ts_raw)
                elif isinstance(ts_raw, (int, float)):
                    dt = datetime.fromtimestamp(float(ts_raw))
                else:
                    dt = ts_raw
            except Exception:
                continue
            try:
                val = float(val_raw)
            except (ValueError, TypeError):
                continue
            req_dates.append(dt)
            req_values.append(val)

        db_dates = []
        db_values = []
        if use_db_history:
            db_dates, db_values = self._load_db_history(node_id, node_type, use_history_days)

        all_dates = db_dates + req_dates
        all_values = db_values + req_values

        if not all_dates:
            raise ValueError("历史数据为空或解析失败，请提供有效历史序列")

        sorted_pairs = sorted(zip(all_dates, all_values), key=lambda x: x[0])
        all_dates_sorted = [p[0] for p in sorted_pairs]
        all_values_sorted = np.array([p[1] for p in sorted_pairs], dtype=np.float64)

        if history_type == "preload":
            hi_values = self._preload_to_hi(all_values_sorted, nominal_preload)
            if len(hi_values) == 0:
                raise ValueError("预紧力转HI失败")
        else:
            hi_values = np.clip(all_values_sorted, 0.0, 100.0)

        base_date = all_dates_sorted[-1]
        day_offsets = np.array([
            (d - all_dates_sorted[0]).total_seconds() / 86400.0
            for d in all_dates_sorted
        ])

        if len(hi_values) < 5:
            data_quality_note = (
                f"历史数据点较少（仅{len(hi_values)}个点），"
                f"建议提供更多历史数据以提高仿真准确性"
            )

        parsed = ParsedHistory(
            dates=all_dates_sorted,
            day_offsets=day_offsets,
            hi_values=hi_values,
            base_date=base_date,
            current_hi=float(hi_values[-1]),
        )

        return parsed, data_quality_note

    def _load_db_history(
        self,
        node_id: str,
        node_type: str,
        use_days: int,
    ) -> Tuple[List[datetime], List[float]]:
        """从数据库加载历史HI数据"""
        dates = []
        values = []
        try:
            with get_db() as db:
                if db is None:
                    return dates, values
                start_time = datetime.now() - timedelta(days=use_days)
                if node_type == "bolt":
                    records = db.query(BoltHealthHistory).filter(
                        BoltHealthHistory.bolt_id == str(node_id),
                        BoltHealthHistory.create_time >= start_time,
                    ).order_by(BoltHealthHistory.create_time.asc()).all()
                else:
                    records = db.query(FlangeHealthHistory).filter(
                        FlangeHealthHistory.flange_id == str(node_id),
                        FlangeHealthHistory.create_time >= start_time,
                    ).order_by(FlangeHealthHistory.create_time.asc()).all()
                for rec in records:
                    dates.append(rec.create_time)
                    values.append(float(rec.hi_score))
        except Exception as e:
            logger.warning(f"加载数据库历史HI失败: {e}")
        return dates, values

    # ==================== 劣化模型拟合与选择 ====================

    def _select_and_fit_model(
        self,
        parsed_history: ParsedHistory,
        preferred_model: Optional[str],
    ) -> FittedModel:
        """选择并拟合劣化模型"""
        x = parsed_history.day_offsets
        y = parsed_history.hi_values

        if len(x) < 3:
            slope, intercept = np.polyfit(x, y, 1)
            return FittedModel(
                model_type=DegradationModelType.LINEAR.value,
                params={"slope": float(slope), "intercept": float(intercept)},
                r_squared=None,
                residuals_std=5.0,
            )

        valid_model_types = {m.value for m in DegradationModelType}
        if preferred_model and preferred_model.lower() in valid_model_types:
            model_type = preferred_model.lower()
            params, _, residuals_std, r2 = self._fit_specific_model(x, y, model_type)
            return FittedModel(
                model_type=model_type,
                params=params,
                r_squared=r2,
                residuals_std=residuals_std,
            )

        best_model = None
        best_r2 = -np.inf
        best_params = None
        best_residuals_std = 5.0

        for mt in DegradationModelType:
            try:
                params, _, residuals_std, r2 = self._fit_specific_model(x, y, mt.value)
                if r2 is not None and r2 > best_r2:
                    best_r2 = r2
                    best_model = mt.value
                    best_params = params
                    best_residuals_std = residuals_std
            except Exception as e:
                logger.debug(f"拟合{mt.value}失败: {e}")
                continue

        if best_model is None:
            slope, intercept = np.polyfit(x, y, 1)
            best_model = DegradationModelType.LINEAR.value
            best_params = {"slope": float(slope), "intercept": float(intercept)}
            best_r2 = None
            best_residuals_std = 5.0

        return FittedModel(
            model_type=best_model,
            params=best_params,
            r_squared=best_r2,
            residuals_std=best_residuals_std,
        )

    def _fit_specific_model(
        self,
        x: np.ndarray,
        y: np.ndarray,
        model_type: str,
    ) -> Tuple[Dict[str, float], np.ndarray, float, Optional[float]]:
        """拟合指定类型的模型"""
        x_arr = np.array(x, dtype=np.float64)
        y_arr = np.array(y, dtype=np.float64)

        if model_type == DegradationModelType.LINEAR.value:
            slope, intercept = np.polyfit(x_arr, y_arr, 1)
            params = {"slope": float(slope), "intercept": float(intercept)}
            fitted = slope * x_arr + intercept
        elif model_type == DegradationModelType.EXPONENTIAL.value:
            y_clipped = np.clip(y_arr, 1.0, None)
            y_log = np.log(y_clipped)
            slope_log, intercept_log = np.polyfit(x_arr, y_log, 1)
            a = float(np.exp(intercept_log))
            b = float(slope_log)
            params = {"a": a, "b": b}
            fitted = a * np.exp(b * x_arr)
        elif model_type == DegradationModelType.POLYNOMIAL.value:
            coeffs = np.polyfit(x_arr, y_arr, 2)
            params = {
                "a": float(coeffs[0]),
                "b": float(coeffs[1]),
                "c": float(coeffs[2]),
            }
            fitted = (
                params["a"] * x_arr ** 2
                + params["b"] * x_arr
                + params["c"]
            )
        else:
            raise ValueError(f"未知模型类型: {model_type}")

        residuals = y_arr - fitted
        residuals_std = float(np.std(residuals)) if len(residuals) > 1 else 5.0
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((y_arr - np.mean(y_arr)) ** 2)
        r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else None

        return params, fitted, residuals_std, r2

    def _predict_model(self, model: FittedModel, x_values: np.ndarray) -> np.ndarray:
        """使用拟合模型预测HI值"""
        x = np.array(x_values, dtype=np.float64)
        if model.model_type == DegradationModelType.LINEAR.value:
            return model.params["slope"] * x + model.params["intercept"]
        elif model.model_type == DegradationModelType.EXPONENTIAL.value:
            return model.params["a"] * np.exp(model.params["b"] * x)
        elif model.model_type == DegradationModelType.POLYNOMIAL.value:
            return (
                model.params["a"] * x ** 2
                + model.params["b"] * x
                + model.params["c"]
            )
        else:
            raise ValueError(f"未知模型类型: {model.model_type}")

    # ==================== 单情景仿真 ====================

    def _simulate_single_scenario(
        self,
        scen_id: str,
        scen_name: str,
        hypothesis: Dict[str, Any],
        forecast_days: int,
        seed: int,
        parsed_history: ParsedHistory,
        fitted_model: FittedModel,
        thresholds: Dict[str, float],
        working_condition: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """执行单个情景的仿真"""
        rng = np.random.RandomState(seed)

        last_hist_offset = float(parsed_history.day_offsets[-1]) if len(parsed_history.day_offsets) > 0 else 0.0
        future_offsets = np.arange(last_hist_offset + 1, last_hist_offset + 1 + forecast_days)
        all_offsets = np.concatenate([parsed_history.day_offsets, future_offsets])

        base_hi = self._predict_model(fitted_model, all_offsets)

        slope_adj = float(hypothesis.get("slope_adjustment", 1.0))
        if slope_adj != 1.0 and len(parsed_history.day_offsets) > 0:
            last_hist_idx = len(parsed_history.day_offsets) - 1
            hist_last_hi = base_hi[last_hist_idx]
            future_mask = all_offsets > last_hist_offset
            original_change = base_hi[future_mask] - hist_last_hi
            adjusted = hist_last_hi + original_change * slope_adj
            base_hi[future_mask] = adjusted

        temp_effects = self._apply_environment_scenarios(
            all_offsets=all_offsets,
            hypothesis=hypothesis,
            base_hi=base_hi,
            working_condition=working_condition,
            last_hist_day=last_hist_offset,
        )

        step_changes = hypothesis.get("step_changes", []) or []
        for sc in step_changes:
            try:
                day_offset = float(sc.get("day_offset", 0))
                hi_delta = float(sc.get("hi_delta", 0))
                target_day = last_hist_offset + day_offset
                mask = all_offsets >= target_day
                base_hi[mask] += hi_delta
            except Exception as e:
                logger.warning(f"应用阶跃变化失败: {e}")

        maintenance_days = set()
        maint_delay = int(hypothesis.get("maintenance_delay_days", 0))
        maint_recovery = float(hypothesis.get("maintenance_recovery_hi", 0.0))

        if maint_recovery > 0:
            intervention_thr = thresholds["intervention_threshold"]
            hist_end_idx = len(parsed_history.day_offsets)
            last_maint_idx = -999
            maint_cooldown_days = 90
            for i in range(hist_end_idx, len(all_offsets)):
                days_since_last_maint = i - last_maint_idx
                if (
                    days_since_last_maint >= maint_cooldown_days
                    and base_hi[i] <= intervention_thr
                ):
                    maint_idx = min(i + maint_delay, len(all_offsets) - 1)
                    if maint_idx < len(all_offsets):
                        base_hi[maint_idx:] += maint_recovery
                        maint_day_from_base = int(round(all_offsets[maint_idx] - last_hist_offset))
                        maintenance_days.add(maint_day_from_base)
                        base_hi = np.clip(base_hi, 0.0, 100.0)
                        last_maint_idx = maint_idx

        noise_level = float(hypothesis.get("noise_level", 0.0))
        if noise_level > 0:
            noise = rng.normal(0, noise_level, size=len(base_hi))
            if len(parsed_history.day_offsets) > 0:
                noise[:len(parsed_history.day_offsets)] = 0.0
            base_hi = base_hi + noise

        base_hi = np.clip(base_hi, 0.0, 100.0)

        trajectory = self._build_trajectory(
            all_offsets=all_offsets,
            hi_values=base_hi,
            temp_effects=temp_effects,
            maintenance_days=maintenance_days,
            parsed_history=parsed_history,
            fitted_model=fitted_model,
            thresholds=thresholds,
            forecast_days=forecast_days,
        )

        first_crossings = self._compute_first_crossings(
            trajectory=trajectory,
            thresholds=thresholds,
        )

        risk_timeline = self._build_risk_timeline(
            trajectory=trajectory,
        )

        interventions = self._recommend_interventions(
            trajectory=trajectory,
            first_crossings=first_crossings,
            thresholds=thresholds,
            hypothesis=hypothesis,
        )

        summary = self._compute_scenario_summary(
            trajectory=trajectory,
            first_crossings=first_crossings,
            thresholds=thresholds,
        )

        return {
            "scenario_id": scen_id,
            "scenario_name": scen_name,
            "hypothesis": hypothesis,
            "trajectory": trajectory,
            "first_crossings": first_crossings,
            "risk_timeline": risk_timeline,
            "recommended_interventions": interventions,
            "summary": summary,
            "degradation_model_used": fitted_model.model_type,
            "model_r_squared": fitted_model.r_squared,
            "model_params": fitted_model.params,
        }

    # ==================== 环境场景 ====================

    def _apply_environment_scenarios(
        self,
        all_offsets: np.ndarray,
        hypothesis: Dict[str, Any],
        base_hi: np.ndarray,
        working_condition: Optional[Dict[str, Any]],
        last_hist_day: float,
    ) -> np.ndarray:
        """应用温度、湿度、振动场景对HI的衰减影响"""
        effects = np.zeros(len(all_offsets), dtype=np.float64)

        temp_scenario = hypothesis.get("temperature_scenario", "normal").lower()
        hum_scenario = hypothesis.get("humidity_scenario", "normal").lower()
        vib_scenario = hypothesis.get("vibration_scenario", "normal").lower()

        temp_factor_map = {
            "normal": 1.0,
            "high": 1.3,
            "extreme": 1.8,
            "cold": 0.9,
            "custom": 1.0,
        }
        hum_factor_map = {
            "normal": 1.0,
            "high": 1.2,
            "low": 0.95,
            "custom": 1.0,
        }
        vib_factor_map = {
            "normal": 1.0,
            "elevated": 1.4,
            "severe": 2.0,
            "custom": 1.0,
        }

        temp_factor = temp_factor_map.get(temp_scenario, 1.0)
        hum_factor = hum_factor_map.get(hum_scenario, 1.0)
        vib_factor = vib_factor_map.get(vib_scenario, 1.0)

        combined_factor = temp_factor * hum_factor * vib_factor

        if combined_factor != 1.0 and len(all_offsets) > 0:
            last_hist_idx = 0
            for i in range(len(all_offsets)):
                if all_offsets[i] <= last_hist_day:
                    last_hist_idx = i
            anchor_hi = base_hi[last_hist_idx]

            for i in range(last_hist_idx + 1, len(base_hi)):
                original_change = base_hi[i] - anchor_hi
                base_hi[i] = anchor_hi + original_change * combined_factor
                effects[i] = original_change * (combined_factor - 1.0)

        return effects

    # ==================== 轨迹构建 ====================

    def _build_trajectory(
        self,
        all_offsets: np.ndarray,
        hi_values: np.ndarray,
        temp_effects: np.ndarray,
        maintenance_days: set,
        parsed_history: ParsedHistory,
        fitted_model: FittedModel,
        thresholds: Dict[str, float],
        forecast_days: int,
    ) -> List[Dict[str, Any]]:
        """构建模拟轨迹列表"""
        trajectory = []
        last_hist_day = float(parsed_history.day_offsets[-1]) if len(parsed_history.day_offsets) > 0 else 0.0

        for i in range(len(all_offsets)):
            offset = float(all_offsets[i])
            hi = float(hi_values[i])
            hi_level = self._hi_to_level(hi, thresholds)
            risk_score = self._hi_to_risk_score(hi, thresholds)
            risk_level = self._risk_score_to_level(risk_score)
            risk_score_100 = self._risk_score_10_to_100(risk_score)
            risk_status = self._risk_level_to_status(risk_level)

            uncertainty = fitted_model.residuals_std * (
                1.0 + abs(offset - last_hist_day) / max(forecast_days, 1) * 0.5
            )
            lower = float(max(0.0, hi - uncertainty * 1.96))
            upper = float(min(100.0, hi + uncertainty * 1.96))

            day_offset_from_base = int(round(offset - last_hist_day))
            date = parsed_history.base_date + timedelta(days=day_offset_from_base)

            is_prediction = offset > last_hist_day
            maint_applied = day_offset_from_base in maintenance_days

            temp_eff_val = float(temp_effects[i]) if i < len(temp_effects) else None
            if temp_eff_val is not None:
                temp_eff_val = round(temp_eff_val, 4)

            trajectory.append({
                "date": date,
                "day_offset": day_offset_from_base,
                "predicted_hi": round(hi, 2),
                "lower_bound": round(lower, 2),
                "upper_bound": round(upper, 2),
                "hi_level": hi_level,
                "risk_level": risk_level,
                "risk_score": round(risk_score, 2),
                "risk_status": risk_status,
                "risk_score_100": round(risk_score_100, 2),
                "temperature_effect": temp_eff_val,
                "maintenance_applied": maint_applied,
                "is_prediction": is_prediction,
            })

        return trajectory

    # ==================== 首次触阈 ====================

    def _compute_first_crossings(
        self,
        trajectory: List[Dict[str, Any]],
        thresholds: Dict[str, float],
    ) -> Dict[str, Dict[str, Any]]:
        """计算首次触阈信息"""
        threshold_defs = [
            ("intervention", thresholds["intervention_threshold"]),
            ("warning", thresholds["warning_threshold"]),
            ("failure", thresholds["failure_threshold"]),
        ]

        crossings = {}
        for name, thr_val in threshold_defs:
            was_already_below = False
            crossing_date = None
            crossing_day = None
            hi_at_crossing = None
            confidence = None

            for idx, point in enumerate(trajectory):
                hi = point["predicted_hi"]

                if idx == 0 and hi <= thr_val:
                    was_already_below = True
                    break

                if hi <= thr_val:
                    crossing_date = point["date"]
                    crossing_day = point["day_offset"]
                    hi_at_crossing = hi
                    uncertainty_width = (point["upper_bound"] - point["lower_bound"]) / 2
                    confidence = float(np.clip(
                        1.0 - uncertainty_width / max(thr_val, 1e-6),
                        0.5,
                        0.95,
                    ))
                    break

            crossings[name] = {
                "threshold_name": name,
                "threshold_value": thr_val,
                "crossing_date": crossing_date,
                "crossing_day_offset": crossing_day,
                "hi_at_crossing": hi_at_crossing,
                "confidence": confidence,
                "was_already_below": was_already_below,
            }

        return crossings

    # ==================== 风险等级时间线 ====================

    def _build_risk_timeline(
        self,
        trajectory: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """构建风险等级时间线"""
        if not trajectory:
            return []

        timeline = []
        current_level = trajectory[0]["risk_level"]
        current_status = trajectory[0]["risk_status"]
        start_idx = 0
        n = len(trajectory)

        for i in range(1, n):
            last_point = (i == n - 1)
            if trajectory[i]["risk_level"] != current_level or last_point:
                end_idx = i if not last_point else i
                segment = trajectory[start_idx : end_idx + 1]
                his = [p["predicted_hi"] for p in segment]

                is_last_segment = last_point
                timeline.append({
                    "risk_level": current_level,
                    "risk_status": current_status,
                    "start_day_offset": segment[0]["day_offset"],
                    "end_day_offset": segment[-1]["day_offset"] if not is_last_segment else None,
                    "start_date": segment[0]["date"],
                    "end_date": segment[-1]["date"] if not is_last_segment else None,
                    "duration_days": len(segment),
                    "hi_range": {
                        "min": round(min(his), 2),
                        "max": round(max(his), 2),
                        "avg": round(sum(his) / len(his), 2),
                    },
                })

                if not last_point:
                    current_level = trajectory[i]["risk_level"]
                    current_status = trajectory[i]["risk_status"]
                    start_idx = i

        return timeline

    # ==================== 推荐干预 ====================

    def _recommend_interventions(
        self,
        trajectory: List[Dict[str, Any]],
        first_crossings: Dict[str, Dict[str, Any]],
        thresholds: Dict[str, float],
        hypothesis: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """推荐干预时间点"""
        interventions = []

        intervention_cross = first_crossings.get("intervention", {})
        warning_cross = first_crossings.get("warning", {})
        failure_cross = first_crossings.get("failure", {})

        if (
            not intervention_cross.get("was_already_below")
            and intervention_cross.get("crossing_day_offset") is not None
        ):
            inter_day = intervention_cross["crossing_day_offset"]
            rec_day = max(0, inter_day - 10)
            fail_day = failure_cross.get("crossing_day_offset")
            priority = "high" if (
                fail_day is not None and fail_day - inter_day < 30
            ) else "medium"

            interventions.append({
                "intervention_type": "preventive",
                "priority": priority,
                "recommended_date": (
                    trajectory[0]["date"] + timedelta(days=rec_day)
                    if rec_day >= 0 else None
                ),
                "recommended_day_offset": rec_day if rec_day >= 0 else None,
                "deadline_date": intervention_cross["crossing_date"],
                "deadline_day_offset": inter_day,
                "reason": (
                    f"预计{inter_day}天后将达到干预阈值（HI="
                    f"{thresholds['intervention_threshold']}），"
                    f"建议提前进行预防性维护以延缓劣化。"
                ),
                "expected_risk_reduction": 30.0,
                "maintenance_window_days": 14,
                "measures": [
                    "按标准扭矩值重新紧固螺栓，必要时更换螺栓",
                    "检查法兰面密封件老化情况",
                    "进行超声波探伤核查螺栓预紧力均匀性",
                ],
            })

        if (
            warning_cross.get("was_already_below")
            or warning_cross.get("crossing_day_offset") is not None
        ):
            warn_day = warning_cross["crossing_day_offset"] or 0
            interventions.append({
                "intervention_type": "corrective",
                "priority": "high",
                "recommended_date": warning_cross.get("crossing_date") or trajectory[0]["date"],
                "recommended_day_offset": warn_day,
                "deadline_date": failure_cross.get("crossing_date"),
                "deadline_day_offset": failure_cross.get("crossing_day_offset"),
                "reason": (
                    f"预计{warn_day}天后达到预警阈值（HI="
                    f"{thresholds['warning_threshold']}），"
                    f"需尽快安排纠正性维护。"
                ),
                "expected_risk_reduction": 45.0,
                "maintenance_window_days": 7,
                "measures": [
                    "立即安排检修并重新紧固问题螺栓预紧力",
                    "必要时更换密封垫片",
                    "全面核查法兰面平行度",
                ],
            })

        fail_day = failure_cross.get("crossing_day_offset")
        if failure_cross.get("was_already_below") or (
            fail_day is not None and fail_day < 15
        ):
            f_day = fail_day or 0
            interventions.append({
                "intervention_type": "urgent",
                "priority": "urgent",
                "recommended_date": failure_cross.get("crossing_date") or trajectory[0]["date"],
                "recommended_day_offset": f_day,
                "deadline_date": (
                    failure_cross.get("crossing_date")
                    or (trajectory[0]["date"] + timedelta(days=3))
                ),
                "deadline_day_offset": f_day + 3,
                "reason": "即将或已达到故障阈值，需紧急处理。",
                "expected_risk_reduction": 60.0,
                "maintenance_window_days": 2,
                "measures": [
                    "停机并更换全部螺栓",
                    "更换法兰密封组件",
                    "进行泄漏测试",
                ],
            })

        priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        interventions.sort(key=lambda x: priority_order.get(x["priority"], 99))

        return interventions

    # ==================== 情景汇总 ====================

    def _compute_scenario_summary(
        self,
        trajectory: List[Dict[str, Any]],
        first_crossings: Dict[str, Dict[str, Any]],
        thresholds: Dict[str, float],
    ) -> Dict[str, Any]:
        """计算情景汇总指标"""
        his = [p["predicted_hi"] for p in trajectory]
        risk_scores = [p["risk_score"] for p in trajectory]
        risk_scores_100 = [p["risk_score_100"] for p in trajectory]
        high_risk_days = sum(
            1 for p in trajectory if p["risk_level"] == "高"
        )
        critical_days = sum(
            1 for p in trajectory if p["risk_status"] == "critical"
        )
        warning_days = sum(
            1 for p in trajectory if p["risk_status"] == "warning"
        )

        failure_cross = first_crossings.get("failure", {})
        rul_days = None
        rul_confidence = None
        if (
            failure_cross.get("crossing_day_offset") is not None
            and not failure_cross["was_already_below"]
        ):
            rul_days = float(failure_cross["crossing_day_offset"])
            rul_confidence = failure_cross.get("confidence", 0.7)

        if len(trajectory) >= 2:
            avg_rate = (his[-1] - his[0]) / max(1, len(trajectory) - 1)
        else:
            avg_rate = 0.0

        maintenance_count = sum(1 for p in trajectory if p["maintenance_applied"])

        return {
            "final_hi": round(his[-1], 2),
            "min_hi": round(min(his), 2),
            "avg_degradation_rate": round(avg_rate, 4),
            "rul_days": rul_days,
            "rul_confidence": rul_confidence,
            "total_risk_exposure": round(sum(11.0 - s for s in risk_scores), 2),
            "high_risk_days": high_risk_days,
            "total_risk_exposure_100": round(sum(risk_scores_100), 2),
            "critical_days": critical_days,
            "warning_days": warning_days,
            "maintenance_count": maintenance_count,
        }

    # ==================== 批量情景对比 ====================

    def _generate_scenario_comparison(
        self,
        scenario_results: List[Dict[str, Any]],
        baseline_scenario_id: str,
        thresholds: Dict[str, float],
    ) -> Dict[str, Any]:
        """生成跨情景对比分析"""
        metrics_defs = [
            ("rul_days", "剩余使用寿命RUL", "天", "higher_better"),
            ("first_warning_day", "首次预警天数", "天", "higher_better"),
            ("first_failure_day", "首次故障天数", "天", "higher_better"),
            ("total_risk", "总风险暴露量", "分", "lower_better"),
            ("high_risk_days", "高风险天数", "天", "lower_better"),
            ("final_hi", "仿真期末HI", "分", "higher_better"),
            ("min_hi", "仿真期最低HI", "分", "higher_better"),
            ("avg_degradation_rate", "平均劣化速率", "HI/天", "higher_better"),
            ("maintenance_count", "维护次数", "次", "lower_better"),
        ]

        comparison_metrics = []

        scen_metric_values = {}
        for s in scenario_results:
            sid = s["scenario_id"]
            summ = s["summary"]
            cross = s["first_crossings"]
            scen_metric_values[sid] = {
                "rul_days": summ.get("rul_days"),
                "first_warning_day": cross.get("warning", {}).get("crossing_day_offset"),
                "first_failure_day": cross.get("failure", {}).get("crossing_day_offset"),
                "total_risk": summ.get("total_risk_exposure"),
                "high_risk_days": float(summ.get("high_risk_days", 0)),
                "final_hi": summ.get("final_hi"),
                "min_hi": summ.get("min_hi"),
                "avg_degradation_rate": summ.get("avg_degradation_rate"),
                "maintenance_count": float(summ.get("maintenance_count", 0)),
            }

        for code, name, unit, direction in metrics_defs:
            values = {}
            best_sid = None
            best_val = None

            for s in scenario_results:
                sid = s["scenario_id"]
                v = scen_metric_values[sid][code]
                values[sid] = v

                if v is not None:
                    if best_val is None:
                        best_val = v
                        best_sid = sid
                    else:
                        if direction == "higher_better" and v > best_val:
                            best_val = v
                            best_sid = sid
                        elif direction == "lower_better" and v < best_val:
                            best_val = v
                            best_sid = sid

            delta = {}
            baseline_v = scen_metric_values.get(baseline_scenario_id, {}).get(code)
            for s in scenario_results:
                sid = s["scenario_id"]
                v = values.get(sid)
                if v is not None and baseline_v is not None:
                    delta[sid] = round(v - baseline_v, 4)
                else:
                    delta[sid] = None

            comparison_metrics.append({
                "metric_code": code,
                "metric_name": name,
                "unit": unit,
                "scenario_values": values,
                "best_scenario_id": best_sid,
                "delta_vs_baseline": delta,
            })

        ranked = []
        for s in scenario_results:
            sid = s["scenario_id"]
            summ = s["summary"]
            score = 0.0

            rul_vals = [sr["summary"].get("rul_days") or 0.0 for sr in scenario_results]
            max_rul = max(rul_vals) if rul_vals and max(rul_vals) > 0 else 1.0
            score += 0.3 * ((summ.get("rul_days") or 0.0) / max_rul)

            risk_vals = [
                sr["summary"].get("total_risk_exposure") or 1.0
                for sr in scenario_results
            ]
            max_risk = max(risk_vals) if risk_vals and max(risk_vals) > 0 else 1.0
            score += 0.3 * (1.0 - (summ.get("total_risk_exposure") or 0.0) / max_risk)

            minhi_vals = [sr["summary"].get("min_hi") or 0.0 for sr in scenario_results]
            max_min_hi = max(minhi_vals) if minhi_vals and max(minhi_vals) > 0 else 100.0
            score += 0.2 * ((summ.get("min_hi") or 0.0) / max_min_hi)

            score += 0.2 * ((summ.get("final_hi") or 0.0) / 100.0)

            ranked.append({
                "scenario_id": sid,
                "scenario_name": s["scenario_name"],
                "score": round(score, 4),
                "pros": [],
                "cons": [],
            })

        ranked.sort(key=lambda x: -x["score"])
        for i, r in enumerate(ranked):
            r["rank"] = i + 1

        if len(ranked) >= 2:
            best = ranked[0]
            best_sr = next(
                (sr for sr in scenario_results if sr["scenario_id"] == best["scenario_id"]),
                None,
            )
            if best_sr:
                best_summary = best_sr["summary"]
                recommendation = (
                    f"综合推荐采用【{best['scenario_name']}】方案。"
                    f"该方案RUL约{best_summary.get('rul_days')}天，"
                    f"总风险暴露量{best_summary.get('total_risk_exposure')}分，"
                    f"为最优平衡方案。"
                )
            else:
                recommendation = "情景对比分析完成。"
        else:
            recommendation = "情景对比分析完成。"

        return {
            "baseline_scenario_id": baseline_scenario_id,
            "comparison_metrics": comparison_metrics,
            "recommendation_summary": recommendation,
            "ranked_scenarios": ranked,
        }

    # ==================== 工具函数 ====================

    @staticmethod
    def _parse_timestamp(ts_str: str) -> datetime:
        """解析时间戳字符串"""
        formats = [
            "%Y%m%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%Y%m%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue
        try:
            return pd.Timestamp(ts_str).to_pydatetime()
        except Exception:
            raise ValueError(f"无法解析时间戳: {ts_str}")

    @staticmethod
    def _preload_to_hi(preload_values: np.ndarray, nominal: float) -> np.ndarray:
        """预紧力(kN) → HI(0-100) 转换"""
        deviation = np.abs(preload_values - nominal) / nominal
        scores = np.where(
            deviation <= 0.05,
            100.0,
            np.where(
                deviation <= 0.10,
                80.0 - (deviation - 0.05) * 400,
                np.where(
                    deviation <= 0.20,
                    60.0 - (deviation - 0.10) * 300,
                    np.maximum(0.0, 30.0 - (deviation - 0.20) * 200),
                ),
            ),
        )
        return np.clip(scores, 0.0, 100.0)

    @staticmethod
    def _hi_to_level(hi: float, thresholds: Dict[str, float]) -> str:
        """HI → 健康等级"""
        if hi >= thresholds["excellent_threshold"]:
            return HealthLevel.EXCELLENT.value
        elif hi >= thresholds["good_threshold"]:
            return HealthLevel.GOOD.value
        elif hi >= thresholds["fair_threshold"]:
            return HealthLevel.FAIR.value
        elif hi >= thresholds["poor_threshold"]:
            return HealthLevel.POOR.value
        else:
            return HealthLevel.CRITICAL.value

    @staticmethod
    def _hi_to_risk_score(hi: float, thresholds: Dict[str, float]) -> float:
        """HI → 风险评分（与BayesianRiskModel口径一致：1-10分，越高越安全）

        BayesianRiskModel 口径:
        - risk_score = weighted_score * 9 + 1 → [1, 10]
        - 1-3分: 高风险
        - 4-7分: 中风险
        - 8-10分: 低风险
        """
        score = 1.0 + hi * 0.09
        return float(np.clip(score, 1.0, 10.0))

    @staticmethod
    def _risk_score_to_level(score: float) -> str:
        """风险评分 → 风险等级（与BayesianRiskModel口径一致：中文）

        - 高风险: score ≤ 3
        - 中风险: 3 < score ≤ 7
        - 低风险: score > 7
        """
        if score <= 3.0:
            return RiskLevel.HIGH.value
        elif score <= 7.0:
            return RiskLevel.MEDIUM.value
        else:
            return RiskLevel.LOW.value

    @staticmethod
    def _risk_score_10_to_100(score_10: float) -> float:
        """Bayesian 1-10分（越高越安全）→ 复检排程 0-100分（越高越危险）

        线性映射: risk_100 = (10 - risk_10) / 9 * 100

        对应关系:
        - score_10=10 (最安全) → score_100=0
        - score_10=5.5 (中间) → score_100=50
        - score_10=1 (最危险) → score_100=100
        """
        score_100 = (10.0 - float(score_10)) / 9.0 * 100.0
        return float(np.clip(score_100, 0.0, 100.0))

    @staticmethod
    def _risk_score_100_to_10(score_100: float) -> float:
        """复检排程 0-100分（越高越危险）→ Bayesian 1-10分（越高越安全）

        线性映射: risk_10 = 10 - risk_100 / 100 * 9

        对应关系:
        - score_100=0 → score_10=10
        - score_100=50 → score_10=5.5
        - score_100=100 → score_10=1
        """
        score_10 = 10.0 - float(score_100) / 100.0 * 9.0
        return float(np.clip(score_10, 1.0, 10.0))

    @staticmethod
    def _risk_level_to_status(level: str) -> str:
        """Bayesian中文等级（低/中/高）→ 复检排程英文状态（normal/warning/critical）

        与 retest_service._risk_to_status 对齐:
        - normal: 风险评分 < 40（对应 Bayesian 低风险 "低"）
        - warning: 40 ≤ 风险评分 < 70（对应 Bayesian 中风险 "中"）
        - critical: 风险评分 ≥ 70（对应 Bayesian 高风险 "高"）
        """
        if level == RiskLevel.HIGH.value:
            return RiskStatus.CRITICAL.value
        elif level == RiskLevel.MEDIUM.value:
            return RiskStatus.WARNING.value
        else:
            return RiskStatus.NORMAL.value

    @staticmethod
    def _risk_status_to_level(status: str) -> str:
        """复检排程英文状态（normal/warning/critical）→ Bayesian中文等级（低/中/高）"""
        if status == RiskStatus.CRITICAL.value:
            return RiskLevel.HIGH.value
        elif status == RiskStatus.WARNING.value:
            return RiskLevel.MEDIUM.value
        else:
            return RiskLevel.LOW.value

    @staticmethod
    def _risk_score_100_to_status(score_100: float) -> str:
        """复检排程 0-100分 → 状态 normal/warning/critical

        与 retest_service._risk_to_status 完全一致:
        - ≥70: critical
        - ≥40: warning
        - <40: normal
        """
        if score_100 >= 70.0:
            return RiskStatus.CRITICAL.value
        elif score_100 >= 40.0:
            return RiskStatus.WARNING.value
        else:
            return RiskStatus.NORMAL.value
