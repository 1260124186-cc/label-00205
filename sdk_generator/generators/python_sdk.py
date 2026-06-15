"""
Python SDK 生成器

生成包含重试、鉴权、游标同步封装的 Python SDK。
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from loguru import logger

from .base import BaseSDKGenerator


class PythonSDKGenerator(BaseSDKGenerator):
    """Python SDK 生成器"""

    @property
    def language_name(self) -> str:
        return "python"

    def _generate_project_structure(self, output_dir: Path) -> None:
        """生成项目目录结构"""
        pkg_name = self.config.python["module_name"]
        pkg_dir = output_dir / pkg_name

        dirs = [
            pkg_dir,
            pkg_dir / "models",
            pkg_dir / "api",
            pkg_dir / "core",
            output_dir / "tests",
            output_dir / "examples",
        ]

        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        for d in dirs:
            init_file = d / "__init__.py"
            if not init_file.exists() and d != output_dir:
                init_file.write_text("")

    def _generate_models(self, output_dir: Path) -> None:
        """生成数据模型"""
        pkg_name = self.config.python["module_name"]
        models_dir = output_dir / pkg_name / "models"

        schemas = self._get_schemas()

        models_content = self._generate_models_content(schemas)
        (models_dir / "base.py").write_text(self._generate_base_model())
        (models_dir / "__init__.py").write_text(
            self._generate_models_init(schemas)
        )

        for schema_name, schema in schemas.items():
            if schema.get("type") == "object" or "properties" in schema:
                model_code = self._generate_model_class(schema_name, schema)
                file_name = self._to_snake_case(schema_name) + ".py"
                (models_dir / file_name).write_text(model_code)

    def _generate_base_model(self) -> str:
        """生成基础模型"""
        return '''"""
