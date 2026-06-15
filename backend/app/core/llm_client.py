"""
大模型接口客户端模块

提供与大语言模型的集成接口，用于：
1. 诊断结论整理和总结
2. 推荐措施生成
3. 自然语言报告生成

支持的模型:
- OpenAI API
- 通义千问
- 文心一言
- 本地模型

使用示例:
    from app.core.llm_client import LLMClient
    
    client = LLMClient()
    summary = client.summarize_diagnosis(diagnosis_data)
"""

import os
import json
import re
import time
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import httpx
from loguru import logger

from app.utils.config import config


class LLMProvider(Enum):
    """LLM提供商"""
    OPENAI = "openai"
    QWEN = "qwen"  # 通义千问
    WENXIN = "wenxin"  # 文心一言
    LOCAL = "local"  # 本地模型


@dataclass
class LLMResponse:
    """
    LLM响应
    
    Attributes:
        content: 响应内容
        model: 使用的模型
        tokens_used: 使用的token数
        prompt_tokens: 输入token数
        completion_tokens: 输出token数
        latency_ms: 响应延迟（毫秒）
        success: 是否成功
        error: 错误信息
    """
    content: str
    model: str
    tokens_used: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None


class UrgencyLevel(Enum):
    """紧急程度等级"""
    LOW = "low"           # 低 - 常规维护即可
    MEDIUM = "medium"     # 中 - 需要关注
    HIGH = "high"         # 高 - 尽快处理
    CRITICAL = "critical" # 紧急 - 立即处理


@dataclass
class DiagnosisReport:
    """
    智能诊断报告
    
    Attributes:
        diagnosis_summary: 诊断摘要（200字内）
        recommended_actions: 推荐处置措施（分步骤）
        urgency_level: 紧急程度
        model: 使用的模型
        tokens_used: token用量
        latency_ms: 生成延迟（毫秒）
        is_fallback: 是否使用降级模板
    """
    diagnosis_summary: str
    recommended_actions: List[str]
    urgency_level: UrgencyLevel
    model: str = "local_template"
    tokens_used: int = 0
    latency_ms: float = 0.0
    is_fallback: bool = False


class BaseLLMClient(ABC):
    """LLM客户端基类"""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """生成响应"""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI API客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-3.5-turbo"
    ):
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.base_url = base_url
        self.model = model
        
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """调用OpenAI API"""
        if not self.api_key:
            return LLMResponse(
                content="",
                model=self.model,
                success=False,
                error="OpenAI API key not configured"
            )
        
        start_time = time.time()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "你是一个专业的螺栓预紧力分析专家。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": kwargs.get('temperature', 0.7),
                        "max_tokens": kwargs.get('max_tokens', 1000)
                    },
                    timeout=30.0
                )
                
                latency_ms = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    usage = data.get('usage', {})
                    return LLMResponse(
                        content=data['choices'][0]['message']['content'],
                        model=self.model,
                        tokens_used=usage.get('total_tokens', 0),
                        prompt_tokens=usage.get('prompt_tokens', 0),
                        completion_tokens=usage.get('completion_tokens', 0),
                        latency_ms=latency_ms,
                        success=True
                    )
                else:
                    return LLMResponse(
                        content="",
                        model=self.model,
                        latency_ms=latency_ms,
                        success=False,
                        error=f"API error: {response.status_code}"
                    )
                    
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return LLMResponse(
                content="",
                model=self.model,
                latency_ms=latency_ms,
                success=False,
                error=str(e)
            )


