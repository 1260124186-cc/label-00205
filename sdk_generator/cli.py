"""
SDK 生成器命令行工具
"""

import sys
import json
from pathlib import Path
from typing import Optional

import click
from loguru import logger

from .config import SDKConfig
from .export_openapi import export_openapi
from .generators import get_generator
from .breaking_change import detect_breaking_changes
from .version_manager import create_version_manager, VersionBumpType
from .publisher import create_publisher, PublishConfig


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="启用详细日志")
@click.option("--config", "-c", type=str, help="配置文件路径")
def cli(verbose: bool, config: str):
    """多语言 OpenAPI SDK 自动生成与发布工具"""
    if not verbose:
        logger.remove()
        logger.add(sys.stderr, level="INFO")


@cli.command()
@click.option(
    "--app-module",
    default="main:create_app",
    help="FastAPI 应用模块路径 (如 main:create_app)",
)
@click.option(
    "--output",
    "-o",
    default="./openapi.json",
    help="输出文件路径",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "yaml", "yml"]),
    default="json",
    help="输出格式",
)
@click.option(
    "--api-version",
    default="v1",
    help="API 版本",
)
def export(app_module: str, output: str, format: str, api_version: str):
    """从 FastAPI 导出 OpenAPI 规范"""
    logger.info(f"从 {app_module} 导出 OpenAPI 规范")

    spec = export_openapi(app_module, output, format, api_version)
    logger.info(f"导出完成，共 {len(spec.get('paths', {}))} 个路径")


@cli.command()
@click.argument("openapi_spec", type=str)
@click.option(
    "--output",
    "-o",
    type=str,
    default="./sdks",
    help="SDK 输出目录",
)
@click.option(
    "--language",
    "-l",
    type=str,
    default=None,
    help="指定语言 (python/typescript/java/go)，不指定则生成所有语言",
)
@click.option(
    "--api-version",
    default="v1",
    help="API 版本",
)
@click.option(
    "--base-url",
    default="https://api.example.com",
    help="API 基础 URL",
)
def generate(
    openapi_spec: str,
    output: str,
    language: Optional[str],
    api_version: str,
    base_url: str,
):
    """生成多语言 SDK"""
    logger.info(f"从 {openapi_spec} 生成 SDK")

    config = SDKConfig(
        api_version=api_version,
        base_url=base_url,
        output_dir=Path(output),
    )

    if language:
        languages = [language]
    else:
        languages = config.languages

    spec_path = Path(openapi_spec)

    for lang in languages:
        try:
            generator = get_generator(lang, config)
            generator.load_openapi_spec(spec_path)
            sdk_dir = generator.generate(generator.openapi_spec)
            logger.success(f"{lang} SDK 生成完成: {sdk_dir}")
        except Exception as e:
            logger.error(f"{lang} SDK 生成失败: {e}")
            raise


@cli.command("breaking-change")
@click.argument("old_spec", type=str)
@click.argument("new_spec", type=str)
@click.option(
    "--output",
    "-o",
    type=str,
    default=None,
    help="报告输出路径",
)
@click.option(
    "--fail-on-breaking",
    is_flag=True,
    help="检测到破坏性变更时返回非零退出码",
)
def breaking_change(
    old_spec: str,
    new_spec: str,
    output: Optional[str],
    fail_on_breaking: bool,
):
    """检测两个 OpenAPI 规范之间的破坏性变更"""
    logger.info(f"检测 Breaking Changes: {old_spec} -> {new_spec}")

    report = detect_breaking_changes(old_spec, new_spec, output)

    click.echo(f"总变更数: {report.total_changes}")
    click.echo(f"破坏性变更: {len(report.breaking_changes)}")
    click.echo(f"弃用变更: {len(report.deprecated_changes)}")
    click.echo(f"新增变更: {len(report.additive_changes)}")

    if report.breaking_changes:
        click.echo("\n破坏性变更列表:")
        for change in report.breaking_changes[:10]:
            click.echo(f"  - [{change.type}] {change.description}")
        if len(report.breaking_changes) > 10:
            click.echo(f"  ... 还有 {len(report.breaking_changes) - 10} 项")

    if fail_on_breaking and report.has_breaking_changes:
        sys.exit(1)


