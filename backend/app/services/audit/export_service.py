"""
监管导出服务

按时间范围导出审计包：
1. CSV 格式导出
2. PDF 格式导出（含可解释性报告摘要）
"""

import csv
import io
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from loguru import logger

from app.utils.database import get_db, PredictionAudit
from app.services.audit.explainability_service import ExplainabilityService


class ExportService:
    """
    监管导出服务

    按时间范围导出审计包，支持 CSV 和 PDF 格式。
    """

    def __init__(self):
        self.explainability_service = ExplainabilityService()
        logger.info("监管导出服务初始化完成")

    def _query_audits_for_export(
        self,
        start_time: datetime,
        end_time: datetime,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> List[PredictionAudit]:
        """
        查询指定时间范围内的审计记录
        """
        with get_db() as db:
            if db is None:
                return []

            query = db.query(PredictionAudit).filter(
                PredictionAudit.create_time >= start_time,
                PredictionAudit.create_time <= end_time,
            )

            if node_type:
                query = query.filter(
                    PredictionAudit.node_type == node_type
                )
            if node_id:
                query = query.filter(
                    PredictionAudit.node_id == str(node_id)
                )

            return query.order_by(
                PredictionAudit.create_time.asc()
            ).all()

    def export_csv(
        self,
        start_time: datetime,
        end_time: datetime,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> str:
        """
        导出 CSV 格式审计包

        Args:
            start_time: 起始时间
            end_time: 结束时间
            node_type: 节点类型过滤
            node_id: 节点ID过滤

        Returns:
            CSV 内容字符串
        """
        records = self._query_audits_for_export(
            start_time, end_time, node_type, node_id
        )

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            '审计ID', '预测ID', '节点类型', '节点ID',
            '输入哈希', '模型版本', '模型类型',
            '特征均值', '特征标准差', '特征最小值', '特征最大值', '数据点数',
            '最终状态码', '最终状态', '置信度', '风险评分',
            '策略类型', '策略版本',
            '风险因子分解(主导因子)', '规则命中项',
            '保留年限', '创建时间', '过期时间',
        ])

        for record in records:
            feature_summary = self._safe_json_loads(
                record.feature_summary, {}
            )
            final_decision = self._safe_json_loads(
                record.final_decision, {}
            )
            explainability = self._safe_json_loads(
                record.explainability, {}
            )

            risk_decomp = explainability.get(
                'risk_factor_decomposition', {}
            )
            dominant = risk_decomp.get('dominant_factor', '')

            rule_hits = explainability.get('rule_hits', [])
            hit_names = '; '.join(
                r.get('rule_name', '')
                for r in rule_hits
                if r.get('hit')
            )

            writer.writerow([
                record.id,
                record.prediction_id,
                record.node_type,
                record.node_id,
                record.input_hash,
                record.model_version,
                record.model_type,
                feature_summary.get('mean', ''),
                feature_summary.get('std', ''),
                feature_summary.get('min', ''),
                feature_summary.get('max', ''),
                feature_summary.get('count', ''),
                final_decision.get('status_code', ''),
                final_decision.get('status', ''),
                final_decision.get('confidence', ''),
                final_decision.get('risk_score', ''),
                record.strategy_type,
                record.strategy_version,
                dominant,
                hit_names,
                record.retention_years,
                record.create_time.isoformat()
                if record.create_time else '',
                record.expire_time.isoformat()
                if record.expire_time else '',
            ])

        logger.info(
            f"CSV审计包导出完成: {len(records)} 条记录, "
            f"时间范围 {start_time} ~ {end_time}"
        )
        return output.getvalue()

    def export_pdf_data(
        self,
        start_time: datetime,
        end_time: datetime,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        导出 PDF 审计包所需的结构化数据

        PDF 生成需要 HTML 模板和结构化数据，
        此方法返回完整的结构化数据供 PDF 渲染使用。

        Args:
            start_time: 起始时间
            end_time: 结束时间
            node_type: 节点类型过滤
            node_id: 节点ID过滤

        Returns:
            PDF 渲染数据字典
        """
        records = self._query_audits_for_export(
            start_time, end_time, node_type, node_id
        )

        report_items = []
        for record in records:
            feature_summary = self._safe_json_loads(
                record.feature_summary, {}
            )
            final_decision = self._safe_json_loads(
                record.final_decision, {}
            )
            intermediate = self._safe_json_loads(
                record.intermediate_results, {}
            )
            explainability = self._safe_json_loads(
                record.explainability, {}
            )

            item = {
                'prediction_id': record.prediction_id,
                'node_type': record.node_type,
                'node_id': record.node_id,
                'input_hash': record.input_hash,
                'model_version': record.model_version,
                'model_type': record.model_type,
                'feature_summary': feature_summary,
                'final_decision': final_decision,
                'intermediate_results': intermediate,
                'strategy_version': record.strategy_version,
                'strategy_type': record.strategy_type,
                'explainability': {
                    'risk_factor_decomposition': explainability.get(
                        'risk_factor_decomposition', {}
                    ),
                    'rule_hits': explainability.get('rule_hits', []),
                    'key_timesteps': explainability.get(
                        'key_timesteps', []
                    ),
                    'attention_weights': explainability.get(
                        'attention_weights', {}
                    ),
                },
                'create_time': (
                    record.create_time.isoformat()
                    if record.create_time else ''
                ),
                'expire_time': (
                    record.expire_time.isoformat()
                    if record.expire_time else ''
                ),
            }
            report_items.append(item)

        summary = self._generate_export_summary(report_items)

        export_data = {
            'title': '合规审计报告',
            'export_time': datetime.now().isoformat(),
            'time_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
            },
            'filters': {
                'node_type': node_type,
                'node_id': node_id,
            },
            'summary': summary,
            'records': report_items,
            'total_count': len(report_items),
        }

        logger.info(
            f"PDF审计包数据准备完成: {len(records)} 条记录, "
            f"时间范围 {start_time} ~ {end_time}"
        )
        return export_data

    def generate_pdf_html(
        self,
        start_time: datetime,
        end_time: datetime,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> str:
        """
        生成 PDF 审计报告的 HTML 内容

        使用 HTML 转 PDF 方式生成，返回可直接渲染的 HTML。

        Args:
            start_time: 起始时间
            end_time: 结束时间
            node_type: 节点类型过滤
            node_id: 节点ID过滤

        Returns:
            HTML 字符串
        """
        data = self.export_pdf_data(
            start_time, end_time, node_type, node_id
        )

        html_parts = [
            '<!DOCTYPE html>',
            '<html><head><meta charset="utf-8">',
            '<style>',
            'body { font-family: "SimSun", serif; margin: 40px; }',
            'h1 { text-align: center; color: #333; }',
            'h2 { color: #555; border-bottom: 1px solid #ccc; }',
            'table { border-collapse: collapse; width: 100%; margin: 10px 0; }',
            'th, td { border: 1px solid #999; padding: 6px 8px; font-size: 12px; }',
            'th { background: #f0f0f0; }',
            '.summary { background: #f9f9f9; padding: 15px; margin: 10px 0; }',
            '.factor { margin: 5px 0; }',
            '.hit { color: #c00; font-weight: bold; }',
            '.miss { color: #090; }',
            '</style>',
            '</head><body>',
            f'<h1>{data["title"]}</h1>',
            f'<p>导出时间: {data["export_time"]}</p>',
            f'<p>审计范围: {data["time_range"]["start"]} ~ '
            f'{data["time_range"]["end"]}</p>',
            f'<p>总记录数: {data["total_count"]}</p>',
        ]

        summary = data.get('summary', {})
        html_parts.append('<div class="summary">')
        html_parts.append(f'<h2>审计摘要</h2>')
        html_parts.append(
            f'<p>总预测次数: {summary.get("total_predictions", 0)}</p>'
        )
        html_parts.append(
            f'<p>异常预测次数: {summary.get("abnormal_predictions", 0)}</p>'
        )
        html_parts.append(
            f'<p>涉及节点数: {summary.get("unique_nodes", 0)}</p>'
        )

        level_dist = summary.get('level_distribution', {})
        if level_dist:
            html_parts.append('<p>状态分布:</p><ul>')
            for level, count in level_dist.items():
                html_parts.append(f'<li>{level}: {count} 次</li>')
            html_parts.append('</ul>')
        html_parts.append('</div>')

        for item in data['records']:
            html_parts.append('<div style="page-break-inside: avoid;">')
            html_parts.append(f'<h2>预测 #{item["prediction_id"][:8]}...</h2>')
            html_parts.append(
                f'<p>节点: {item["node_type"]}/{item["node_id"]} | '
                f'模型: {item["model_type"]} v{item["model_version"]} | '
                f'时间: {item["create_time"]}</p>'
            )

            decision = item.get('final_decision', {})
            html_parts.append('<h3>最终决策</h3>')
            html_parts.append('<table>')
            html_parts.append(
                '<tr><th>状态码</th><th>状态</th>'
                '<th>置信度</th><th>风险评分</th></tr>'
            )
            html_parts.append(
                f'<tr><td>{decision.get("status_code", "")}</td>'
                f'<td>{decision.get("status", "")}</td>'
                f'<td>{decision.get("confidence", "")}</td>'
                f'<td>{decision.get("risk_score", "")}</td></tr>'
            )
            html_parts.append('</table>')

            expl = item.get('explainability', {})
            risk_decomp = expl.get('risk_factor_decomposition', {})
            if risk_decomp:
                html_parts.append('<h3>风险因子分解</h3>')
                html_parts.append('<table>')
                html_parts.append(
                    '<tr><th>因子</th><th>得分</th>'
                    '<th>权重</th><th>贡献</th></tr>'
                )
                for factor_name, factor_data in risk_decomp.get(
                    'factor_contributions', {}
                ).items():
                    html_parts.append(
                        f'<tr><td>{factor_name}</td>'
                        f'<td>{factor_data.get("score", 0):.3f}</td>'
                        f'<td>{factor_data.get("weight", 0):.2f}</td>'
                        f'<td>{factor_data.get("contribution", 0):.4f}</td></tr>'
                    )
                html_parts.append('</table>')
                html_parts.append(
                    f'<p>主导因子: '
                    f'{risk_decomp.get("dominant_factor", "N/A")}</p>'
                )

            rule_hits = expl.get('rule_hits', [])
            if rule_hits:
                html_parts.append('<h3>规则命中项</h3>')
                html_parts.append('<table>')
                html_parts.append(
                    '<tr><th>规则ID</th><th>规则名称</th>'
                    '<th>命中</th><th>对应级别</th></tr>'
                )
                for rule in rule_hits:
                    hit_class = 'hit' if rule.get('hit') else 'miss'
                    html_parts.append(
                        f'<tr><td>{rule.get("rule_id", "")}</td>'
                        f'<td>{rule.get("rule_name", "")}</td>'
                        f'<td class="{hit_class}">'
                        f'{"是" if rule.get("hit") else "否"}</td>'
                        f'<td>{rule.get("resulting_level", "")}</td></tr>'
                    )
                html_parts.append('</table>')

            html_parts.append('</div><hr/>')

        html_parts.append('</body></html>')
        return '\n'.join(html_parts)

    def _generate_export_summary(
        self, records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        生成导出摘要统计
        """
        total = len(records)
        abnormal = 0
        node_set = set()
        level_dist: Dict[str, int] = {}

        for item in records:
            decision = item.get('final_decision', {})
            status_code = decision.get('status_code', 0)
            if status_code and status_code > 0:
                abnormal += 1

            node_key = f"{item.get('node_type', '')}/{item.get('node_id', '')}"
            node_set.add(node_key)

            status = decision.get('status', '未知')
            level_dist[status] = level_dist.get(status, 0) + 1

        return {
            'total_predictions': total,
            'abnormal_predictions': abnormal,
            'normal_predictions': total - abnormal,
            'unique_nodes': len(node_set),
            'level_distribution': level_dist,
        }

    @staticmethod
    def _safe_json_loads(
        text: Optional[str], default: Any = None
    ) -> Any:
        """安全解析 JSON 字符串"""
        if not text:
            return default
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return default
