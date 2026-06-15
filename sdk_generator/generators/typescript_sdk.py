"""
TypeScript SDK 生成器

生成包含重试、鉴权、游标同步封装的 TypeScript SDK。
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from loguru import logger

from .base import BaseSDKGenerator


class TypeScriptSDKGenerator(BaseSDKGenerator):
    """TypeScript SDK 生成器"""

    @property
    def language_name(self) -> str:
        return "typescript"

    def _generate_project_structure(self, output_dir: Path) -> None:
        """生成项目目录结构"""
        dirs = [
            output_dir / "src",
            output_dir / "src" / "models",
            output_dir / "src" / "api",
            output_dir / "src" / "core",
            output_dir / "tests",
            output_dir / "examples",
        ]

        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _generate_models(self, output_dir: Path) -> None:
        """生成数据模型"""
        models_dir = output_dir / "src" / "models"
        schemas = self._get_schemas()

        (models_dir / "index.ts").write_text(self._generate_models_index(schemas))

        all_interfaces = []
        for schema_name, schema in schemas.items():
            if schema.get("type") == "object" or "properties" in schema:
                interface_code = self._generate_interface(schema_name, schema)
                all_interfaces.append(interface_code)

        (models_dir / "types.ts").write_text("\n\n".join(all_interfaces) + "\n")

    def _generate_interface(self, name: str, schema: Dict[str, Any]) -> str:
        """生成 TypeScript 接口"""
        interface_name = self._to_pascal_case(name)
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        lines = [
            f"/** {schema.get('description', name)} */",
            f"export interface {interface_name} {{",
        ]

        for prop_name, prop_schema in properties.items():
            ts_name = self._to_camel_case(prop_name)
            ts_type = self._map_ts_type(prop_schema)
            is_required = prop_name in required

            optional_mark = "" if is_required else "?"
            description = prop_schema.get("description", "")

            if description:
                lines.append(f"  /** {description} */")

            if ts_name != prop_name:
                lines.append(f"  // OpenAPI name: {prop_name}")

            lines.append(f"  {ts_name}{optional_mark}: {ts_type};")

        lines.append("}")
        return "\n".join(lines)

    def _map_ts_type(self, schema: Any, with_models_prefix: bool = False) -> str:
        """映射 OpenAPI 类型到 TypeScript 类型"""
        if not isinstance(schema, dict):
            return "any"

        if "$ref" in schema:
            ref_name = schema["$ref"].split("/")[-1]
            type_name = self._to_pascal_case(ref_name)
            return f"Models.{type_name}" if with_models_prefix else type_name

        type_name = schema.get("type", "any")
        format_name = schema.get("format", "")

        if type_name == "string":
            if format_name in ("date", "date-time"):
                return "Date | string"
            return "string"
        elif type_name == "integer":
            return "number"
        elif type_name == "number":
            return "number"
        elif type_name == "boolean":
            return "boolean"
        elif type_name == "array":
            items = schema.get("items", {})
            item_type = self._map_ts_type(items, with_models_prefix)
            return f"{item_type}[]"
        elif type_name == "object":
            additional = schema.get("additionalProperties", {})
            if isinstance(additional, dict) and additional:
                value_type = self._map_ts_type(additional, with_models_prefix)
                return f"Record<string, {value_type}>"
            return "Record<string, any>"
        else:
            return "any"

    def _generate_models_index(self, schemas: Dict[str, Any]) -> str:
        """生成 models index.ts"""
        exports = ['export * from "./types";', ""]
        return "\n".join(exports)

    def _generate_api_clients(self, output_dir: Path) -> None:
        """生成 API 客户端"""
        api_dir = output_dir / "src" / "api"
        groups = self._parse_paths()

        for i, group in enumerate(groups):
            tag = group["tag"]
            operations = group["operations"]
            sanitized_tag = self._sanitize_tag(tag, i)
            file_name = self._to_camel_case(sanitized_tag) + ".ts"
            class_name = self._to_pascal_case(sanitized_tag) + "Client"
            code = self._generate_api_client_class(class_name, sanitized_tag, operations)
            (api_dir / file_name).write_text(code)
            group["_sanitized_tag"] = sanitized_tag

        (api_dir / "index.ts").write_text(self._generate_api_index(groups))

    def _generate_api_client_class(
        self,
        class_name: str,
        tag: str,
        operations: List[Dict[str, Any]],
    ) -> str:
        """生成单个 API 客户端类"""
        lines = [
            f"/** {tag} API 客户端 */",
            "",
            "import { BaseAPIClient } from \"../core/client\";",
            "import { CursorPaginator } from \"../core/pagination\";",
            "import * as Models from \"../models\";",
            "",
            f"export class {class_name} extends BaseAPIClient {{",
        ]

        for op in operations:
            method_code = self._generate_api_method(op)
            lines.append(method_code)

        lines.append("}")
        return "\n".join(lines)

    def _generate_api_method(self, operation: Dict[str, Any]) -> str:
        """生成单个 API 方法"""
        op = operation["operation"]
        method_name = self._to_camel_case(op.get("operationId", operation["operation_id"]))
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

        params_list = []
        for p in path_params:
            param_name = self._to_camel_case(p["name"])
            param_type = self._map_ts_type(p.get("schema", {}), with_models_prefix=True)
            params_list.append(f"{param_name}: {param_type}")

        if body_param:
            body_schema = (
                body_param.get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            body_type = self._map_ts_type(body_schema, with_models_prefix=True)
            params_list.append(f"body: {body_type}")

        for p in query_params:
            param_name = self._to_camel_case(p["name"])
            param_type = self._map_ts_type(p.get("schema", {}), with_models_prefix=True)
            required = p.get("required", False)
            if required:
                params_list.append(f"{param_name}: {param_type}")
            else:
                params_list.append(f"{param_name}?: {param_type}")

        return_type = "any"
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
                return_type = self._map_ts_type(schema, with_models_prefix=True)

        method_path = operation["path"]
        for p in path_params:
            param_name = p["name"]
            ts_name = self._to_camel_case(param_name)
            method_path = method_path.replace("{" + param_name + "}", "${" + ts_name + "}")

        lines = [
            "",
            f"  /**",
            f"   * {summary}",
            f"   */",
            f"  async {method_name}(",
        ]

        for i, param in enumerate(params_list):
            if i < len(params_list) - 1:
                lines.append(f"    {param},")
            else:
                lines.append(f"    {param}")

        if is_paginated:
            lines.append(f"  ): CursorPaginator<{return_type}> {{")
        else:
            lines.append(f"  ): Promise<{return_type}> {{")

        if is_paginated:
            lines.append(f"    const params: Record<string, any> = {{}};")
            for p in query_params:
                param_name = self._to_camel_case(p["name"])
                if p["name"] not in (
                    self.config.pagination_config["cursor_param"],
                    self.config.pagination_config["limit_param"],
                ):
                    lines.append(f"    if ({param_name} !== undefined) params['{p['name']}'] = {param_name};")

            lines.append("")
            lines.append(f"    return new CursorPaginator(")
            lines.append(f"      this,")
            lines.append(f'      `/api/{self.config.api_version}{method_path}`,')
            lines.append(f'      "{operation["method"]}",')
            lines.append(f"      params")
            if body_param:
                lines.append(f"      ,body")
            lines.append(f"    );")
        else:
            lines.append(f"    const params: Record<string, any> = {{}};")
            for p in query_params:
                param_name = self._to_camel_case(p["name"])
                lines.append(f"    if ({param_name} !== undefined) params['{p['name']}'] = {param_name};")

            lines.append("")
            lines.append(f"    return this._request(")
            lines.append(f'      "{operation["method"]}",')
            lines.append(f'      `/api/{self.config.api_version}{method_path}`,')
            lines.append(f"      params,")
            if body_param:
                lines.append(f"      body")
            else:
                lines.append(f"      undefined")
            lines.append(f"    );")

        lines.append(f"  }}")
        return "\n".join(lines)

    def _generate_api_index(self, groups: List[Dict[str, Any]]) -> str:
        """生成 api index.ts"""
        exports = []
        for group in groups:
            sanitized_tag = group.get("_sanitized_tag", group["tag"])
            file_name = self._to_camel_case(sanitized_tag)
            class_name = self._to_pascal_case(sanitized_tag) + "Client"
            exports.append(f"export {{ {class_name} }} from './{file_name}';")
        return "\n".join(exports) + "\n"

    def _generate_core_modules(self, output_dir: Path) -> None:
        """生成核心模块"""
        core_dir = output_dir / "src" / "core"

        (core_dir / "config.ts").write_text(self._generate_core_config())
        (core_dir / "auth.ts").write_text(self._generate_core_auth())
        (core_dir / "retry.ts").write_text(self._generate_core_retry())
        (core_dir / "pagination.ts").write_text(self._generate_core_pagination())
        (core_dir / "client.ts").write_text(self._generate_core_client())
        (core_dir / "index.ts").write_text(self._generate_core_index())

    def _generate_core_config(self) -> str:
        """生成配置模块"""
        return f'''/**
 * SDK 配置
 */

export interface SDKConfig {{
  /** API 基础 URL */
  baseUrl: string;
  /** API 密钥 */
  apiKey?: string;
  /** API 版本 */
  apiVersion: string;
  /** 请求超时时间（毫秒） */
  timeout: number;

  /** 最大重试次数 */
  maxRetries: number;
  /** 重试退避因子 */
  retryBackoffFactor: number;
  /** 需要重试的 HTTP 状态码 */
  retryStatusCodes: number[];

  /** API Key 请求头名称 */
  apiKeyHeader: string;

  /** 分页游标参数名 */
  paginationCursorParam: string;
  /** 分页数量参数名 */
  paginationLimitParam: string;
  /** 默认每页数量 */
  paginationDefaultLimit: number;
  /** 最大每页数量 */
  paginationMaxLimit: number;
}}

/**
 * 默认配置
 */
export const defaultConfig: SDKConfig = {{
  baseUrl: "{self.config.base_url}",
  apiVersion: "{self.config.api_version}",
  timeout: 30000,

  maxRetries: {self.config.retry_config["max_retries"]},
  retryBackoffFactor: {self.config.retry_config["backoff_factor"]},
  retryStatusCodes: {json.dumps(self.config.retry_config["status_forcelist"])},

  apiKeyHeader: "{self.config.auth_config["header_name"]}",

  paginationCursorParam: "{self.config.pagination_config["cursor_param"]}",
  paginationLimitParam: "{self.config.pagination_config["limit_param"]}",
  paginationDefaultLimit: {self.config.pagination_config["default_limit"]},
  paginationMaxLimit: {self.config.pagination_config["max_limit"]},
}};
'''

    def _generate_core_auth(self) -> str:
        """生成鉴权模块"""
        return f'''/**
 * 鉴权模块
 */

export interface AuthManagerOptions {{
  apiKey?: string;
  headerName?: string;
}}

export class AuthManager {{
  private apiKey?: string;
  private headerName: string;

  constructor(options: AuthManagerOptions = {{}}) {{
    this.apiKey = options.apiKey;
    this.headerName = options.headerName || "X-API-Key";
  }}

  /**
   * 获取认证请求头
   */
  getHeaders(): Record<string, string> {{
    const headers: Record<string, string> = {{}};
    if (this.apiKey) {{
      headers[this.headerName] = this.apiKey;
    }}
    return headers;
  }}

  /**
   * 设置 API Key
   */
  setApiKey(apiKey: string): void {{
    this.apiKey = apiKey;
  }}
}}
'''

    def _generate_core_retry(self) -> str:
        """生成重试模块"""
        return f'''/**
 * 重试模块
 */

export interface RetryManagerOptions {{
  maxRetries?: number;
  backoffFactor?: number;
  statusCodes?: number[];
}}

export class RetryManager {{
  private maxRetries: number;
  private backoffFactor: number;
  private statusCodes: number[];

  constructor(options: RetryManagerOptions = {{}}) {{
    this.maxRetries = options.maxRetries ?? {self.config.retry_config["max_retries"]};
    this.backoffFactor = options.backoffFactor ?? {self.config.retry_config["backoff_factor"]};
    this.statusCodes = options.statusCodes ?? {json.dumps(self.config.retry_config["status_forcelist"])};
  }}

  /**
   * 执行带重试的异步函数
   */
  async execute<T>(fn: () => Promise<T>): Promise<T> {{
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {{
      try {{
        return await fn();
      }} catch (error: any) {{
        lastError = error;

        const statusCode = error?.response?.status || error?.statusCode;
        if (!this.statusCodes.includes(statusCode)) {{
          throw error;
        }}

        if (attempt >= this.maxRetries) {{
          console.warn(`Max retries (${{this.maxRetries}}) reached, giving up`);
          throw error;
        }}

        const waitTime = this.backoffFactor * Math.pow(2, attempt) * 1000;
        console.warn(
          `Retry attempt ${{attempt + 1}}/${{this.maxRetries}}, ` +
          `waiting ${{waitTime}}ms before retry. Error: ${{error.message}}`
        );

        await this.sleep(waitTime);
      }}
    }}

    throw lastError!;
  }}

  private sleep(ms: number): Promise<void> {{
    return new Promise(resolve => setTimeout(resolve, ms));
  }}
}}
'''

    def _generate_core_pagination(self) -> str:
        """生成游标分页模块"""
        cursor_param = self.config.pagination_config["cursor_param"]
        limit_param = self.config.pagination_config["limit_param"]
        default_limit = self.config.pagination_config["default_limit"]
        cursor_field = self.config.pagination_config["response_cursor_field"]
        items_field = self.config.pagination_config["response_items_field"]

        return f'''/**
 * 游标分页模块
 */

import {{ BaseAPIClient }} from "./client";

export interface CursorPaginatorOptions {{
  cursorParam?: string;
  limitParam?: string;
  defaultLimit?: number;
  responseCursorField?: string;
  responseItemsField?: string;
}}

export class CursorPaginator<T> {{
  private client: BaseAPIClient;
  private path: string;
  private method: string;
  private params: Record<string, any>;
  private body?: any;

  private cursorParam: string;
  private limitParam: string;
  private defaultLimit: number;
  private responseCursorField: string;
  private responseItemsField: string;

  private _cursor: string | null = null;
  private _hasMore: boolean = true;
  private _buffer: T[] = [];

  constructor(
    client: BaseAPIClient,
    path: string,
    method: string = "GET",
    params: Record<string, any> = {{}},
    body?: any,
    options: CursorPaginatorOptions = {{}}
  ) {{
    this.client = client;
    this.path = path;
    this.method = method;
    this.params = params;
    this.body = body;

    this.cursorParam = options.cursorParam ?? "{cursor_param}";
    this.limitParam = options.limitParam ?? "{limit_param}";
    this.defaultLimit = options.defaultLimit ?? {default_limit};
    this.responseCursorField = options.responseCursorField ?? "{cursor_field}";
    this.responseItemsField = options.responseItemsField ?? "{items_field}";
  }}

  /**
   * 获取下一页数据
   */
  async nextPage(limit?: number): Promise<T[]> {{
    if (!this._hasMore) {{
      return [];
    }}

    const params = {{ ...this.params }};
    params[this.limitParam] = limit ?? this.defaultLimit;

    if (this._cursor) {{
      params[this.cursorParam] = this._cursor;
    }}

    const response: any = await this.client._request(
      this.method,
      this.path,
      params,
      this.body
    );

    if (Array.isArray(response)) {{
      this._hasMore = false;
      return response as T[];
    }}

    const items = response?.[this.responseItemsField] ?? [];
    this._cursor = response?.[this.responseCursorField] ?? null;
    this._hasMore = this._cursor !== null;

    return items as T[];
  }}

  /**
   * 获取所有数据
   */
  async all(limit?: number): Promise<T[]> {{
    const allItems: T[] = [];
    while (this._hasMore) {{
      const items = await this.nextPage(limit);
      allItems.push(...items);
    }}
    return allItems;
  }}

  /**
   * 是否有更多数据
   */
  get hasMore(): boolean {{
    return this._hasMore;
  }}

  /**
   * 当前游标
   */
  get cursor(): string | null {{
    return this._cursor;
  }}

  /**
   * 异步迭代器支持
   */
  async *[Symbol.asyncIterator](): AsyncIterator<T> {{
    while (this._hasMore) {{
      const items = await this.nextPage();
      for (const item of items) {{
        yield item;
      }}
    }}
  }}
}}
'''

    def _generate_core_client(self) -> str:
        """生成核心客户端"""
        return '''/**
 * API 客户端基类
 */

import axios, { AxiosInstance, AxiosRequestConfig } from "axios";
import axiosRetry from "axios-retry";

import { SDKConfig, defaultConfig } from "./config";
import { AuthManager } from "./auth";
import { RetryManager } from "./retry";

export class BaseAPIClient {
  protected config: SDKConfig;
  protected auth: AuthManager;
  protected retry: RetryManager;
  private _client: AxiosInstance | null = null;

  constructor(config: Partial<SDKConfig>, auth: AuthManager, retry: RetryManager) {
    this.config = { ...defaultConfig, ...config };
    this.auth = auth;
    this.retry = retry;
  }

  /**
   * 获取 HTTP 客户端
   */
  protected get client(): AxiosInstance {
    if (!this._client) {
      this._client = axios.create({
        baseURL: this.config.baseUrl,
        timeout: this.config.timeout,
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
      });

      axiosRetry(this._client, {
        retries: this.config.maxRetries,
        retryDelay: axiosRetry.exponentialDelay,
        retryCondition: (error) => {
          return this.config.retryStatusCodes.includes(error.response?.status || 0);
        },
      });
    }
    return this._client;
  }

  /**
   * 发送 HTTP 请求
   */
  async _request(
    method: string,
    path: string,
    params?: Record<string, any>,
    data?: any,
    headers?: Record<string, string>
  ): Promise<any> {
    const requestHeaders = { ...this.auth.getHeaders(), ...headers };

    const config: AxiosRequestConfig = {
      method: method as any,
      url: path,
      params,
      data,
      headers: requestHeaders,
    };

    const response = await this.client.request(config);
    return response.data;
  }
}
'''

    def _generate_core_index(self) -> str:
        """生成 core index.ts"""
        return '''export { SDKConfig, defaultConfig } from "./config";
export { AuthManager } from "./auth";
export { RetryManager } from "./retry";
export { CursorPaginator } from "./pagination";
export { BaseAPIClient } from "./client";
'''

    def _generate_package_files(self, output_dir: Path) -> None:
        """生成包配置文件"""
        pkg = self.config.typescript

        (output_dir / "package.json").write_text(self._generate_package_json())
        (output_dir / "tsconfig.json").write_text(self._generate_tsconfig_json())
        (output_dir / ".npmrc").write_text(self._generate_npmrc())

        (output_dir / "src" / "index.ts").write_text(self._generate_main_index())

    def _generate_package_json(self) -> str:
        """生成 package.json"""
        pkg = self.config.typescript
        version = self.openapi_spec.get("info", {}).get("version", "1.0.0")

        return json.dumps(
            {
                "name": pkg["package_name"],
                "version": version,
                "description": "螺栓预紧力预测系统 TypeScript SDK",
                "main": "dist/index.js",
                "types": "dist/index.d.ts",
                "files": ["dist/"],
                "scripts": {
                    "build": "tsc",
                    "clean": "rm -rf dist",
                    "prepare": "npm run build",
                    "test": "echo \"Error: no test specified\" && exit 1",
                },
                "keywords": ["bolt", "prediction", "sdk"],
                "author": pkg["author"],
                "license": "MIT",
                "dependencies": pkg["dependencies"],
                "devDependencies": pkg["dev_dependencies"],
                "engines": {
                    "node": pkg["node_version"],
                },
                "publishConfig": {
                    "registry": pkg["private_registry_url"],
                    "access": "restricted",
                },
            },
            indent=2,
        ) + "\n"

    def _generate_tsconfig_json(self) -> str:
        """生成 tsconfig.json"""
        return json.dumps(
            {
                "compilerOptions": {
                    "target": "ES2020",
                    "module": "commonjs",
                    "lib": ["ES2020", "DOM"],
                    "declaration": True,
                    "declarationMap": True,
                    "sourceMap": True,
                    "outDir": "./dist",
                    "rootDir": "./src",
                    "strict": True,
                    "noImplicitAny": True,
                    "strictNullChecks": True,
                    "esModuleInterop": True,
                    "skipLibCheck": True,
                    "forceConsistentCasingInFileNames": True,
                    "resolveJsonModule": True,
                    "moduleResolution": "node",
                },
                "include": ["src/**/*"],
                "exclude": ["node_modules", "dist", "tests"],
            },
            indent=2,
        ) + "\n"

    def _generate_npmrc(self) -> str:
        """生成 .npmrc"""
        pkg = self.config.typescript
        scope = pkg["scope"]
        registry = pkg["private_registry_url"]
        return f"@{scope}:registry={registry}\n"

    def _generate_main_index(self) -> str:
        """生成主入口 index.ts"""
        return '''/**
 * 螺栓预紧力预测系统 TypeScript SDK
 *
 * 特性:
 * - 完整的 API 客户端覆盖
 * - 内置指数退避重试机制
 * - API Key 鉴权支持
 * - 游标分页同步封装
 * - TypeScript 类型支持
 */

export * from "./core";
export * from "./models";
export * from "./api";
'''

    def _generate_readme(self, output_dir: Path) -> None:
        """生成 README"""
        pkg = self.config.typescript
        readme = f'''# {pkg["package_name"]}

螺栓预紧力预测系统 TypeScript SDK

## 安装

```bash
npm install {pkg["package_name"]}
```

## 快速开始

```typescript
import {{ SDKConfig, 预测Client }} from '{pkg["package_name"]}';

const config: SDKConfig = {{
  baseUrl: "https://api.example.com",
  apiKey: "your-api-key",
}};

const client = new 预测Client(config);

// 调用 API
const result = await client.predictBolt({{
  boltId: "B001",
  data: [["2025-01-01", 400.0]]
}});

console.log(result);
```

## 特性

- **完整 API 覆盖**: 支持所有 API 端点
- **自动重试**: 指数退避重试，支持配置
- **API Key 鉴权**: 支持 X-API-Key 头部认证
- **游标分页**: 自动处理游标分页，支持异步迭代
- **TypeScript 类型**: 完整的类型定义

## 分页示例

```typescript
// 使用游标分页获取所有数据
const paginator = client.listItems({{ limit: 20 }});
const allItems = await paginator.all();

// 或者使用异步迭代
for await (const item of client.listItems()) {{
  console.log(item);
}}
```
'''

        (output_dir / "README.md").write_text(readme)
