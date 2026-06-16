"""
搜索空间定义模块

定义超参搜索空间，支持：
- 层数 (num_layers)
- 隐藏层大小 (hidden_size)
- Dropout率 (dropout_rate)
- 学习率 (learning_rate)
- 序列长度 (sequence_length)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import json


class ParamType(str, Enum):
    """参数类型枚举"""
    INT = "int"
    FLOAT = "float"
    CATEGORICAL = "categorical"
    UNIFORM = "uniform"
    LOG_UNIFORM = "log_uniform"
    DISCRETE_UNIFORM = "discrete_uniform"


@dataclass
class SearchSpaceParam:
    """搜索空间参数定义"""
    name: str
    param_type: ParamType
    low: Optional[Union[int, float]] = None
    high: Optional[Union[int, float]] = None
    choices: Optional[List[Any]] = None
    step: Optional[Union[int, float]] = None
    default_value: Optional[Any] = None
    log: bool = False
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "param_type": self.param_type.value,
            "low": self.low,
            "high": self.high,
            "choices": self.choices,
            "step": self.step,
            "default_value": self.default_value,
            "log": self.log,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchSpaceParam":
        """从字典创建"""
        return cls(
            name=data["name"],
            param_type=ParamType(data["param_type"]),
            low=data.get("low"),
            high=data.get("high"),
            choices=data.get("choices"),
            step=data.get("step"),
            default_value=data.get("default_value"),
            log=data.get("log", False),
            description=data.get("description"),
        )


@dataclass
class SearchSpace:
    """搜索空间定义"""
    params: List[SearchSpaceParam] = field(default_factory=list)

    def add_param(self, param: SearchSpaceParam) -> "SearchSpace":
        """添加参数"""
        self.params.append(param)
        return self

    def get_param(self, name: str) -> Optional[SearchSpaceParam]:
        """获取指定名称的参数"""
        for param in self.params:
            if param.name == name:
                return param
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "params": [p.to_dict() for p in self.params],
        }

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchSpace":
        """从字典创建"""
        params = [SearchSpaceParam.from_dict(p) for p in data.get("params", [])]
        return cls(params=params)

    @classmethod
    def from_json(cls, json_str: str) -> "SearchSpace":
        """从JSON字符串创建"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def __iter__(self):
        return iter(self.params)

    def __len__(self):
        return len(self.params)


def default_bolt_search_space() -> SearchSpace:
    """
    默认螺栓模型搜索空间

    Returns:
        SearchSpace: 螺栓模型的默认搜索空间
    """
    return SearchSpace(params=[
        SearchSpaceParam(
            name="num_layers",
            param_type=ParamType.INT,
            low=1,
            high=4,
            default_value=2,
            description="LSTM层数",
        ),
        SearchSpaceParam(
            name="hidden_size",
            param_type=ParamType.CATEGORICAL,
            choices=[32, 64, 128, 256, 512],
            default_value=128,
            description="隐藏层大小",
        ),
        SearchSpaceParam(
            name="dropout_rate",
            param_type=ParamType.FLOAT,
            low=0.0,
            high=0.5,
            step=0.05,
            default_value=0.2,
            description="Dropout率",
        ),
        SearchSpaceParam(
            name="learning_rate",
            param_type=ParamType.LOG_UNIFORM,
            low=1e-5,
            high=1e-2,
            log=True,
            default_value=0.001,
            description="学习率",
        ),
        SearchSpaceParam(
            name="sequence_length",
            param_type=ParamType.CATEGORICAL,
            choices=[50, 100, 150, 200],
            default_value=100,
            description="输入序列长度",
        ),
    ])


def default_flange_search_space() -> SearchSpace:
    """
    默认法兰面模型搜索空间

    Returns:
        SearchSpace: 法兰面模型的默认搜索空间
    """
    return SearchSpace(params=[
        SearchSpaceParam(
            name="num_layers",
            param_type=ParamType.INT,
            low=1,
            high=3,
            default_value=2,
            description="Transformer层数",
        ),
        SearchSpaceParam(
            name="hidden_size",
            param_type=ParamType.CATEGORICAL,
            choices=[64, 128, 256, 512],
            default_value=128,
            description="隐藏层大小",
        ),
        SearchSpaceParam(
            name="dropout_rate",
            param_type=ParamType.FLOAT,
            low=0.0,
            high=0.4,
            step=0.05,
            default_value=0.1,
            description="Dropout率",
        ),
        SearchSpaceParam(
            name="learning_rate",
            param_type=ParamType.LOG_UNIFORM,
            low=1e-5,
            high=1e-2,
            log=True,
            default_value=0.001,
            description="学习率",
        ),
        SearchSpaceParam(
            name="sequence_length",
            param_type=ParamType.CATEGORICAL,
            choices=[50, 100, 150],
            default_value=100,
            description="每个螺栓的序列长度",
        ),
    ])


