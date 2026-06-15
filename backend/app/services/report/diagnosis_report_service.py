"""
智能诊断报告服务

提供基于LLM的智能诊断报告生成功能，包括：
1. 单次预测的诊断报告生成
2. 周报/月报生成（按 bolt_id/flange_id 聚合）
3. LLM降级支持
4. Token用量和延迟日志

使用示例:
    from app.services.report import get_diagnosis_report_service
    
    service = get_diagnosis_report_service()
    report = service.generate_single_report(
        status="关注级预警",
        risk_score=6.5,
        node_type="bolt",
        node_id="B001"
    )
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass
from loguru import logger

from app.core.llm_client import (
    LLMClient,
    DiagnosisReport,
    UrgencyLevel,
    llm_client,
)
from app.utils.config import config


class ReportType(Enum):
    """报告类型"""
    SINGLE = "single"       # 单次诊断报告
    WEEKLY = "weekly"       # 周报
    MONTHLY = "monthly"     # 月报


@dataclass
class PeriodicReportData:
    """
    周期报告数据（周报/月报用）
    
    用于聚合一段时间内的预测数据。
    """
    node_id: str
    node_type: str
    period_start: datetime
    period_end: datetime
    prediction_count: int = 0
    status_distribution: Dict[str, int] = None
    avg_risk_score: float = 0.0
    min_risk_score: float = 10.0
    max_risk_score: float = 0.0
    trend: str = "stable"
    fault_types: List[str] = None
    recent_values: List[float] = None
    historical_incidents: int = 0
    max_status: str = "正常"
    max_status_code: int = 0


class DiagnosisReportService:
    """
    智能诊断报告服务
    
    封装LLM诊断报告生成逻辑，提供统一的报告生成接口。
    支持LLM不可用时的模板降级，以及全局开关控制。
    """
    
    def __init__(self, llm: Optional[LLMClient] = None):
        """
        初始化报告服务
        
        Args:
            llm: LLM客户端实例，None则使用全局实例
        """
        self.llm = llm or llm_client
        self.enabled = config.get('llm.enabled', True)
        
        logger.info(
            f"诊断报告服务初始化完成: enabled={self.enabled}, "
            f"provider={self.llm.provider if hasattr(self.llm, 'provider') else 'unknown'}"
        )
    
    def is_enabled(self) -> bool:
        """检查报告服务是否启用"""
        return self.enabled and self.llm.is_enabled()
    
    # ---------- 单次诊断报告 ----------
    
    async def generate_single_report_async(
        self,
        status: str,
        risk_score: float,
        node_type: str = "bolt",
        node_id: str = "",
        fault_type: Optional[str] = None,
        trend: Optional[str] = None,
        recent_values: Optional[List[float]] = None,
        historical_incidents: Optional[int] = None,
    ) -> DiagnosisReport:
        """
        生成单次诊断报告（异步）
        
        Args:
            status: 状态（正常/关注级预警/检查级预警/紧急级预警/故障）
            risk_score: 风险评分(0-10)，分数越低风险越高
            node_type: 节点类型（bolt/flange）
            node_id: 节点ID
            fault_type: 故障类型
            trend: 趋势
            recent_values: 近期数值列表
            historical_incidents: 历史事件数
            
        Returns:
            DiagnosisReport: 诊断报告
        """
        if not self.is_enabled():
            logger.debug("LLM报告功能未启用，使用模板生成")
        
        report = await self.llm.generate_diagnosis_report(
            status=status,
            risk_score=risk_score,
            fault_type=fault_type,
            trend=trend,
            recent_values=recent_values,
            historical_incidents=historical_incidents,
            node_type=node_type,
            node_id=node_id,
        )
        
        return report
    
    def generate_single_report(
        self,
        status: str,
        risk_score: float,
        **kwargs
    ) -> DiagnosisReport:
        """
        生成单次诊断报告（同步）
        
        Args:
            status: 状态
            risk_score: 风险评分
            **kwargs: 其他参数
            
        Returns:
            DiagnosisReport: 诊断报告
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.generate_single_report_async(
                status=status,
                risk_score=risk_score,
                **kwargs
            )
        )
    
    # ---------- 周期报告（周报/月报） ----------
    
    async def generate_periodic_report_async(
        self,
        node_id: str,
        node_type: str,
        report_type: ReportType,
        period_data: PeriodicReportData,
    ) -> Dict[str, Any]:
        """
        生成周期报告（周报/月报，异步）
        
        Args:
            node_id: 节点ID
            node_type: 节点类型
            report_type: 报告类型
            period_data: 周期数据
            
        Returns:
            Dict: 报告结果
        """
        node_label = "螺栓" if node_type == "bolt" else "法兰面"
        period_label = "周" if report_type == ReportType.WEEKLY else "月"
        
        # 构建诊断摘要
        summary = await self._build_periodic_summary(
            node_id=node_id,
            node_type=node_type,
            node_label=node_label,
            period_label=period_label,
            period_data=period_data,
        )
        
        # 生成推荐措施
        recommendations = self._build_periodic_recommendations(
            period_data=period_data,
            node_type=node_type,
        )
        
        # 计算整体紧急程度
        urgency = self._calculate_periodic_urgency(period_data)
        
        # 构建完整报告
        report = {
            "report_type": report_type.value,
            "node_id": node_id,
            "node_type": node_type,
            "period_start": period_data.period_start,
            "period_end": period_data.period_end,
            "diagnosis_summary": summary,
            "recommended_actions": recommendations,
            "urgency_level": urgency.value,
            "statistics": {
                "prediction_count": period_data.prediction_count,
                "avg_risk_score": round(period_data.avg_risk_score, 2),
                "min_risk_score": round(period_data.min_risk_score, 2),
                "max_risk_score": round(period_data.max_risk_score, 2),
                "status_distribution": period_data.status_distribution or {},
                "trend": period_data.trend,
                "max_status": period_data.max_status,
                "fault_types": period_data.fault_types or [],
            },
            "generated_at": datetime.now(),
            "model": self.llm.provider if hasattr(self.llm, 'provider') else "unknown",
            "is_fallback": self._is_fallback_mode(),
        }
        
        logger.info(
            f"[Report] 生成{period_label}报: node={node_type}/{node_id}, "
            f"urgency={urgency.value}, predictions={period_data.prediction_count}"
        )
        
        return report
    
    def generate_periodic_report(
        self,
        node_id: str,
        node_type: str,
        report_type: ReportType,
        period_data: PeriodicReportData,
    ) -> Dict[str, Any]:
        """
        生成周期报告（同步）
        
        Args:
            node_id: 节点ID
            node_type: 节点类型
            report_type: 报告类型
            period_data: 周期数据
            
        Returns:
            Dict: 报告结果
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.generate_periodic_report_async(
                node_id=node_id,
                node_type=node_type,
                report_type=report_type,
                period_data=period_data,
            )
        )
    
    async def _build_periodic_summary(
        self,
        node_id: str,
        node_type: str,
        node_label: str,
        period_label: str,
        period_data: PeriodicReportData,
    ) -> str:
        """
        构建周期报告摘要
        
        如果LLM可用，使用LLM生成；否则使用模板生成。
        """
        if not self.is_enabled():
            return self._build_periodic_summary_template(
                node_label=node_label,
                node_id=node_id,
                period_label=period_label,
                period_data=period_data,
            )
        
        # 构建LLM提示词
        status_dist_str = ", ".join(
            [f"{k}:{v}次" for k, v in (period_data.status_distribution or {}).items()]
        )
        
        prompt = f"""你是一位专业的工业设备故障诊断专家。请根据以下{node_label}的本{period_label}监测数据，生成一份周期诊断摘要。

