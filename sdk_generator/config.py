"""
SDK 生成器配置
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SDKConfig:
    """SDK 生成配置"""

    api_name: str = "bolt-prediction"
    api_version: str = "v1"
    base_url: str = "https://api.example.com"
    output_dir: Path = field(default_factory=lambda: Path("./sdks"))

    languages: List[str] = field(
        default_factory=lambda: ["python", "typescript", "java", "go"]
    )

    retry_config: Dict = field(
        default_factory=lambda: {
            "max_retries": 3,
            "backoff_factor": 0.5,
            "status_forcelist": [429, 500, 502, 503, 504],
        }
    )

    auth_config: Dict = field(
        default_factory=lambda: {
            "type": "api_key",
            "header_name": "X-API-Key",
            "query_param_name": "api_key",
        }
    )

    pagination_config: Dict = field(
        default_factory=lambda: {
            "type": "cursor",
            "cursor_param": "cursor",
            "limit_param": "limit",
            "default_limit": 20,
            "max_limit": 100,
            "response_cursor_field": "next_cursor",
            "response_items_field": "items",
        }
    )

    python: Dict = field(
        default_factory=lambda: {
            "package_name": "bolt_prediction_sdk",
            "module_name": "bolt_prediction_sdk",
            "author": "SDK Generator",
            "python_requires": ">=3.9",
            "dependencies": [
                "httpx>=0.26.0",
                "pydantic>=2.0.0",
                "tenacity>=8.2.0",
            ],
            "private_repo_url": "https://pypi.example.com/simple",
        }
    )

    typescript: Dict = field(
        default_factory=lambda: {
            "package_name": "@bolt-prediction/sdk",
            "scope": "bolt-prediction",
            "author": "SDK Generator",
            "node_version": ">=18.0.0",
            "dependencies": {
                "axios": "^1.6.0",
                "axios-retry": "^4.0.0",
            },
            "dev_dependencies": {
                "typescript": "^5.3.0",
                "@types/node": "^20.10.0",
            },
            "private_registry_url": "https://npm.example.com",
        }
    )

    java: Dict = field(
        default_factory=lambda: {
            "group_id": "com.boltprediction",
            "artifact_id": "bolt-prediction-sdk",
            "package_name": "com.boltprediction.sdk",
            "java_version": "11",
            "dependencies": [
                "com.squareup.okhttp3:okhttp:4.12.0",
                "com.fasterxml.jackson.core:jackson-databind:2.16.0",
                "org.apache.commons:commons-lang3:3.14.0",
                "io.github.resilience4j:resilience4j-retry:2.1.0",
            ],
            "private_repo_url": "https://maven.example.com/repository/private",
            "snapshot_repo_url": "https://maven.example.com/repository/snapshots",
        }
    )

    go: Dict = field(
        default_factory=lambda: {
            "module_name": "github.com/bolt-prediction/sdk-go",
            "package_name": "boltprediction",
            "go_version": "1.21",
            "dependencies": [
                "github.com/go-resty/resty/v2 v2.10.0",
            ],
            "private_repo_url": "",
        }
    )

    @classmethod
    def from_env(cls) -> "SDKConfig":
        """从环境变量加载配置"""
        config = cls()

        if os.getenv("SDK_API_NAME"):
            config.api_name = os.getenv("SDK_API_NAME")
        if os.getenv("SDK_API_VERSION"):
            config.api_version = os.getenv("SDK_API_VERSION")
        if os.getenv("SDK_BASE_URL"):
            config.base_url = os.getenv("SDK_BASE_URL")
        if os.getenv("SDK_OUTPUT_DIR"):
            config.output_dir = Path(os.getenv("SDK_OUTPUT_DIR"))
        if os.getenv("SDK_LANGUAGES"):
            config.languages = os.getenv("SDK_LANGUAGES").split(",")

        return config
