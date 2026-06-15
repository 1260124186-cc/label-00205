"""
版本管理工具

基于 API 版本号和 Breaking Change 检测结果进行 semver 版本管理。
SDK 版本与 API v1 主版本对齐。
"""

import re
import json
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from loguru import logger

try:
    import semver
except ImportError:
    semver = None


class VersionBumpType(str, Enum):
    """版本升级类型"""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


@dataclass
class VersionInfo:
    """版本信息"""

    api_version: str
    sdk_version: str
    sdk_version_semver: Tuple[int, int, int]
    is_prerelease: bool = False
    prerelease_tag: Optional[str] = None

    def __str__(self) -> str:
        return self.sdk_version


class VersionManager:
    """版本管理器

    SDK 版本策略:
    - 主版本号: 与 API 主版本对齐（API v1 -> SDK 1.x.x）
    - 次版本号: API 新增功能（非破坏性）
    - 修订号: Bug 修复和小改进
    """

    def __init__(
        self,
        api_version: str = "v1",
        current_version: Optional[str] = None,
    ):
        """
        初始化版本管理器

        Args:
            api_version: API 版本（如 v1）
            current_version: 当前 SDK 版本
        """
        self.api_version = api_version
        self.api_major = self._parse_api_major(api_version)

        if current_version:
            self.current_version = self._parse_semver(current_version)
        else:
            self.current_version = (self.api_major, 0, 0)

    def _parse_api_major(self, api_version: str) -> int:
        """解析 API 版本的主版本号"""
        match = re.match(r"v(\d+)", api_version)
        if match:
            return int(match.group(1))
        return 1

    def _parse_semver(self, version: str) -> Tuple[int, int, int]:
        """解析语义化版本号"""
        version = version.strip()
        if version.startswith("v"):
            version = version[1:]

        parts = version.split(".")
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0

        return (major, minor, patch)

    def _format_version(self, version: Tuple[int, int, int]) -> str:
        """格式化版本号"""
        return f"{version[0]}.{version[1]}.{version[2]}"

    def determine_bump_type(
        self,
        has_breaking_changes: bool = False,
        has_new_features: bool = False,
        has_fixes: bool = True,
    ) -> VersionBumpType:
        """
        确定版本升级类型

        Args:
            has_breaking_changes: 是否有破坏性变更
            has_new_features: 是否有新功能
            has_fixes: 是否有修复

        Returns:
            版本升级类型
        """
        if has_breaking_changes:
            return VersionBumpType.MAJOR
        elif has_new_features:
            return VersionBumpType.MINOR
        else:
            return VersionBumpType.PATCH

    def bump_version(
        self,
        bump_type: Optional[VersionBumpType] = None,
        has_breaking_changes: bool = False,
        has_new_features: bool = False,
    ) -> VersionInfo:
        """
        升级版本

        Args:
            bump_type: 升级类型（可选，自动推断）
            has_breaking_changes: 是否有破坏性变更
            has_new_features: 是否有新功能

        Returns:
            新版本信息
        """
        if bump_type is None:
            bump_type = self.determine_bump_type(
                has_breaking_changes=has_breaking_changes,
                has_new_features=has_new_features,
            )

        major, minor, patch = self.current_version

        if bump_type == VersionBumpType.MAJOR:
            major += 1
            minor = 0
            patch = 0
        elif bump_type == VersionBumpType.MINOR:
            minor += 1
            patch = 0
        else:
            patch += 1

        new_version = (major, minor, patch)

        logger.info(
            f"版本升级: {self._format_version(self.current_version)} -> "
            f"{self._format_version(new_version)} ({bump_type.value})"
        )

        self.current_version = new_version

        return VersionInfo(
            api_version=self.api_version,
            sdk_version=self._format_version(new_version),
            sdk_version_semver=new_version,
        )

    def align_with_api_version(self) -> bool:
        """
        检查并对齐 SDK 主版本与 API 版本

        Returns:
            是否进行了版本对齐
        """
        current_major = self.current_version[0]

        if current_major != self.api_major:
            logger.warning(
                f"SDK 主版本 ({current_major}) 与 API 版本 ({self.api_major}) 不一致，"
                f"将 SDK 主版本调整为 {self.api_major}"
            )
            self.current_version = (self.api_major, 0, 0)
            return True

        return False

    def validate_version_alignment(self) -> bool:
        """
        验证 SDK 版本与 API 版本是否对齐

        Returns:
            是否对齐
        """
        return self.current_version[0] == self.api_major

    def get_current_version(self) -> VersionInfo:
        """获取当前版本信息"""
        return VersionInfo(
            api_version=self.api_version,
            sdk_version=self._format_version(self.current_version),
            sdk_version_semver=self.current_version,
        )

    def update_version_files(
        self,
        output_dir: str | Path,
        languages: Optional[list] = None,
    ) -> None:
        """
        更新各语言 SDK 版本文件

        Args:
            output_dir: 输出目录
            languages: 语言列表
        """
        output_dir = Path(output_dir)
        version = self._format_version(self.current_version)

        if languages is None:
            languages = ["python", "typescript", "java", "go"]

        for lang in languages:
            lang_dir = output_dir / lang
            if not lang_dir.exists():
                continue

            if lang == "python":
                self._update_python_version(lang_dir, version)
            elif lang == "typescript":
                self._update_typescript_version(lang_dir, version)
            elif lang == "java":
                self._update_java_version(lang_dir, version)
            elif lang == "go":
                self._update_go_version(lang_dir, version)

    def _update_python_version(self, lang_dir: Path, version: str) -> None:
        """更新 Python SDK 版本"""
        setup_py = lang_dir / "setup.py"
        if setup_py.exists():
            content = setup_py.read_text()
            content = re.sub(
                r'version="[^"]+"',
                f'version="{version}"',
                content,
            )
            setup_py.write_text(content)

        pyproject = lang_dir / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text()
            content = re.sub(
                r'version\s*=\s*"[^"]+"',
                f'version = "{version}"',
                content,
            )
            pyproject.write_text(content)

    def _update_typescript_version(self, lang_dir: Path, version: str) -> None:
        """更新 TypeScript SDK 版本"""
        pkg_json = lang_dir / "package.json"
        if pkg_json.exists():
            with open(pkg_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["version"] = version
            with open(pkg_json, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.write("\n")

    def _update_java_version(self, lang_dir: Path, version: str) -> None:
        """更新 Java SDK 版本"""
        pom_xml = lang_dir / "pom.xml"
        if pom_xml.exists():
            content = pom_xml.read_text()
            content = re.sub(
                r"<version>[^<]+</version>",
                f"<version>{version}</version>",
                content,
                count=1,
            )
            pom_xml.write_text(content)

    def _update_go_version(self, lang_dir: Path, version: str) -> None:
        """更新 Go SDK 版本（通过 version.go 文件）"""
        pkg_name = "boltprediction"
        version_file = lang_dir / pkg_name / "version.go"
        version_file.parent.mkdir(parents=True, exist_ok=True)

        content = f"""package {pkg_name}

// Version SDK 版本号
const Version = "{version}"
"""
        version_file.write_text(content)


def create_version_manager(
    api_version: str = "v1",
    current_version: Optional[str] = None,
) -> VersionManager:
    """
    便捷函数：创建版本管理器

    Args:
        api_version: API 版本
        current_version: 当前 SDK 版本

    Returns:
        版本管理器
    """
    return VersionManager(api_version, current_version)