class QwenClient(BaseLLMClient):
    """通义千问客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "qwen-turbo"
    ):
        self.api_key = api_key or os.environ.get('QWEN_API_KEY')
        self.model = model
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """调用通义千问API"""
        if not self.api_key:
            return LLMResponse(
                content="",
                model=self.model,
                success=False,
                error="Qwen API key not configured"
            )
        
        start_time = time.time()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "input": {
                            "messages": [
                                {"role": "system", "content": "你是一个专业的螺栓预紧力分析专家。"},
                                {"role": "user", "content": prompt}
                            ]
                        }
                    },
                    timeout=30.0
                )
                
                latency_ms = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    usage = data.get('usage', {})
                    return LLMResponse(
                        content=data['output']['text'],
                        model=self.model,
                        tokens_used=usage.get('total_tokens', 0),
                        prompt_tokens=usage.get('input_tokens', 0),
                        completion_tokens=usage.get('output_tokens', 0),
                        latency_ms=latency_ms,
                        success=True
                    )
                else:
                    return LLMResponse(
                        content="",
                        model=self.model,
                        latency_ms=latency_ms,
                        success=False,
                        error=f"API error: {response.status_code}"
                    )
                    
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return LLMResponse(
                content="",
                model=self.model,
                latency_ms=latency_ms,
                success=False,
                error=str(e)
            )


class LocalTemplateClient(BaseLLMClient):
    """本地模板客户端（不需要LLM API）"""
    
    def __init__(self):
        self.model = "local_template"
        
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """使用本地模板生成响应"""
        start_time = time.time()
        content = self._generate_from_template(prompt)
        latency_ms = (time.time() - start_time) * 1000
        
        return LLMResponse(
            content=content,
            model=self.model,
            latency_ms=latency_ms,
            success=True
        )
    
    def _generate_from_template(self, prompt: str) -> str:
        """基于模板生成响应"""
        if "诊断" in prompt or "分析" in prompt:
            return self._diagnosis_template(prompt)
        elif "推荐" in prompt or "建议" in prompt:
            return self._recommendation_template(prompt)
        else:
            return self._general_template(prompt)
    
    def generate_structured_diagnosis(
        self,
        status: str,
        risk_score: float,
        fault_type: Optional[str],
        trend: Optional[str],
        recent_values: Optional[List[float]],
        historical_incidents: Optional[int],
        node_type: str = "bolt",
        node_id: str = ""
    ) -> DiagnosisReport:
        """
        使用模板生成结构化诊断报告
        
        Args:
            status: 状态
            risk_score: 风险评分(0-10)
            fault_type: 故障类型
            trend: 趋势
            recent_values: 近期数值
            historical_incidents: 历史事件数
            node_type: 节点类型
            node_id: 节点ID
            
        Returns:
            DiagnosisReport: 诊断报告
        """
        start_time = time.time()
        
        # 计算紧急程度
        urgency_level = self._calculate_urgency(risk_score, status)
        
        # 生成诊断摘要
        diagnosis_summary = self._build_diagnosis_summary(
            status=status,
            risk_score=risk_score,
            fault_type=fault_type,
            trend=trend,
            recent_values=recent_values,
            historical_incidents=historical_incidents,
            node_type=node_type,
            node_id=node_id
        )
        
        # 生成推荐措施
        recommended_actions = self._build_recommendations(
            status=status,
            risk_score=risk_score,
            fault_type=fault_type,
            urgency_level=urgency_level,
            node_type=node_type
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        return DiagnosisReport(
            diagnosis_summary=diagnosis_summary,
            recommended_actions=recommended_actions,
            urgency_level=urgency_level,
            model=self.model,
            tokens_used=0,
            latency_ms=latency_ms,
            is_fallback=True
        )
    
    def _calculate_urgency(self, risk_score: float, status: str) -> UrgencyLevel:
        """根据风险评分和状态计算紧急程度"""
        status_code_map = {
            "正常": 0,
            "关注级预警": 1,
            "检查级预警": 2,
            "紧急级预警": 3,
            "故障": 4
        }
        status_code = status_code_map.get(status, 0)
        
        if status_code >= 4 or risk_score <= 2:
            return UrgencyLevel.CRITICAL
        elif status_code >= 3 or risk_score <= 4:
            return UrgencyLevel.HIGH
        elif status_code >= 1 or risk_score <= 7:
            return UrgencyLevel.MEDIUM
        else:
            return UrgencyLevel.LOW
    
    def _build_diagnosis_summary(
        self,
        status: str,
        risk_score: float,
        fault_type: Optional[str],
        trend: Optional[str],
        recent_values: Optional[List[float]],
        historical_incidents: Optional[int],
        node_type: str,
        node_id: str
    ) -> str:
        """构建诊断摘要"""
        node_label = "螺栓" if node_type == "bolt" else "法兰面"
        node_display = node_id if node_id else "该节点"
        
        # 计算近期值统计
        value_stats = ""
        if recent_values and len(recent_values) > 0:
            avg_val = sum(recent_values) / len(recent_values)
            max_val = max(recent_values)
            min_val = min(recent_values)
            value_stats = f"近期预紧力均值{avg_val:.1f}，范围[{min_val:.1f}, {max_val:.1f}]。"
        
        # 故障类型描述
        fault_desc = ""
        if fault_type:
            fault_type_map = {
                "loosening": "松动",
                "preload_decrease": "预紧力下降",
                "severe_anomaly": "严重异常",
                "failure": "故障"
            }
            fault_desc = f"故障类型为{fault_type_map.get(fault_type, fault_type)}。"
        
        # 趋势描述
        trend_desc = ""
        if trend:
            trend_map = {
                "stable": "趋势稳定",
                "decreasing": "呈下降趋势",
                "increasing": "呈上升趋势",
                "fluctuating": "波动较大"
            }
            trend_desc = f"{trend_map.get(trend, trend)}。"
        
        # 历史事件描述
        hist_desc = ""
        if historical_incidents is not None and historical_incidents > 0:
            hist_desc = f"历史同类事件{historical_incidents}次。"
        
        summary = (
            f"{node_label}{node_display}当前状态为「{status}」，风险评分{risk_score:.1f}/10。"
            f"{value_stats}{fault_desc}{trend_desc}{hist_desc}"
            f"建议根据风险等级采取相应处置措施。"
        )
        
        # 限制在200字以内
        if len(summary) > 200:
            summary = summary[:197] + "..."
        
        return summary
    
    def _build_recommendations(
        self,
        status: str,
        risk_score: float,
        fault_type: Optional[str],
        urgency_level: UrgencyLevel,
        node_type: str
    ) -> List[str]:
        """构建推荐措施列表"""
        actions = []
        node_label = "螺栓" if node_type == "bolt" else "法兰面"
        
        if urgency_level == UrgencyLevel.CRITICAL:
            actions = [
                f"立即停止相关设备运行，对该{node_label}进行紧急检查",
                "通知运维人员到达现场，评估安全风险",
                "准备备件和维修工具，制定更换或修复方案",
                "加密监测频率，每小时记录一次数据",
                "记录详细的故障信息，更新知识库"
            ]
        elif urgency_level == UrgencyLevel.HIGH:
            actions = [
                "安排专业人员在24小时内进行现场检查",
                "增加监测频率，密切关注状态变化",
                "评估设备运行风险，必要时降载运行",
                "制定预防性维护计划，准备相关备件",
                "记录异常特征，用于后续分析"
            ]
        elif urgency_level == UrgencyLevel.MEDIUM:
            actions = [
                "加强日常监测，关注趋势变化",
                "安排在下次例行维护时重点检查",
                "记录当前数据特征，用于趋势对比",
                "检查周边设备运行状态，排除关联影响"
            ]
        else:
            actions = [
                "保持常规监测频率",
                "按计划执行例行维护",
                "关注数据质量，确保采集正常"
            ]
        
        # 根据故障类型补充建议
        if fault_type == "loosening":
            actions.insert(0, "检查螺栓预紧力，按规程进行复紧")
        elif fault_type == "preload_decrease":
            actions.insert(0, "分析预紧力下降原因，评估是否需要重新紧固")
        
        return actions
    
    def _diagnosis_template(self, prompt: str) -> str:
        """诊断报告模板"""
        return """
