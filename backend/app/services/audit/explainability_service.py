"""
模型可解释性服务

生成可解释性报告，包含:
1. LSTM 注意力权重提取
2. 关键时间步识别
3. 风险因子分解
4. 规则命中项
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from loguru import logger

from app.models.risk_model import BayesianRiskModel, RiskAssessment
from app.services.prediction.rule_classifier import RuleBasedClassifier
from app.services.prediction.warning_strategy import WarningStrategyPolicy
from app.utils.config import config


class ExplainabilityService:
    """
    模型可解释性服务

    对每次预测生成可解释性报告，支持监管审计需求。
    """

    def __init__(self):
        self.risk_model = BayesianRiskModel()
        self.rule_classifier = RuleBasedClassifier()
        self.warning_policy = WarningStrategyPolicy()
        logger.info("可解释性服务初始化完成")

    def generate_bolt_explainability(
        self,
        data: np.ndarray,
        processed_data: Optional[np.ndarray],
        model_output: Optional[Dict[str, Any]],
        risk_assessment: Optional[RiskAssessment],
        status_code: int,
        confidence: float,
        probs: Optional[np.ndarray],
        strategy_result: Tuple[int, str],
    ) -> Dict[str, Any]:
        """
        生成螺栓预测可解释性报告

        Args:
            data: 原始输入数据
            processed_data: 预处理后数据
            model_output: 模型原始输出（含attention weights等）
            risk_assessment: 风险评估结果
            status_code: 最终状态码
            confidence: 置信度
            probs: 概率分布
            strategy_result: 策略应用结果 (code, label)

        Returns:
            可解释性报告字典
        """
        feature_attributions = self.generate_feature_attributions(
            data=data,
            risk_assessment=risk_assessment,
            probs=probs,
        )

        report = {
            'attention_weights': self._extract_attention_weights(
                data, model_output
            ),
            'key_timesteps': self._identify_key_timesteps(
                data, processed_data
            ),
            'risk_factor_decomposition': self._decompose_risk_factors(
                data, risk_assessment
            ),
            'rule_hits': self._extract_rule_hits(data),
            'strategy_adjustment': {
                'original_status_code': status_code,
                'adjusted_status_code': strategy_result[0],
                'adjusted_status': strategy_result[1],
                'strategy_type': self.warning_policy.strategy_type,
                'confidence_threshold': (
                    self.warning_policy.strategy_1_threshold
                    if self.warning_policy.strategy_type == 1
                    else self.warning_policy.strategy_2_threshold
                ),
                'confidence_passed': confidence >= (
                    self.warning_policy.strategy_1_threshold
                    if self.warning_policy.strategy_type == 1
                    else self.warning_policy.strategy_2_threshold
                ),
            },
            'probability_distribution': (
                probs.tolist() if probs is not None else None
            ),
            'feature_attributions': feature_attributions,
        }
        return report

    def generate_flange_explainability(
        self,
        multi_bolt_data: List[np.ndarray],
        attention_weights: Optional[np.ndarray],
        model_output: Optional[Dict[str, Any]],
        risk_assessment: Optional[RiskAssessment],
        status_code: int,
        confidence: float,
        strategy_result: Tuple[int, str],
    ) -> Dict[str, Any]:
        """
        生成法兰面预测可解释性报告

        Args:
            multi_bolt_data: 多螺栓数据列表
            attention_weights: 法兰面注意力权重
            model_output: 模型原始输出
            risk_assessment: 风险评估结果
            status_code: 最终状态码
            confidence: 置信度
            strategy_result: 策略应用结果

        Returns:
            可解释性报告字典
        """
        bolt_reports = []
        for i, bolt_data in enumerate(multi_bolt_data):
            bolt_report = {
                'bolt_index': i,
                'attention_weight': (
                    float(attention_weights[i])
                    if attention_weights is not None and i < len(attention_weights)
                    else None
                ),
                'feature_summary': {
                    'mean': float(np.mean(bolt_data)),
                    'std': float(np.std(bolt_data)),
                    'min': float(np.min(bolt_data)),
                    'max': float(np.max(bolt_data)),
                },
                'key_timesteps': self._identify_key_timesteps(
                    bolt_data, None
                ),
                'rule_hits': self._extract_rule_hits(bolt_data),
            }
            bolt_reports.append(bolt_report)

        if attention_weights is not None:
            ranked_bolts = sorted(
                range(len(attention_weights)),
                key=lambda i: attention_weights[i],
                reverse=True,
            )
        else:
            ranked_bolts = list(range(len(multi_bolt_data)))

        feature_attributions = self.generate_feature_attributions(
            data=np.concatenate(multi_bolt_data) if multi_bolt_data else None,
            risk_assessment=risk_assessment,
            attention_weights=attention_weights,
        )

        report = {
            'attention_weights': (
                attention_weights.tolist()
                if attention_weights is not None
                else None
            ),
            'bolt_explanations': bolt_reports,
            'most_influential_bolts': ranked_bolts[:3],
            'risk_factor_decomposition': self._decompose_risk_factors(
                np.concatenate(multi_bolt_data), risk_assessment
            ),
            'strategy_adjustment': {
                'original_status_code': status_code,
                'adjusted_status_code': strategy_result[0],
                'adjusted_status': strategy_result[1],
                'strategy_type': self.warning_policy.strategy_type,
                'confidence_passed': confidence >= (
                    self.warning_policy.strategy_1_threshold
                    if self.warning_policy.strategy_type == 1
                    else self.warning_policy.strategy_2_threshold
                ),
            },
            'feature_attributions': feature_attributions,
        }
        return report

    def _extract_attention_weights(
        self,
        data: np.ndarray,
        model_output: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        提取LSTM注意力权重

        对于LSTM模型，通过时间步梯度显著性近似注意力。
        """
        if model_output and 'attention_weights' in model_output:
            weights = model_output['attention_weights']
            if isinstance(weights, np.ndarray):
                return {
                    'type': 'model_attention',
                    'weights': weights.tolist(),
                    'top_k_indices': (
                        np.argsort(weights)[-5:].tolist()
                        if len(weights) >= 5
                        else np.argsort(weights).tolist()
                    ),
                }

        n = len(data)
        if n < 2:
            return None

        diffs = np.abs(np.diff(data))
        if len(diffs) == 0:
            return None

        total_diff = np.sum(diffs) + 1e-8
        saliency = diffs / total_diff

        top_k = min(5, len(saliency))
        top_indices = np.argsort(saliency)[-top_k:].tolist()

        return {
            'type': 'gradient_saliency',
            'weights': saliency.tolist(),
            'top_k_indices': top_indices,
        }

    def _identify_key_timesteps(
        self,
        raw_data: np.ndarray,
        processed_data: Optional[np.ndarray],
    ) -> List[Dict[str, Any]]:
        """
        识别关键时间步

        检测突变点、极值点、趋势转折点
        """
        key_steps = []
        data = raw_data.flatten()

        if len(data) < 3:
            return key_steps

        mean_val = np.mean(data)
        std_val = np.std(data)

        diffs = np.diff(data)

        for i in range(len(diffs)):
            abs_diff = abs(diffs[i])
            if abs_diff > std_val * 2:
                key_steps.append({
                    'index': int(i + 1),
                    'value': float(data[i + 1]),
                    'type': 'sudden_change',
                    'change_magnitude': float(abs_diff),
                    'direction': 'up' if diffs[i] > 0 else 'down',
                })

        for i in range(len(data)):
            if abs(data[i] - mean_val) > std_val * 2:
                key_steps.append({
                    'index': int(i),
                    'value': float(data[i]),
                    'type': 'extreme_value',
                    'deviation_sigma': float(
                        abs(data[i] - mean_val) / (std_val + 1e-8)
                    ),
                })

        if len(data) >= 5:
            window = min(5, len(data) // 2)
            for i in range(window, len(data) - window):
                before = np.mean(data[max(0, i - window):i])
                after = np.mean(data[i + 1:min(len(data), i + window + 1)])
                if (before > mean_val and after < mean_val) or (
                    before < mean_val and after > mean_val
                ):
                    key_steps.append({
                        'index': int(i),
                        'value': float(data[i]),
                        'type': 'trend_reversal',
                        'before_avg': float(before),
                        'after_avg': float(after),
                    })

        seen = set()
        unique_steps = []
        for step in key_steps:
            key = (step['index'], step['type'])
            if key not in seen:
                seen.add(key)
                unique_steps.append(step)

        unique_steps.sort(key=lambda x: x['index'])
        return unique_steps[:20]

    def _decompose_risk_factors(
        self,
        data: np.ndarray,
        risk_assessment: Optional[RiskAssessment],
    ) -> Dict[str, Any]:
        """
        风险因子分解

        将风险评分拆解为各项因子的贡献
        """
        deviation_score = self.risk_model.calculate_deviation_score(data)
        volatility_score = self.risk_model.calculate_volatility_score(data)
        trend_score = self.risk_model.calculate_trend_score(data)
        extreme_score = self.risk_model.calculate_extreme_score(data)

        weights = self.risk_model.prior_weights

        contributions = {
            'mean_deviation': {
                'score': float(deviation_score),
                'weight': weights['mean_deviation'],
                'contribution': float(
                    deviation_score * weights['mean_deviation']
                ),
                'description': '预紧力均值偏离正常范围的程度',
            },
            'volatility': {
                'score': float(volatility_score),
                'weight': weights['volatility'],
                'contribution': float(
                    volatility_score * weights['volatility']
                ),
                'description': '预紧力数据的波动性',
            },
            'trend': {
                'score': float(trend_score),
                'weight': weights['trend'],
                'contribution': float(trend_score * weights['trend']),
                'description': '预紧力变化趋势的稳定性',
            },
            'extreme_values': {
                'score': float(extreme_score),
                'weight': weights['extreme_values'],
                'contribution': float(
                    extreme_score * weights['extreme_values']
                ),
                'description': '极端预紧力值的存在',
            },
        }

        total_contribution = sum(
            c['contribution'] for c in contributions.values()
        )

        dominant_factor = max(
            contributions, key=lambda k: contributions[k]['contribution']
        )

        result = {
            'factor_contributions': contributions,
            'total_weighted_score': float(total_contribution),
            'dominant_factor': dominant_factor,
            'factors_list': (
                risk_assessment.factors
                if risk_assessment
                else ['未评估']
            ),
        }

        if risk_assessment:
            result['risk_score'] = float(risk_assessment.score)
            result['risk_level'] = risk_assessment.level.value
            result['confidence'] = float(risk_assessment.confidence)

        return result

    def _extract_rule_hits(
        self,
        data: np.ndarray,
    ) -> List[Dict[str, Any]]:
        """
        提取规则命中项

        逐条检查规则分类器的判断逻辑，记录每条规则的命中情况
        """
        mean_val = float(np.mean(data))
        std_val = float(np.std(data))
        min_normal = self.rule_classifier.min_normal
        max_normal = self.rule_classifier.max_normal

        rules = [
            {
                'rule_id': 'R001',
                'rule_name': '均值超出正常范围50%',
                'condition': (
                    f'mean({mean_val:.1f}) < {min_normal * 0.5:.1f} '
                    f'or mean({mean_val:.1f}) > {max_normal * 1.5:.1f}'
                ),
                'threshold_low': float(min_normal * 0.5),
                'threshold_high': float(max_normal * 1.5),
                'hit': (
                    mean_val < min_normal * 0.5
                    or mean_val > max_normal * 1.5
                ),
                'resulting_level': 4,
            },
            {
                'rule_id': 'R002',
                'rule_name': '均值超出正常范围20%',
                'condition': (
                    f'mean({mean_val:.1f}) < {min_normal * 0.8:.1f} '
                    f'or mean({mean_val:.1f}) > {max_normal * 1.2:.1f}'
                ),
                'threshold_low': float(min_normal * 0.8),
                'threshold_high': float(max_normal * 1.2),
                'hit': (
                    mean_val < min_normal * 0.8
                    or mean_val > max_normal * 1.2
                ),
                'resulting_level': 3,
            },
            {
                'rule_id': 'R003',
                'rule_name': '均值超出正常范围',
                'condition': (
                    f'mean({mean_val:.1f}) < {min_normal} '
                    f'or mean({mean_val:.1f}) > {max_normal}'
                ),
                'threshold_low': float(min_normal),
                'threshold_high': float(max_normal),
                'hit': mean_val < min_normal or mean_val > max_normal,
                'resulting_level': 2,
            },
            {
                'rule_id': 'R004',
                'rule_name': '标准差大于均值20%',
                'condition': (
                    f'std({std_val:.1f}) > mean({mean_val:.1f}) * 0.2 '
                    f'= {mean_val * 0.2:.1f}'
                ),
                'threshold': float(mean_val * 0.2),
                'hit': std_val > mean_val * 0.2,
                'resulting_level': 1,
            },
        ]

        hit_rules = [r for r in rules if r['hit']]
        if not hit_rules:
            rules.append({
                'rule_id': 'R000',
                'rule_name': '所有规则均未命中',
                'hit': True,
                'resulting_level': 0,
            })

        return rules

    def generate_feature_attributions(
        self,
        data: Optional[np.ndarray] = None,
        risk_assessment: Optional[RiskAssessment] = None,
        integrated_gradients: Optional[Dict[str, Any]] = None,
        shap_values: Optional[Dict[str, Any]] = None,
        attention_weights: Optional[np.ndarray] = None,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
        probs: Optional[np.ndarray] = None,
    ) -> List[Dict[str, Any]]:
        """
        生成统一的 feature_attributions 数组

        将各模型的特征贡献度统一格式，便于前端渲染和审计追溯。

        Args:
            data: 输入数据（用于风险因子计算）
            risk_assessment: 风险评估结果
            integrated_gradients: LSTM 积分梯度结果
            shap_values: SHAP 值结果
            attention_weights: 注意力权重
            node_type: 节点类型
            node_id: 节点ID
            probs: LSTM 概率分布

        Returns:
            List[Dict]: 特征归因数组，每项包含:
                - name: 特征名称
                - value: 贡献值（归一化）
                - direction: 贡献方向 ('positive' | 'negative')
                - method: 计算方法
                - category: 类别 ('risk_factor' | 'temporal' | 'attention' | 'bolt')
                - rank: 重要性排名
                - description: 中文描述
        """
        attributions = []

        if data is not None and risk_assessment is not None:
            risk_factors = self._get_risk_factor_attributions(
                data, risk_assessment, probs
            )
            attributions.extend(risk_factors)

        if integrated_gradients is not None:
            ig_attributions = self._get_ig_attributions(integrated_gradients)
            attributions.extend(ig_attributions)

        if shap_values is not None:
            shap_attributions = self._get_shap_attributions(shap_values)
            attributions.extend(shap_attributions)

        if attention_weights is not None:
            attn_attributions = self._get_attention_attributions(attention_weights)
            attributions.extend(attn_attributions)

        attributions.sort(key=lambda x: abs(x['value']), reverse=True)

        for i, attr in enumerate(attributions):
            attr['rank'] = i + 1

        return attributions

    def _get_risk_factor_attributions(
        self,
        data: np.ndarray,
        risk_assessment: RiskAssessment,
        probs: Optional[np.ndarray] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取风险因子的特征归因
        """
        attributions = []

        factor_contribs = getattr(risk_assessment, 'factor_contributions', None)
        if factor_contribs:
            descriptions = {
                'mean_deviation': '预紧力均值偏离正常范围的程度',
                'volatility': '预紧力数据的波动性',
                'trend': '预紧力变化趋势的稳定性',
                'extreme_values': '极端预紧力值的存在',
                'lstm_prediction': 'LSTM模型预测异常概率',
            }

            for factor in factor_contribs:
                name = factor.name
                raw_val = getattr(factor, 'raw_score', 0.5)
                weighted_val = getattr(factor, 'weighted_score', 0)
                direction = 'positive' if raw_val >= 0.5 else 'negative'

                attributions.append({
                    'name': name,
                    'value': float(weighted_val),
                    'direction': direction,
                    'method': 'weighted_contribution',
                    'category': 'risk_factor',
                    'rank': 0,
                    'description': descriptions.get(name, name),
                    'raw_score': float(raw_val),
                    'weight': float(getattr(factor, 'weight', 0)),
                    'contribution_ratio': float(getattr(factor, 'contribution_ratio', 0)),
                })

        return attributions

    def _get_ig_attributions(
        self,
        ig_result: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        从 Integrated Gradients 结果生成特征归因
        """
        attributions = []

        if 'feature_importance' in ig_result:
            feat_imp = ig_result['feature_importance']
            for feat_name, imp_val in feat_imp.items():
                attributions.append({
                    'name': f'feature_{feat_name}',
                    'value': float(imp_val),
                    'direction': 'positive' if imp_val >= 0 else 'negative',
                    'method': 'integrated_gradients',
                    'category': 'feature',
                    'rank': 0,
                    'description': f'特征 {feat_name} 的积分梯度贡献',
                })

        if 'time_step_importance' in ig_result:
            ts_imp = ig_result['time_step_importance']
            if isinstance(ts_imp, (list, np.ndarray)) and len(ts_imp) > 0:
                top_k_ts = ig_result.get('top_k_timesteps', list(range(min(5, len(ts_imp)))))
                for idx in top_k_ts:
                    idx_val = int(idx) if idx < len(ts_imp) else 0
                    imp_val = float(ts_imp[idx_val]) if idx_val < len(ts_imp) else 0.0
                    attributions.append({
                        'name': f'timestep_{idx_val}',
                        'value': imp_val,
                        'direction': 'positive',
                        'method': 'integrated_gradients',
                        'category': 'temporal',
                        'rank': 0,
                        'description': f'时间步 {idx_val} 的积分梯度重要性',
                        'timestep_index': idx_val,
                    })

        if 'bolt_importance_scores' in ig_result:
            bolt_imp = ig_result['bolt_importance_scores']
            if isinstance(bolt_imp, (list, np.ndarray)):
                top_k_bolts = ig_result.get('top_k_bolts', list(range(min(3, len(bolt_imp)))))
                for idx in top_k_bolts:
                    idx_val = int(idx)
                    imp_val = float(bolt_imp[idx_val]) if idx_val < len(bolt_imp) else 0.0
                    attributions.append({
                        'name': f'bolt_{idx_val}',
                        'value': imp_val,
                        'direction': 'positive',
                        'method': 'integrated_gradients',
                        'category': 'bolt',
                        'rank': 0,
                        'description': f'螺栓 {idx_val} 的积分梯度重要性',
                        'bolt_index': idx_val,
                    })

        return attributions

    def _get_shap_attributions(
        self,
        shap_result: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        从 SHAP 结果生成特征归因
        """
        attributions = []

        if 'shap_values' in shap_result:
            shap_vals = shap_result['shap_values']
            if isinstance(shap_vals, dict):
                descriptions = {
                    'mean_deviation': '预紧力均值偏离的SHAP贡献',
                    'volatility': '波动性的SHAP贡献',
                    'trend': '变化趋势的SHAP贡献',
                    'extreme_values': '极端值的SHAP贡献',
                    'lstm_prediction': 'LSTM预测的SHAP贡献',
                }
                for name, val in shap_vals.items():
                    attributions.append({
                        'name': name,
                        'value': float(val),
                        'direction': 'positive' if val >= 0 else 'negative',
                        'method': 'shap',
                        'category': 'risk_factor',
                        'rank': 0,
                        'description': descriptions.get(name, f'{name} 的SHAP贡献'),
                    })

        if 'time_step_shap' in shap_result:
            ts_shap = shap_result['time_step_shap']
            if isinstance(ts_shap, (list, np.ndarray)) and len(ts_shap) > 0:
                abs_ts = np.abs(np.array(ts_shap))
                top_indices = np.argsort(abs_ts)[-5:][::-1].tolist()
                for idx in top_indices:
                    idx_val = int(idx)
                    val = float(ts_shap[idx_val]) if idx_val < len(ts_shap) else 0.0
                    attributions.append({
                        'name': f'timestep_shap_{idx_val}',
                        'value': val,
                        'direction': 'positive' if val >= 0 else 'negative',
                        'method': 'shap_time_series',
                        'category': 'temporal',
                        'rank': 0,
                        'description': f'时间步 {idx_val} 的SHAP贡献',
                        'timestep_index': idx_val,
                    })

        return attributions

    def _get_attention_attributions(
        self,
        attention_weights: np.ndarray,
    ) -> List[Dict[str, Any]]:
        """
        从注意力权重生成特征归因
        """
        attributions = []

        weights = np.array(attention_weights)
        if weights.ndim == 1:
            top_k = min(5, len(weights))
            top_indices = np.argsort(weights)[-top_k:][::-1].tolist()

            for idx in top_indices:
                idx_val = int(idx)
                w_val = float(weights[idx_val])
                attributions.append({
                    'name': f'attention_weight_{idx_val}',
                    'value': w_val,
                    'direction': 'positive',
                    'method': 'attention',
                    'category': 'temporal',
                    'rank': 0,
                    'description': f'时间步 {idx_val} 的注意力权重',
                    'timestep_index': idx_val,
                })

        return attributions

    def get_explainability_for_audit(
        self, audit_record,
    ) -> Optional[Dict[str, Any]]:
        """
        从审计记录中获取可解释性报告

        Args:
            audit_record: PredictionAudit ORM 对象

        Returns:
            可解释性报告字典
        """
        if not audit_record or not audit_record.explainability:
            return None

        try:
            import json
            return json.loads(audit_record.explainability)
        except (json.JSONDecodeError, TypeError):
            return None
