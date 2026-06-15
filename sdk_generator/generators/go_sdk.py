"""
Go SDK 生成器

生成包含重试、鉴权、游标同步封装的 Go SDK。
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from loguru import logger

from .base import BaseSDKGenerator


class GoSDKGenerator(BaseSDKGenerator):
    """Go SDK 生成器"""

    @property
    def language_name(self) -> str:
        return "go"

    def _generate_project_structure(self, output_dir: Path) -> None:
        """生成项目目录结构"""
        pkg_name = self.config.go["package_name"]

        dirs = [
            output_dir / pkg_name,
            output_dir / pkg_name / "models",
            output_dir / pkg_name / "api",
            output_dir / pkg_name / "internal" / "client",
            output_dir / "examples",
        ]

        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _generate_models(self, output_dir: Path) -> None:
        """生成数据模型"""
        pkg_name = self.config.go["package_name"]
        models_dir = output_dir / pkg_name / "models"
        schemas = self._get_schemas()

        all_structs = []
        for schema_name, schema in schemas.items():
            if schema.get("type") == "object" or "properties" in schema:
                struct_code = self._generate_struct(schema_name, schema)
                all_structs.append(struct_code)

        (models_dir / "models.go").write_text(
            self._generate_models_file(all_structs)
        )

    def _generate_struct(self, name: str, schema: Dict[str, Any]) -> str:
        """生成 Go struct"""
        struct_name = self._to_pascal_case(name)
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        lines = [
            f"// {struct_name} {schema.get('description', name)}",
            f"type {struct_name} struct {{",
        ]

        for prop_name, prop_schema in properties.items():
            go_name = self._to_pascal_case(prop_name)
            go_type = self._map_go_type(prop_schema)
            is_required = prop_name in required

            json_tag = f'json:"{prop_name}'
            if not is_required:
                json_tag += ",omitempty"
            json_tag += '"'

            lines.append(f"\t{go_name} {go_type} `{json_tag}`")

        lines.append("}")
        return "\n".join(lines)

    def _map_go_type(self, schema: Dict[str, Any]) -> str:
        """映射 OpenAPI 类型到 Go 类型"""
        if "$ref" in schema:
            ref_name = schema["$ref"].split("/")[-1]
            return "*" + self._to_pascal_case(ref_name)

        type_name = schema.get("type", "interface{}")
        format_name = schema.get("format", "")

        if type_name == "string":
            if format_name in ("date", "date-time"):
                return "time.Time"
            return "string"
        elif type_name == "integer":
            if format_name == "int64":
                return "int64"
            return "int"
        elif type_name == "number":
            if format_name == "float":
                return "float32"
            return "float64"
        elif type_name == "boolean":
            return "bool"
        elif type_name == "array":
            items = schema.get("items", {})
            item_type = self._map_go_type(items)
            return "[]" + item_type.lstrip("*")
        elif type_name == "object":
            additional = schema.get("additionalProperties", {})
            if additional:
                value_type = self._map_go_type(additional)
                return "map[string]" + value_type
            return "map[string]interface{}"
        else:
            return "interface{}"

    def _generate_models_file(self, structs: List[str]) -> str:
        """生成 models 文件"""
        return f'''package models

import "time"

{chr(10).join(structs)}
'''

    def _generate_api_clients(self, output_dir: Path) -> None:
        """生成 API 客户端"""
        pkg_name = self.config.go["package_name"]
        api_dir = output_dir / pkg_name / "api"
        groups = self._parse_paths()

        for group in groups:
            tag = group["tag"]
            operations = group["operations"]
            file_name = self._to_snake_case(tag) + ".go"
            struct_name = self._to_pascal_case(tag) + "Client"
            code = self._generate_api_client_file(struct_name, tag, operations)
            (api_dir / file_name).write_text(code)

    def _generate_api_client_file(
        self,
        struct_name: str,
        tag: str,
        operations: List[Dict[str, Any]],
    ) -> str:
        """生成单个 API 客户端文件"""
        pkg = self.config.go["package_name"]

        lines = [
            "package api",
            "",
            f'import "{pkg}/{pkg}/models"',
            'import "fmt"',
            'import "net/url"',
            "",
            f"// {struct_name} {tag} API 客户端",
            f"type {struct_name} struct {{",
            "\tclient *BaseClient",
            "}",
            "",
            f"// New{struct_name} 创建 {tag} API 客户端",
            f"func New{struct_name}(client *BaseClient) *{struct_name} {{",
            f"\treturn &{struct_name}{{client: client}}",
            "}",
            "",
        ]

        for op in operations:
            method_code = self._generate_api_method(op, struct_name)
            lines.append(method_code)
            lines.append("")

        return "\n".join(lines)

    def _generate_api_method(
        self,
        operation: Dict[str, Any],
        struct_name: str,
    ) -> str:
        """生成单个 API 方法"""
        op = operation["operation"]
        method_name = self._to_pascal_case(op.get("operationId", operation["operation_id"]))
        summary = op.get("summary", "")

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
        params_list.append("ctx context.Context")

        for p in path_params:
            param_name = self._to_camel_case(p["name"])
            param_type = self._map_go_type(p.get("schema", {})).lstrip("*")
            params_list.append(f"{param_name} {param_type}")

        if body_param:
            body_schema = (
                body_param.get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            body_type = self._map_go_type(body_schema).lstrip("*")
            params_list.append(f"body *{body_type}")

        for p in query_params:
            param_name = self._to_camel_case(p["name"])
            param_type = self._map_go_type(p.get("schema", {})).lstrip("*")
            required = p.get("required", False)
            if not required:
                param_type = "*" + param_type
            params_list.append(f"{param_name} {param_type}")

        return_type = "map[string]interface{}"
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
                return_type = self._map_go_type(schema).lstrip("*")

        method_path = operation["path"]
        for p in path_params:
            param_name = p["name"]
            go_name = self._to_camel_case(param_name)
            method_path = method_path.replace("{" + param_name + "}", "%s")

        lines = [
            f"// {method_name} {summary}",
            f"func (c *{struct_name}) {method_name}(",
        ]

        for i, param in enumerate(params_list):
            if i < len(params_list) - 1:
                lines.append(f"\t{param},")
            else:
                lines.append(f"\t{param}")

        if is_paginated:
            lines.append(f") (*CursorPaginator, error) {{")
        else:
            lines.append(f") (*{return_type}, error) {{")

        lines.append(f"\tparams := url.Values{{}}")
        for p in query_params:
            param_name = self._to_camel_case(p["name"])
            required = p.get("required", False)
            if required:
                lines.append(f'\tparams.Set("{p["name"]}", fmt.Sprintf("%v", {param_name}))')
            else:
                lines.append(f"\tif {param_name} != nil {{")
                lines.append(f'\t\tparams.Set("{p["name"]}", fmt.Sprintf("%v", *{param_name}))')
                lines.append(f"\t}}")

        lines.append("")

        path_args = ", ".join(
            self._to_camel_case(p["name"]) for p in path_params
        )
        fmt_path_str = f'/api/{self.config.api_version}{method_path}'

        if is_paginated:
            lines.append(f"\treturn NewCursorPaginator(")
            lines.append(f"\t\tc.client,")
            lines.append(f'\t\tfmt.Sprintf("{fmt_path_str}", {path_args}),')
            lines.append(f'\t\t"{operation["method"]}",')
            lines.append(f"\t\tparams,")
            if body_param:
                lines.append(f"\t\tbody,")
            lines.append(f"\t)")
        else:
            lines.append(f"\tvar result {return_type}")
            lines.append(f"\terr := c.client.Request(")
            lines.append(f"\t\tctx,")
            lines.append(f'\t\t"{operation["method"]}",')
            lines.append(f'\t\tfmt.Sprintf("{fmt_path_str}", {path_args}),')
            lines.append(f"\t\tparams,")
            if body_param:
                lines.append(f"\t\tbody,")
            else:
                lines.append(f"\t\tnil,")
            lines.append(f"\t\t&result,")
            lines.append(f"\t)")
            lines.append(f"\treturn &result, err")

        lines.append(f"}}")
        return "\n".join(lines)

    def _generate_core_modules(self, output_dir: Path) -> None:
        """生成核心模块"""
        pkg_name = self.config.go["package_name"]
        client_dir = output_dir / pkg_name / "internal" / "client"

        (client_dir / "config.go").write_text(self._generate_core_config())
        (client_dir / "auth.go").write_text(self._generate_core_auth())
        (client_dir / "retry.go").write_text(self._generate_core_retry())
        (client_dir / "base_client.go").write_text(self._generate_core_client())

        api_dir = output_dir / pkg_name / "api"
        (api_dir / "base.go").write_text(self._generate_api_base())
        (api_dir / "pagination.go").write_text(self._generate_core_pagination())

    def _generate_core_config(self) -> str:
        """生成配置模块"""
        cfg = self.config
        return f'''package client

import "time"

// Config SDK 配置
type Config struct {{
	BaseURL     string
	APIKey      string
	APIVersion  string
	Timeout     time.Duration

	MaxRetries         int
	RetryBackoffFactor float64
	RetryStatusCodes   []int

	APIKeyHeader string

	PaginationCursorParam  string
	PaginationLimitParam   string
	PaginationDefaultLimit int
	PaginationMaxLimit     int
}}

// DefaultConfig 默认配置
func DefaultConfig() Config {{
	return Config{{
		BaseURL:     "{cfg.base_url}",
		APIVersion:  "{cfg.api_version}",
		Timeout:     30 * time.Second,

		MaxRetries:         {cfg.retry_config["max_retries"]},
		RetryBackoffFactor: {cfg.retry_config["backoff_factor"]},
		RetryStatusCodes:   []int{{{ ", ".join(str(s) for s in cfg.retry_config["status_forcelist"]) }}},

		APIKeyHeader: "{cfg.auth_config["header_name"]}",

		PaginationCursorParam:  "{cfg.pagination_config["cursor_param"]}",
		PaginationLimitParam:   "{cfg.pagination_config["limit_param"]}",
		PaginationDefaultLimit: {cfg.pagination_config["default_limit"]},
		PaginationMaxLimit:     {cfg.pagination_config["max_limit"]},
	}}
}}
'''

    def _generate_core_auth(self) -> str:
        """生成鉴权模块"""
        return f'''package client

// AuthManager 认证管理器
type AuthManager struct {{
	apiKey     string
	headerName string
}}

// NewAuthManager 创建认证管理器
func NewAuthManager(apiKey, headerName string) *AuthManager {{
	return &AuthManager{{
		apiKey:     apiKey,
		headerName: headerName,
	}}
}}

// GetHeaders 获取认证请求头
func (a *AuthManager) GetHeaders() map[string]string {{
	headers := make(map[string]string)
	if a.apiKey != "" {{
		headers[a.headerName] = a.apiKey
	}}
	return headers
}}

// SetAPIKey 设置 API Key
func (a *AuthManager) SetAPIKey(apiKey string) {{
	a.apiKey = apiKey
}}
'''

    def _generate_core_retry(self) -> str:
        """生成重试模块"""
        return f'''package client

import (
	"context"
	"math"
	"net/http"
	"time"
)

// RetryManager 重试管理器
type RetryManager struct {{
	maxRetries         int
	backoffFactor      float64
	retryStatusCodes   []int
}}

// NewRetryManager 创建重试管理器
func NewRetryManager(maxRetries int, backoffFactor float64, retryStatusCodes []int) *RetryManager {{
	return &RetryManager{{
		maxRetries:       maxRetries,
		backoffFactor:    backoffFactor,
		retryStatusCodes: retryStatusCodes,
	}}
}}

// RetryableFunc 可重试的函数类型
type RetryableFunc func(ctx context.Context) (*http.Response, error)

// ShouldRetry 判断是否应该重试
func (r *RetryManager) ShouldRetry(statusCode int) bool {{
	for _, code := range r.retryStatusCodes {{
		if code == statusCode {{
			return true
		}}
	}}
	return false
}}

// Execute 执行带重试的请求
func (r *RetryManager) Execute(ctx context.Context, fn RetryableFunc) (*http.Response, error) {{
	var lastErr error

	for attempt := 0; attempt <= r.maxRetries; attempt++ {{
		resp, err := fn(ctx)
		if err != nil {{
			lastErr = err
			if attempt >= r.maxRetries {{
				return nil, err
			}}
		}} else if !r.ShouldRetry(resp.StatusCode) {{
			return resp, nil
		}} else {{
			lastErr = nil
			if attempt >= r.maxRetries {{
				return resp, nil
			}}
			resp.Body.Close()
		}}

		waitTime := time.Duration(r.backoffFactor * math.Pow(2, float64(attempt)) * float64(time.Second))
		select {{
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(waitTime):
		}}
	}}

	return nil, lastErr
}}
'''

    def _generate_core_client(self) -> str:
        """生成核心客户端"""
        return '''package client

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
)

// HTTPClient HTTP 客户端接口
type HTTPClient interface {
	Do(req *http.Request) (*http.Response, error)
}

// BaseClient 基础客户端
type BaseClient struct {
	config  Config
	auth    *AuthManager
	retry   *RetryManager
	http    HTTPClient
}

// NewBaseClient 创建基础客户端
func NewBaseClient(config Config) *BaseClient {
	return &BaseClient{
		config: config,
		auth:   NewAuthManager(config.APIKey, config.APIKeyHeader),
		retry:  NewRetryManager(config.MaxRetries, config.RetryBackoffFactor, config.RetryStatusCodes),
		http:   &http.Client{Timeout: config.Timeout},
	}
}

// Request 发送 HTTP 请求
func (c *BaseClient) Request(
	ctx context.Context,
	method string,
	path string,
	queryParams url.Values,
	body interface{},
	result interface{},
) error {
	fullURL := c.config.BaseURL + path
	if queryParams != nil && len(queryParams) > 0 {
		fullURL += "?" + queryParams.Encode()
	}

	var bodyReader io.Reader
	if body != nil {
		bodyBytes, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("failed to marshal request body: %w", err)
		}
		bodyReader = bytes.NewReader(bodyBytes)
	}

	req, err := http.NewRequestWithContext(ctx, method, fullURL, bodyReader)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	for key, value := range c.auth.GetHeaders() {
		req.Header.Set(key, value)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")

	retryFn := func(ctx context.Context) (*http.Response, error) {
		return c.http.Do(req)
	}

	resp, err := c.retry.Execute(ctx, retryFn)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("API error (status %d): %s", resp.StatusCode, string(bodyBytes))
	}

	if result != nil {
		bodyBytes, err := io.ReadAll(resp.Body)
		if err != nil {
			return fmt.Errorf("failed to read response body: %w", err)
		}
		if len(bodyBytes) > 0 {
			if err := json.Unmarshal(bodyBytes, result); err != nil {
				return fmt.Errorf("failed to unmarshal response: %w", err)
			}
		}
	}

	return nil
}
'''

    def _generate_api_base(self) -> str:
        """生成 API 基础文件"""
        pkg = self.config.go["package_name"]
        return f'''package api

import (
	"context"
	"net/url"

	"{pkg}/{pkg}/internal/client"
)

// BaseClient 基础 API 客户端
type BaseClient = client.BaseClient

// NewClient 创建新的 API 客户端
func NewClient(config client.Config) *BaseClient {{
	return client.NewBaseClient(config)
}}

// Config 类型别名
type Config = client.Config

// DefaultConfig 获取默认配置
func DefaultConfig() client.Config {{
	return client.DefaultConfig()
}}
'''

    def _generate_core_pagination(self) -> str:
        """生成游标分页模块"""
        cfg = self.config.pagination_config
        return f'''package api

import (
	"context"
	"encoding/json"
	"fmt"
	"net/url"
)

// CursorPaginator 游标分页器
type CursorPaginator struct {{
	client    *BaseClient
	path      string
	method    string
	params    url.Values
	body      interface{{}}

	cursorParam  string
	limitParam   string
	defaultLimit int

	responseCursorField string
	responseItemsField  string

	cursor   string
	hasMore  bool
}}

// NewCursorPaginator 创建游标分页器
func NewCursorPaginator(
	client *BaseClient,
	path string,
	method string,
	params url.Values,
	body interface{{}},
) *CursorPaginator {{
	return &CursorPaginator{{
		client:              client,
		path:                path,
		method:              method,
		params:              params,
		body:                body,
		cursorParam:         "{cfg["cursor_param"]}",
		limitParam:          "{cfg["limit_param"]}",
		defaultLimit:        {cfg["default_limit"]},
		responseCursorField: "{cfg["response_cursor_field"]}",
		responseItemsField:  "{cfg["response_items_field"]}",
		hasMore:             true,
	}}
}}

// NextPage 获取下一页数据
func (p *CursorPaginator) NextPage(ctx context.Context, items interface{{}}, limit ...int) error {{
	if !p.hasMore {{
		return nil
	}}

	params := url.Values{{}}
	for k, v := range p.params {{
		params[k] = v
	}}

	pageLimit := p.defaultLimit
	if len(limit) > 0 && limit[0] > 0 {{
		pageLimit = limit[0]
	}}
	params.Set(p.limitParam, fmt.Sprintf("%d", pageLimit))

	if p.cursor != "" {{
		params.Set(p.cursorParam, p.cursor)
	}}

	var rawResponse map[string]json.RawMessage
	err := p.client.Request(ctx, p.method, p.path, params, p.body, &rawResponse)
	if err != nil {{
		return err
	}}

	if itemsField, ok := rawResponse[p.responseItemsField]; ok {{
		if err := json.Unmarshal(itemsField, items); err != nil {{
			return fmt.Errorf("failed to unmarshal items: %w", err)
		}}
	}}

	if cursorField, ok := rawResponse[p.responseCursorField]; ok {{
		var cursor string
		if err := json.Unmarshal(cursorField, &cursor); err == nil {{
			p.cursor = cursor
			p.hasMore = cursor != ""
		}} else {{
			p.hasMore = false
		}}
	}} else {{
		p.hasMore = false
	}}

	return nil
}}

// HasMore 是否有更多数据
func (p *CursorPaginator) HasMore() bool {{
	return p.hasMore
}}

// Cursor 当前游标
func (p *CursorPaginator) Cursor() string {{
	return p.cursor
}}

// All 获取所有数据
func (p *CursorPaginator) All(ctx context.Context, items interface{{}}, limit ...int) error {{
	var allItems []interface{{}}

	for p.hasMore {{
		var pageItems []interface{{}}
		if err := p.NextPage(ctx, &pageItems, limit...); err != nil {{
			return err
		}}
		allItems = append(allItems, pageItems...)
	}}

	// 将所有数据序列化再反序列化到目标类型
	bytes, err := json.Marshal(allItems)
	if err != nil {{
		return err
	}}
	return json.Unmarshal(bytes, items)
}}
'''

    def _generate_package_files(self, output_dir: Path) -> None:
        """生成包配置文件"""
        go_cfg = self.config.go
        version = self.openapi_spec.get("info", {}).get("version", "1.0.0")

        go_mod_content = f"module {go_cfg['module_name']}\n\n"
        go_mod_content += f"go {go_cfg['go_version']}\n\n"
        go_mod_content += "require (\n"
        for dep in go_cfg["dependencies"]:
            go_mod_content += f"\t{dep}\n"
        go_mod_content += ")\n"

        (output_dir / "go.mod").write_text(go_mod_content)

        pkg_name = go_cfg["package_name"]
        main_export = output_dir / pkg_name / "sdk.go"
        main_export.write_text(f'''package {pkg_name}

import (
	"{go_cfg["module_name"]}/{pkg_name}/api"
	"{go_cfg["module_name"]}/{pkg_name}/models"
)

// SDK 入口别名
type Config = api.Config
type Client = api.Client

// NewClient 创建 SDK 客户端
func NewClient(config Config) *Client {{
	return api.NewClient(config)
}}

// DefaultConfig 获取默认配置
func DefaultConfig() Config {{
	return api.DefaultConfig()
}}

// 导出所有模型和 API
var (
	Models = models.AllModels
)
''')

    def _generate_readme(self, output_dir: Path) -> None:
        """生成 README"""
        go_cfg = self.config.go
        readme = f'''# {go_cfg["package_name"]}

螺栓预紧力预测系统 Go SDK

## 安装

```bash
go get {go_cfg["module_name"]}
```

## 快速开始

```go
package main

import (
    "context"
    "fmt"
    "{go_cfg["module_name"]}/{go_cfg["package_name"]}"
)

func main() {{
    config := {go_cfg["package_name"]}.DefaultConfig()
    config.BaseURL = "https://api.example.com"
    config.APIKey = "your-api-key"

    client := {go_cfg["package_name"]}.NewClient(config)

    // 调用 API
    result, err := client.PredictBolt(ctx, "B001", data)
    if err != nil {{
        panic(err)
    }}

    fmt.Println(result.Status)
}}
```

## 特性

- **完整 API 覆盖**: 支持所有 API 端点
- **自动重试**: 指数退避重试，支持配置
- **API Key 鉴权**: 支持 X-API-Key 头部认证
- **游标分页**: 自动处理游标分页
- **Context 支持**: 完整的 context 传递支持

## 分页示例

```go
// 使用游标分页获取所有数据
paginator := client.ListItems(ctx)

var allItems []Item
for paginator.HasMore() {{
    var page []Item
    if err := paginator.NextPage(ctx, &page); err != nil {{
        panic(err)
    }}
    allItems = append(allItems, page...)
}}
```
'''

        (output_dir / "README.md").write_text(readme)