## 诊断分析报告

### 1. 数据概况
根据提供的预紧力数据，系统已完成自动分析。

### 2. 异常检测结果
- 使用孤立森林算法检测异常值
- 结合统计方法验证结果
- 识别潜在的趋势变化

### 3. 状态评估
基于LSTM深度学习模型的预测结果，结合贝叶斯风险评估模型的分析。

### 4. 结论
请参考系统返回的具体状态码和置信度进行决策。
"""
    
    def _recommendation_template(self, prompt: str) -> str:
        """推荐措施模板"""
        return """
## 推荐措施

### 短期措施
1. 加强监测频率
2. 记录异常特征
3. 准备必要的维护工具

### 中期措施
1. 安排专业检查
2. 制定预防性维护计划
3. 评估设备整体状态

### 长期措施
1. 优化维护周期
2. 更新监测策略
3. 完善预警机制
"""
    
    def _general_template(self, prompt: str) -> str:
        """通用模板"""
        return "基于系统分析，请参考预测结果和风险评估进行相应处理。"


class LLMClient:
    """
    LLM客户端统一接口
    
    自动选择可用的LLM提供商，支持全局开关和降级策略。
    """
    
    def __init__(self):
        """初始化LLM客户端"""
        llm_config = config.get('llm', {})
        self.enabled = llm_config.get('enabled', False)
        self.provider = llm_config.get('provider', 'local')
        
        # 初始化客户端
        self._clients: Dict[str, BaseLLMClient] = {}
        self._init_clients(llm_config)
        
        logger.info(
            f"LLM客户端初始化完成: enabled={self.enabled}, provider={self.provider}"
        )
    
    def _init_clients(self, llm_config: Dict) -> None:
        """初始化所有客户端"""
        # 本地模板客户端（总是可用，作为降级兜底）
        self._clients['local'] = LocalTemplateClient()
        
        # OpenAI客户端
        if llm_config.get('openai', {}).get('api_key'):
            self._clients['openai'] = OpenAIClient(
                api_key=llm_config['openai']['api_key'],
                model=llm_config['openai'].get('model', 'gpt-3.5-turbo')
            )
        
        # 通义千问客户端
        if llm_config.get('qwen', {}).get('api_key'):
            self._clients['qwen'] = QwenClient(
                api_key=llm_config['qwen']['api_key'],
                model=llm_config['qwen'].get('model', 'qwen-turbo')
            )
    
    def _get_client(self) -> BaseLLMClient:
        """获取可用的客户端"""
        if not self.enabled:
            return self._clients['local']
        if self.provider in self._clients:
            return self._clients[self.provider]
        return self._clients['local']
    
    def is_enabled(self) -> bool:
        """检查LLM功能是否启用"""
        return self.enabled
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """
        生成响应
        
        Args:
            prompt: 提示词
            **kwargs: 额外参数
            
        Returns:
            LLMResponse: 响应
        """
        if not self.enabled:
            # 全局关闭时直接使用本地模板
            client = self._clients['local']
            response = await client.generate(prompt, **kwargs)
            self._log_usage(response, prompt, "disabled_fallback")
            return response
        
        client = self._get_client()
        start_time = time.time()
        response = await client.generate(prompt, **kwargs)
        
        # 如果失败且不是本地模式，尝试本地模板降级
        if not response.success and self.provider != 'local':
            logger.warning(f"LLM调用失败，降级使用本地模板: {response.error}")
            fallback_start = time.time()
            response = await self._clients['local'].generate(prompt)
            response.latency_ms = (time.time() - start_time) * 1000
            self._log_usage(response, prompt, "fallback")
        else:
            self._log_usage(response, prompt, "normal")
        
        return response
    
    def _log_usage(self, response: LLMResponse, prompt: str, mode: str) -> None:
        """
        记录LLM使用日志（用于成本控制）
        
        Args:
            response: LLM响应
            prompt: 提示词
            mode: 调用模式 (normal/fallback/disabled_fallback)
        """
        logger.info(
            f"[LLM Usage] mode={mode}, model={response.model}, "
            f"tokens_total={response.tokens_used}, "
            f"tokens_prompt={response.prompt_tokens}, "
            f"tokens_completion={response.completion_tokens}, "
            f"latency_ms={response.latency_ms:.2f}, "
            f"success={response.success}, "
            f"error={response.error or 'none'}, "
            f"prompt_preview={prompt[:50].replace(chr(10), ' ')}..."
        )
    
    async def generate_diagnosis_report(
        self,
        status: str,
        risk_score: float,
        fault_type: Optional[str] = None,
        trend: Optional[str] = None,
        recent_values: Optional[List[float]] = None,
        historical_incidents: Optional[int] = None,
        node_type: str = "bolt",
        node_id: str = "",
    ) -> DiagnosisReport:
        """
        生成结构化诊断报告
        
        输入结构化数据，输出诊断摘要、推荐措施和紧急程度。
        LLM不可用时自动降级到模板生成。
        
        Args:
            status: 状态（如：正常、关注级预警、检查级预警、紧急级预警、故障）
            risk_score: 风险评分(0-10)，分数越低风险越高
            fault_type: 故障类型（如：loosening, preload_decrease, severe_anomaly, failure）
            trend: 趋势（如：stable, decreasing, increasing, fluctuating）
            recent_values: 近期预紧力数值列表
            historical_incidents: 历史同类事件数
            node_type: 节点类型（bolt/flange）
            node_id: 节点ID
            
        Returns:
            DiagnosisReport: 结构化诊断报告
        """
        # LLM未启用或使用本地provider时，直接用模板生成
        if not self.enabled or self.provider == 'local':
            local_client = self._clients['local']
            report = local_client.generate_structured_diagnosis(
                status=status,
                risk_score=risk_score,
                fault_type=fault_type,
                trend=trend,
                recent_values=recent_values,
                historical_incidents=historical_incidents,
                node_type=node_type,
                node_id=node_id,
            )
            self._log_structured_usage(report, "template")
            return report
        
        # 构建提示词，要求JSON输出
        prompt = self._build_diagnosis_prompt(
            status=status,
            risk_score=risk_score,
            fault_type=fault_type,
            trend=trend,
            recent_values=recent_values,
            historical_incidents=historical_incidents,
            node_type=node_type,
            node_id=node_id,
        )
        
        try:
            response = await self.generate(prompt, max_tokens=800, temperature=0.7)
            
            if response.success:
                report = self._parse_diagnosis_response(
                    content=response.content,
                    model=response.model,
                    tokens_used=response.tokens_used,
                    latency_ms=response.latency_ms,
                    default_status=status,
                    default_risk_score=risk_score,
                    node_type=node_type,
                )
                self._log_structured_usage(report, "llm")
                return report
        except Exception as e:
            logger.warning(f"LLM诊断报告生成异常，降级到模板: {e}")
        
        # 降级到模板
        local_client = self._clients['local']
        report = local_client.generate_structured_diagnosis(
            status=status,
            risk_score=risk_score,
            fault_type=fault_type,
            trend=trend,
            recent_values=recent_values,
            historical_incidents=historical_incidents,
            node_type=node_type,
            node_id=node_id,
        )
        self._log_structured_usage(report, "fallback")
        return report
    
    def _build_diagnosis_prompt(
        self,
        status: str,
        risk_score: float,
        fault_type: Optional[str],
        trend: Optional[str],
        recent_values: Optional[List[float]],
        historical_incidents: Optional[int],
        node_type: str,
        node_id: str,
    ) -> str:
        """构建诊断报告提示词"""
        node_label = "螺栓" if node_type == "bolt" else "法兰面"
        
        # 计算近期值统计
        value_stats = ""
        if recent_values and len(recent_values) > 0:
            avg_val = sum(recent_values) / len(recent_values)
            max_val = max(recent_values)
            min_val = min(recent_values)
            value_stats = f"""
