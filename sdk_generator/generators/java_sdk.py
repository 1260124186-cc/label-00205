"""
Java SDK 生成器

生成包含重试、鉴权、游标同步封装的 Java SDK。
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from loguru import logger

from .base import BaseSDKGenerator


class JavaSDKGenerator(BaseSDKGenerator):
    """Java SDK 生成器"""

    @property
    def language_name(self) -> str:
        return "java"

    def _java_package_dir(self, output_dir: Path) -> Path:
        """获取 Java 包目录"""
        pkg = self.config.java["package_name"]
        parts = pkg.split(".")
        path = output_dir / "src" / "main" / "java"
        for part in parts:
            path = path / part
        return path

    def _generate_project_structure(self, output_dir: Path) -> None:
        """生成项目目录结构"""
        pkg_dir = self._java_package_dir(output_dir)
        test_dir = output_dir / "src" / "test" / "java"

        dirs = [
            pkg_dir / "model",
            pkg_dir / "api",
            pkg_dir / "core",
            test_dir,
            output_dir / "examples",
        ]

        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _generate_models(self, output_dir: Path) -> None:
        """生成数据模型"""
        pkg_dir = self._java_package_dir(output_dir)
        model_dir = pkg_dir / "model"
        schemas = self._get_schemas()

        for schema_name, schema in schemas.items():
            if schema.get("type") == "object" or "properties" in schema:
                class_code = self._generate_model_class(schema_name, schema)
                file_name = self._to_pascal_case(schema_name) + ".java"
                (model_dir / file_name).write_text(class_code)

    def _generate_model_class(self, name: str, schema: Dict[str, Any]) -> str:
        """生成单个模型类"""
        class_name = self._to_pascal_case(name)
        package_name = self.config.java["package_name"]
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        lines = [
            f"package {package_name}.model;",
            "",
            "import com.fasterxml.jackson.annotation.JsonProperty;",
            "import com.fasterxml.jackson.annotation.JsonIgnoreProperties;",
            "import java.util.List;",
            "import java.util.Map;",
            "import java.time.OffsetDateTime;",
            "",
            f"/** {schema.get('description', name)} */",
            "@JsonIgnoreProperties(ignoreUnknown = true)",
            f"public class {class_name} {{",
            "",
        ]

        for prop_name, prop_schema in properties.items():
            java_name = self._to_camel_case(prop_name)
            java_type = self._map_java_type(prop_schema)
            is_required = prop_name in required

            lines.append(f"    @JsonProperty(\"{prop_name}\")")
            lines.append(f"    private {java_type} {java_name};")
            lines.append("")

        for prop_name, prop_schema in properties.items():
            java_name = self._to_camel_case(prop_name)
            java_type = self._map_java_type(prop_schema)
            cap_name = self._to_pascal_case(prop_name)

            lines.append(f"    public {java_type} get{cap_name}() {{")
            lines.append(f"        return {java_name};")
            lines.append("    }")
            lines.append("")

            lines.append(f"    public void set{cap_name}({java_type} {java_name}) {{")
            lines.append(f"        this.{java_name} = {java_name};")
            lines.append("    }")
            lines.append("")

        lines.append("}")
        return "\n".join(lines)

    def _map_java_type(self, schema: Dict[str, Any]) -> str:
        """映射 OpenAPI 类型到 Java 类型"""
        if "$ref" in schema:
            ref_name = schema["$ref"].split("/")[-1]
            return self._to_pascal_case(ref_name)

        type_name = schema.get("type", "Object")
        format_name = schema.get("format", "")

        if type_name == "string":
            if format_name in ("date", "date-time"):
                return "OffsetDateTime"
            return "String"
        elif type_name == "integer":
            if format_name == "int64":
                return "Long"
            return "Integer"
        elif type_name == "number":
            if format_name == "float":
                return "Float"
            return "Double"
        elif type_name == "boolean":
            return "Boolean"
        elif type_name == "array":
            items = schema.get("items", {})
            item_type = self._map_java_type(items)
            return f"List<{item_type}>"
        elif type_name == "object":
            additional = schema.get("additionalProperties", {})
            if additional:
                value_type = self._map_java_type(additional)
                return f"Map<String, {value_type}>"
            return "Map<String, Object>"
        else:
            return "Object"

    def _generate_api_clients(self, output_dir: Path) -> None:
        """生成 API 客户端"""
        pkg_dir = self._java_package_dir(output_dir)
        api_dir = pkg_dir / "api"
        groups = self._parse_paths()

        for group in groups:
            tag = group["tag"]
            operations = group["operations"]
            class_name = self._to_pascal_case(tag) + "Client"
            file_name = class_name + ".java"
            code = self._generate_api_client_class(class_name, tag, operations)
            (api_dir / file_name).write_text(code)

    def _generate_api_client_class(
        self,
        class_name: str,
        tag: str,
        operations: List[Dict[str, Any]],
    ) -> str:
        """生成单个 API 客户端类"""
        package_name = self.config.java["package_name"]

        lines = [
            f"package {package_name}.api;",
            "",
            f"import {package_name}.core.BaseAPIClient;",
            f"import {package_name}.core.CursorPaginator;",
            f"import {package_name}.model.*;",
            "",
            "import okhttp3.*;",
            "import com.fasterxml.jackson.databind.ObjectMapper;",
            "import java.io.IOException;",
            "import java.util.*;",
            "",
            f"/** {tag} API 客户端 */",
            f"public class {class_name} extends BaseAPIClient {{",
            "",
            f"    public {class_name}(ApiClientConfig config) {{",
            "        super(config);",
            "    }",
            "",
        ]

        for op in operations:
            method_code = self._generate_api_method(op)
            lines.append(method_code)
            lines.append("")

        lines.append("}")
        return "\n".join(lines)

    def _generate_api_method(self, operation: Dict[str, Any]) -> str:
        """生成单个 API 方法"""
        op = operation["operation"]
        method_name = self._to_camel_case(op.get("operationId", operation["operation_id"]))
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
        for p in path_params:
            param_name = self._to_camel_case(p["name"])
            param_type = self._map_java_type(p.get("schema", {}))
            params_list.append(f"{param_type} {param_name}")

        if body_param:
            body_schema = (
                body_param.get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            body_type = self._map_java_type(body_schema)
            params_list.append(f"{body_type} body")

        for p in query_params:
            param_name = self._to_camel_case(p["name"])
            param_type = self._map_java_type(p.get("schema", {}))
            params_list.append(f"{param_type} {param_name}")

        return_type = "Map<String, Object>"
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
                return_type = self._map_java_type(schema)

        method_path = operation["path"]
        for p in path_params:
            param_name = p["name"]
            java_name = self._to_camel_case(param_name)
            method_path = method_path.replace("{" + param_name + "}", "\" + " + java_name + " + \"")

        lines = [
            f"    /** {summary} */",
            f"    public {is_paginated and 'CursorPaginator<' + return_type + '>' or return_type} {method_name}(",
        ]

        for i, param in enumerate(params_list):
            if i < len(params_list) - 1:
                lines.append(f"            {param},")
            else:
                lines.append(f"            {param}")

        lines.append(f"    ) throws IOException {{")

        if is_paginated:
            lines.append(f"        Map<String, String> params = new HashMap<>();")
            for p in query_params:
                param_name = self._to_camel_case(p["name"])
                if p["name"] not in (
                    self.config.pagination_config["cursor_param"],
                    self.config.pagination_config["limit_param"],
                ):
                    lines.append(f"        if ({param_name} != null) params.put(\"{p['name']}\", String.valueOf({param_name}));")
            lines.append("")
            lines.append(f"        return new CursorPaginator<>(")
            lines.append(f"                this,")
            lines.append(f"                \"/api/{self.config.api_version}{method_path}\",")
            lines.append(f"                \"{operation['method']}\",")
            lines.append(f"                params")
            if body_param:
                lines.append(f"                , body")
            lines.append(f"        );")
        else:
            lines.append(f"        Map<String, String> params = new HashMap<>();")
            for p in query_params:
                param_name = self._to_camel_case(p["name"])
                lines.append(f"        if ({param_name} != null) params.put(\"{p['name']}\", String.valueOf({param_name}));")
            lines.append("")
            lines.append(f"        return _request(")
            lines.append(f"                \"{operation['method']}\",")
            lines.append(f"                \"/api/{self.config.api_version}{method_path}\",")
            lines.append(f"                params,")
            if body_param:
                lines.append(f"                body,")
            else:
                lines.append(f"                null,")
            lines.append(f"                {return_type}.class")
            lines.append(f"        );")

        lines.append(f"    }}")
        return "\n".join(lines)

    def _generate_core_modules(self, output_dir: Path) -> None:
        """生成核心模块"""
        pkg_dir = self._java_package_dir(output_dir)
        core_dir = pkg_dir / "core"

        (core_dir / "ApiClientConfig.java").write_text(self._generate_core_config())
        (core_dir / "AuthManager.java").write_text(self._generate_core_auth())
        (core_dir / "RetryManager.java").write_text(self._generate_core_retry())
        (core_dir / "CursorPaginator.java").write_text(self._generate_core_pagination())
        (core_dir / "BaseAPIClient.java").write_text(self._generate_core_client())

    def _generate_core_config(self) -> str:
        """生成配置类"""
        package_name = self.config.java["package_name"]
        cfg = self.config

        return f'''package {package_name}.core;

/**
 * API 客户端配置
 */
public class ApiClientConfig {{
    private String baseUrl = "{cfg.base_url}";
    private String apiKey;
    private String apiVersion = "{cfg.api_version}";
    private int timeout = 30;

    private int maxRetries = {cfg.retry_config["max_retries"]};
    private double retryBackoffFactor = {cfg.retry_config["backoff_factor"]};
    private int[] retryStatusCodes = {{{", ".join(str(s) for s in cfg.retry_config["status_forcelist"])}}};

    private String apiKeyHeader = "{cfg.auth_config["header_name"]}";

    private String paginationCursorParam = "{cfg.pagination_config["cursor_param"]}";
    private String paginationLimitParam = "{cfg.pagination_config["limit_param"]}";
    private int paginationDefaultLimit = {cfg.pagination_config["default_limit"]};
    private int paginationMaxLimit = {cfg.pagination_config["max_limit"]};

    public String getBaseUrl() {{ return baseUrl; }}
    public void setBaseUrl(String baseUrl) {{ this.baseUrl = baseUrl; }}

    public String getApiKey() {{ return apiKey; }}
    public void setApiKey(String apiKey) {{ this.apiKey = apiKey; }}

    public String getApiVersion() {{ return apiVersion; }}
    public void setApiVersion(String apiVersion) {{ this.apiVersion = apiVersion; }}

    public int getTimeout() {{ return timeout; }}
    public void setTimeout(int timeout) {{ this.timeout = timeout; }}

    public int getMaxRetries() {{ return maxRetries; }}
    public void setMaxRetries(int maxRetries) {{ this.maxRetries = maxRetries; }}

    public double getRetryBackoffFactor() {{ return retryBackoffFactor; }}
    public void setRetryBackoffFactor(double retryBackoffFactor) {{ this.retryBackoffFactor = retryBackoffFactor; }}

    public int[] getRetryStatusCodes() {{ return retryStatusCodes; }}
    public void setRetryStatusCodes(int[] retryStatusCodes) {{ this.retryStatusCodes = retryStatusCodes; }}

    public String getApiKeyHeader() {{ return apiKeyHeader; }}
    public void setApiKeyHeader(String apiKeyHeader) {{ this.apiKeyHeader = apiKeyHeader; }}

    public String getPaginationCursorParam() {{ return paginationCursorParam; }}
    public void setPaginationCursorParam(String paginationCursorParam) {{ this.paginationCursorParam = paginationCursorParam; }}

    public String getPaginationLimitParam() {{ return paginationLimitParam; }}
    public void setPaginationLimitParam(String paginationLimitParam) {{ this.paginationLimitParam = paginationLimitParam; }}

    public int getPaginationDefaultLimit() {{ return paginationDefaultLimit; }}
    public void setPaginationDefaultLimit(int paginationDefaultLimit) {{ this.paginationDefaultLimit = paginationDefaultLimit; }}

    public int getPaginationMaxLimit() {{ return paginationMaxLimit; }}
    public void setPaginationMaxLimit(int paginationMaxLimit) {{ this.paginationMaxLimit = paginationMaxLimit; }}
}}
'''

    def _generate_core_auth(self) -> str:
        """生成鉴权模块"""
        package_name = self.config.java["package_name"]
        return f'''package {package_name}.core;

import java.util.HashMap;
import java.util.Map;

/**
 * 认证管理器
 */
public class AuthManager {{
    private String apiKey;
    private String headerName;

    public AuthManager(String apiKey) {{
        this(apiKey, "X-API-Key");
    }}

    public AuthManager(String apiKey, String headerName) {{
        this.apiKey = apiKey;
        this.headerName = headerName;
    }}

    public Map<String, String> getHeaders() {{
        Map<String, String> headers = new HashMap<>();
        if (apiKey != null && !apiKey.isEmpty()) {{
            headers.put(headerName, apiKey);
        }}
        return headers;
    }}

    public void setApiKey(String apiKey) {{
        this.apiKey = apiKey;
    }}
}}
'''

    def _generate_core_retry(self) -> str:
        """生成重试模块"""
        package_name = self.config.java["package_name"]
        cfg = self.config
        return f'''package {package_name}.core;

import java.io.IOException;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 重试管理器
 */
public class RetryManager {{
    private final int maxRetries;
    private final double backoffFactor;
    private final List<Integer> statusCodes;

    public RetryManager(int maxRetries, double backoffFactor, int[] statusCodes) {{
        this.maxRetries = maxRetries;
        this.backoffFactor = backoffFactor;
        this.statusCodes = Arrays.stream(statusCodes).boxed().collect(Collectors.toList());
    }}

    public interface Retryable<T> {{
        T execute() throws IOException;
    }}

    public <T> T execute(Retryable<T> retryable) throws IOException {{
        IOException lastException = null;

        for (int attempt = 0; attempt <= maxRetries; attempt++) {{
            try {{
                return retryable.execute();
            }} catch (IOException e) {{
                lastException = e;
                int statusCode = extractStatusCode(e);

                if (!statusCodes.contains(statusCode)) {{
                    throw e;
                }}

                if (attempt >= maxRetries) {{
                    throw new IOException("Max retries (" + maxRetries + ") reached", e);
                }}

                double waitTime = backoffFactor * Math.pow(2, attempt) * 1000;
                try {{
                    Thread.sleep((long) waitTime);
                }} catch (InterruptedException ie) {{
                    Thread.currentThread().interrupt();
                    throw new IOException("Retry interrupted", ie);
                }}
            }}
        }}

        throw lastException;
    }}

    private int extractStatusCode(IOException e) {{
        String message = e.getMessage();
        if (message != null && message.contains("HTTP")) {{
            try {{
                String[] parts = message.split(" ");
                for (String part : parts) {{
                    if (part.matches("\\\\d{{3}}")) {{
                        return Integer.parseInt(part);
                    }}
                }}
            }} catch (Exception ignored) {{
            }}
        }}
        return 0;
    }}
}}
'''

    def _generate_core_pagination(self) -> str:
        """生成游标分页模块"""
        package_name = self.config.java["package_name"]
        cfg = self.config.pagination_config
        return f'''package {package_name}.core;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

/**
 * 游标分页器
 */
public class CursorPaginator<T> implements Iterable<T> {{
    private final BaseAPIClient client;
    private final String path;
    private final String method;
    private final Map<String, String> params;
    private final Object body;
    private final Class<T> itemType;
    private final ObjectMapper objectMapper;

    private final String cursorParam;
    private final String limitParam;
    private final int defaultLimit;
    private final String responseCursorField;
    private final String responseItemsField;

    private String cursor;
    private boolean hasMore = true;
    private List<T> buffer = new ArrayList<>();

    public CursorPaginator(BaseAPIClient client, String path, String method,
                           Map<String, String> params, Object body, Class<T> itemType) {{
        this.client = client;
        this.path = path;
        this.method = method;
        this.params = params;
        this.body = body;
        this.itemType = itemType;
        this.objectMapper = new ObjectMapper();

        this.cursorParam = "{cfg["cursor_param"]}";
        this.limitParam = "{cfg["limit_param"]}";
        this.defaultLimit = {cfg["default_limit"]};
        this.responseCursorField = "{cfg["response_cursor_field"]}";
        this.responseItemsField = "{cfg["response_items_field"]}";
    }}

    public List<T> nextPage() throws IOException {{
        return nextPage(defaultLimit);
    }}

    public List<T> nextPage(int limit) throws IOException {{
        if (!hasMore) {{
            return new ArrayList<>();
        }}

        Map<String, String> requestParams = new java.util.HashMap<>(params);
        requestParams.put(limitParam, String.valueOf(limit));
        if (cursor != null && !cursor.isEmpty()) {{
            requestParams.put(cursorParam, cursor);
        }}

        JsonNode response = client._requestJson(method, path, requestParams, body);

        if (response.isArray()) {{
            hasMore = false;
            return parseItems(response);
        }}

        JsonNode itemsNode = response.get(responseItemsField);
        JsonNode cursorNode = response.get(responseCursorField);

        List<T> items = itemsNode != null ? parseItems(itemsNode) : new ArrayList<>();
        cursor = cursorNode != null && !cursorNode.isNull() ? cursorNode.asText() : null;
        hasMore = cursor != null && !cursor.isEmpty();

        return items;
    }}

    public List<T> all() throws IOException {{
        List<T> allItems = new ArrayList<>();
        while (hasMore) {{
            allItems.addAll(nextPage());
        }}
        return allItems;
    }}

    public boolean hasMore() {{
        return hasMore;
    }}

    public String getCursor() {{
        return cursor;
    }}

    private List<T> parseItems(JsonNode itemsNode) throws IOException {{
        List<T> items = new ArrayList<>();
        for (JsonNode itemNode : itemsNode) {{
            T item = objectMapper.treeToValue(itemNode, itemType);
            items.add(item);
        }}
        return items;
    }}

    @Override
    public Iterator<T> iterator() {{
        return new PaginatorIterator();
    }}

    private class PaginatorIterator implements Iterator<T> {{
        private Iterator<T> currentPageIterator;

        public PaginatorIterator() {{
            try {{
                loadNextPage();
            }} catch (IOException e) {{
                throw new RuntimeException(e);
            }}
        }}

        @Override
        public boolean hasNext() {{
            try {{
                if (currentPageIterator != null && currentPageIterator.hasNext()) {{
                    return true;
                }}
                if (hasMore) {{
                    loadNextPage();
                    return currentPageIterator.hasNext();
                }}
                return false;
            }} catch (IOException e) {{
                throw new RuntimeException(e);
            }}
        }}

        @Override
        public T next() {{
            return currentPageIterator.next();
        }}

        private void loadNextPage() throws IOException {{
            List<T> page = nextPage();
            currentPageIterator = page.iterator();
        }}
    }}
}}
'''

    def _generate_core_client(self) -> str:
        """生成核心客户端"""
        package_name = self.config.java["package_name"]
        return f'''package {package_name}.core;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import okhttp3.*;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * API 客户端基类
 */
public abstract class BaseAPIClient {{
    protected final ApiClientConfig config;
    protected final AuthManager auth;
    protected final RetryManager retry;
    protected final OkHttpClient httpClient;
    protected final ObjectMapper objectMapper;

    public BaseAPIClient(ApiClientConfig config) {{
        this.config = config;
        this.auth = new AuthManager(config.getApiKey(), config.getApiKeyHeader());
        this.retry = new RetryManager(
            config.getMaxRetries(),
            config.getRetryBackoffFactor(),
            config.getRetryStatusCodes()
        );
        this.objectMapper = new ObjectMapper();
        this.httpClient = new OkHttpClient.Builder()
            .connectTimeout(config.getTimeout(), TimeUnit.SECONDS)
            .readTimeout(config.getTimeout(), TimeUnit.SECONDS)
            .writeTimeout(config.getTimeout(), TimeUnit.SECONDS)
            .build();
    }}

    protected <T> T _request(String method, String path, Map<String, String> params,
                             Object body, Class<T> responseType) throws IOException {{
        return retry.execute(() -> {{
            Request request = buildRequest(method, path, params, body);
            try (Response response = httpClient.newCall(request).execute()) {{
                if (!response.isSuccessful()) {{
                    throw new IOException("HTTP " + response.code() + ": " + response.message());
                }}
                ResponseBody responseBody = response.body();
                if (responseBody == null) {{
                    return null;
                }}
                String bodyStr = responseBody.string();
                if (bodyStr.isEmpty()) {{
                    return null;
                }}
                return objectMapper.readValue(bodyStr, responseType);
            }}
        }});
    }}

    protected JsonNode _requestJson(String method, String path, Map<String, String> params,
                                    Object body) throws IOException {{
        return retry.execute(() -> {{
            Request request = buildRequest(method, path, params, body);
            try (Response response = httpClient.newCall(request).execute()) {{
                if (!response.isSuccessful()) {{
                    throw new IOException("HTTP " + response.code() + ": " + response.message());
                }}
                ResponseBody responseBody = response.body();
                if (responseBody == null) {{
                    return null;
                }}
                String bodyStr = responseBody.string();
                if (bodyStr.isEmpty()) {{
                    return objectMapper.createObjectNode();
                }}
                return objectMapper.readTree(bodyStr);
            }}
        }});
    }}

    private Request buildRequest(String method, String path, Map<String, String> params,
                                 Object body) throws IOException {{
        HttpUrl.Builder urlBuilder = HttpUrl.parse(config.getBaseUrl() + path).newBuilder();
        if (params != null) {{
            for (Map.Entry<String, String> entry : params.entrySet()) {{
                if (entry.getValue() != null) {{
                    urlBuilder.addQueryParameter(entry.getKey(), entry.getValue());
                }}
            }}
        }}
        HttpUrl url = urlBuilder.build();

        Request.Builder requestBuilder = new Request.Builder().url(url);

        Map<String, String> headers = auth.getHeaders();
        for (Map.Entry<String, String> entry : headers.entrySet()) {{
            requestBuilder.header(entry.getKey(), entry.getValue());
        }}
        requestBuilder.header("Content-Type", "application/json");
        requestBuilder.header("Accept", "application/json");

        RequestBody requestBody = null;
        if (body != null) {{
            String bodyJson = objectMapper.writeValueAsString(body);
            requestBody = RequestBody.create(
                bodyJson,
                MediaType.parse("application/json")
            );
        }}

        requestBuilder.method(method, requestBody);
        return requestBuilder.build();
    }}
}}
'''

    def _generate_package_files(self, output_dir: Path) -> None:
        """生成包配置文件"""
        (output_dir / "pom.xml").write_text(self._generate_pom_xml())
        (output_dir / ".mvn" / "maven.config").write_text("-s .mvn/settings.xml\n")
        (output_dir / ".mvn" / "settings.xml").write_text(self._generate_maven_settings())

    def _generate_pom_xml(self) -> str:
        """生成 pom.xml"""
        java = self.config.java
        version = self.openapi_spec.get("info", {}).get("version", "1.0.0")

        dependencies_xml = "\n".join(
            f"""        <dependency>
            <groupId>{dep.split(":")[0]}</groupId>
            <artifactId>{dep.split(":")[1]}</artifactId>
            <version>{dep.split(":")[2]}</version>
        </dependency>"""
            for dep in java["dependencies"]
        )

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>{java["group_id"]}</groupId>
    <artifactId>{java["artifact_id"]}</artifactId>
    <version>{version}</version>
    <packaging>jar</packaging>

    <name>Bolt Prediction SDK</name>
    <description>螺栓预紧力预测系统 Java SDK</description>

    <properties>
        <maven.compiler.source>{java["java_version"]}</maven.compiler.source>
        <maven.compiler.target>{java["java_version"]}</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>

    <dependencies>
{dependencies_xml}
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.11.0</version>
                <configuration>
                    <source>{java["java_version"]}</source>
                    <target>{java["java_version"]}</target>
                </configuration>
            </plugin>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-source-plugin</artifactId>
                <version>3.3.0</version>
                <executions>
                    <execution>
                        <id>attach-sources</id>
                        <goals>
                            <goal>jar</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-javadoc-plugin</artifactId>
                <version>3.6.0</version>
                <executions>
                    <execution>
                        <id>attach-javadocs</id>
                        <goals>
                            <goal>jar</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>
        </plugins>
    </build>

    <distributionManagement>
        <repository>
            <id>private-repo</id>
            <url>{java["private_repo_url"]}</url>
        </repository>
        <snapshotRepository>
            <id>private-repo</id>
            <url>{java["snapshot_repo_url"]}</url>
        </snapshotRepository>
    </distributionManagement>
</project>
'''

    def _generate_maven_settings(self) -> str:
        """生成 Maven settings"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.0.0
                              http://maven.apache.org/xsd/settings-1.0.0.xsd">
    <servers>
        <server>
            <id>private-repo</id>
            <username>${env.MAVEN_USERNAME}</username>
            <password>${env.MAVEN_PASSWORD}</password>
        </server>
    </servers>
