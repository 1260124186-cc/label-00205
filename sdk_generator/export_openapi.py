"""
OpenAPI 规范导出工具

从 FastAPI 应用导出 OpenAPI 3 规范，并进行优化和后处理。
"""

import json
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger


class OpenAPIExporter:
    """OpenAPI 规范导出器"""

    def __init__(self, app_module: str = "main:create_app"):
        """
        初始化导出器

        Args:
            app_module: FastAPI 应用工厂函数路径，格式为 "module:factory_func"
        """
        self.app_module = app_module

    def load_app(self):
        """加载 FastAPI 应用"""
        import importlib

        module_path, factory_name = self.app_module.split(":")
        module = importlib.import_module(module_path)
        factory = getattr(module, factory_name)
        return factory()

    def export(
        self,
        output_path: str | Path,
        format: str = "json",
        api_version: str = "v1",
    ) -> Dict[str, Any]:
        """
        导出 OpenAPI 规范

        Args:
            output_path: 输出文件路径
            format: 输出格式，json 或 yaml
            api_version: API 版本

        Returns:
            OpenAPI 规范字典
        """
        logger.info(f"导出 OpenAPI 规范，格式: {format}")

        app = self.load_app()
        openapi_schema = app.openapi()

        openapi_schema = self._post_process(openapi_schema, api_version)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(openapi_schema, f, ensure_ascii=False, indent=2)
        elif format in ("yaml", "yml"):
            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(openapi_schema, f, allow_unicode=True, default_flow_style=False)
        else:
            raise ValueError(f"不支持的格式: {format}")

        logger.info(f"OpenAPI 规范已导出到: {output_path}")
        return openapi_schema

    def _post_process(
        self, schema: Dict[str, Any], api_version: str
    ) -> Dict[str, Any]:
        """
        后处理 OpenAPI 规范

        Args:
            schema: 原始 OpenAPI 规范
            api_version: API 版本

        Returns:
            处理后的 OpenAPI 规范
        """
        if "info" not in schema:
            schema["info"] = {}

        schema["info"]["version"] = api_version
        schema["servers"] = [
            {
                "url": f"/api/{api_version}",
                "description": f"API {api_version}",
            }
        ]

        schema = self._add_security_schemes(schema)
        schema = self._add_common_responses(schema)
        schema = self._extract_path_parameters(schema)

        return schema

    def _add_security_schemes(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """添加安全认证方案"""
        if "components" not in schema:
            schema["components"] = {}
        if "securitySchemes" not in schema["components"]:
            schema["components"]["securitySchemes"] = {}

        schema["components"]["securitySchemes"]["ApiKeyAuth"] = {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API 密钥认证",
        }

        schema["security"] = [{"ApiKeyAuth": []}]

        return schema

    def _add_common_responses(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """添加通用响应定义"""
        if "components" not in schema:
            schema["components"] = {}
        if "responses" not in schema["components"]:
            schema["components"]["responses"] = {}

        schema["components"]["responses"].update(
            {
                "BadRequest": {
                    "description": "请求参数错误",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ErrorResponse"
                            }
                        }
                    },
                },
                "Unauthorized": {
                    "description": "未授权，需要有效的 API Key",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "detail": {"type": "string"}
                                },
                            }
                        }
                    },
                },
                "NotFound": {
                    "description": "资源不存在",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "detail": {"type": "string"}
                                },
                            }
                        }
                    },
                },
                "TooManyRequests": {
                    "description": "请求频率超限",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "detail": {"type": "string"}
                                },
                            }
                        }
                    },
                },
                "InternalServerError": {
                    "description": "服务器内部错误",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "detail": {"type": "string"}
                                },
                            }
                        }
                    },
                },
            }
        )

        return schema

    def _extract_path_parameters(
        self, schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """提取路径参数到 components 中复用"""
        if "components" not in schema:
            schema["components"] = {}
        if "parameters" not in schema["components"]:
            schema["components"]["parameters"] = {}

        common_params = {
            "page_cursor": {
                "name": "cursor",
                "in": "query",
                "description": "分页游标，用于获取下一页数据",
                "required": False,
                "schema": {"type": "string"},
            },
            "page_limit": {
                "name": "limit",
                "in": "query",
                "description": "每页返回数量，默认 20，最大 100",
                "required": False,
                "schema": {"type": "integer", "default": 20, "maximum": 100},
            },
        }

        schema["components"]["parameters"].update(common_params)
        return schema


def export_openapi(
    app_module: str,
    output_path: str | Path,
    format: str = "json",
    api_version: str = "v1",
) -> Dict[str, Any]:
    """
    便捷函数：导出 OpenAPI 规范

    Args:
        app_module: FastAPI 应用模块路径
        output_path: 输出文件路径
        format: 输出格式
        api_version: API 版本

    Returns:
        OpenAPI 规范字典
    """
    exporter = OpenAPIExporter(app_module)
    return exporter.export(output_path, format, api_version)
