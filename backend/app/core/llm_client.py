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
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
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
        success: 是否成功
        error: 错误信息
    """
    content: str
    model: str
    tokens_used: int = 0
    success: bool = True
    error: Optional[str] = None


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
                
                if response.status_code == 200:
                    data = response.json()
                    return LLMResponse(
                        content=data['choices'][0]['message']['content'],
                        model=self.model,
                        tokens_used=data.get('usage', {}).get('total_tokens', 0),
                        success=True
                    )
                else:
                    return LLMResponse(
                        content="",
                        model=self.model,
                        success=False,
                        error=f"API error: {response.status_code}"
                    )
                    
        except Exception as e:
            return LLMResponse(
                content="",
                model=self.model,
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
                
                if response.status_code == 200:
                    data = response.json()
                    return LLMResponse(
                        content=data['output']['text'],
                        model=self.model,
                        tokens_used=data.get('usage', {}).get('total_tokens', 0),
                        success=True
                    )
                else:
                    return LLMResponse(
                        content="",
                        model=self.model,
                        success=False,
                        error=f"API error: {response.status_code}"
                    )
                    
        except Exception as e:
            return LLMResponse(
                content="",
                model=self.model,
                success=False,
                error=str(e)
            )


class LocalTemplateClient(BaseLLMClient):
    """本地模板客户端（不需要LLM API）"""
    
    def __init__(self):
        self.model = "local_template"
        
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """使用本地模板生成响应"""
        # 基于关键词匹配生成响应
        content = self._generate_from_template(prompt)
        
        return LLMResponse(
            content=content,
            model=self.model,
            success=True
        )
    
    def _generate_from_template(self, prompt: str) -> str:
        """基于模板生成响应"""
        # 检测任务类型
        if "诊断" in prompt or "分析" in prompt:
            return self._diagnosis_template(prompt)
        elif "推荐" in prompt or "建议" in prompt:
            return self._recommendation_template(prompt)
        else:
            return self._general_template(prompt)
    
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
    
    自动选择可用的LLM提供商。
    """
    
    def __init__(self):
        """初始化LLM客户端"""
        llm_config = config.get('llm', {})
        self.provider = llm_config.get('provider', 'local')
        
        # 初始化客户端
        self._clients: Dict[str, BaseLLMClient] = {}
        self._init_clients(llm_config)
        
        logger.info(f"LLM客户端初始化完成: provider={self.provider}")
    
    def _init_clients(self, llm_config: Dict) -> None:
        """初始化所有客户端"""
        # 本地模板客户端（总是可用）
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
        if self.provider in self._clients:
            return self._clients[self.provider]
        return self._clients['local']
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """
        生成响应
        
        Args:
            prompt: 提示词
            **kwargs: 额外参数
            
        Returns:
            LLMResponse: 响应
        """
        client = self._get_client()
        response = await client.generate(prompt, **kwargs)
        
        # 如果失败，尝试本地模板
        if not response.success and self.provider != 'local':
            logger.warning(f"LLM调用失败，使用本地模板: {response.error}")
            response = await self._clients['local'].generate(prompt)
        
        return response
    
    async def summarize_diagnosis(
        self,
        status: str,
        risk_score: float,
        risk_level: str,
        factors: List[str],
        preload_stats: Dict[str, float]
    ) -> str:
        """
        总结诊断结论
        
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
        生成推荐措施
        
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
