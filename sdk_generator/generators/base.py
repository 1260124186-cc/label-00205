"""
SDK 生成器基类

定义 SDK 生成的通用接口和工具方法。
"""

import re
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from abc import ABC, abstractmethod
from loguru import logger


class BaseSDKGenerator(ABC):
    """SDK 生成器基类"""

    def __init__(self, config):
        """
        初始化生成器

        Args:
            config: SDKConfig 配置对象
        """
        self.config = config
        self.openapi_spec: Optional[Dict[str, Any]] = None

    def generate(
        self, openapi_spec: Dict[str, Any], output_dir: Optional[Path] = None
    ) -> Path:
        """
        生成 SDK

        Args:
            openapi_spec: OpenAPI 规范
            output_dir: 输出目录

        Returns:
            SDK 输出目录路径
        """
        self.openapi_spec = openapi_spec
        output_dir = output_dir or self.config.output_dir / self.language_name
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"开始生成 {self.language_name} SDK，输出目录: {output_dir}")

        self._generate_project_structure(output_dir)
        self._generate_models(output_dir)
        self._generate_api_clients(output_dir)
        self._generate_core_modules(output_dir)
        self._generate_package_files(output_dir)
        self._generate_readme(output_dir)

        logger.info(f"{self.language_name} SDK 生成完成")
        return output_dir

    @property
    @abstractmethod
    def language_name(self) -> str:
        """语言名称"""
        pass

    @abstractmethod
    def _generate_project_structure(self, output_dir: Path) -> None:
        """生成项目目录结构"""
        pass

    @abstractmethod
    def _generate_models(self, output_dir: Path) -> None:
        """生成数据模型"""
        pass

    @abstractmethod
    def _generate_api_clients(self, output_dir: Path) -> None:
        """生成 API 客户端"""
        pass

    @abstractmethod
    def _generate_core_modules(self, output_dir: Path) -> None:
        """生成核心模块（重试、鉴权、分页等）"""
        pass

    @abstractmethod
    def _generate_package_files(self, output_dir: Path) -> None:
        """生成包配置文件"""
        pass

    @abstractmethod
    def _generate_readme(self, output_dir: Path) -> None:
        """生成 README 文档"""
        pass

    def _parse_paths(self) -> List[Dict[str, Any]]:
        """
        解析 API 路径，按标签分组

        Returns:
            分组后的 API 列表
        """
        paths = self.openapi_spec.get("paths", {})
        grouped = {}

        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.lower() not in [
                    "get",
                    "post",
                    "put",
                    "delete",
                    "patch",
                    "head",
                    "options",
                ]:
                    continue

                tags = operation.get("tags", ["default"])
                for tag in tags:
                    if tag not in grouped:
                        grouped[tag] = []

                    grouped[tag].append(
                        {
                            "path": path,
                            "method": method.upper(),
                            "operation": operation,
                            "operation_id": operation.get(
                                "operationId",
                                self._generate_operation_id(path, method),
                            ),
                            "summary": operation.get("summary", ""),
                            "description": operation.get("description", ""),
                            "parameters": operation.get("parameters", []),
                            "request_body": operation.get("requestBody"),
                            "responses": operation.get("responses", {}),
                        }
                    )

        return [{"tag": tag, "operations": ops} for tag, ops in grouped.items()]

    def _generate_operation_id(self, path: str, method: str) -> str:
        """生成操作 ID"""
        path_parts = re.findall(r"[a-zA-Z0-9]+", path)
        return f"{method.lower()}_{'_'.join(path_parts)}"

    def _get_schemas(self) -> Dict[str, Any]:
        """获取所有 schema 定义"""
        return (
            self.openapi_spec.get("components", {}).get("schemas", {})
        )

    def _to_pascal_case(self, name: str) -> str:
        """转换为 PascalCase"""
        name_str = str(name)
        name_str = re.sub(r"[^a-zA-Z0-9]", "_", name_str)
        name_str = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name_str)
        name_str = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name_str)
        parts = name_str.split("_")
        return "".join(part.capitalize() for part in parts if part)

    def _to_camel_case(self, name: str) -> str:
        """转换为 camelCase"""
        pascal = self._to_pascal_case(name)
        return pascal[0].lower() + pascal[1:] if pascal else ""

    def _to_snake_case(self, name: str) -> str:
        """转换为 snake_case，同时处理特殊字符"""
        name = re.sub(r"[^a-zA-Z0-9_]", "_", str(name))
        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", name)
        name = re.sub(r"_+", "_", name)
        return name.lower().strip("_")

    def _to_kebab_case(self, name: str) -> str:
        """转换为 kebab-case"""
        return self._to_snake_case(name).replace("_", "-")

    def _safe_filename(self, name: str) -> str:
        """
        生成安全的文件名，确保不包含中文、空格和特殊字符。
        对于中文标签，转换为 api_group_<序号> 的形式。
        """
        import re
        import hashlib

        name_str = str(name).strip()

        if not name_str:
            return "api"

        if re.match(r"^[a-zA-Z0-9_]+$", name_str):
            return name_str.lower()

        if re.search(r"[^\x00-\x7F]", name_str):
            hash_digest = hashlib.md5(name_str.encode("utf-8")).hexdigest()[:8]
            safe_name = self._to_snake_case(
                re.sub(r"[^\x00-\x7F]", "", name_str)
            )
            if not safe_name or len(safe_name) < 3:
                safe_name = "api_group"
            return f"{safe_name}_{hash_digest}"

        safe_name = re.sub(r"[^a-zA-Z0-9]", "_", name_str)
        safe_name = re.sub(r"_+", "_", safe_name).strip("_")
        return safe_name.lower()

    def _sanitize_tag(self, tag: str, index: int = 0) -> str:
        """
        清理标签名，确保可用于文件名和类名。
        对于中文标签，返回英文描述或序号形式。
        """
        import re

        tag_str = str(tag).strip()

        if not re.search(r"[^\x00-\x7F]", tag_str):
            return tag_str

        tag_mappings = {
            "预测": "Prediction",
            "风险评估": "RiskAssessment",
            "模型管理": "ModelManagement",
            "配置": "Config",
            "联邦学习": "FederatedLearning",
            "告警管理": "AlertManagement",
            "告警订阅": "AlertSubscription",
            "通知渠道": "NotificationChannel",
            "工单管理": "WorkOrder",
            "工单统计": "WorkOrderStats",
            "CMMS集成": "CMMSIntegration",
            "合规审计": "ComplianceAudit",
            "数据质量": "DataQuality",
            "边缘计算": "EdgeComputing",
            "多租户": "MultiTenant",
            "组织架构": "Organization",
            "配额管理": "QuotaManagement",
            "租户用户": "TenantUser",
            "租户API Key": "TenantApiKey",
            "知识库CBR": "KnowledgeBase",
            "健康度评分": "HealthScore",
            "流式预测": "StreamPrediction",
            "配置中心": "ConfigCenter",
            "调度器": "Scheduler",
            "异常管理": "AnomalyManagement",
            "API密钥管理": "ApiKeyManagement",
            "API审计日志": "ApiAuditLog",
            "LLM智能诊断": "LLMDiagnosis",
            "碳排与能效分析": "CarbonAnalysis",
            "系统": "System",
            "监控": "Monitoring",
        }

        if tag_str in tag_mappings:
            return tag_mappings[tag_str]

        return f"ApiGroup{index + 1}"

    def _get_type_mapping(self) -> Dict[str, str]:
        """获取 OpenAPI 类型到目标语言的映射"""
        return {
            "string": "string",
            "integer": "number",
            "number": "number",
            "boolean": "boolean",
            "array": "array",
            "object": "object",
        }

    def _resolve_ref(self, ref: str) -> Dict[str, Any]:
        """解析 $ref 引用"""
        parts = ref.replace("#/", "").split("/")
        current = self.openapi_spec
        for part in parts:
            current = current.get(part, {})
        return current

    def _is_pagination_endpoint(self, operation: Dict[str, Any]) -> bool:
        """判断是否为分页端点"""
        params = operation.get("parameters", [])
        has_cursor = any(
            p.get("name") == self.config.pagination_config["cursor_param"]
            for p in params
        )
        has_limit = any(
            p.get("name") == self.config.pagination_config["limit_param"]
            for p in params
        )
        return has_cursor and has_limit

    def load_openapi_spec(self, spec_path: str | Path) -> Dict[str, Any]:
        """
        从文件加载 OpenAPI 规范

        Args:
            spec_path: 规范文件路径

        Returns:
            OpenAPI 规范字典
        """
        spec_path = Path(spec_path)
        with open(spec_path, "r", encoding="utf-8") as f:
            if spec_path.suffix in (".yaml", ".yml"):
                self.openapi_spec = yaml.safe_load(f)
            else:
                self.openapi_spec = json.load(f)
        return self.openapi_spec
