"""
Breaking Change 检测工具

对比两个版本的 OpenAPI 规范，检测破坏性变更。
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class ChangeLevel(str, Enum):
    """变更级别"""

    BREAKING = "breaking"
    DEPRECATED = "deprecated"
    ADDITIVE = "additive"
    UNKNOWN = "unknown"


@dataclass
class BreakingChange:
    """单个破坏性变更"""

    path: str
    type: str
    description: str
    level: ChangeLevel
    old_value: Any = None
    new_value: Any = None


@dataclass
class BreakingChangeReport:
    """破坏性变更报告"""

    total_changes: int = 0
    breaking_changes: List[BreakingChange] = field(default_factory=list)
    deprecated_changes: List[BreakingChange] = field(default_factory=list)
    additive_changes: List[BreakingChange] = field(default_factory=list)

    @property
    def has_breaking_changes(self) -> bool:
        """是否包含破坏性变更"""
        return len(self.breaking_changes) > 0

    def add(self, change: BreakingChange) -> None:
        """添加变更"""
        self.total_changes += 1
        if change.level == ChangeLevel.BREAKING:
            self.breaking_changes.append(change)
        elif change.level == ChangeLevel.DEPRECATED:
            self.deprecated_changes.append(change)
        elif change.level == ChangeLevel.ADDITIVE:
            self.additive_changes.append(change)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_changes": self.total_changes,
            "has_breaking_changes": self.has_breaking_changes,
            "breaking_changes": [
                {
                    "path": c.path,
                    "type": c.type,
                    "description": c.description,
                    "level": c.level.value,
                    "old_value": c.old_value,
                    "new_value": c.new_value,
                }
                for c in self.breaking_changes
            ],
            "deprecated_changes": [
                {
                    "path": c.path,
                    "type": c.type,
                    "description": c.description,
                    "level": c.level.value,
                }
                for c in self.deprecated_changes
            ],
            "additive_changes": [
                {
                    "path": c.path,
                    "type": c.type,
                    "description": c.description,
                    "level": c.level.value,
                }
                for c in self.additive_changes
            ],
        }


class BreakingChangeDetector:
    """破坏性变更检测器"""

    def __init__(self, old_spec: Dict[str, Any], new_spec: Dict[str, Any]):
        """
        初始化检测器

        Args:
            old_spec: 旧版 OpenAPI 规范
            new_spec: 新版 OpenAPI 规范
        """
        self.old_spec = old_spec
        self.new_spec = new_spec
        self.report = BreakingChangeReport()

    def detect(self) -> BreakingChangeReport:
        """
        执行破坏性变更检测

        Returns:
            破坏性变更报告
        """
        logger.info("开始检测 Breaking Changes")

        self._check_paths()
        self._check_schemas()
        self._check_parameters()
        self._check_security()
        self._check_servers()

        logger.info(
            f"检测完成: 共 {self.report.total_changes} 处变更, "
            f"{len(self.report.breaking_changes)} 处破坏性变更"
        )

        return self.report

    def _check_paths(self) -> None:
        """检查路径变更"""
        old_paths = set(self.old_spec.get("paths", {}).keys())
        new_paths = set(self.new_spec.get("paths", {}).keys())

        for path in old_paths - new_paths:
            self.report.add(
                BreakingChange(
                    path=path,
                    type="path_removed",
                    description=f"路径 {path} 被移除",
                    level=ChangeLevel.BREAKING,
                    old_value=path,
                )
            )

        for path in new_paths - old_paths:
            self.report.add(
                BreakingChange(
                    path=path,
                    type="path_added",
                    description=f"新增路径 {path}",
                    level=ChangeLevel.ADDITIVE,
                    new_value=path,
                )
            )

        for path in old_paths & new_paths:
            self._check_path_operations(path)

    def _check_path_operations(self, path: str) -> None:
        """检查路径下的操作变更"""
        old_ops = self.old_spec["paths"][path]
        new_ops = self.new_spec["paths"][path]

        old_methods = set(k.upper() for k in old_ops.keys() if k.lower() in [
            "get", "post", "put", "delete", "patch", "head", "options"
        ])
        new_methods = set(k.upper() for k in new_ops.keys() if k.lower() in [
            "get", "post", "put", "delete", "patch", "head", "options"
        ])

        for method in old_methods - new_methods:
            self.report.add(
                BreakingChange(
                    path=f"{path} {method}",
                    type="operation_removed",
                    description=f"{path} {method} 操作被移除",
                    level=ChangeLevel.BREAKING,
                )
            )

        for method in new_methods - old_methods:
            self.report.add(
                BreakingChange(
                    path=f"{path} {method}",
                    type="operation_added",
                    description=f"新增 {path} {method} 操作",
                    level=ChangeLevel.ADDITIVE,
                )
            )

        for method in old_methods & new_methods:
            old_op = old_ops.get(method.lower(), {})
            new_op = new_ops.get(method.lower(), {})
            self._check_operation_params(f"{path} {method}", old_op, new_op)
            self._check_operation_request_body(f"{path} {method}", old_op, new_op)
            self._check_operation_responses(f"{path} {method}", old_op, new_op)
            self._check_operation_deprecated(f"{path} {method}", old_op, new_op)

    def _check_operation_params(
        self, path: str, old_op: Dict, new_op: Dict
    ) -> None:
        """检查操作参数变更"""
        old_params = {}
        for p in old_op.get("parameters", []):
            key = f"{p.get('in', 'query')}.{p.get('name', '')}"
            old_params[key] = p

        new_params = {}
        for p in new_op.get("parameters", []):
            key = f"{p.get('in', 'query')}.{p.get('name', '')}"
            new_params[key] = p

        for key in set(old_params.keys()) - set(new_params.keys()):
            self.report.add(
                BreakingChange(
                    path=f"{path}.{key}",
                    type="parameter_removed",
                    description=f"参数 {key} 被移除",
                    level=ChangeLevel.BREAKING,
                )
            )

        for key in set(new_params.keys()) - set(old_params.keys()):
            param = new_params[key]
            if param.get("required", False):
                level = ChangeLevel.BREAKING
                desc = f"新增必需参数 {key}"
            else:
                level = ChangeLevel.ADDITIVE
                desc = f"新增可选参数 {key}"
            self.report.add(
                BreakingChange(
                    path=f"{path}.{key}",
                    type="parameter_added",
                    description=desc,
                    level=level,
                )
            )

        for key in set(old_params.keys()) & set(new_params.keys()):
            old_param = old_params[key]
            new_param = new_params[key]

            if old_param.get("required", False) != new_param.get("required", False):
                if new_param.get("required", False):
                    self.report.add(
                        BreakingChange(
                            path=f"{path}.{key}.required",
                            type="parameter_required_changed",
                            description=f"参数 {key} 从可选变为必需",
                            level=ChangeLevel.BREAKING,
                            old_value=False,
                            new_value=True,
                        )
                    )
                else:
                    self.report.add(
                        BreakingChange(
                            path=f"{path}.{key}.required",
                            type="parameter_required_changed",
                            description=f"参数 {key} 从必需变为可选",
                            level=ChangeLevel.ADDITIVE,
                            old_value=True,
                            new_value=False,
                        )
                    )

            old_type = old_param.get("schema", {}).get("type", "")
            new_type = new_param.get("schema", {}).get("type", "")
            if old_type and new_type and old_type != new_type:
                self.report.add(
                    BreakingChange(
                        path=f"{path}.{key}.type",
                        type="parameter_type_changed",
                        description=f"参数 {key} 类型从 {old_type} 变为 {new_type}",
                        level=ChangeLevel.BREAKING,
                        old_value=old_type,
                        new_value=new_type,
                    )
                )

    def _check_operation_request_body(
        self, path: str, old_op: Dict, new_op: Dict
    ) -> None:
        """检查请求体变更"""
        old_body = old_op.get("requestBody")
        new_body = new_op.get("requestBody")

        if old_body and not new_body:
            self.report.add(
                BreakingChange(
                    path=f"{path}.requestBody",
                    type="request_body_removed",
                    description="请求体被移除",
                    level=ChangeLevel.BREAKING,
                )
            )
        elif not old_body and new_body:
            if new_body.get("required", False):
                level = ChangeLevel.BREAKING
            else:
                level = ChangeLevel.ADDITIVE
            self.report.add(
                BreakingChange(
                    path=f"{path}.requestBody",
                    type="request_body_added",
                    description="新增请求体",
                    level=level,
                )
            )
        elif old_body and new_body:
            old_required = old_body.get("required", False)
            new_required = new_body.get("required", False)
            if old_required != new_required:
                if new_required:
                    self.report.add(
                        BreakingChange(
                            path=f"{path}.requestBody.required",
                            type="request_body_required_changed",
                            description="请求体从可选变为必需",
                            level=ChangeLevel.BREAKING,
                        )
                    )
                else:
                    self.report.add(
                        BreakingChange(
                            path=f"{path}.requestBody.required",
                            type="request_body_required_changed",
                            description="请求体从必需变为可选",
                            level=ChangeLevel.ADDITIVE,
                        )
                    )

    def _check_operation_responses(
        self, path: str, old_op: Dict, new_op: Dict
    ) -> None:
        """检查响应变更"""
        old_responses = set(old_op.get("responses", {}).keys())
        new_responses = set(new_op.get("responses", {}).keys())

        for code in old_responses - new_responses:
            if code.startswith("2") or code == "default":
                self.report.add(
                    BreakingChange(
                        path=f"{path}.responses.{code}",
                        type="response_removed",
                        description=f"响应 {code} 被移除",
                        level=ChangeLevel.BREAKING,
                    )
                )

        for code in new_responses - old_responses:
            self.report.add(
                BreakingChange(
                    path=f"{path}.responses.{code}",
                    type="response_added",
                    description=f"新增响应 {code}",
                    level=ChangeLevel.ADDITIVE,
                )
            )

    def _check_operation_deprecated(
        self, path: str, old_op: Dict, new_op: Dict
    ) -> None:
        """检查弃用状态变更"""
        old_deprecated = old_op.get("deprecated", False)
        new_deprecated = new_op.get("deprecated", False)

        if not old_deprecated and new_deprecated:
            self.report.add(
                BreakingChange(
                    path=path,
                    type="operation_deprecated",
                    description=f"操作 {path} 被标记为弃用",
                    level=ChangeLevel.DEPRECATED,
                )
            )

    def _check_schemas(self) -> None:
        """检查 schema 变更"""
        old_schemas = self.old_spec.get("components", {}).get("schemas", {})
        new_schemas = self.new_spec.get("components", {}).get("schemas", {})

        for name in set(old_schemas.keys()) - set(new_schemas.keys()):
            self.report.add(
                BreakingChange(
                    path=f"components.schemas.{name}",
                    type="schema_removed",
                    description=f"Schema {name} 被移除",
                    level=ChangeLevel.BREAKING,
                )
            )

        for name in set(new_schemas.keys()) - set(old_schemas.keys()):
            self.report.add(
                BreakingChange(
                    path=f"components.schemas.{name}",
                    type="schema_added",
                    description=f"新增 Schema {name}",
                    level=ChangeLevel.ADDITIVE,
                )
            )

        for name in set(old_schemas.keys()) & set(new_schemas.keys()):
            self._check_schema_properties(
                f"components.schemas.{name}",
                old_schemas[name],
                new_schemas[name],
            )

    def _check_schema_properties(
        self, path: str, old_schema: Dict, new_schema: Dict
    ) -> None:
        """检查 schema 属性变更"""
        old_props = old_schema.get("properties", {})
        new_props = new_schema.get("properties", {})
        old_required = set(old_schema.get("required", []))
        new_required = set(new_schema.get("required", []))

        for prop in set(old_props.keys()) - set(new_props.keys()):
            self.report.add(
                BreakingChange(
                    path=f"{path}.{prop}",
                    type="property_removed",
                    description=f"属性 {prop} 被移除",
                    level=ChangeLevel.BREAKING,
                )
            )

        for prop in set(new_props.keys()) - set(old_props.keys()):
            if prop in new_required:
                level = ChangeLevel.BREAKING
                desc = f"新增必需属性 {prop}"
            else:
                level = ChangeLevel.ADDITIVE
                desc = f"新增可选属性 {prop}"
            self.report.add(
                BreakingChange(
                    path=f"{path}.{prop}",
                    type="property_added",
                    description=desc,
                    level=level,
                )
            )

        for prop in set(old_props.keys()) & set(new_props.keys()):
            old_prop = old_props[prop]
            new_prop = new_props[prop]

            old_type = old_prop.get("type", "")
            new_type = new_prop.get("type", "")
            if old_type and new_type and old_type != new_type:
                self.report.add(
                    BreakingChange(
                        path=f"{path}.{prop}.type",
                        type="property_type_changed",
                        description=f"属性 {prop} 类型从 {old_type} 变为 {new_type}",
                        level=ChangeLevel.BREAKING,
                        old_value=old_type,
                        new_value=new_type,
                    )
                )

            was_required = prop in old_required
            is_required = prop in new_required
            if was_required != is_required:
                if is_required:
                    self.report.add(
                        BreakingChange(
                            path=f"{path}.{prop}.required",
                            type="property_required_changed",
                            description=f"属性 {prop} 从可选变为必需",
                            level=ChangeLevel.BREAKING,
                            old_value=False,
                            new_value=True,
                        )
                    )
                else:
                    self.report.add(
                        BreakingChange(
                            path=f"{path}.{prop}.required",
                            type="property_required_changed",
                            description=f"属性 {prop} 从必需变为可选",
                            level=ChangeLevel.ADDITIVE,
                            old_value=True,
                            new_value=False,
                        )
                    )

            if old_prop.get("deprecated", False) != new_prop.get("deprecated", False):
                if new_prop.get("deprecated", False):
                    self.report.add(
                        BreakingChange(
                            path=f"{path}.{prop}",
                            type="property_deprecated",
                            description=f"属性 {prop} 被标记为弃用",
                            level=ChangeLevel.DEPRECATED,
                        )
                    )

    def _check_parameters(self) -> None:
        """检查全局参数组件"""
        old_params = self.old_spec.get("components", {}).get("parameters", {})
        new_params = self.new_spec.get("components", {}).get("parameters", {})

        for name in set(old_params.keys()) - set(new_params.keys()):
            self.report.add(
                BreakingChange(
                    path=f"components.parameters.{name}",
                    type="parameter_component_removed",
                    description=f"参数组件 {name} 被移除",
                    level=ChangeLevel.BREAKING,
                )
            )

        for name in set(new_params.keys()) - set(old_params.keys()):
            self.report.add(
                BreakingChange(
                    path=f"components.parameters.{name}",
                    type="parameter_component_added",
                    description=f"新增参数组件 {name}",
                    level=ChangeLevel.ADDITIVE,
                )
            )

    def _check_security(self) -> None:
        """检查安全方案变更"""
        old_security = set(
            self.old_spec.get("components", {}).get("securitySchemes", {}).keys()
        )
        new_security = set(
            self.new_spec.get("components", {}).get("securitySchemes", {}).keys()
        )

        for name in old_security - new_security:
            self.report.add(
                BreakingChange(
                    path=f"components.securitySchemes.{name}",
                    type="security_scheme_removed",
                    description=f"安全方案 {name} 被移除",
                    level=ChangeLevel.BREAKING,
                )
            )

        for name in new_security - old_security:
            self.report.add(
                BreakingChange(
                    path=f"components.securitySchemes.{name}",
                    type="security_scheme_added",
                    description=f"新增安全方案 {name}",
                    level=ChangeLevel.ADDITIVE,
                )
            )

    def _check_servers(self) -> None:
        """检查服务器配置变更"""
        old_servers = [s.get("url", "") for s in self.old_spec.get("servers", [])]
        new_servers = [s.get("url", "") for s in self.new_spec.get("servers", [])]

        if old_servers != new_servers:
            self.report.add(
                BreakingChange(
                    path="servers",
                    type="servers_changed",
                    description="服务器配置发生变更",
                    level=ChangeLevel.UNKNOWN,
                    old_value=old_servers,
                    new_value=new_servers,
                )
            )


def load_spec(path: str | Path) -> Dict[str, Any]:
    """
    加载 OpenAPI 规范文件

    Args:
        path: 文件路径

    Returns:
        OpenAPI 规范字典
    """
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        if path.suffix in (".yaml", ".yml"):
            return yaml.safe_load(f)
        else:
            return json.load(f)


def detect_breaking_changes(
    old_spec_path: str | Path,
    new_spec_path: str | Path,
    output_path: Optional[str | Path] = None,
) -> BreakingChangeReport:
    """
    便捷函数：检测破坏性变更

    Args:
        old_spec_path: 旧版规范路径
        new_spec_path: 新版规范路径
        output_path: 报告输出路径（可选）

    Returns:
        破坏性变更报告
    """
    old_spec = load_spec(old_spec_path)
    new_spec = load_spec(new_spec_path)

    detector = BreakingChangeDetector(old_spec, new_spec)
    report = detector.detect()

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"Breaking Change 报告已保存到: {output_path}")

    return report