近期预紧力数据（最近{len(recent_values)}个点）:
- 平均值: {avg_val:.2f}
- 最大值: {max_val:.2f}
- 最小值: {min_val:.2f}
- 数据点: {recent_values[-10:]}
"""
        
        fault_desc = f"故障类型: {fault_type}" if fault_type else "故障类型: 未指定"
        trend_desc = f"趋势: {trend}" if trend else "趋势: 未提供"
        hist_desc = f"历史同类事件数: {historical_incidents}" if historical_incidents is not None else "历史同类事件数: 未知"
        
        prompt = f"""你是一位专业的工业设备故障诊断专家。请根据以下{node_label}的预紧力监测数据，生成一份结构化的诊断报告。

【基本信息】
节点类型: {node_label}
节点ID: {node_id if node_id else '未提供'}
当前状态: {status}
风险评分: {risk_score}/10（分数越低风险越高）
{fault_desc}
{trend_desc}
{hist_desc}
{value_stats}
【输出要求】
请严格按照以下JSON格式输出，不要包含任何额外文字：

{{
  "diagnosis_summary": "诊断摘要，200字以内，用简洁专业的语言描述当前状态、主要风险和关键发现",
  "recommended_actions": [
    "步骤1：具体的处置建议",
    "步骤2：具体的处置建议",
    "步骤3：具体的处置建议"
  ],
  "urgency_level": "low|medium|high|critical"
}}

