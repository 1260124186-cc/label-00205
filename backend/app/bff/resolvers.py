import json
from typing import Optional, List
from datetime import datetime

import strawberry
from strawberry.types import Info
from loguru import logger

from app.bff.types import (
    PredictionInfo,
    HealthInfo,
    HealthFactor,
    RULInfo,
    RULForecastPoint,
    AnomalyRecord,
    WorkOrderRecord,
    KnowledgeRecommendation,
    BoltDashboard,
)
from app.bff.middleware import (
    get_tenant_context_from_request,
    get_allowed_fields,
    filter_fields,
    enforce_tenant_isolation,
)


DASHBOARD_FIELDS = {
    "prediction", "health", "rul",
    "recent_anomalies", "work_orders", "knowledge_recommendations",
}


async def _fetch_prediction(bolt_id: str, tenant_id: Optional[int]) -> Optional[PredictionInfo]:
    try:
        from app.utils.database import get_db, AbnormalPrediction
        from sqlalchemy import desc
        with get_db() as db:
            if db is None:
                return None
            rec = (
                db.query(AbnormalPrediction)
                .filter(AbnormalPrediction.bolt_id == str(bolt_id))
                .order_by(desc(AbnormalPrediction.create_time))
                .first()
            )
            if not rec:
                return None
            status_labels = {0: "正常", 1: "关注级预警", 2: "检查级预警", 3: "紧急级预警", 4: "故障"}
            pw_type_map = {"normal": 0, "attention": 1, "inspection": 2, "urgent": 3, "fault": 4}
            status_code = pw_type_map.get(rec.pw_type, 0) if rec.pw_type else 0
            return PredictionInfo(
                bolt_id=bolt_id,
                status_code=status_code,
                status_label=status_labels.get(status_code, rec.pw_type or "未知"),
                confidence=rec.confidence or 0.0,
                risk_level=rec.pw_type or "normal",
                predicted_at=rec.create_time,
            )
    except Exception as e:
        logger.warning(f"BFF: prediction fetch failed for {bolt_id}: {e}")
        return None


async def _fetch_health(bolt_id: str, tenant_id: Optional[int]) -> Optional[HealthInfo]:
    try:
        from app.utils.database import get_db, BoltHealthHistory
        from sqlalchemy import desc
        with get_db() as db:
            if db is None:
                return None
            rec = (
                db.query(BoltHealthHistory)
                .filter(BoltHealthHistory.bolt_id == str(bolt_id))
                .order_by(desc(BoltHealthHistory.create_time))
                .first()
            )
            if not rec:
                return None
            factors = []
            if rec.factors_detail:
                try:
                    raw = json.loads(rec.factors_detail) if isinstance(rec.factors_detail, str) else rec.factors_detail
                    for f in raw:
                        factors.append(HealthFactor(
                            factor_name=f.get("factor_name", ""),
                            factor_code=f.get("factor_code", ""),
                            score=f.get("score", 0.0),
                            weight=f.get("weight", 0.0),
                            contribution=f.get("contribution", 0.0),
                        ))
                except (json.JSONDecodeError, TypeError):
                    pass
            return HealthInfo(
                bolt_id=bolt_id,
                hi_score=rec.hi_score,
                hi_level=rec.hi_level,
                trend=getattr(rec, "trend", None),
                trend_rate=getattr(rec, "trend_rate", None),
                factors=factors,
                calculated_at=rec.create_time,
            )
    except Exception as e:
        logger.warning(f"BFF: health fetch failed for {bolt_id}: {e}")
        return None


async def _fetch_rul(bolt_id: str, tenant_id: Optional[int]) -> Optional[RULInfo]:
    try:
        from app.services.health_service import HealthService
        svc = HealthService()
        result = svc.predict_rul(
            node_id=bolt_id,
            node_type="bolt",
            save_to_db=False,
        )
        forecast = []
        for pt in result.get("forecast_series", []):
            forecast.append(RULForecastPoint(
                day=pt.get("day", 0),
                predicted_hi=pt.get("predicted_hi", 0),
                lower_bound=pt.get("lower_bound", 0),
                upper_bound=pt.get("upper_bound", 0),
                is_prediction=pt.get("is_prediction", False),
            ))
        return RULInfo(
            bolt_id=bolt_id,
            current_hi=result.get("current_hi", 0),
            rul_days=result.get("rul_days", 0),
            rul_lower_bound=result.get("rul_lower_bound", 0),
            rul_upper_bound=result.get("rul_upper_bound", 0),
            rul_confidence=result.get("rul_confidence", 0),
            failure_threshold=result.get("failure_threshold", 30),
            warning_threshold=result.get("warning_threshold", 50),
            days_to_warning=result.get("days_to_warning"),
            degradation_model=result.get("degradation_model", "linear"),
            r_squared=result.get("r_squared"),
            forecast_series=forecast,
        )
    except Exception as e:
        logger.warning(f"BFF: RUL fetch failed for {bolt_id}: {e}")
        return None


