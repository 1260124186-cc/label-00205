"""
SDK 生成器模块
"""

from .base import BaseSDKGenerator
from .python_sdk import PythonSDKGenerator
from .typescript_sdk import TypeScriptSDKGenerator
from .java_sdk import JavaSDKGenerator
from .go_sdk import GoSDKGenerator


def get_generator(language: str, config):
    """
    获取对应语言的 SDK 生成器

    Args:
        language: 语言名称
        config: SDK 配置

    Returns:
        SDK 生成器实例
    """
    generators = {
        "python": PythonSDKGenerator,
        "typescript": TypeScriptSDKGenerator,
        "java": JavaSDKGenerator,
        "go": GoSDKGenerator,
    }

    if language not in generators:
        raise ValueError(f"不支持的语言: {language}")

    return generators[language](config)


__all__ = [
    "BaseSDKGenerator",
    "PythonSDKGenerator",
    "TypeScriptSDKGenerator",
    "JavaSDKGenerator",
    "GoSDKGenerator",
    "get_generator",
]