@cli.command()
@click.option(
    "--current-version",
    type=str,
    default=None,
    help="当前 SDK 版本",
)
@click.option(
    "--api-version",
    default="v1",
    help="API 版本",
)
@click.option(
    "--bump-type",
    type=click.Choice(["major", "minor", "patch"]),
    default=None,
    help="手动指定升级类型",
)
@click.option(
    "--set",
    "set_version",
    type=str,
    default=None,
    help="直接设置版本号（替代 bump），例如 1.2.3",
)
@click.option(
    "--breaking-change-report",
    type=str,
    default=None,
    help="Breaking Change 报告路径",
)
@click.option(
    "--sdk-dir",
    type=str,
    default="./sdks",
    help="SDK 目录，用于更新版本文件",
)
@click.option(
    "--update-files",
    is_flag=True,
    help="更新 SDK 版本文件",
)
@click.option(
    "--assert-alignment",
    is_flag=True,
    help="强校验 SDK 主版本与 API 版本一致，不一致则报错退出",
)
def version(
    current_version: Optional[str],
    api_version: str,
    bump_type: Optional[str],
    set_version: Optional[str],
    breaking_change_report: Optional[str],
    sdk_dir: str,
    update_files: bool,
    assert_alignment: bool,
):
    """管理 SDK 版本（semver，与 API v1 对齐）"""
    vm = create_version_manager(api_version, current_version)

    if set_version:
        new_version = vm.set_version(set_version)
        click.echo(f"版本已设置: {new_version.sdk_version}")
        click.echo(f"API 版本: {new_version.api_version}")
    else:
        has_breaking = False
        has_new_features = False

        if breaking_change_report:
            with open(breaking_change_report, "r") as f:
                report_data = json.load(f)
            has_breaking = report_data.get("has_breaking_changes", False)
            has_new_features = len(report_data.get("additive_changes", [])) > 0

        if bump_type:
            bump = VersionBumpType(bump_type)
        else:
            bump = vm.determine_bump_type(
                has_breaking_changes=has_breaking,
                has_new_features=has_new_features,
            )

        new_version = vm.bump_version(bump)
        click.echo(f"新版本: {new_version.sdk_version} ({bump.value})")
        click.echo(f"API 版本: {new_version.api_version}")

    if assert_alignment:
        try:
            vm.assert_major_version_matches()
            click.echo("✓ 版本对齐校验通过")
        except ValueError as e:
            click.echo(f"✗ 版本对齐校验失败: {e}", err=True)
            sys.exit(1)
    elif not vm.validate_version_alignment():
        click.echo("警告: SDK 主版本与 API 版本不对齐")

    if update_files:
        vm.update_version_files(sdk_dir)
        click.echo("版本文件已更新")


@cli.command()
@click.argument("sdk_dir", type=str)
@click.option(
    "--language",
    "-l",
    type=str,
    default=None,
    help="指定语言，不指定则发布所有语言",
)
@click.option(
    "--version",
    "-v",
    type=str,
    required=True,
    help="发布版本",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="试运行模式，不实际发布",
)
@click.option(
    "--skip-tests",
    is_flag=True,
    help="跳过测试",
)
def publish(
    sdk_dir: str,
    language: Optional[str],
    version: str,
    dry_run: bool,
    skip_tests: bool,
):
    """发布 SDK 到私有仓库"""
    config = PublishConfig(dry_run=dry_run, skip_tests=skip_tests)
    publisher = create_publisher(config)

    sdk_path = Path(sdk_dir)

    if language:
        result = publisher.publish(sdk_path / language, language, version)
        if result:
            logger.success(f"{language} SDK 发布成功")
        else:
            logger.error(f"{language} SDK 发布失败")
            sys.exit(1)
    else:
        results = publisher.publish_all(sdk_path, version)
        success_count = sum(1 for r in results.values() if r)
        fail_count = sum(1 for r in results.values() if not r)

        click.echo(f"发布完成: {success_count} 成功, {fail_count} 失败")

        if fail_count > 0:
            sys.exit(1)


@cli.command()
@click.option(
    "--app-module",
    default="main:create_app",
    help="FastAPI 应用模块路径",
)
@click.option(
    "--output",
    "-o",
    type=str,
    default="./sdks",
    help="输出目录",
)
@click.option(
    "--old-spec",
    type=str,
    default=None,
    help="旧版 OpenAPI 规范（用于 Breaking Change 检测）",
)
@click.option(
    "--api-version",
    default="v1",
    help="API 版本",
)
@click.option(
    "--base-url",
    default="https://api.example.com",
    help="API 基础 URL",
)
@click.option(
    "--publish",
    is_flag=True,
    help="生成后自动发布",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="试运行模式",
)
def all(
    app_module: str,
    output: str,
    old_spec: Optional[str],
    api_version: str,
    base_url: str,
    publish: bool,
    dry_run: bool,
):
    """执行完整流程：导出 → 生成 → 检测 → 发布"""
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    spec_path = output_dir / "openapi.json"

    logger.info("Step 1: 导出 OpenAPI 规范")
    spec = export_openapi(app_module, spec_path, "json", api_version)

    if old_spec and Path(old_spec).exists():
        logger.info("Step 2: 检测 Breaking Changes")
        report_path = output_dir / "breaking-change-report.json"
        report = detect_breaking_changes(old_spec, spec_path, report_path)

        if report.has_breaking_changes:
            logger.warning(
                f"检测到 {len(report.breaking_changes)} 处破坏性变更"
            )
    else:
        logger.info("Step 2: 跳过 Breaking Change 检测（无旧版规范）")
        report = None

    logger.info("Step 3: 生成 SDK")
    config = SDKConfig(
        api_version=api_version,
        base_url=base_url,
        output_dir=output_dir,
    )

    for lang in config.languages:
        try:
            generator = get_generator(lang, config)
            generator.load_openapi_spec(spec_path)
            sdk_dir = generator.generate(generator.openapi_spec)
            logger.success(f"{lang} SDK 生成完成")
        except Exception as e:
            logger.error(f"{lang} SDK 生成失败: {e}")

    if publish:
        logger.info("Step 4: 发布 SDK")
        pub_config = PublishConfig(dry_run=dry_run)
        pub = create_publisher(pub_config)
        # 版本号从 spec 中获取
        version = spec.get("info", {}).get("version", "1.0.0")
        results = pub.publish_all(output_dir, version)
        success_count = sum(1 for r in results.values() if r)
        logger.info(f"发布完成: {success_count}/{len(results)} 成功")


def main():
    """主入口"""
    cli()


if __name__ == "__main__":
    main()
