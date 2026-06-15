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
        parts = re.sub(r"[^a-zA-Z0-9]", "_", name).split("_")
        return "".join(part.capitalize() for part in parts if part)

    def _to_camel_case(self, name: str) -> str:
        """转换为 camelCase"""
        pascal = self._to_pascal_case(name)
        return pascal[0].lower() + pascal[1:] if pascal else ""

    def _to_snake_case(self, name: str) -> str:
        """转换为 snake_case"""
        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", name)
        return name.lower()

    def _to_kebab_case(self, name: str) -> str:
        """转换为 kebab-case"""
        return self._to_snake_case(name).replace("_", "-")

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
