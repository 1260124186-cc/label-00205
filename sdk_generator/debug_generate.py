#!/usr/bin/env python3
"""
调试脚本：直接生成 Python SDK 并测试方法签名
"""

import sys
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

# 直接修复 __version__ 的问题再导入
from app import __version__ as app_version

from sdk_generator.export_openapi import OpenAPIExporter
from sdk_generator.generators.python_sdk import PythonSDKGenerator
from sdk_generator.config import SDKConfig

# 1. 导出 OpenAPI 规范
print("=" * 60)
print("Step 1: 导出 OpenAPI 规范")
print("=" * 60)

output_dir = ROOT / "sdks"
output_dir.mkdir(exist_ok=True)

spec_path = output_dir / "openapi.json"

exporter = OpenAPIExporter("main:create_app")

# 手动加载并修复
import importlib
module = importlib.import_module("main")
app = module.create_app()

openapi_schema = app.openapi()
print(f"✓ 获取到 OpenAPI 规范，共 {len(openapi_schema.get('paths', {}))} 个路径")

# 保存
with open(spec_path, "w", encoding="utf-8") as f:
    json.dump(openapi_schema, f, ensure_ascii=False, indent=2)

# 2. 测试 Python SDK 生成
print("\n" + "=" * 60)
print("Step 2: 测试 Python SDK 方法生成")
print("=" * 60)

config = SDKConfig(
    api_name="bolt-prediction",
    api_version="v1",
    base_url="https://api.example.com",
    output_dir=output_dir,
)

generator = PythonSDKGenerator(config)
generator.openapi_spec = openapi_schema

# 解析路径
groups = generator._parse_paths()
print(f"✓ 解析到 {len(groups)} 个 API 分组")

# 遍历所有组，找出有问题的方法
errors = []
total_ops = 0

for group in groups:
    tag = group["tag"]
    ops = group["operations"]
    print(f"\n分组: {tag} ({len(ops)} 个操作)")
    
    for op in ops:
        total_ops += 1
        op_id = op.get("operation_id", "unknown")
        try:
            code = generator._generate_api_method(op)
        except Exception as e:
            errors.append({
                "tag": tag,
                "operation_id": op_id,
                "path": op.get("path", ""),
                "method": op.get("method", ""),
                "error": str(e),
            })
            print(f"  ✗ {op_id}: {e}")

print(f"\n总共 {total_ops} 个操作，{len(errors)} 个失败")

if errors:
    print("\n" + "=" * 60)
    print("错误详情")
    print("=" * 60)
    for err in errors[:5]:
        print(f"\n操作: {err['operation_id']}")
        print(f"路径: {err['method']} {err['path']}")
        print(f"错误: {err['error']}")

# 3. 尝试完整生成
print("\n" + "=" * 60)
print("Step 3: 尝试完整生成 Python SDK")
print("=" * 60)

try:
    sdk_dir = generator.generate(openapi_schema)
    print(f"✓ 完整生成成功: {sdk_dir}")
except Exception as e:
    print(f"✗ 完整生成失败: {e}")
    import traceback
    traceback.print_exc()