def build_search_space(
    model_type: str,
    custom_params: Optional[Dict[str, Any]] = None,
    fixed_params: Optional[Dict[str, Any]] = None,
) -> SearchSpace:
    """
    构建搜索空间

    Args:
        model_type: 模型类型 (bolt/flange)
        custom_params: 自定义参数覆盖，格式: {param_name: {low, high, choices, ...}}
        fixed_params: 固定参数，格式: {param_name: value}，这些参数将从搜索空间中移除

    Returns:
        SearchSpace: 构建的搜索空间
    """
    if model_type == "bolt":
        search_space = default_bolt_search_space()
    elif model_type == "flange":
        search_space = default_flange_search_space()
    else:
        raise ValueError(f"未知模型类型: {model_type}")

    if custom_params:
        for param_name, param_config in custom_params.items():
            param = search_space.get_param(param_name)
            if param:
                if "low" in param_config:
                    param.low = param_config["low"]
                if "high" in param_config:
                    param.high = param_config["high"]
                if "choices" in param_config:
                    param.choices = param_config["choices"]
                if "step" in param_config:
                    param.step = param_config["step"]
                if "log" in param_config:
                    param.log = param_config["log"]
                if "param_type" in param_config:
                    param.param_type = ParamType(param_config["param_type"])

    if fixed_params:
        search_space.params = [
            p for p in search_space.params
            if p.name not in fixed_params
        ]

    return search_space


def sample_from_search_space(
    trial: Any,
    search_space: SearchSpace,
    framework: str = "optuna",
) -> Dict[str, Any]:
    """
    从搜索空间中采样参数

    Args:
        trial: 试验对象 (Optuna trial 或 Ray Tune config)
        search_space: 搜索空间
        framework: 框架类型 (optuna/ray_tune)

    Returns:
        Dict[str, Any]: 采样的参数
    """
    params = {}

    for param in search_space:
        param_name = param.name

        if framework == "optuna":
            if param.param_type == ParamType.INT:
                params[param_name] = trial.suggest_int(
                    param_name,
                    int(param.low),
                    int(param.high),
                    step=int(param.step) if param.step else 1,
                )
            elif param.param_type == ParamType.FLOAT:
                params[param_name] = trial.suggest_float(
                    param_name,
                    float(param.low),
                    float(param.high),
                    step=float(param.step) if param.step else None,
                )
            elif param.param_type == ParamType.CATEGORICAL:
                params[param_name] = trial.suggest_categorical(
                    param_name,
                    param.choices,
                )
            elif param.param_type == ParamType.UNIFORM:
                params[param_name] = trial.suggest_float(
                    param_name,
                    float(param.low),
                    float(param.high),
                )
            elif param.param_type == ParamType.LOG_UNIFORM:
                params[param_name] = trial.suggest_float(
                    param_name,
                    float(param.low),
                    float(param.high),
                    log=True,
                )
            elif param.param_type == ParamType.DISCRETE_UNIFORM:
                params[param_name] = trial.suggest_float(
                    param_name,
                    float(param.low),
                    float(param.high),
                    step=float(param.step) if param.step else 1.0,
                )

        elif framework == "ray_tune":
            if param.param_type == ParamType.INT:
                from ray import tune
                params[param_name] = tune.randint(
                    int(param.low),
                    int(param.high) + 1,
                )
            elif param.param_type == ParamType.FLOAT:
                from ray import tune
                if param.step:
                    params[param_name] = tune.choice(
                        [i * param.step for i in range(
                            int(param.low / param.step),
                            int(param.high / param.step) + 1
                        )]
                    )
                else:
                    params[param_name] = tune.uniform(
                        float(param.low),
                        float(param.high),
                    )
            elif param.param_type == ParamType.CATEGORICAL:
                from ray import tune
                params[param_name] = tune.choice(param.choices)
            elif param.param_type == ParamType.LOG_UNIFORM:
                from ray import tune
                params[param_name] = tune.loguniform(
                    float(param.low),
                    float(param.high),
                )

    return params
