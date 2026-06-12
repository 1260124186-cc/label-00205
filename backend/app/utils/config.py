"""
配置管理模块

负责加载和管理系统配置，支持从YAML文件和环境变量读取配置。

主要功能:
1. 加载YAML配置文件
2. 支持环境变量覆盖
3. 提供配置验证
4. 支持热重载

使用示例:
    from app.utils.config import Config
    config = Config()
    db_config = config.get('database')
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from loguru import logger


class Config:
    """
    配置管理类

    单例模式实现，确保全局配置一致性。
    支持从YAML文件加载配置，并允许环境变量覆盖。

    Attributes:
        _instance: 单例实例
        _config: 配置字典
        _config_path: 配置文件路径
    """

    _instance: Optional['Config'] = None
    _config: Dict[str, Any] = {}
    _config_path: Optional[Path] = None

    def __new__(cls, config_path: Optional[str] = None) -> 'Config':
        """
        单例模式实现

        Args:
            config_path: 配置文件路径，可选

        Returns:
            Config: 配置实例
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置

        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        if getattr(self, '_initialized', False):
            return

        if config_path is None:
            # 默认配置文件路径
            config_path = os.environ.get(
                'CONFIG_PATH',
                str(Path(__file__).parent.parent.parent / 'config' / 'config.yaml')
            )

        self._config_path = Path(config_path)
        self._load_config()
        self._apply_env_overrides()
        self._initialized = True

    def _load_config(self) -> None:
        """
        从YAML文件加载配置

        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML解析错误
        """
        if not self._config_path.exists():
            logger.warning(f"配置文件不存在: {self._config_path}, 使用默认配置")
            self._config = self._get_default_config()
            return

        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
            logger.info(f"配置文件加载成功: {self._config_path}")
        except yaml.YAMLError as e:
            logger.error(f"配置文件解析错误: {e}")
            self._config = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认配置

        Returns:
            Dict: 默认配置字典
        """
        return {
            'database': {
                'host': '127.0.0.1',
                'port': 3306,
                'user': 'root',
                'password': '',
                'database': 'bolt_preload'
            },
            'api': {
                'host': '0.0.0.0',
                'port': 8000,
                'debug': False
            },
            'model': {
                'save_path': './trained_models'
            },
            'hardware': {
                'prefer_gpu': True
            },
            'logging': {
                'level': 'INFO',
                'format': '{time} - {name} - {level} - {message}',
                'file': './logs/app.log'
            },
            'auth': {
                'enabled': False,
                'master_key': ''
            },
            'llm': {
                'provider': 'local',
                'openai': {
                    'api_key': '',
                    'model': 'gpt-3.5-turbo',
                    'base_url': 'https://api.openai.com/v1'
                },
                'qwen': {
                    'api_key': '',
                    'model': 'qwen-turbo'
                }
            },
            'audit': {
                'retention_years': 3,
                'auto_cleanup_enabled': True,
                'cleanup_interval_hours': 24
            }
        }

    def _apply_env_overrides(self) -> None:
        """
        应用环境变量覆盖配置

        支持的环境变量:
        - DB_HOST: 数据库主机
        - DB_PORT: 数据库端口
        - DB_USER: 数据库用户
        - DB_PASSWORD: 数据库密码
        - DB_NAME: 数据库名
        - API_HOST: API主机
        - API_PORT: API端口
        - LOG_LEVEL: 日志级别
        - AUTH_ENABLED: 是否启用认证
        - AUTH_MASTER_KEY: 认证主密钥
        - LLM_PROVIDER: LLM提供商
        - LLM_OPENAI_API_KEY: OpenAI API密钥
        - LLM_OPENAI_MODEL: OpenAI模型名称
        - LLM_OPENAI_BASE_URL: OpenAI API基础URL
        - LLM_QWEN_API_KEY: 通义千问API密钥
        - LLM_QWEN_MODEL: 通义千问模型名称
        """
        env_mappings = {
            'DB_HOST': ('database', 'host'),
            'DB_PORT': ('database', 'port'),
            'DB_USER': ('database', 'user'),
            'DB_PASSWORD': ('database', 'password'),
            'DB_NAME': ('database', 'database'),
            'API_HOST': ('api', 'host'),
            'API_PORT': ('api', 'port'),
            'LOG_LEVEL': ('logging', 'level'),
            'AUTH_ENABLED': ('auth', 'enabled'),
            'AUTH_MASTER_KEY': ('auth', 'master_key'),
            'LLM_PROVIDER': ('llm', 'provider'),
            'LLM_OPENAI_API_KEY': ('llm', 'openai', 'api_key'),
            'LLM_OPENAI_MODEL': ('llm', 'openai', 'model'),
            'LLM_OPENAI_BASE_URL': ('llm', 'openai', 'base_url'),
            'LLM_QWEN_API_KEY': ('llm', 'qwen', 'api_key'),
            'LLM_QWEN_MODEL': ('llm', 'qwen', 'model'),
        }

        for env_key, config_path in env_mappings.items():
            env_value = os.environ.get(env_key)
            if env_value is not None:
                self._set_nested(config_path, env_value)
                if env_key.endswith('_KEY') or env_key.endswith('_PASSWORD'):
                    logger.debug(f"环境变量覆盖: {env_key}=***")
                else:
                    logger.debug(f"环境变量覆盖: {env_key}={env_value}")

    def _set_nested(self, path: tuple, value: Any) -> None:
        """
        设置嵌套配置值

        Args:
            path: 配置路径元组
            value: 配置值
        """
        d = self._config
        for key in path[:-1]:
            d = d.setdefault(key, {})

        existing_value = d.get(path[-1])
        if existing_value is not None:
            if isinstance(existing_value, bool):
                value = value.lower() in ('true', '1', 'yes')
            elif isinstance(existing_value, int):
                value = int(value)
            elif isinstance(existing_value, float):
                value = float(value)
        else:
            lower_val = value.lower()
            if lower_val in ('true', 'false', '1', '0', 'yes', 'no'):
                value = lower_val in ('true', '1', 'yes')
            elif value.isdigit():
                value = int(value)
            else:
                try:
                    value = float(value)
                except ValueError:
                    pass

        d[path[-1]] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        支持点分隔的嵌套键，如 'database.host'

        Args:
            key: 配置键
            default: 默认值

        Returns:
            Any: 配置值
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

            if value is None:
                return default

        return value

    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置

        Returns:
            Dict: 完整配置字典
        """
        return self._config.copy()

    def reload(self) -> None:
        """
        重新加载配置文件
        """
        self._load_config()
        self._apply_env_overrides()
        logger.info("配置已重新加载")


# 全局配置实例
config = Config()