async def _fetch_anomalies(bolt_id: str, tenant_id: Optional[int]) -> List[AnomalyRecord]:
    try:
        from app.services.anomaly_service import get_anomaly_service
        svc = get_anomaly_service()
        _, anomalies = svc.query_anomalies(
            sensor_id=bolt_id,
            limit=10,
        )
        return [
            AnomalyRecord(
                id=a.get("id", 0),
                sensor_id=a.get("sensor_id", ""),
                anomaly_type=a.get("anomaly_type"),
                anomaly_score=a.get("anomaly_score"),
                anomaly_value=a.get("anomaly_value"),
                classification=a.get("classification"),
                original_time=a.get("original_time"),
                is_confirmed=a.get("is_confirmed", False),
                is_false_positive=a.get("is_false_positive", False),
            )
            for a in anomalies
        ]
    except Exception as e:
        logger.warning(f"BFF: anomaly fetch failed for {bolt_id}: {e}")
        return []


async def _fetch_work_orders(bolt_id: str, tenant_id: Optional[int]) -> List[WorkOrderRecord]:
    try:
        from app.services.alert.work_order_service import WorkOrderService
        svc = WorkOrderService()
        orders = svc.list_work_orders(node_id=bolt_id, limit=10)
        result = []
        for wo in orders:
            result.append(WorkOrderRecord(
                id=wo.id,
                order_no=wo.order_no or "",
                title=wo.title or "",
                priority=wo.priority or "low",
                status=wo.status or "pending",
                assignee=wo.assignee_name,
                due_time=wo.due_time,
                created_at=wo.create_time,
            ))
        return result
    except Exception as e:
        logger.warning(f"BFF: work order fetch failed for {bolt_id}: {e}")
        return []


async def _fetch_knowledge(bolt_id: str, tenant_id: Optional[int]) -> List[KnowledgeRecommendation]:
    try:
        from app.services.knowledge import KnowledgeService
        svc = KnowledgeService()
        similar = svc.search_similar_cases(
            node_type="bolt",
            node_id=bolt_id,
            top_k=5,
            tenant_id=tenant_id,
        )
        result = []
        for item in similar:
            case = item.case
            treatment = None
            try:
                tp = json.loads(case.treatment_plan) if case.treatment_plan else {}
                steps = tp.get("steps", [])
                treatment = "; ".join(s.get("action", "") for s in steps[:3]) or None
            except Exception:
                pass
            result.append(KnowledgeRecommendation(
                case_id=case.id,
                case_title=case.case_title or "",
                similarity_score=item.similarity_score,
                fault_type=case.fault_type,
                diagnosis=case.diagnosis,
                treatment_summary=treatment,
                effectiveness_score=case.effectiveness_score,
            ))
        return result
    except Exception as e:
        logger.warning(f"BFF: knowledge fetch failed for {bolt_id}: {e}")
        return []


@strawberry.type
class Query:
    @strawberry.field
    async def bolt_dashboard(
        self,
        info: Info,
        bolt_id: str,
    ) -> BoltDashboard:
        request = info.context.get("request")
        tenant_ctx = {}
        if request is not None:
            tenant_ctx = get_tenant_context_from_request(request)

        tenant_id = tenant_ctx.get("tenant_id")
        role = tenant_ctx.get("role", "anonymous")

        allowed = get_allowed_fields(role)

        prediction = None
        if "prediction" in allowed:
            prediction = await _fetch_prediction(bolt_id, tenant_id)

        health = None
        if "health" in allowed:
            health = await _fetch_health(bolt_id, tenant_id)

        rul = None
        if "rul" in allowed:
            rul = await _fetch_rul(bolt_id, tenant_id)

        anomalies = []
        if "recent_anomalies" in allowed:
            anomalies = await _fetch_anomalies(bolt_id, tenant_id)

        work_orders = []
        if "work_orders" in allowed:
            work_orders = await _fetch_work_orders(bolt_id, tenant_id)

        knowledge = []
        if "knowledge_recommendations" in allowed:
            knowledge = await _fetch_knowledge(bolt_id, tenant_id)

        return BoltDashboard(
            bolt_id=bolt_id,
            prediction=prediction,
            health=health,
            rul=rul,
            recent_anomalies=anomalies,
            work_orders=work_orders,
            knowledge_recommendations=knowledge,
        )

    @strawberry.field
    async def bolt_dashboards(
        self,
        info: Info,
        bolt_ids: List[str],
    ) -> List[BoltDashboard]:
        results = []
        for bid in bolt_ids:
            dashboard = await self.bolt_dashboard(info=info, bolt_id=bid)
            results.append(dashboard)
        return results