基础模型
"""

from typing import Optional, Any, Dict, List
from pydantic import BaseModel, ConfigDict


class SDKBaseModel(BaseModel):
    """SDK 基础模型"""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
        use_attribute_docstrings=True,
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump(by_alias=True, exclude_none=True)

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return self.model_dump_json(by_alias=True, exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SDKBaseModel":
        """从字典创建模型"""
        return cls(**data)
'''

    def _generate_models_content(self, schemas: Dict[str, Any]) -> str:
        """生成所有模型的汇总内容"""
        return ""

    def _generate_models_init(self, schemas: Dict[str, Any]) -> str:
        """生成 models __init__.py"""
        imports = ["from .base import SDKBaseModel", ""]

        for schema_name in schemas:
            if schemas[schema_name].get("type") == "object" or "properties" in schemas[schema_name]:
                module_name = self._to_snake_case(schema_name)
                class_name = self._to_pascal_case(schema_name)
                imports.append(f"from .{module_name} import {class_name}")

        return "\n".join(imports) + "\n"

    def _generate_model_class(self, name: str, schema: Dict[str, Any]) -> str:
        """生成单个模型类"""
        class_name = self._to_pascal_case(name)
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        lines = [
            '"""',
            f"{name} 模型",
            '"""',
            "",
            "from typing import Optional, Any, Dict, List",
            "from datetime import datetime",
            "from pydantic import Field",
            "",
            "from .base import SDKBaseModel",
            "",
            "",
            f"class {class_name}(SDKBaseModel):",
            f'    """{schema.get("description", name)}"""',
            "",
        ]

        if not properties:
            lines.append("    pass")
            lines.append("")
            return "\n".join(lines)

        for prop_name, prop_schema in properties.items():
            py_name = self._to_snake_case(prop_name)
            py_type = self._map_python_type(prop_schema)
            is_required = prop_name in required

            field_args = []
            if py_name != prop_name:
                field_args.append(f'alias="{prop_name}"')

            description = prop_schema.get("description", "")
            if description:
                field_args.append(f'description="{description}"')

            default = "None"
            if not is_required:
                if "default" in prop_schema:
                    default = repr(prop_schema["default"])
                field_args.append(f"default={default}")

            field_str = ", ".join(field_args)

            if is_required:
                type_annotation = py_type
            else:
                type_annotation = f"Optional[{py_type}]"

            lines.append(
                f"    {py_name}: {type_annotation} = Field({field_str})"
            )

        lines.append("")
        return "\n".join(lines)

    def _map_python_type(self, schema: Any) -> str:
        """映射 OpenAPI 类型到 Python 类型"""
        if not isinstance(schema, dict):
            return "Any"

        if "$ref" in schema:
            ref_name = schema["$ref"].split("/")[-1]
            return self._to_pascal_case(ref_name)

        type_name = schema.get("type", "any")
        format_name = schema.get("format", "")

        if type_name == "string":
            if format_name in ("date", "date-time"):
                return "datetime"
            return "str"
        elif type_name == "integer":
            return "int"
        elif type_name == "number":
            return "float"
        elif type_name == "boolean":
            return "bool"
        elif type_name == "array":
            items = schema.get("items", {})
            item_type = self._map_python_type(items)
            return f"List[{item_type}]"
        elif type_name == "object":
            additional = schema.get("additionalProperties", {})
            if isinstance(additional, dict) and additional:
                value_type = self._map_python_type(additional)
                return f"Dict[str, {value_type}]"
            return "Dict[str, Any]"
        else:
            return "Any"

    def _generate_api_clients(self, output_dir: Path) -> None:
        """生成 API 客户端"""
        pkg_name = self.config.python["module_name"]
        api_dir = output_dir / pkg_name / "api"

        groups = self._parse_paths()

        for i, group in enumerate(groups):
            tag = group["tag"]
            operations = group["operations"]
            sanitized_tag = self._sanitize_tag(tag, i)
            file_name = self._to_snake_case(sanitized_tag) + ".py"
            class_name = self._to_pascal_case(sanitized_tag) + "Client"
            code = self._generate_api_client_class(class_name, sanitized_tag, operations)
            (api_dir / file_name).write_text(code)
            group["_sanitized_tag"] = sanitized_tag

        (api_dir / "__init__.py").write_text(
            self._generate_api_init(groups)
        )

    def _generate_api_client_class(
        self,
        class_name: str,
        tag: str,
        operations: List[Dict[str, Any]],
    ) -> str:
        """生成单个 API 客户端类"""
        lines = [
            '"""',
            f"{tag} API 客户端",
            '"""',
            "",
            "from typing import Optional, Dict, Any, List, AsyncIterator",
            "import json",
            "",
            "from ..core.client import BaseAPIClient",
            "from ..core.pagination import CursorPaginator",
            "from ..models import *",
            "",
            "",
            f"class {class_name}(BaseAPIClient):",
            f'    """{tag} API 客户端"""',
            "",
        ]

        for op in operations:
            method_code = self._generate_api_method(op)
            lines.append(method_code)
            lines.append("")

        return "\n".join(lines)

    def _generate_api_method(self, operation: Dict[str, Any]) -> str:
        """生成单个 API 方法"""
        op = operation["operation"]
        method_name = self._to_snake_case(op.get("operationId", operation["operation_id"]))
        summary = op.get("summary", "")
        description = op.get("description", "")

        path_params = []
        query_params = []
        body_param = None

        for param in op.get("parameters", []):
            if param.get("in") == "path":
                path_params.append(param)
            elif param.get("in") == "query":
                query_params.append(param)

        if "requestBody" in op:
            body_param = op["requestBody"]

        is_paginated = self._is_pagination_endpoint(op)

        params = ["self"]
        for p in path_params:
            param_name = self._to_snake_case(p["name"])
            param_type = self._map_python_type(p.get("schema", {}))
            params.append(f"{param_name}: {param_type}")

        if body_param:
            body_schema = (
                body_param.get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            body_type = self._map_python_type(body_schema)
            params.append(f"body: {body_type}")

        for p in query_params:
            param_name = self._to_snake_case(p["name"])
            param_type = self._map_python_type(p.get("schema", {}))
            required = p.get("required", False)
            if required:
                params.append(f"{param_name}: {param_type}")
            else:
                params.append(f"{param_name}: Optional[{param_type}] = None")

        return_type = "Dict[str, Any]"
        responses = op.get("responses", {})
        success_resp = None
        for code in ["200", "201", "202", "204"]:
            if code in responses:
                success_resp = responses[code]
                break

        if success_resp:
            content = success_resp.get("content", {})
            json_content = content.get("application/json", {})
            schema = json_content.get("schema", {})
            if schema:
                return_type = self._map_python_type(schema)

        method_path = operation["path"]
        for p in path_params:
            param_name = p["name"]
            method_path = method_path.replace(
                "{" + param_name + "}", f"{{{self._to_snake_case(param_name)}}}"
            )

        lines = [
            f"    async def {method_name}(",
        ]

        for i, param in enumerate(params):
            if i == len(params) - 1:
                lines.append(f"        {param}")
            else:
                lines.append(f"        {param},")

        if is_paginated:
            lines.append(") -> CursorPaginator:")
        else:
            lines.append(f") -> {return_type}:")

        lines.append(f'        """')
        if summary:
            lines.append(f"        {summary}")
        if description:
            lines.append(f"")
            for line in description.split("\n"):
                lines.append(f"        {line}")
        lines.append(f'        """')
        lines.append("")

        if is_paginated:
            lines.append(f"        return CursorPaginator(")
            lines.append(f"            client=self,")
            lines.append(f'            path=f"/api/{self.config.api_version}{method_path}",')
            lines.append(f'            method="{operation["method"]}",')
            if body_param:
                lines.append(f"            body=body,")
            lines.append(f"            params={{")
            for p in query_params:
                param_name = self._to_snake_case(p["name"])
                if p["name"] not in (
                    self.config.pagination_config["cursor_param"],
                    self.config.pagination_config["limit_param"],
                ):
                    lines.append(f'                "{p["name"]}": {param_name},')
            lines.append(f"            }},")
            lines.append(f"        )")
        else:
            lines.append(f"        response = await self._request(")
            lines.append(f'            method="{operation["method"]}",')
            lines.append(f'            path=f"/api/{self.config.api_version}{method_path}",')
            if body_param:
                lines.append(f"            json=body.to_dict() if hasattr(body, 'to_dict') else body,")
            if query_params:
                lines.append(f"            params={{")
                for p in query_params:
                    param_name = self._to_snake_case(p["name"])
                    lines.append(f'                "{p["name"]}": {param_name},')
                lines.append(f"            }},")
            lines.append(f"        )")
            lines.append("")
            lines.append(f"        return response")

        return "\n".join(lines)

    def _generate_api_init(self, groups: List[Dict[str, Any]]) -> str:
        """生成 api __init__.py"""
        imports = []
        for group in groups:
            sanitized_tag = group.get("_sanitized_tag", group["tag"])
            module_name = self._to_snake_case(sanitized_tag)
            class_name = self._to_pascal_case(sanitized_tag) + "Client"
            imports.append(f"from .{module_name} import {class_name}")
        return "\n".join(imports) + "\n"

    def _generate_core_modules(self, output_dir: Path) -> None:
        """生成核心模块"""
        pkg_name = self.config.python["module_name"]
        core_dir = output_dir / pkg_name / "core"

        (core_dir / "__init__.py").write_text(self._generate_core_init())

        (core_dir / "config.py").write_text(self._generate_core_config())
        (core_dir / "auth.py").write_text(self._generate_core_auth())
        (core_dir / "retry.py").write_text(self._generate_core_retry())
        (core_dir / "pagination.py").write_text(self._generate_core_pagination())
        (core_dir / "client.py").write_text(self._generate_core_client())

    def _generate_core_init(self) -> str:
        """生成 core __init__.py"""
        return '''"""
核心模块
"""

from .config import SDKConfig
from .auth import AuthManager
from .retry import RetryManager
from .pagination import CursorPaginator
from .client import BaseAPIClient
'''

    def _generate_core_config(self) -> str:
        """生成配置模块"""
        return f'''"""
SDK 配置
"""

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class SDKConfig:
    """SDK 配置"""

    base_url: str = "{self.config.base_url}"
    api_key: Optional[str] = None
    api_version: str = "{self.config.api_version}"
    timeout: int = 30

    max_retries: int = {self.config.retry_config["max_retries"]}
    retry_backoff_factor: float = {self.config.retry_config["backoff_factor"]}
    retry_status_codes: List[int] = field(
        default_factory=lambda: {self.config.retry_config["status_forcelist"]}
    )

    api_key_header: str = "{self.config.auth_config["header_name"]}"

    pagination_cursor_param: str = "{self.config.pagination_config["cursor_param"]}"
    pagination_limit_param: str = "{self.config.pagination_config["limit_param"]}"
    pagination_default_limit: int = {self.config.pagination_config["default_limit"]}
    pagination_max_limit: int = {self.config.pagination_config["max_limit"]}

    def validate(self) -> None:
        """验证配置"""
        if not self.base_url:
            raise ValueError("base_url is required")
'''

    def _generate_core_auth(self) -> str:
        """生成鉴权模块"""
        return f'''"""
鉴权模块
"""

from typing import Optional, Dict, Any


class AuthManager:
    """认证管理器"""

    def __init__(self, api_key: Optional[str] = None, header_name: str = "X-API-Key"):
        self.api_key = api_key
        self.header_name = header_name

    def get_headers(self) -> Dict[str, str]:
        """获取认证请求头"""
        headers = {{}}
        if self.api_key:
            headers[self.header_name] = self.api_key
        return headers

    def set_api_key(self, api_key: str) -> None:
        """设置 API Key"""
        self.api_key = api_key
'''

    def _generate_core_retry(self) -> str:
        """生成重试模块"""
        return f'''"""
重试模块
"""

import asyncio
from typing import Callable, Awaitable, Any, List
from loguru import logger


class RetryManager:
    """重试管理器"""

    def __init__(
        self,
        max_retries: int = {self.config.retry_config["max_retries"]},
        backoff_factor: float = {self.config.retry_config["backoff_factor"]},
        status_codes: List[int] = None,
    ):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.status_codes = status_codes or {self.config.retry_config["status_forcelist"]}

    async def execute(
        self,
        func: Callable[..., Awaitable[Any]],
        *args,
        **kwargs,
    ) -> Any:
        """
        执行带重试的异步函数

        Args:
            func: 要执行的异步函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数执行结果
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                status_code = getattr(e, "status_code", None)

                if status_code not in self.status_codes:
                    raise

                if attempt >= self.max_retries:
                    logger.warning(
                        f"Max retries ({{self.max_retries}}) reached, giving up"
                    )
                    raise

                wait_time = self.backoff_factor * (2 ** attempt)
                logger.warning(
                    f"Retry attempt {{attempt + 1}}/{{self.max_retries}}, "
                    f"waiting {{wait_time}}s before retry. Error: {{e}}"
                )
                await asyncio.sleep(wait_time)

        raise last_exception
'''

    def _generate_core_pagination(self) -> str:
        """生成游标分页模块"""
        cursor_param = self.config.pagination_config["cursor_param"]
        limit_param = self.config.pagination_config["limit_param"]
        default_limit = self.config.pagination_config["default_limit"]
        cursor_field = self.config.pagination_config["response_cursor_field"]
        items_field = self.config.pagination_config["response_items_field"]

        return f'''"""
游标分页模块
"""

from typing import Any, Dict, List, Optional, AsyncIterator
from loguru import logger


class CursorPaginator:
    """游标分页器

    支持同步迭代和异步迭代两种方式遍历所有数据。
    """

    def __init__(
        self,
        client: Any,
        path: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Any] = None,
        cursor_param: str = "{cursor_param}",
        limit_param: str = "{limit_param}",
        default_limit: int = {default_limit},
        response_cursor_field: str = "{cursor_field}",
        response_items_field: str = "{items_field}",
    ):
        self.client = client
        self.path = path
        self.method = method
        self.params = params or {{}}
        self.body = body
        self.cursor_param = cursor_param
        self.limit_param = limit_param
        self.default_limit = default_limit
        self.response_cursor_field = response_cursor_field
        self.response_items_field = response_items_field

        self._cursor: Optional[str] = None
        self._has_more: bool = True
        self._buffer: List[Any] = []

    async def next_page(self, limit: Optional[int] = None) -> List[Any]:
        """
        获取下一页数据

        Args:
            limit: 每页数量

        Returns:
            本页数据列表
        """
        if not self._has_more:
            return []

        params = dict(self.params)
        params[self.limit_param] = limit or self.default_limit

        if self._cursor:
            params[self.cursor_param] = self._cursor

        request_kwargs = {{
            "method": self.method,
            "path": self.path,
            "params": params,
        }}

        if self.body is not None:
            request_kwargs["json"] = self.body

        response = await self.client._request(**request_kwargs)

        if isinstance(response, dict):
            items = response.get(self.response_items_field, [])
            self._cursor = response.get(self.response_cursor_field)
            self._has_more = self._cursor is not None
        else:
            items = response
            self._has_more = False

        return items

    async def all(self, limit: Optional[int] = None) -> List[Any]:
        """
        获取所有数据

        Args:
            limit: 每页数量

        Returns:
            所有数据的列表
        """
        all_items: List[Any] = []
        while self._has_more:
            items = await self.next_page(limit)
            all_items.extend(items)
        return all_items

    async def __aiter__(self) -> AsyncIterator[Any]:
        """异步迭代器支持"""
        while self._has_more:
            items = await self.next_page()
            for item in items:
                yield item
'''

    def _generate_core_client(self) -> str:
        """生成核心客户端"""
        return '''"""
API 客户端基类
"""

import json
from typing import Optional, Dict, Any, Union
from urllib.parse import urljoin

import httpx
from loguru import logger

from .config import SDKConfig
from .auth import AuthManager
from .retry import RetryManager


class BaseAPIClient:
    """API 客户端基类"""

    def __init__(self, config: SDKConfig, auth: AuthManager, retry: RetryManager):
        self.config = config
        self.auth = auth
        self.retry = retry
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )
        return self._client

    async def close(self) -> None:
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """
        发送 HTTP 请求

        Args:
            method: HTTP 方法
            path: 请求路径
            params: 查询参数
            json: 请求体 JSON
            headers: 自定义请求头

        Returns:
            响应数据

        Raises:
            httpx.HTTPError: HTTP 请求错误
        """
        async def _do_request():
            client = await self._get_client()

            request_headers = self.auth.get_headers()
            if headers:
                request_headers.update(headers)

            request_headers.setdefault("Content-Type", "application/json")
            request_headers.setdefault("Accept", "application/json")

            url = urljoin(self.config.base_url, path)

            logger.debug(f"{method} {url}")

            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json,
                headers=request_headers,
            )

            response.raise_for_status()

            if response.content:
                return response.json()
            return None

        return await self.retry.execute(_do_request)
'''

    def _generate_package_files(self, output_dir: Path) -> None:
        """生成包配置文件"""
        pkg_name = self.config.python["module_name"]

        (output_dir / pkg_name / "__init__.py").write_text(
            self._generate_main_init()
        )

        (output_dir / "setup.py").write_text(self._generate_setup_py())
        (output_dir / "pyproject.toml").write_text(self._generate_pyproject_toml())
        (output_dir / "requirements.txt").write_text(
            "\n".join(self.config.python["dependencies"]) + "\n"
        )

    def _generate_main_init(self) -> str:
        """生成主包 __init__.py"""
        return f'''"""
{self.config.python["package_name"]} - 螺栓预紧力预测系统 Python SDK

特性:
- 完整的 API 客户端覆盖
- 内置指数退避重试机制
- API Key 鉴权支持
- 游标分页同步封装
- 异步/同步双模式支持
"""

from .core.config import SDKConfig
from .core.auth import AuthManager
from .core.retry import RetryManager
from .core.pagination import CursorPaginator
from .models import *
from .api import *

__version__ = "{self.openapi_spec.get("info", {}).get("version", "1.0.0")}"
__all__ = [
    "SDKConfig",
    "AuthManager",
    "RetryManager",
    "CursorPaginator",
]
'''

    def _generate_setup_py(self) -> str:
        """生成 setup.py"""
        pkg = self.config.python
        return f'''"""
{pkg["package_name"]} 安装脚本
"""

from setuptools import setup, find_packages

setup(
    name="{pkg["package_name"]}",
    version="1.0.0",
    description="螺栓预紧力预测系统 Python SDK",
    author="{pkg["author"]}",
    packages=find_packages(),
    python_requires="{pkg["python_requires"]}",
    install_requires={json.dumps(pkg["dependencies"])},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
'''

    def _generate_pyproject_toml(self) -> str:
        """生成 pyproject.toml"""
        pkg = self.config.python
        return f'''[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{pkg["package_name"]}"
version = "1.0.0"
description = "螺栓预紧力预测系统 Python SDK"
readme = "README.md"
requires-python = "{pkg["python_requires"]}"
authors = [
    {{name = "{pkg["author"]}"}},
]
dependencies = [
    {',\n    '.join(f'"{d}"' for d in pkg["dependencies"])}
]

[project.urls]
Homepage = "https://github.com/bolt-prediction/sdk-python"

[tool.setuptools.packages.find]
include = ["{pkg["module_name"]}*"]
'''

    def _generate_readme(self, output_dir: Path) -> None:
        """生成 README"""
        readme = f'''# {self.config.python["package_name"]}

螺栓预紧力预测系统 Python SDK

## 安装

```bash
pip install {self.config.python["package_name"]}
```

## 快速开始

```python
import asyncio
from {self.config.python["module_name"]} import SDKConfig, 预测Client

async def main():
    config = SDKConfig(
        base_url="https://api.example.com",
        api_key="your-api-key",
    )

    # 创建客户端
    client = 预测Client(config)

    # 调用 API
    result = await client.predict_bolt(
        bolt_id="B001",
        data=[["2025-01-01", 400.0]]
    )
    print(result)

    await client.close()

asyncio.run(main())
```

## 特性

- **完整 API 覆盖**: 支持所有 API 端点
- **自动重试**: 指数退避重试，支持配置
- **API Key 鉴权**: 支持 X-API-Key 头部认证
- **游标分页**: 自动处理游标分页，支持异步迭代
- **类型提示**: 完整的类型定义和 Pydantic 模型

## 配置

通过环境变量配置:

- `SDK_BASE_URL`: API 基础 URL
- `SDK_API_KEY`: API 密钥
- `SDK_MAX_RETRIES`: 最大重试次数

## 分页示例

```python
# 使用游标分页迭代所有数据
paginator = client.list_items(limit=20)
all_items = await paginator.all()

# 或者使用异步迭代
async for item in client.list_items():
    process_item(item)
```
'''

        (output_dir / "README.md").write_text(readme)
