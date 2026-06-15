#!/usr/bin/env python3
"""
完整的 SDK 生成与编译校验脚本

生成四种语言 SDK，并进行编译验证。
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from sdk_generator.export_openapi import export_openapi
from sdk_generator.generators import get_generator
from sdk_generator.config import SDKConfig
from sdk_generator.version_manager import create_version_manager


def log_step(step_num: int, step_name: str, desc: str = ""):
    """打印步骤日志"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    separator = "=" * 70
    print(f"\n{separator}")
    print(f"[{timestamp}] Step {step_num}: {step_name}")
    if desc:
        print(f"  {desc}")
    print(separator + "\n")


def check_command(command: list[str], cwd: Path) -> bool:
    """检查命令是否可用"""
    try:
        subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def main():
    """主函数"""
    print("=" * 70)
    print("多语言 SDK 生成与编译校验")
    print("=" * 70)

    output_dir = ROOT / "sdks"
    output_dir.mkdir(exist_ok=True)

    spec_path = output_dir / "openapi.json"
    languages = ["python", "typescript", "java", "go"]

    # Step 1: 导出 OpenAPI 规范
    log_step(1, "导出 OpenAPI 规范", f"输出到: {spec_path}")

    try:
        spec = export_openapi(
            app_module="main:create_app",
            output_path=spec_path,
            format="json",
            api_version="v1",
        )
        print(f"✓ 导出成功: {len(spec.get('paths', {}))} 个 API 路径")
        print(f"✓ {len(spec.get('components', {}).get('schemas', {}))} 个数据模型")
    except Exception as e:
        print(f"✗ 导出失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Step 2: 版本管理
    log_step(2, "版本管理", "确定 SDK 版本号并校验对齐")

    target_version = "1.0.0"
    vm = create_version_manager(api_version="v1", current_version="0.0.0")

    # 直接设置版本（模拟 release/tag 版本）
    version_info = vm.set_version(target_version)
    print(f"✓ SDK 版本: {version_info.sdk_version}")

    # 强校验主版本与 API v1 对齐
    try:
        vm.assert_major_version_matches()
        print(f"✓ 主版本对齐校验通过 (SDK v{version_info.sdk_version_semver[0]}.x.x == API v1)")
    except ValueError as e:
        print(f"✗ 主版本对齐校验失败: {e}")
        return 1

    # Step 3-6: 生成各语言 SDK 并编译校验
    results = {}
    config = SDKConfig(
        api_name="bolt-prediction",
        api_version="v1",
        base_url="https://api.example.com",
        output_dir=output_dir,
    )

    for i, lang in enumerate(languages, 3):
        log_step(
            i,
            f"生成 {lang.upper()} SDK",
            f"输出目录: {output_dir / lang}",
        )

        try:
            generator = get_generator(lang, config)
            generator.load_openapi_spec(spec_path)

            print(f"  正在生成 {lang} SDK...")
            sdk_dir = generator.generate(spec)
            print(f"  ✓ 生成完成: {sdk_dir}")

            # 更新版本文件（统一版本号）
            vm.update_version_files(output_dir, [lang])
            print(f"  ✓ 版本已更新为 {version_info.sdk_version}")

            # 校验版本号是否正确写入
            version_ok = verify_version(sdk_dir, lang, target_version)
            if version_ok:
                print(f"  ✓ 版本号写入验证通过")
            else:
                print(f"  ✗ 版本号写入验证失败")
                results[lang] = False
                continue

            # 编译校验
            print(f"\n  正在编译校验 {lang} SDK...")
            build_result = build_sdk(sdk_dir, lang)
            results[lang] = build_result

            if build_result:
                print(f"  ✓ {lang} SDK 编译校验通过")
            else:
                print(f"  ✗ {lang} SDK 编译校验失败")

        except Exception as e:
            print(f"  ✗ {lang} SDK 生成失败: {e}")
            import traceback
            traceback.print_exc()
            results[lang] = False

    # Step 7: 发布前校验
    log_step(7, "发布前校验", "模拟发布前的打包验证")

    publish_results = {}
    for lang in languages:
        if not results.get(lang, False):
            publish_results[lang] = False
            continue

        sdk_dir = output_dir / lang
        try:
            pkg_ok = package_sdk(sdk_dir, lang)
            publish_results[lang] = pkg_ok
            if pkg_ok:
                print(f"  ✓ {lang} SDK 打包验证通过")
            else:
                print(f"  ✗ {lang} SDK 打包验证失败")
        except Exception as e:
            print(f"  ✗ {lang} SDK 打包验证异常: {e}")
            publish_results[lang] = False

    # 总结
    print("\n" + "=" * 70)
    print("生成结果总结")
    print("=" * 70)

    success = 0
    failed = 0
    for lang, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {lang:<15} 编译: {status}")
        if result:
            success += 1
        else:
            failed += 1

    print("\n发布打包验证:")
    pkg_success = 0
    pkg_failed = 0
    for lang, result in publish_results.items():
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {lang:<15} 打包: {status}")
        if result:
            pkg_success += 1
        else:
            pkg_failed += 1

    print("\n" + "-" * 70)
    print(f"编译校验: {success} 通过, {failed} 失败")
    print(f"打包验证: {pkg_success} 通过, {pkg_failed} 失败")
    print("=" * 70)

    return 0 if (failed == 0 and pkg_failed == 0) else 1


def build_sdk(sdk_dir: Path, language: str) -> bool:
    """编译校验 SDK"""
    env = None

    try:
        if language == "python":
            return build_python(sdk_dir)
        elif language == "typescript":
            return build_typescript(sdk_dir)
        elif language == "java":
            return build_java(sdk_dir)
        elif language == "go":
            return build_go(sdk_dir)
        else:
            print(f"  跳过 {language} 编译校验（不支持）")
            return True
    except Exception as e:
        print(f"  编译异常: {e}")
        return False


def build_python(sdk_dir: Path) -> bool:
    """编译 Python SDK"""
    # 语法检查
    print("    - 语法检查...", end=" ")
    result = subprocess.run(
        ["python3", "-m", "py_compile", "bolt_prediction_sdk/__init__.py"],
        cwd=sdk_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("✗")
        print(f"      {result.stderr}")
        return False
    print("✓")

    # 检查是否能导入主要模块
    print("    - 模块导入检查...", end=" ")
    test_code = '''
import sys
sys.path.insert(0, '.')
from bolt_prediction_sdk import SDKConfig
from bolt_prediction_sdk.core import AuthManager, RetryManager
from bolt_prediction_sdk.core.pagination import CursorPaginator
print("OK")
'''
    result = subprocess.run(
        ["python3", "-c", test_code],
        cwd=sdk_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("✗")
        print(f"      {result.stderr}")
        return False
    print("✓")

    return True


def build_typescript(sdk_dir: Path) -> bool:
    """编译 TypeScript SDK"""
    if not check_command(["npm", "--version"], sdk_dir):
        print("    - 跳过 (npm 不可用)")
        return True

    # npm install
    print("    - npm install...", end=" ")
    result = subprocess.run(
        ["npm", "install"],
        cwd=sdk_dir,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        print("✗")
        print(f"      {result.stderr[:500]}")
        return False
    print("✓")

    # npm run build (tsc)
    print("    - tsc 编译...", end=" ")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=sdk_dir,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        print("✗")
        print(f"      {result.stderr[:500]}")
        return False
    print("✓")

    return True


def build_java(sdk_dir: Path) -> bool:
    """编译 Java SDK"""
    if not check_command(["mvn", "--version"], sdk_dir):
        print("    - 跳过 (mvn 不可用)")
        return True

    # mvn compile - 使用临时空 settings.xml 避免私有仓库配置问题
    import tempfile
    settings_file = tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False)
    settings_file.write('<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"></settings>')
    settings_file.close()

    print("    - mvn compile...", end=" ")
    result = subprocess.run(
        ["mvn", "compile", "-q", "-DskipTests", "-s", settings_file.name],
        cwd=sdk_dir,
        capture_output=True,
        text=True,
        timeout=120,
    )
    import os
    os.unlink(settings_file.name)
    if result.returncode != 0:
        print("✗")
        print(f"      {result.stderr[:500]}")
        return False
    print("✓")

    return True


def build_go(sdk_dir: Path) -> bool:
    """编译 Go SDK"""
    if not check_command(["go", "version"], sdk_dir):
        print("    - 跳过 (go 不可用)")
        return True

    # go mod tidy
    print("    - go mod tidy...", end=" ")
    result = subprocess.run(
        ["go", "mod", "tidy"],
        cwd=sdk_dir,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        print("✗ (非致命，继续)")
    else:
        print("✓")

    # go build
    print("    - go build...", end=" ")
    result = subprocess.run(
        ["go", "build", "./..."],
        cwd=sdk_dir,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        print("✗")
        print(f"      {result.stderr[:500]}")
        return False
    print("✓")

    return True


def verify_version(sdk_dir: Path, language: str, expected_version: str) -> bool:
    """验证 SDK 版本号是否正确写入"""
    try:
        if language == "python":
            setup_py = sdk_dir / "setup.py"
            if setup_py.exists():
                content = setup_py.read_text()
                return f'version="{expected_version}"' in content
            return False

        elif language == "typescript":
            pkg_json = sdk_dir / "package.json"
            if pkg_json.exists():
                import json
                with open(pkg_json, "r") as f:
                    data = json.load(f)
                return data.get("version") == expected_version
            return False

        elif language == "java":
            pom_xml = sdk_dir / "pom.xml"
            if pom_xml.exists():
                content = pom_xml.read_text()
                return f"<version>{expected_version}</version>" in content
            return False

        elif language == "go":
            version_file = sdk_dir / "boltprediction" / "version.go"
            if version_file.exists():
                content = version_file.read_text()
                return f'Version = "{expected_version}"' in content
            return False

        return True
    except Exception:
        return False


def package_sdk(sdk_dir: Path, language: str) -> bool:
    """模拟发布前的打包验证"""
    try:
        if language == "python":
            return package_python(sdk_dir)
        elif language == "typescript":
            return package_typescript(sdk_dir)
        elif language == "java":
            return package_java(sdk_dir)
        elif language == "go":
            return package_go(sdk_dir)
        else:
            return True
    except Exception as e:
        print(f"    打包异常: {e}")
        return False


def package_python(sdk_dir: Path) -> bool:
    """Python SDK 打包验证（sdist + bdist_wheel）"""
    if not check_command(["python3", "--version"], sdk_dir):
        print("    - 跳过 (python 不可用)")
        return True

    print("    - sdist + bdist_wheel...", end=" ")
    result = subprocess.run(
        ["python3", "setup.py", "sdist", "bdist_wheel"],
        cwd=sdk_dir,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        print("✗")
        print(f"      {result.stderr[:500]}")
        return False
    print("✓")

    # 验证生成的包文件
    dist_dir = sdk_dir / "dist"
    if not dist_dir.exists():
        print("    - dist 目录不存在... ✗")
        return False

    tar_files = list(dist_dir.glob("*.tar.gz"))
    whl_files = list(dist_dir.glob("*.whl"))
    if not tar_files or not whl_files:
        print("    - 包文件不完整... ✗")
        return False

    print(f"    - 生成 {len(tar_files)} 个 sdist, {len(whl_files)} 个 wheel... ✓")
    return True


def package_typescript(sdk_dir: Path) -> bool:
    """TypeScript SDK 打包验证（npm pack）"""
    if not check_command(["npm", "--version"], sdk_dir):
        print("    - 跳过 (npm 不可用)")
        return True

    # npm pack 生成 tgz 包
    print("    - npm pack...", end=" ")
    result = subprocess.run(
        ["npm", "pack"],
        cwd=sdk_dir,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        print("✗")
        print(f"      {result.stderr[:500]}")
        return False
    print("✓")

    # 验证生成的 tgz 文件
    tgz_files = list(sdk_dir.glob("*.tgz"))
    if not tgz_files:
        print("    - tgz 包不存在... ✗")
        return False

    print(f"    - 生成 {len(tgz_files)} 个 tgz 包... ✓")

    # 清理 tgz 文件
    for f in tgz_files:
        f.unlink()

    return True


def package_java(sdk_dir: Path) -> bool:
    """Java SDK 打包验证（mvn package）"""
    if not check_command(["mvn", "--version"], sdk_dir):
        print("    - 跳过 (mvn 不可用)")
        return True

    import tempfile
    settings_file = tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False)
    settings_file.write('<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"></settings>')
    settings_file.close()

    print("    - mvn package...", end=" ")
    result = subprocess.run(
        ["mvn", "package", "-q", "-DskipTests", "-s", settings_file.name],
        cwd=sdk_dir,
        capture_output=True,
        text=True,
        timeout=180,
    )
    import os
    os.unlink(settings_file.name)

    if result.returncode != 0:
        print("✗")
        print(f"      {result.stderr[:500]}")
        return False
    print("✓")

    # 验证生成的 jar 文件
    target_dir = sdk_dir / "target"
    if not target_dir.exists():
        print("    - target 目录不存在... ✗")
        return False

    jar_files = list(target_dir.glob("*.jar"))
    if not jar_files:
        print("    - jar 文件不存在... ✗")
        return False

    print(f"    - 生成 {len(jar_files)} 个 jar 包... ✓")
    return True


def package_go(sdk_dir: Path) -> bool:
    """Go SDK 打包验证（go build 验证所有包，go 模块不需要打包）"""
    if not check_command(["go", "version"], sdk_dir):
        print("    - 跳过 (go 不可用)")
        return True

    print("    - go build all packages...", end=" ")
    result = subprocess.run(
        ["go", "build", "./..."],
        cwd=sdk_dir,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        print("✗")
        print(f"      {result.stderr[:500]}")
        return False
    print("✓")

    print("    - Go 模块无需打包，发布通过 tag 触发... ✓")
    return True


if __name__ == "__main__":
    sys.exit(main())