</settings>
'''

    def _generate_readme(self, output_dir: Path) -> None:
        """生成 README"""
        java = self.config.java
        readme = f'''# {java["artifact_id"]}

螺栓预紧力预测系统 Java SDK

## 安装

Maven 依赖:

```xml
<dependency>
    <groupId>{java["group_id"]}</groupId>
    <artifactId>{java["artifact_id"]}</artifactId>
    <version>1.0.0</version>
</dependency>
```

## 快速开始

```java
import {java["package_name"]}.api.预测Client;
import {java["package_name"]}.core.ApiClientConfig;

public class Example {{
    public static void main(String[] args) throws Exception {{
        ApiClientConfig config = new ApiClientConfig();
        config.setBaseUrl("https://api.example.com");
        config.setApiKey("your-api-key");

        预测Client client = new 预测Client(config);

        BoltPredictionResponse result = client.predictBolt("B001", data);
        System.out.println(result.getStatus());
    }}
}}
```

## 特性

- **完整 API 覆盖**: 支持所有 API 端点
- **自动重试**: 指数退避重试，支持配置
- **API Key 鉴权**: 支持 X-API-Key 头部认证
- **游标分页**: 自动处理游标分页，支持迭代器模式
- **Java 11+ 兼容**: 兼容 Java 11 及以上版本

## 分页示例

```java
CursorPaginator<Item> paginator = client.listItems();

// 获取所有数据
List<Item> allItems = paginator.all();

// 或者使用迭代器
for (Item item : paginator) {{
    System.out.println(item);
}}

// 逐页获取
while (paginator.hasMore()) {{
    List<Item> page = paginator.nextPage();
    // 处理当前页
}}
```
'''

        (output_dir / "README.md").write_text(readme)