【说明】
- urgency_level取值说明:
  - low: 低风险，常规维护即可
  - medium: 中风险，需要关注，安排检查
  - high: 高风险，应尽快处理
  - critical: 紧急，需立即处理

请确保:
1. diagnosis_summary在200字以内
2. recommended_actions为3-6条分步骤的具体建议
3. urgency_level根据风险评分和状态综合判断
4. 输出必须是有效的JSON格式
"""
        return prompt
    
    def _parse_diagnosis_response(
        self,
        content: str,
        model: str,
        tokens_used: int,
        latency_ms: float,
        default_status: str,
        default_risk_score: float,
        node_type: str,
    ) -> DiagnosisReport:
        """
        解析LLM响应，提取结构化诊断报告
        
        Args:
            content: LLM响应内容
            model: 模型名称
            tokens_used: token使用量
            latency_ms: 延迟
            default_status: 默认状态
            default_risk_score: 默认风险评分
            node_type: 节点类型
            
        Returns:
            DiagnosisReport: 诊断报告
        """
        try:
            # 尝试提取JSON部分
            json_str = self._extract_json(content)
            data = json.loads(json_str)
            
            # 提取字段并验证
            diagnosis_summary = str(data.get('diagnosis_summary', ''))
            if len(diagnosis_summary) > 300:
                diagnosis_summary = diagnosis_summary[:297] + "..."
            
            recommended_actions = data.get('recommended_actions', [])
            if not isinstance(recommended_actions, list):
                recommended_actions = [str(recommended_actions)]
            recommended_actions = [str(a) for a in recommended_actions if a]
            
            urgency_str = data.get('urgency_level', 'medium').lower()
            try:
                urgency_level = UrgencyLevel(urgency_str)
            except ValueError:
                urgency_level = UrgencyLevel.MEDIUM
            
            return DiagnosisReport(
                diagnosis_summary=diagnosis_summary,
                recommended_actions=recommended_actions[:8],
                urgency_level=urgency_level,
                model=model,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                is_fallback=False
            )
        except Exception as e:
            logger.warning(f"解析LLM诊断响应失败，使用模板兜底: {e}")
            # 解析失败，降级到模板
            local_client = self._clients['local']
            report = local_client.generate_structured_diagnosis(
                status=default_status,
                risk_score=default_risk_score,
                fault_type=None,
                trend=None,
                recent_values=None,
                historical_incidents=None,
                node_type=node_type,
                node_id="",
            )
            report.model = model
            report.tokens_used = tokens_used
            report.latency_ms = latency_ms
            report.is_fallback = True
            return report
    
    def _extract_json(self, content: str) -> str:
        """
        从文本中提取JSON字符串
        
        Args:
            content: 可能包含JSON的文本
            
        Returns:
            str: 提取的JSON字符串
        """
        # 尝试直接解析
        try:
            json.loads(content)
            return content
        except json.JSONDecodeError:
            pass
        
        # 尝试提取第一个{...}块
        match = re.search(r'\{[\s\S]*\}', content)
        if match:
            return match.group(0)
        
        # 尝试用markdown代码块包裹
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
        if match:
            return match.group(1).strip()
        
        raise ValueError("无法从响应中提取JSON")
    
    def _log_structured_usage(self, report: DiagnosisReport, mode: str) -> None:
        """
        记录结构化诊断的使用日志
        
        Args:
            report: 诊断报告
            mode: 模式 (llm/template/fallback)
        """
        logger.info(
            f"[LLM Diagnosis] mode={mode}, model={report.model}, "
            f"urgency={report.urgency_level.value}, "
            f"tokens={report.tokens_used}, "
            f"latency_ms={report.latency_ms:.2f}, "
            f"is_fallback={report.is_fallback}, "
            f"actions_count={len(report.recommended_actions)}, "
            f"summary_len={len(report.diagnosis_summary)}"
        )
    
    async def summarize_diagnosis(
        self,
        status: str,
        risk_score: float,
        risk_level: str,
        factors: List[str],
        preload_stats: Dict[str, float]
    ) -> str:
        """
        总结诊断结论（兼容旧接口）
        
        Args:
            status: 预测状态
            risk_score: 风险评分
            risk_level: 风险等级
            factors: 风险因素
            preload_stats: 预紧力统计
            
        Returns:
            str: 诊断总结
        """
        prompt = f"""
