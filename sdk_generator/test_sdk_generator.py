#!/usr/bin/env python3
"""
SDK 生成器测试脚本

验证 SDK 生成器的核心功能是否正常工作。
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_breaking_change_detector():
    """测试 Breaking Change 检测"""
    print("Testing Breaking Change Detector...", end=" ")

    from sdk_generator.breaking_change import (
        BreakingChangeDetector,
        ChangeLevel,
    )

    old_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "v1"},
        "paths": {
            "/test": {
                "get": {
                    "parameters": [
                        {"name": "id", "in": "query", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
        "components": {
            "schemas": {
                "TestModel": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                    },
                    "required": ["id", "name"],
                }
            }
        },
    }

    new_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "v1"},
        "paths": {
            "/test": {
                "get": {
                    "parameters": [
                        {"name": "id", "in": "query", "schema": {"type": "integer"}}
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/new": {
                "get": {
                    "responses": {"200": {"description": "OK"}},
                }
            },
        },
        "components": {
            "schemas": {
                "TestModel": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "extra": {"type": "string"},
                    },
                    "required": ["id"],
                }
            }
        },
    }

    detector = BreakingChangeDetector(old_spec, new_spec)
    report = detector.detect()

    assert report.total_changes > 0, "应该检测到变更"
    assert len(report.breaking_changes) > 0, "应该有破坏性变更"

    print("✓")
    return True


def test_version_manager():
    """测试版本管理器"""
    print("Testing Version Manager...", end=" ")

    from sdk_generator.version_manager import (
        VersionManager,
        VersionBumpType,
    )

    vm = VersionManager(api_version="v1", current_sdk_version="1.2.3")

    current = vm.get_current_version()
    assert current.sdk_version == "1.2.3"
    assert vm.validate_version_alignment()

    vm.bump_version(VersionBumpType.PATCH)
    assert vm.get_current_version().sdk_version == "1.2.4"

    vm2 = VersionManager(api_version="v1", current_sdk_version="1.2.3")
    vm2.bump_version(VersionBumpType.MINOR)
    assert vm2.get_current_version().sdk_version == "1.3.0"

    vm3 = VersionManager(api_version="v1", current_sdk_version="1.2.3")
    vm3.bump_version(VersionBumpType.MAJOR)
    assert vm3.get_current_version().sdk_version == "2.0.0"

    bump_type = vm3.determine_bump_type(
        has_breaking_changes=True,
        has_new_features=True,
    )
    assert bump_type == VersionBumpType.MAJOR

    print("✓")
    return True


def test_config():
    """测试配置"""
    print("Testing Config...", end=" ")

    from sdk_generator.config import SDKConfig

    config = SDKConfig()
    assert config.api_name == "bolt-prediction"
    assert config.api_version == "v1"
    assert len(config.languages) == 4
    assert "python" in config.languages
    assert config.retry_config["max_retries"] == 3
    assert config.auth_config["header_name"] == "X-API-Key"

    print("✓")
    return True


def test_generators_base():
    """测试生成器基类"""
    print("Testing Generator Base...", end=" ")

    from sdk_generator.generators.base import BaseSDKGenerator
    from sdk_generator.config import SDKConfig

    config = SDKConfig()

    class TestGenerator(BaseSDKGenerator):
        @property
        def language_name(self):
            return "test"

        def _generate_project_structure(self, output_dir):
            pass

        def _generate_models(self, output_dir):
            pass

        def _generate_api_clients(self, output_dir):
            pass

        def _generate_core_modules(self, output_dir):
            pass

        def _generate_package_files(self, output_dir):
            pass

        def _generate_readme(self, output_dir):
            pass

    gen = TestGenerator(config)
    assert gen.language_name == "test"

    assert gen._to_pascal_case("hello_world") == "HelloWorld"
    assert gen._to_camel_case("hello_world") == "helloWorld"
    assert gen._to_snake_case("HelloWorld") == "hello_world"
    assert gen._to_kebab_case("hello_world") == "hello-world"

    print("✓")
    return True


def test_python_generator():
    """测试 Python 生成器"""
    print("Testing Python Generator...", end=" ")

    from sdk_generator.generators.python_sdk import PythonSDKGenerator
    from sdk_generator.config import SDKConfig

    config = SDKConfig()
    gen = PythonSDKGenerator(config)

    assert gen.language_name == "python"

    test_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/test": {
                "get": {
                    "tags": ["测试"],
                    "summary": "测试接口",
                    "operationId": "getTest",
                    "parameters": [],
                    "responses": {"200": {"description": "成功"}},
                }
            }
        },
        "components": {
            "schemas": {
                "TestResponse": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                    },
                }
            }
        },
    }

    gen.openapi_spec = test_spec
    groups = gen._parse_paths()
    assert len(groups) > 0

    print("✓")
    return True


def test_typescript_generator():
    """测试 TypeScript 生成器"""
    print("Testing TypeScript Generator...", end=" ")

    from sdk_generator.generators.typescript_sdk import TypeScriptSDKGenerator
    from sdk_generator.config import SDKConfig

    config = SDKConfig()
    gen = TypeScriptSDKGenerator(config)

    assert gen.language_name == "typescript"

    print("✓")
    return True


def test_java_generator():
    """测试 Java 生成器"""
    print("Testing Java Generator...", end=" ")

    from sdk_generator.generators.java_sdk import JavaSDKGenerator
    from sdk_generator.config import SDKConfig

    config = SDKConfig()
    gen = JavaSDKGenerator(config)

    assert gen.language_name == "java"

    print("✓")
    return True


def test_go_generator():
    """测试 Go 生成器"""
    print("Testing Go Generator...", end=" ")

    from sdk_generator.generators.go_sdk import GoSDKGenerator
    from sdk_generator.config import SDKConfig

    config = SDKConfig()
    gen = GoSDKGenerator(config)

    assert gen.language_name == "go"

    print("✓")
    return True


def main():
    """运行所有测试"""
    print("=" * 60)
    print("SDK 生成器单元测试")
    print("=" * 60)
    print()

    tests = [
        test_config,
        test_breaking_change_detector,
        test_version_manager,
        test_generators_base,
        test_python_generator,
        test_typescript_generator,
        test_java_generator,
        test_go_generator,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ 失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print()
    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