【节点信息】
节点类型: {node_label}
节点ID: {node_id}
报告周期: {period_label}报
统计周期: {period_data.period_start.strftime('%Y-%m-%d')} 至 {period_data.period_end.strftime('%Y-%m-%d')}

【统计数据】
- 预测次数: {period_data.prediction_count}次
- 平均风险评分: {period_data.avg_risk_score:.2f}/10
- 最低风险评分: {period_data.min_risk_score:.2f}/10（最高风险）
- 最高风险评分: {period_data.max_risk_score:.2f}/10（最低风险）
- 状态分布: {status_dist_str}
- 整体趋势: {period_data.trend}
- 本周期最高状态: {period_data.max_status}
- 出现的故障类型: {', '.join(period_data.fault_types) if period_data.fault_types else '无'}
- 历史同类事件: {period_data.historical_incidents}次

【要求】
请用150-200字总结本{period_label}的整体状况、主要风险点、趋势变化和需要关注的问题。
语言要专业、简洁、客观。
"""
        
        try:
            response = await self.llm.generate(prompt, max_tokens=500, temperature=0.7)
            if response.success:
                summary = response.content.strip()
                # 限制在200字以内
                if len(summary) > 300:
                    summary = summary[:297] + "..."
                return summary
        except Exception as e:
            logger.warning(f"LLM生成周期摘要失败，使用模板: {e}")
        
        # 降级到模板
        return self._build_periodic_summary_template(
            node_label=node_label,
            node_id=node_id,
            period_label=period_label,
            period_data=period_data,
        )
    
    def _build_periodic_summary_template(
        self,
        node_label: str,
        node_id: str,
        period_label: str,
        period_data: PeriodicReportData,
    ) -> str:
        """使用模板生成周期报告摘要"""
        status_dist = period_data.status_distribution or {}
        abnormal_count = sum(
            v for k, v in status_dist.items() if k not in ("正常", "0")
        )
        
        trend_map = {
            "stable": "整体平稳",
            "decreasing": "呈下降趋势，风险有所增加",
            "increasing": "呈上升趋势，风险有所降低",
            "fluctuating": "波动较大",
            "worsening": "持续恶化，需重点关注",
            "improving": "持续好转",
        }
        trend_desc = trend_map.get(period_data.trend, "状态稳定")
        
        fault_desc = ""
        if period_data.fault_types:
            fault_type_names = []
            for ft in period_data.fault_types:
                ft_map = {
                    "loosening": "松动",
                    "preload_decrease": "预紧力下降",
                    "severe_anomaly": "严重异常",
                    "failure": "故障",
                }
                fault_type_names.append(ft_map.get(ft, ft))
            fault_desc = f"，出现{ '、'.join(fault_type_names)}等异常类型"
        
        summary = (
            f"{node_label}{node_id}本{period_label}共监测{period_data.prediction_count}次，"
            f"平均风险评分{period_data.avg_risk_score:.2f}/10，"
            f"最高状态为「{period_data.max_status}」。"
            f"{trend_desc}{fault_desc}。"
            f"异常预警{abnormal_count}次，建议关注状态变化趋势，"
            f"按风险等级制定相应的维护计划。"
        )
        
        # 限制在200字以内
        if len(summary) > 200:
            summary = summary[:197] + "..."
        
        return summary
    
    def _build_periodic_recommendations(
        self,
        period_data: PeriodicReportData,
        node_type: str,
    ) -> List[str]:
        """构建周期报告推荐措施"""
        node_label = "螺栓" if node_type == "bolt" else "法兰面"
        recommendations = []
        
        urgency = self._calculate_periodic_urgency(period_data)
        
        if urgency == UrgencyLevel.CRITICAL:
            recommendations = [
                f"立即组织专项检查，对该{node_label}进行全面检测",
                "评估设备安全风险，必要时停机检修",
                "制定紧急维修方案，准备备件和工具",
                "加密监测频率，密切跟踪状态变化",
                "分析根因，制定长期改进措施",
                "建立专项档案，记录完整的处理过程",
            ]
        elif urgency == UrgencyLevel.HIGH:
            recommendations = [
                "安排专业人员进行现场检查和评估",
                "增加监测频率，重点关注异常变化",
                "制定预防性维护计划，优先安排检修",
                "检查相关设备，排查潜在关联影响",
                "准备必要的备件和维修资源",
                "跟踪状态变化，及时调整维护策略",
            ]
        elif urgency == UrgencyLevel.MEDIUM:
            recommendations = [
                "加强日常监测，关注趋势变化",
                "在下次例行维护时进行重点检查",
                "分析异常原因，制定改进措施",
                "检查周边设备运行状态，排除干扰",
                "做好维护记录，积累历史数据",
            ]
        else:
            recommendations = [
                "保持常规监测频率",
                "按计划执行例行维护",
                "关注数据质量，确保采集正常",
                "定期回顾运行状态，优化维护策略",
            ]
        
        # 根据故障类型补充建议
        if period_data.fault_types:
            if "loosening" in period_data.fault_types:
                recommendations.insert(0, "重点检查螺栓预紧力，按规程进行复紧")
            if "preload_decrease" in period_data.fault_types:
                recommendations.insert(0, "分析预紧力下降原因，评估密封性能")
        
        return recommendations[:8]
    
    def _calculate_periodic_urgency(self, period_data: PeriodicReportData) -> UrgencyLevel:
        """计算周期报告的整体紧急程度"""
        status_code_map = {
            "正常": 0,
            "关注级预警": 1,
            "检查级预警": 2,
            "紧急级预警": 3,
            "故障": 4,
        }
        
        max_status_code = status_code_map.get(period_data.max_status, 0)
        avg_risk = period_data.avg_risk_score
        
        # 综合判断
        if max_status_code >= 4 or avg_risk <= 2:
            return UrgencyLevel.CRITICAL
        elif max_status_code >= 3 or avg_risk <= 4:
            return UrgencyLevel.HIGH
        elif max_status_code >= 1 or avg_risk <= 7:
            return UrgencyLevel.MEDIUM
        else:
            return UrgencyLevel.LOW
    
    def _is_fallback_mode(self) -> bool:
        """判断是否处于降级模式"""
        if not self.enabled:
            return True
        if not hasattr(self.llm, 'provider'):
            return True
        return self.llm.provider == 'local'
    
    # ---------- 从历史预测数据构建周期数据 ----------
    
    def build_period_data_from_predictions(
        self,
        predictions: List[Dict[str, Any]],
        node_id: str,
        node_type: str,
        report_type: ReportType,
    ) -> PeriodicReportData:
        """
        从历史预测记录构建周期报告数据
        
        Args:
            predictions: 预测记录列表
            node_id: 节点ID
            node_type: 节点类型
            report_type: 报告类型
            
        Returns:
            PeriodicReportData: 周期数据
        """
        if not predictions:
            now = datetime.now()
            if report_type == ReportType.WEEKLY:
                start = now - timedelta(days=7)
            else:
                start = now - timedelta(days=30)
            return PeriodicReportData(
                node_id=node_id,
                node_type=node_type,
                period_start=start,
                period_end=now,
            )
        
        status_dist: Dict[str, int] = {}
        total_risk = 0.0
        min_risk = 10.0
        max_risk = 0.0
        fault_types_set = set()
        all_values: List[float] = []
        max_status_code = 0
        max_status = "正常"
        
        status_code_map = {
            "正常": 0,
            "关注级预警": 1,
            "检查级预警": 2,
            "紧急级预警": 3,
            "故障": 4,
        }
        
        period_start = None
        period_end = None
        
        for pred in predictions:
            status = pred.get('status', '正常')
            risk_score = float(pred.get('risk_score', 5.0))
            fault_type = pred.get('fault_type')
            recent_val = pred.get('recent_value')
            
            # 状态分布
            status_dist[status] = status_dist.get(status, 0) + 1
            
            # 风险统计
            total_risk += risk_score
            min_risk = min(min_risk, risk_score)
            max_risk = max(max_risk, risk_score)
            
            # 最高状态
            code = status_code_map.get(status, 0)
            if code > max_status_code:
                max_status_code = code
                max_status = status
            
            # 故障类型
            if fault_type:
                fault_types_set.add(fault_type)
            
            # 数值收集
            if recent_val is not None:
                all_values.append(float(recent_val))
            
            # 时间范围
            pred_time = pred.get('prediction_time') or pred.get('create_time')
            if pred_time:
                if isinstance(pred_time, str):
                    try:
                        pred_time = datetime.fromisoformat(pred_time)
                    except ValueError:
                        pred_time = None
                if pred_time:
                    if period_start is None or pred_time < period_start:
                        period_start = pred_time
                    if period_end is None or pred_time > period_end:
                        period_end = pred_time
        
        count = len(predictions)
        avg_risk = total_risk / count if count > 0 else 5.0
        
        # 判断趋势
        trend = self._detect_trend(predictions)
        
        # 时间范围兜底
        now = datetime.now()
        if period_start is None:
            if report_type == ReportType.WEEKLY:
                period_start = now - timedelta(days=7)
            else:
                period_start = now - timedelta(days=30)
        if period_end is None:
            period_end = now
        
        return PeriodicReportData(
            node_id=node_id,
            node_type=node_type,
            period_start=period_start,
            period_end=period_end,
            prediction_count=count,
            status_distribution=status_dist,
            avg_risk_score=avg_risk,
            min_risk_score=min_risk,
            max_risk_score=max_risk,
            trend=trend,
            fault_types=list(fault_types_set),
            recent_values=all_values[-20:] if all_values else None,
            historical_incidents=0,
            max_status=max_status,
            max_status_code=max_status_code,
        )
    
    def _detect_trend(self, predictions: List[Dict[str, Any]]) -> str:
        """检测趋势"""
        if len(predictions) < 3:
            return "stable"
        
        # 按时间排序
        sorted_preds = sorted(
            predictions,
            key=lambda p: p.get('prediction_time') or p.get('create_time', ''),
        )
        
        # 简单的趋势判断：比较前1/3和后1/3的平均风险评分
        n = len(sorted_preds)
        first_third = sorted_preds[:n // 3]
        last_third = sorted_preds[-n // 3:]
        
        if not first_third or not last_third:
            return "stable"
        
        first_avg = sum(
            float(p.get('risk_score', 5.0)) for p in first_third
        ) / len(first_third)
        last_avg = sum(
            float(p.get('risk_score', 5.0)) for p in last_third
        ) / len(last_third)
        
        diff = first_avg - last_avg  # 风险评分降低 = 风险升高
        
        if diff > 1.0:
            return "worsening"  # 恶化
        elif diff > 0.3:
            return "decreasing"  # 下降（风险增加）
        elif diff < -1.0:
            return "improving"  # 好转
        elif diff < -0.3:
            return "increasing"  # 上升（风险降低）
        else:
            # 检查波动
            risks = [float(p.get('risk_score', 5.0)) for p in sorted_preds]
            if len(risks) >= 3:
                variance = sum((r - sum(risks)/len(risks))**2 for r in risks) / len(risks)
                if variance > 2.0:
                    return "fluctuating"
            return "stable"


# 单例实例
_report_service: Optional[DiagnosisReportService] = None


def get_diagnosis_report_service() -> DiagnosisReportService:
    """
    获取诊断报告服务单例
    
    Returns:
        DiagnosisReportService: 报告服务实例
    """
    global _report_service
    if _report_service is None:
        _report_service = DiagnosisReportService()
    return _report_service