请根据以下螺栓预紧力分析结果，生成一份简洁的诊断总结：

当前状态: {status}
风险评分: {risk_score}/10
风险等级: {risk_level}
风险因素: {', '.join(factors) if factors else '无明显风险因素'}

预紧力统计:
- 平均值: {preload_stats.get('mean', 'N/A')}
- 标准差: {preload_stats.get('std', 'N/A')}
- 最大值: {preload_stats.get('max', 'N/A')}
- 最小值: {preload_stats.get('min', 'N/A')}

请用100-150字总结当前状态和主要发现。
"""
        response = await self.generate(prompt)
        return response.content
    
    async def generate_recommendations(
        self,
        status: str,
        risk_level: str,
        factors: List[str]
    ) -> List[str]:
        """
        生成推荐措施（兼容旧接口）
        
        Args:
            status: 预测状态
            risk_level: 风险等级
            factors: 风险因素
            
        Returns:
            List[str]: 推荐措施列表
        """
        prompt = f"""
根据以下螺栓预紧力分析结果，生成3-5条具体的推荐措施：

当前状态: {status}
风险等级: {risk_level}
风险因素: {', '.join(factors) if factors else '无明显风险因素'}

请提供具体、可操作的建议，每条建议不超过30字。
格式：每条建议一行，以"-"开头。
"""
        response = await self.generate(prompt)
        
        # 解析推荐措施
        recommendations = []
        for line in response.content.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('•'):
                recommendations.append(line.lstrip('-•').strip())
            elif line and len(recommendations) < 5:
                recommendations.append(line)
        
        return recommendations[:5] if recommendations else [
            "保持常规监测",
            "按计划执行维护"
        ]
    
    def generate_diagnosis_report_sync(
        self,
        status: str,
        risk_score: float,
        **kwargs
    ) -> DiagnosisReport:
        """同步版本的诊断报告生成方法"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.generate_diagnosis_report(
                status=status,
                risk_score=risk_score,
                **kwargs
            )
        )
    
    def generate_sync(self, prompt: str, **kwargs) -> LLMResponse:
        """同步版本的生成方法"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.generate(prompt, **kwargs))


# 全局LLM客户端
llm_client = LLMClient()
