#!/usr/bin/env python3
"""
SDK 生成器使用示例

演示如何使用 SDK 生成工具。
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def example_export_openapi():
    """示例：导出 OpenAPI 规范"""
    print("=" * 60)
    print("示例 1: 导出 OpenAPI 规范")
    print("=" * 60)

    from sdk_generator.export_openapi import export_openapi

    try:
        spec = export_openapi(
            app_module="main:create_app",
            output_path="./sdks/openapi.json",
            format="json",
            api_version="v1",
        )
        print(f"✓ 导出成功，共 {len(spec.get('paths', {}))} 个 API 路径")
        print(f"✓ 共 {len(spec.get('components', {}).get('schemas', {}))} 个 Schema")
    except Exception as e:
        print(f"✗ 导出失败: {e}")
        print("提示: 请确保 backend 目录在 Python 路径中")


def example_detect_breaking_changes():
    """示例：检测破坏性变更"""
    print("\n" + "=" * 60)
    print("示例 2: 检测 Breaking Changes")
    print("=" * 60)

    from sdk_generator.breaking_change import (
        detect_breaking_changes,
        BreakingChangeDetector,
    )

    old_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "v1"},
        "paths": {
            "/api/v1/items": {
                "get": {
                    "summary": "获取项目列表",
                    "parameters": [
                        {"name": "page", "in": "query", "schema": {"type": "integer"}}
                    ],
                    "responses": {
                        "200": {"description": "成功"}
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Item": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                    },
                    "required": ["id", "name"],
                }
            }
        }
    }

    new_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "v1"},
        "paths": {
            "/api/v1/items": {
                "get": {
                    "summary": "获取项目列表",
                    "parameters": [
                        {"name": "page", "in": "query", "schema": {"type": "integer"}},
                        {"name": "limit", "in": "query", "required": True, "schema": {"type": "integer"}},
                    ],
                    "responses": {
                        "200": {"description": "成功"}
                    }
                },
                "post": {
                    "summary": "创建项目",
                    "responses": {
                        "201": {"description": "创建成功"}
                    }
                }
            },
            "/api/v1/items/{id}": {
                "delete": {
                    "summary": "删除项目",
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {
                        "204": {"description": "删除成功"}
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Item": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["id"],
                },
                "NewItem": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                    "required": ["name"],
                }
            }
        }
    }

    detector = BreakingChangeDetector(old_spec, new_spec)
    report = detector.detect()

    print(f"总变更数: {report.total_changes}")
    print(f"破坏性变更: {len(report.breaking_changes)}")
    print(f"弃用变更: {len(report.deprecated_changes)}")
    print(f"新增变更: {len(report.additive_changes)}")

    if report.breaking_changes:
        print("\n破坏性变更列表:")
        for change in report.breaking_changes:
            print(f"  - [{change.type}] {change.description}")


def example_version_management():
    """示例：版本管理"""
    print("\n" + "=" * 60)
    print("示例 3: 版本管理")
    print("=" * 60)

    from sdk_generator.version_manager import (
        create_version_manager,
        VersionBumpType,
    )

    vm = create_version_manager(api_version="v1", current_version="1.2.3")
    current = vm.get_current_version()
    print(f"当前版本: {current.sdk_version}")
    print(f"API 版本对齐: {'是' if vm.validate_version_alignment() else '否'}")

    # Patch 升级
    new_ver = vm.bump_version(VersionBumpType.PATCH)
    print(f"\nPatch 升级后: {new_ver.sdk_version}")

    # Minor 升级
    vm2 = create_version_manager(api_version="v1", current_version="1.2.3")
    new_ver2 = vm2.bump_version(has_new_features=True)
    print(f"Minor 升级后: {new_ver2.sdk_version}")

    # Major 升级
    vm3 = create_version_manager(api_version="v1", current_version="1.2.3")
    new_ver3 = vm3.bump_version(has_breaking_changes=True)
    print(f"Major 升级后: {new_ver3.sdk_version}")

    # 版本对齐检查
    vm4 = create_version_manager(api_version="v2", current_version="1.2.3")
    aligned = vm4.align_with_api_version()
    print(f"\nAPI v2 对齐后: {vm4.get_current_version().sdk_version} (已对齐: {aligned})")


def example_config():
    """示例：配置管理"""
    print("\n" + "=" * 60)
    print("示例 4: SDK 配置")
    print("=" * 60)

    from sdk_generator.config import SDKConfig

    config = SDKConfig(
        api_name="bolt-prediction",
        api_version="v1",
        base_url="https://api.example.com",
    )

    print(f"API 名称: {config.api_name}")
    print(f"API 版本: {config.api_version}")
    print(f"基础 URL: {config.base_url}")
    print(f"支持语言: {', '.join(config.languages)}")
    print(f"最大重试次数: {config.retry_config['max_retries']}")
    print(f"鉴权方式: {config.auth_config['type']}")
    print(f"分页类型: {config.pagination_config['type']}")


def main():
    """主函数"""
    print("SDK 生成工具使用示例")
    print()

    example_config()
    example_detect_breaking_changes()
    example_version_management()

    try:
        example_export_openapi()
    except Exception as e:
        print(f"\n⚠️  OpenAPI 导出示例跳过: 需要完整的后端环境")
        print(f"   错误: {e}")

    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
