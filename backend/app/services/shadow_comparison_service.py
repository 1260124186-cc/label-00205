"""
影子模式对比分析与版本晋升服务

核心功能:
1. 记录主版本与影子版本的预测对比数据
2. 计算统计指标：一致率、影子更敏感率、影子更保守率、按状态分桶对比
3. 晋升规则评估：影子运行7天 + 一致率>95% + 漏报率下降>10%
4. 自动生成晋升建议工单
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from loguru import logger
from sqlalchemy import and_, func

from app.utils.database import (
    get_db,
    ShadowComparison,
    ModelPromotionSuggestion,
)
from app.middleware import (
    get_effective_tenant_id,
    is_audit_mode,
)
from app.services.tenant import (
    enforce_tenant_access,
    not_found_404,
)


PROMOTION_REQUIRED_DAYS = 7
PROMOTION_MIN_AGREEMENT_RATE = 0.95
PROMOTION_MIN_FN_IMPROVEMENT_RATE = 0.10
MIN_SAMPLE_SIZE = 100


class ShadowComparisonService:
    """
    影子模式对比分析与版本晋升服务

    提供对比记录、统计指标计算、晋升评估等完整能力。
    """

    def __init__(self):
        self.required_days = PROMOTION_REQUIRED_DAYS
        self.min_agreement_rate = PROMOTION_MIN_AGREEMENT_RATE
        self.min_fn_improvement_rate = PROMOTION_MIN_FN_IMPROVEMENT_RATE
        self.min_sample_size = MIN_SAMPLE_SIZE
        logger.info(
            "影子模式对比服务初始化完成: "
            f"required_days={self.required_days}, "
            f"min_agreement={self.min_agreement_rate:.1%}, "
            f"min_fn_improvement={self.min_fn_improvement_rate:.1%}"
        )

    # ============================================================
    # 记录对比数据
    # ============================================================

    def record_comparison(
        self,
        model_type: str,
        node_id: str,
        main_version: str,
        shadow_version: str,
        main_status_code: int,
        main_status: str,
        main_confidence: float,
        shadow_status_code: int,
        shadow_status: str,
        shadow_confidence: float,
        main_latency_ms: Optional[int] = None,
        shadow_latency_ms: Optional[int] = None,
        prediction_time: Optional[datetime] = None,
        tenant_id: Optional[int] = None,
    ) -> Optional[ShadowComparison]:
        """
        记录一次主版本与影子版本的预测对比

        Args:
            model_type: 模型类型 bolt/flange
            node_id: 节点ID
            main_version: 主版本号
            shadow_version: 影子版本号
            main_status_code: 主版本状态码
            main_status: 主版本状态文本
            main_confidence: 主版本置信度
            shadow_status_code: 影子版本状态码
            shadow_status: 影子版本状态文本
            shadow_confidence: 影子版本置信度
            main_latency_ms: 主版本耗时(ms)
            shadow_latency_ms: 影子版本耗时(ms)
            prediction_time: 预测时间
            tenant_id: 租户ID

        Returns:
            创建的 ShadowComparison 记录
        """
        effective_tid = tenant_id or get_effective_tenant_id()
        if effective_tid is None:
            return None

        is_agreement = main_status_code == shadow_status_code
        is_shadow_more_sensitive = (
            main_status_code == 0 and shadow_status_code > 0
        )
        is_shadow_more_conservative = (
            main_status_code > 0 and shadow_status_code == 0
        )

        try:
            with get_db() as db:
                if db is None:
                    return None

                record = ShadowComparison(
                    tenant_id=effective_tid,
                    model_type=model_type,
                    node_id=str(node_id),
                    node_type=model_type,
                    main_version=main_version,
                    shadow_version=shadow_version,
                    main_status_code=main_status_code,
                    main_status=main_status,
                    main_confidence=float(main_confidence) if main_confidence is not None else None,
                    shadow_status_code=shadow_status_code,
                    shadow_status=shadow_status,
                    shadow_confidence=float(shadow_confidence) if shadow_confidence is not None else None,
                    is_agreement=is_agreement,
                    is_shadow_more_sensitive=is_shadow_more_sensitive,
                    is_shadow_more_conservative=is_shadow_more_conservative,
                    main_latency_ms=main_latency_ms,
                    shadow_latency_ms=shadow_latency_ms,
                    prediction_time=prediction_time or datetime.now(),
                )
                db.add(record)
                db.commit()
                db.refresh(record)

                logger.debug(
                    f"影子对比已记录: tenant={effective_tid}, "
                    f"{model_type}/{node_id}, "
                    f"主v{main_version}={main_status}({main_status_code}), "
                    f"影v{shadow_version}={shadow_status}({shadow_status_code}), "
                    f"一致={is_agreement}"
                )
                return record

        except Exception as e:
            logger.error(f"记录影子对比失败: {e}")
            return None

    # ============================================================
    # 查询对比记录列表
    # ============================================================

    def list_comparisons(
        self,
        model_type: Optional[str] = None,
        node_id: Optional[str] = None,
        main_version: Optional[str] = None,
        shadow_version: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        only_disagreement: bool = False,
        limit: int = 100,
        offset: int = 0,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        查询影子对比记录列表（带租户隔离）
        """
        effective_tid = tenant_id or get_effective_tenant_id()
        if effective_tid is None:
            raise not_found_404()

        try:
            with get_db() as db:
                if db is None:
                    raise RuntimeError("数据库不可用")

                q = db.query(ShadowComparison).filter(
                    ShadowComparison.tenant_id == effective_tid
                )

                if model_type:
                    q = q.filter(ShadowComparison.model_type == model_type)
                if node_id:
                    q = q.filter(ShadowComparison.node_id == str(node_id))
                if main_version:
                    q = q.filter(ShadowComparison.main_version == main_version)
                if shadow_version:
                    q = q.filter(ShadowComparison.shadow_version == shadow_version)
                if start_time:
                    q = q.filter(ShadowComparison.prediction_time >= start_time)
                if end_time:
                    q = q.filter(ShadowComparison.prediction_time <= end_time)
                if only_disagreement:
                    q = q.filter(ShadowComparison.is_agreement == False)

                total = q.count()
                items = (
                    q.order_by(ShadowComparison.prediction_time.desc())
                    .offset(offset)
                    .limit(limit)
                    .all()
                )

                return {
                    'total': total,
                    'items': [r.to_dict() for r in items],
                }

        except Exception as e:
            logger.error(f"查询影子对比列表失败: {e}")
            raise

    # ============================================================
    # 计算统计指标
    # ============================================================

    def get_stats(
        self,
        model_type: str,
        main_version: str,
        shadow_version: str,
        node_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        计算影子模式对比统计指标

        统计指标包括:
        - 总样本数、运行天数
        - 一致率 (agreement_rate)
        - 影子更敏感率 (影子检测到异常而主版本没有)
        - 影子更保守率 (主版本检测到异常而影子没有)
        - 漏报率：主版本漏报率（主0影>0）、影子漏报率（影0主>0）
        - 按状态分桶对比：主版本每个状态下，影子版本的分布
        - 延迟对比统计
        """
        effective_tid = tenant_id or get_effective_tenant_id()
        if effective_tid is None:
            raise not_found_404()

        try:
            with get_db() as db:
                if db is None:
                    raise RuntimeError("数据库不可用")

                q = db.query(ShadowComparison).filter(
                    ShadowComparison.tenant_id == effective_tid,
                    ShadowComparison.model_type == model_type,
                    ShadowComparison.main_version == main_version,
                    ShadowComparison.shadow_version == shadow_version,
                )
                if node_id:
                    q = q.filter(ShadowComparison.node_id == str(node_id))
                if start_time:
                    q = q.filter(ShadowComparison.prediction_time >= start_time)
                if end_time:
                    q = q.filter(ShadowComparison.prediction_time <= end_time)

                total = q.count()
                if total == 0:
                    return self._empty_stats(
                        model_type, main_version, shadow_version, node_id
                    )

                agreement_count = q.filter(
                    ShadowComparison.is_agreement == True
                ).count()
                sensitive_count = q.filter(
                    ShadowComparison.is_shadow_more_sensitive == True
                ).count()
                conservative_count = q.filter(
                    ShadowComparison.is_shadow_more_conservative == True
                ).count()

                first_record = q.order_by(
                    ShadowComparison.prediction_time.asc()
                ).first()
                last_record = q.order_by(
                    ShadowComparison.prediction_time.desc()
                ).first()
                shadow_run_days = 0
                if first_record and last_record:
                    delta = last_record.prediction_time - first_record.prediction_time
                    shadow_run_days = delta.days

                main_fn_count = sensitive_count
                shadow_fn_count = conservative_count
                main_abnormal_count = q.filter(
                    ShadowComparison.main_status_code > 0
                ).count()
                shadow_abnormal_count = q.filter(
                    ShadowComparison.shadow_status_code > 0
                ).count()

                main_fn_rate = (
                    main_fn_count / total if total > 0 else 0.0
                )
                shadow_fn_rate = (
                    shadow_fn_count / total if total > 0 else 0.0
                )

                if main_fn_rate > 0:
                    fn_improvement_rate = (
                        main_fn_rate - shadow_fn_rate
                    ) / main_fn_rate
                else:
                    fn_improvement_rate = 0.0 if shadow_fn_rate == 0 else 1.0

                agreement_rate = agreement_count / total if total > 0 else 0.0
                sensitive_rate = sensitive_count / total if total > 0 else 0.0
                conservative_rate = (
                    conservative_count / total if total > 0 else 0.0
                )

                per_status_stats = self._compute_per_status_stats(
                    db, effective_tid, model_type, main_version,
                    shadow_version, node_id, start_time, end_time
                )
                latency_stats = self._compute_latency_stats(
                    db, effective_tid, model_type, main_version,
                    shadow_version, node_id, start_time, end_time
                )

                return {
                    'tenant_id': effective_tid,
                    'model_type': model_type,
                    'node_id': node_id,
                    'main_version': main_version,
                    'shadow_version': shadow_version,
                    'total_comparisons': total,
                    'shadow_run_days': shadow_run_days,
                    'first_prediction_time': (
                        first_record.prediction_time if first_record else None
                    ),
                    'last_prediction_time': (
                        last_record.prediction_time if last_record else None
                    ),
                    'agreement_count': agreement_count,
                    'agreement_rate': agreement_rate,
                    'shadow_more_sensitive_count': sensitive_count,
                    'shadow_more_sensitive_rate': sensitive_rate,
                    'shadow_more_conservative_count': conservative_count,
                    'shadow_more_conservative_rate': conservative_rate,
                    'main_abnormal_count': main_abnormal_count,
                    'shadow_abnormal_count': shadow_abnormal_count,
                    'main_false_negative_count': main_fn_count,
                    'main_false_negative_rate': main_fn_rate,
                    'shadow_false_negative_count': shadow_fn_count,
                    'shadow_false_negative_rate': shadow_fn_rate,
                    'false_negative_improvement_rate': fn_improvement_rate,
                    'per_status_stats': per_status_stats,
                    'latency_stats': latency_stats,
                }

        except Exception as e:
            logger.error(f"计算影子统计指标失败: {e}")
            raise

    def _empty_stats(
        self,
        model_type: str,
        main_version: str,
        shadow_version: str,
        node_id: Optional[str],
    ) -> Dict[str, Any]:
        """返回空统计结果"""
        return {
            'model_type': model_type,
            'node_id': node_id,
            'main_version': main_version,
            'shadow_version': shadow_version,
            'total_comparisons': 0,
            'shadow_run_days': 0,
            'first_prediction_time': None,
            'last_prediction_time': None,
            'agreement_count': 0,
            'agreement_rate': 0.0,
            'shadow_more_sensitive_count': 0,
            'shadow_more_sensitive_rate': 0.0,
            'shadow_more_conservative_count': 0,
            'shadow_more_conservative_rate': 0.0,
            'main_abnormal_count': 0,
            'shadow_abnormal_count': 0,
            'main_false_negative_count': 0,
            'main_false_negative_rate': 0.0,
            'shadow_false_negative_count': 0,
            'shadow_false_negative_rate': 0.0,
            'false_negative_improvement_rate': 0.0,
            'per_status_stats': {},
            'latency_stats': {},
        }

    def _compute_per_status_stats(
        self,
        db,
        tenant_id: int,
        model_type: str,
        main_version: str,
        shadow_version: str,
        node_id: Optional[str],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
    ) -> Dict[str, Any]:
        """按主版本状态分桶，统计影子版本的分布"""
        base_q = db.query(ShadowComparison).filter(
            ShadowComparison.tenant_id == tenant_id,
            ShadowComparison.model_type == model_type,
            ShadowComparison.main_version == main_version,
            ShadowComparison.shadow_version == shadow_version,
        )
        if node_id:
            base_q = base_q.filter(ShadowComparison.node_id == str(node_id))
        if start_time:
            base_q = base_q.filter(ShadowComparison.prediction_time >= start_time)
        if end_time:
            base_q = base_q.filter(ShadowComparison.prediction_time <= end_time)

        status_labels = {
            0: '正常', 1: '关注级预警', 2: '检查级预警',
            3: '紧急级预警', 4: '故障'
        }
        per_status = {}

        for main_code in range(5):
            main_q = base_q.filter(ShadowComparison.main_status_code == main_code)
            main_total = main_q.count()
            if main_total == 0:
                continue

            shadow_dist = {}
            for shadow_code in range(5):
                cnt = main_q.filter(
                    ShadowComparison.shadow_status_code == shadow_code
                ).count()
                if cnt > 0:
                    shadow_dist[str(shadow_code)] = {
                        'label': status_labels.get(shadow_code, f'状态{shadow_code}'),
                        'count': cnt,
                        'ratio': cnt / main_total,
                    }

            agreement_in_bucket = main_q.filter(
                ShadowComparison.is_agreement == True
            ).count()

            per_status[str(main_code)] = {
                'label': status_labels.get(main_code, f'状态{main_code}'),
                'count': main_total,
                'ratio_in_total': 0.0,
                'agreement_count': agreement_in_bucket,
                'agreement_rate_in_bucket': (
                    agreement_in_bucket / main_total if main_total > 0 else 0.0
                ),
                'shadow_distribution': shadow_dist,
            }

        total = base_q.count()
        for code, stat in per_status.items():
            stat['ratio_in_total'] = stat['count'] / total if total > 0 else 0.0

        return per_status

    def _compute_latency_stats(
        self,
        db,
        tenant_id: int,
        model_type: str,
        main_version: str,
        shadow_version: str,
        node_id: Optional[str],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
    ) -> Dict[str, Any]:
        """计算延迟统计"""
        base_q = db.query(ShadowComparison).filter(
            ShadowComparison.tenant_id == tenant_id,
            ShadowComparison.model_type == model_type,
            ShadowComparison.main_version == main_version,
            ShadowComparison.shadow_version == shadow_version,
            ShadowComparison.main_latency_ms.isnot(None),
            ShadowComparison.shadow_latency_ms.isnot(None),
        )
        if node_id:
            base_q = base_q.filter(ShadowComparison.node_id == str(node_id))
        if start_time:
            base_q = base_q.filter(ShadowComparison.prediction_time >= start_time)
        if end_time:
            base_q = base_q.filter(ShadowComparison.prediction_time <= end_time)

        records = base_q.all()
        if not records:
            return {}

        main_latencies = [r.main_latency_ms for r in records if r.main_latency_ms]
        shadow_latencies = [r.shadow_latency_ms for r in records if r.shadow_latency_ms]

        def _stats(vals: List[int]) -> Dict:
            if not vals:
                return {}
            sorted_vals = sorted(vals)
            n = len(sorted_vals)
            return {
                'count': n,
                'avg_ms': sum(sorted_vals) / n,
                'min_ms': sorted_vals[0],
                'max_ms': sorted_vals[-1],
                'p50_ms': sorted_vals[n // 2],
                'p95_ms': sorted_vals[int(n * 0.95)],
                'p99_ms': sorted_vals[int(n * 0.99)],
            }

        main_stats = _stats(main_latencies)
        shadow_stats = _stats(shadow_latencies)

        speedup_ratio = 0.0
        if main_stats and shadow_stats and shadow_stats.get('avg_ms', 0) > 0:
            speedup_ratio = main_stats['avg_ms'] / shadow_stats['avg_ms']

        return {
            'main_version': main_stats,
            'shadow_version': shadow_stats,
            'shadow_vs_main_speedup_ratio': speedup_ratio,
            'sample_count': len(records),
        }

    # ============================================================
    # 晋升规则评估
    # ============================================================

    def evaluate_promotion(
        self,
        model_type: str,
        model_id: str,
        main_version: str,
        shadow_version: str,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        评估影子版本是否满足晋升条件

        晋升规则:
        1. 影子运行 >= 7 天
        2. 一致率 > 95%
        3. 漏报率下降 > 10%  (或主版本漏报率为0且影子漏报率也为0)
        4. 样本量 >= 最小样本量

        Returns:
            评估结果，包含是否满足、各维度检查结果、详细统计
        """
        effective_tid = tenant_id or get_effective_tenant_id()
        if effective_tid is None:
            raise not_found_404()

        stats = self.get_stats(
            model_type=model_type,
            main_version=main_version,
            shadow_version=shadow_version,
            node_id=model_id,
            tenant_id=effective_tid,
        )

        check_days = stats['shadow_run_days'] >= self.required_days
        check_agreement = stats['agreement_rate'] > self.min_agreement_rate

        main_fn_rate = stats['main_false_negative_rate']
        shadow_fn_rate = stats['shadow_false_negative_rate']
        fn_improvement = stats['false_negative_improvement_rate']

        if main_fn_rate == 0 and shadow_fn_rate == 0:
            check_fn_improvement = True
        elif main_fn_rate == 0 and shadow_fn_rate > 0:
            check_fn_improvement = False
        else:
            check_fn_improvement = fn_improvement > self.min_fn_improvement_rate

        check_sample_size = stats['total_comparisons'] >= self.min_sample_size

        all_passed = (
            check_days
            and check_agreement
            and check_fn_improvement
            and check_sample_size
        )

        checks = {
            'shadow_run_days': {
                'label': '影子运行天数',
                'required': f'>= {self.required_days} 天',
                'actual': stats['shadow_run_days'],
                'passed': check_days,
            },
            'agreement_rate': {
                'label': '预测一致率',
                'required': f'> {self.min_agreement_rate:.1%}',
                'actual': f"{stats['agreement_rate']:.2%}",
                'actual_value': stats['agreement_rate'],
                'passed': check_agreement,
            },
            'false_negative_improvement': {
                'label': '漏报率下降比例',
                'required': f'> {self.min_fn_improvement_rate:.1%}',
                'actual': f"{fn_improvement:.2%}",
                'actual_value': fn_improvement,
                'detail': f"主版本漏报率={main_fn_rate:.2%}, 影子版本漏报率={shadow_fn_rate:.2%}",
                'passed': check_fn_improvement,
            },
            'sample_size': {
                'label': '最小样本量',
                'required': f'>= {self.min_sample_size}',
                'actual': stats['total_comparisons'],
                'passed': check_sample_size,
            },
        }

        missing_reasons = []
        if not check_days:
            missing_reasons.append(
                f"影子运行仅 {stats['shadow_run_days']} 天，需满 {self.required_days} 天"
            )
        if not check_agreement:
            missing_reasons.append(
                f"一致率 {stats['agreement_rate']:.2%}，需 > {self.min_agreement_rate:.1%}"
            )
        if not check_fn_improvement:
            missing_reasons.append(
                f"漏报率下降 {fn_improvement:.2%}，需 > {self.min_fn_improvement_rate:.1%}"
            )
        if not check_sample_size:
            missing_reasons.append(
                f"样本量 {stats['total_comparisons']}，需 >= {self.min_sample_size}"
            )

        return {
            'tenant_id': effective_tid,
            'model_type': model_type,
            'model_id': model_id,
            'main_version': main_version,
            'shadow_version': shadow_version,
            'promotable': all_passed,
            'checks': checks,
            'missing_reasons': missing_reasons,
            'stats': stats,
        }

    # ============================================================
    # 晋升建议工单管理
    # ============================================================

    def create_promotion_suggestion(
        self,
        model_type: str,
        model_id: str,
        main_version: str,
        shadow_version: str,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        创建版本晋升建议工单

        先评估是否满足条件，满足则创建建议工单并联动系统工单。
        """
        if is_audit_mode():
            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail={
                    'error': 'Forbidden',
                    'message': '审计模式为只读，无法创建晋升建议',
                },
            )

        effective_tid = tenant_id or get_effective_tenant_id()
        if effective_tid is None:
            raise not_found_404()

        evaluation = self.evaluate_promotion(
            model_type=model_type,
            model_id=model_id,
            main_version=main_version,
            shadow_version=shadow_version,
            tenant_id=effective_tid,
        )

        if not evaluation['promotable']:
            return {
                'success': False,
                'reason': '不满足晋升条件',
                'evaluation': evaluation,
            }

        try:
            with get_db() as db:
                if db is None:
                    raise RuntimeError("数据库不可用")

                existing = db.query(ModelPromotionSuggestion).filter(
                    ModelPromotionSuggestion.tenant_id == effective_tid,
                    ModelPromotionSuggestion.model_type == model_type,
                    ModelPromotionSuggestion.model_id == str(model_id),
                    ModelPromotionSuggestion.main_version == main_version,
                    ModelPromotionSuggestion.shadow_version == shadow_version,
                    ModelPromotionSuggestion.status.in_(['pending', 'approved']),
                ).first()

                if existing:
                    return {
                        'success': False,
                        'reason': '已存在待审批或已批准的晋升建议',
                        'suggestion': existing.to_dict(),
                    }

                suggestion_no = self._generate_suggestion_no(
                    db, model_type, str(model_id)
                )

                stats = evaluation['stats']
                suggestion = ModelPromotionSuggestion(
                    tenant_id=effective_tid,
                    model_type=model_type,
                    model_id=str(model_id),
                    main_version=main_version,
                    shadow_version=shadow_version,
                    suggestion_no=suggestion_no,
                    status='pending',
                    agreement_rate=stats['agreement_rate'],
                    shadow_more_sensitive_rate=stats['shadow_more_sensitive_rate'],
                    shadow_more_conservative_rate=stats['shadow_more_conservative_rate'],
                    main_false_negative_rate=stats['main_false_negative_rate'],
                    shadow_false_negative_rate=stats['shadow_false_negative_rate'],
                    false_negative_improvement_rate=stats['false_negative_improvement_rate'],
                    shadow_run_days=stats['shadow_run_days'],
                    total_comparisons=stats['total_comparisons'],
                    per_status_stats=json.dumps(
                        stats['per_status_stats'], ensure_ascii=False
                    ),
                    latency_stats=json.dumps(
                        stats.get('latency_stats', {}), ensure_ascii=False
                    ),
                )

                work_order_id = self._create_linked_work_order(
                    db, suggestion, stats
                )
                if work_order_id:
                    suggestion.work_order_id = work_order_id

                db.add(suggestion)
                db.commit()
                db.refresh(suggestion)

                logger.info(
                    f"晋升建议已创建: {suggestion_no}, "
                    f"tenant={effective_tid}, "
                    f"{model_type}/{model_id}, "
                    f"{main_version} -> {shadow_version}"
                )

                return {
                    'success': True,
                    'suggestion': suggestion.to_dict(),
                    'evaluation': evaluation,
                }

        except Exception as e:
            logger.error(f"创建晋升建议失败: {e}")
            raise

    def _generate_suggestion_no(self, db, model_type: str, model_id: str) -> str:
        """生成唯一的晋升建议编号"""
        now = datetime.now()
        prefix = now.strftime(f"PS%Y%m%d{model_type.upper()}")
        short_id = str(uuid.uuid4())[:6].upper()
        return f"{prefix}{short_id}"

    def _create_linked_work_order(
        self,
        db,
        suggestion: ModelPromotionSuggestion,
        stats: Dict[str, Any],
    ) -> Optional[int]:
        """联动创建系统工单"""
        try:
            from app.services.alert.work_order_service import WorkOrderService
            from app.utils.database import WorkOrder

            wo_service = WorkOrderService()
            title = (
                f"[模型晋升建议] {suggestion.model_type.upper()} "
                f"{suggestion.model_id} {suggestion.main_version} -> {suggestion.shadow_version}"
            )

            description_lines = [
                f"模型类型: {suggestion.model_type}",
                f"模型ID: {suggestion.model_id}",
                f"主版本: {suggestion.main_version}",
                f"影子版本: {suggestion.shadow_version}",
                f"",
                f"=== 晋升评估指标 ===",
                f"一致率: {stats['agreement_rate']:.2%}",
                f"影子更敏感率: {stats['shadow_more_sensitive_rate']:.2%}",
                f"影子更保守率: {stats['shadow_more_conservative_rate']:.2%}",
                f"主版本漏报率: {stats['main_false_negative_rate']:.2%}",
                f"影子版本漏报率: {stats['shadow_false_negative_rate']:.2%}",
                f"漏报率下降: {stats['false_negative_improvement_rate']:.2%}",
                f"影子运行天数: {stats['shadow_run_days']} 天",
                f"总对比样本: {stats['total_comparisons']}",
                f"",
                f"建议编号: {suggestion.suggestion_no}",
            ]

            work_order = wo_service.create_manual_work_order(
                title=title,
                description='\n'.join(description_lines),
                priority='high',
                node_type=suggestion.model_type,
                node_id=suggestion.model_id,
                alert_level=2,
                creator_id='system',
                creator_name='影子模式自动晋升',
                due_hours=72,
                extra_info={
                    'type': 'model_promotion_suggestion',
                    'suggestion_no': suggestion.suggestion_no,
                    'main_version': suggestion.main_version,
                    'shadow_version': suggestion.shadow_version,
                },
            )

            if work_order:
                logger.info(
                    f"晋升建议联动工单已创建: {work_order.order_no}"
                )
                return work_order.id
            return None

        except Exception as e:
            logger.warning(f"创建晋升联动工单失败（不影响主流程）: {e}")
            return None

    def list_promotion_suggestions(
        self,
        status: Optional[str] = None,
        model_type: Optional[str] = None,
        model_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """查询晋升建议工单列表"""
        effective_tid = tenant_id or get_effective_tenant_id()
        if effective_tid is None:
            raise not_found_404()

        try:
            with get_db() as db:
                if db is None:
                    raise RuntimeError("数据库不可用")

                q = db.query(ModelPromotionSuggestion).filter(
                    ModelPromotionSuggestion.tenant_id == effective_tid
                )
                if status:
                    q = q.filter(ModelPromotionSuggestion.status == status)
                if model_type:
                    q = q.filter(ModelPromotionSuggestion.model_type == model_type)
                if model_id:
                    q = q.filter(ModelPromotionSuggestion.model_id == str(model_id))

                total = q.count()
                items = (
                    q.order_by(ModelPromotionSuggestion.create_time.desc())
                    .offset(offset)
                    .limit(limit)
                    .all()
                )

                return {
                    'total': total,
                    'items': [s.to_dict() for s in items],
                }

        except Exception as e:
            logger.error(f"查询晋升建议列表失败: {e}")
            raise

    def approve_promotion(
        self,
        suggestion_id: int,
        approver_id: Optional[str] = None,
        approver_name: Optional[str] = None,
        approve_note: Optional[str] = None,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        审批通过晋升建议，并自动切换活动版本
        """
        if is_audit_mode():
            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail={
                    'error': 'Forbidden',
                    'message': '审计模式为只读，无法审批晋升',
                },
            )

        effective_tid = tenant_id or get_effective_tenant_id()
        if effective_tid is None:
            raise not_found_404()

        try:
            with get_db() as db:
                if db is None:
                    raise RuntimeError("数据库不可用")

                suggestion = db.query(ModelPromotionSuggestion).filter(
                    ModelPromotionSuggestion.id == suggestion_id,
                    ModelPromotionSuggestion.tenant_id == effective_tid,
                ).first()

                if suggestion is None:
                    raise not_found_404("晋升建议不存在")
                enforce_tenant_access(suggestion.tenant_id, suggestion.id, "ModelPromotionSuggestion")

                if suggestion.status != 'pending':
                    return {
                        'success': False,
                        'reason': f'当前状态为 {suggestion.status}，无法审批',
                    }

                suggestion.status = 'approved'
                suggestion.approver_id = approver_id
                suggestion.approver_name = approver_name
                suggestion.approve_time = datetime.now()
                suggestion.approve_note = approve_note

                from app.services.model_version_service import get_model_version_service
                mv_service = get_model_version_service()

                try:
                    activate_result = mv_service.activate_version(
                        model_type=suggestion.model_type,
                        node_id=suggestion.model_id,
                        version=suggestion.shadow_version,
                        tenant_id=effective_tid,
                    )
                    suggestion.status = 'executed'
                    logger.info(
                        f"版本晋升执行成功: {suggestion.suggestion_no}, "
                        f"{suggestion.model_type}/{suggestion.model_id} "
                        f"{suggestion.main_version} -> {suggestion.shadow_version}"
                    )
                except Exception as e:
                    logger.error(
                        f"版本切换失败，晋升建议保持 approved 状态: {e}"
                    )
                    return {
                        'success': False,
                        'reason': f'版本切换失败: {str(e)}',
                        'suggestion': suggestion.to_dict(),
                    }

                db.commit()
                db.refresh(suggestion)

                return {
                    'success': True,
                    'suggestion': suggestion.to_dict(),
                }

        except Exception as e:
            logger.error(f"审批晋升失败: {e}")
            raise

    def reject_promotion(
        self,
        suggestion_id: int,
        approver_id: Optional[str] = None,
        approver_name: Optional[str] = None,
        approve_note: Optional[str] = None,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """驳回晋升建议"""
        if is_audit_mode():
            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail={
                    'error': 'Forbidden',
                    'message': '审计模式为只读，无法驳回晋升',
                },
            )

        effective_tid = tenant_id or get_effective_tenant_id()
        if effective_tid is None:
            raise not_found_404()

        try:
            with get_db() as db:
                if db is None:
                    raise RuntimeError("数据库不可用")

                suggestion = db.query(ModelPromotionSuggestion).filter(
                    ModelPromotionSuggestion.id == suggestion_id,
                    ModelPromotionSuggestion.tenant_id == effective_tid,
                ).first()

                if suggestion is None:
                    raise not_found_404("晋升建议不存在")
                enforce_tenant_access(suggestion.tenant_id, suggestion.id, "ModelPromotionSuggestion")

                if suggestion.status != 'pending':
                    return {
                        'success': False,
                        'reason': f'当前状态为 {suggestion.status}，无法驳回',
                    }

                suggestion.status = 'rejected'
                suggestion.approver_id = approver_id
                suggestion.approver_name = approver_name
                suggestion.approve_time = datetime.now()
                suggestion.approve_note = approve_note

                db.commit()
                db.refresh(suggestion)

                logger.info(
                    f"晋升建议已驳回: {suggestion.suggestion_no}"
                )
                return {
                    'success': True,
                    'suggestion': suggestion.to_dict(),
                }

        except Exception as e:
            logger.error(f"驳回晋升失败: {e}")
            raise


_shadow_service = None


def get_shadow_comparison_service() -> ShadowComparisonService:
    """获取影子模式对比服务单例"""
    global _shadow_service
    if _shadow_service is None:
        _shadow_service = ShadowComparisonService()
    return _shadow_service
