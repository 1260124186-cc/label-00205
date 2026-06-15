"""
SDK 发布工具

支持发布到私有 npm/Maven/PyPI 仓库。
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass
from loguru import logger


@dataclass
class PublishConfig:
    """发布配置"""

    dry_run: bool = False
    skip_tests: bool = False
    verbose: bool = False

    npm_registry: Optional[str] = None
    npm_token: Optional[str] = None

    maven_repo_url: Optional[str] = None
    maven_snapshot_url: Optional[str] = None
    maven_username: Optional[str] = None
    maven_password: Optional[str] = None

    pypi_repo_url: Optional[str] = None
    pypi_username: Optional[str] = None
    pypi_password: Optional[str] = None

    @classmethod
    def from_env(cls) -> "PublishConfig":
        """从环境变量加载配置"""
        return cls(
            dry_run=os.getenv("PUBLISH_DRY_RUN", "false").lower() == "true",
            skip_tests=os.getenv("PUBLISH_SKIP_TESTS", "false").lower() == "true",
            npm_registry=os.getenv("NPM_REGISTRY"),
            npm_token=os.getenv("NPM_TOKEN"),
            maven_repo_url=os.getenv("MAVEN_REPO_URL"),
            maven_snapshot_url=os.getenv("MAVEN_SNAPSHOT_URL"),
            maven_username=os.getenv("MAVEN_USERNAME"),
            maven_password=os.getenv("MAVEN_PASSWORD"),
            pypi_repo_url=os.getenv("PYPI_REPO_URL"),
            pypi_username=os.getenv("PYPI_USERNAME"),
            pypi_password=os.getenv("PYPI_PASSWORD"),
        )


class SDKPublisher:
    """SDK 发布器"""

    def __init__(self, config: Optional[PublishConfig] = None):
        """
        初始化发布器

        Args:
            config: 发布配置
        """
        self.config = config or PublishConfig.from_env()

    def publish(
        self,
        sdk_dir: str | Path,
        language: str,
        version: str,
    ) -> bool:
        """
        发布 SDK

        Args:
            sdk_dir: SDK 目录
            language: 语言类型
            version: 版本号

        Returns:
            是否发布成功
        """
        sdk_dir = Path(sdk_dir)
        logger.info(f"开始发布 {language} SDK v{version}，目录: {sdk_dir}")

        if self.config.dry_run:
            logger.info(f"[DRY RUN] 将发布 {language} SDK v{version}")
            return True

        try:
            if language == "python":
                return self._publish_python(sdk_dir, version)
            elif language == "typescript":
                return self._publish_typescript(sdk_dir, version)
            elif language == "java":
                return self._publish_java(sdk_dir, version)
            elif language == "go":
                return self._publish_go(sdk_dir, version)
            else:
                logger.error(f"不支持的语言: {language}")
                return False
        except Exception as e:
            logger.error(f"发布失败: {e}")
            return False

    def _publish_python(self, sdk_dir: Path, version: str) -> bool:
        """发布 Python SDK 到私有 PyPI"""
        logger.info("构建 Python SDK 包...")

        env = os.environ.copy()

        if self.config.pypi_repo_url:
            env["TWINE_REPOSITORY_URL"] = self.config.pypi_repo_url
        if self.config.pypi_username:
            env["TWINE_USERNAME"] = self.config.pypi_username
        if self.config.pypi_password:
            env["TWINE_PASSWORD"] = self.config.pypi_password

        try:
            result = subprocess.run(
                ["python", "setup.py", "sdist", "bdist_wheel"],
                cwd=sdk_dir,
                capture_output=True,
                text=True,
                env=env,
            )

            if result.returncode != 0:
                logger.error(f"构建失败: {result.stderr}")
                return False

            logger.info("Python 包构建成功")

            if self.config.pypi_repo_url:
                logger.info("上传到 PyPI 仓库...")
                result = subprocess.run(
                    ["twine", "upload", "dist/*"],
                    cwd=sdk_dir,
                    capture_output=True,
                    text=True,
                    env=env,
                )

                if result.returncode != 0:
                    logger.error(f"上传失败: {result.stderr}")
                    return False

                logger.info("Python SDK 发布成功")
            else:
                logger.warning("未配置 PyPI 仓库，跳过上传")

            return True

        except Exception as e:
            logger.error(f"Python SDK 发布失败: {e}")
            return False

    def _publish_typescript(self, sdk_dir: Path, version: str) -> bool:
        """发布 TypeScript SDK 到私有 npm"""
        logger.info("构建 TypeScript SDK 包...")

        env = os.environ.copy()

        try:
            result = subprocess.run(
                ["npm", "install"],
                cwd=sdk_dir,
                capture_output=True,
                text=True,
                env=env,
            )
            if result.returncode != 0:
                logger.error(f"依赖安装失败: {result.stderr}")
                return False

            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=sdk_dir,
                capture_output=True,
                text=True,
                env=env,
            )
            if result.returncode != 0:
                logger.error(f"构建失败: {result.stderr}")
                return False

            logger.info("TypeScript 包构建成功")

            if self.config.npm_token and self.config.npm_registry:
                logger.info("发布到 npm 仓库...")

                npmrc_path = sdk_dir / ".npmrc"
                with open(npmrc_path, "w") as f:
                    f.write(f"//{self._get_registry_host(self.config.npm_registry)}/:_authToken={self.config.npm_token}\n")
                    f.write(f"registry={self.config.npm_registry}\n")

                result = subprocess.run(
                    ["npm", "publish", "--access", "restricted"],
                    cwd=sdk_dir,
                    capture_output=True,
                    text=True,
                    env=env,
                )

                if result.returncode != 0:
                    logger.error(f"发布失败: {result.stderr}")
                    return False

                logger.info("TypeScript SDK 发布成功")
            else:
                logger.warning("未配置 npm 仓库，跳过发布")

            return True

        except Exception as e:
            logger.error(f"TypeScript SDK 发布失败: {e}")
            return False

    def _get_registry_host(self, registry_url: str) -> str:
        """获取 registry 主机名"""
        from urllib.parse import urlparse
        parsed = urlparse(registry_url)
        return parsed.netloc

    def _publish_java(self, sdk_dir: Path, version: str) -> bool:
        """发布 Java SDK 到私有 Maven 仓库"""
        logger.info("构建 Java SDK 包...")

        env = os.environ.copy()

        if self.config.maven_username:
            env["MAVEN_USERNAME"] = self.config.maven_username
        if self.config.maven_password:
            env["MAVEN_PASSWORD"] = self.config.maven_password

        try:
            is_snapshot = "SNAPSHOT" in version.upper()

            goals = ["clean", "package"]
            if self.config.maven_repo_url:
                goals.append("deploy")

            result = subprocess.run(
                ["mvn"] + goals + ["-B", "-s", ".mvn/settings.xml"],
                cwd=sdk_dir,
                capture_output=True,
                text=True,
                env=env,
            )

            if result.returncode != 0:
                logger.error(f"构建/发布失败: {result.stderr}")
                return False

            if "deploy" in goals:
                logger.info("Java SDK 发布成功")
            else:
                logger.info("Java SDK 构建成功")

            return True

        except Exception as e:
            logger.error(f"Java SDK 发布失败: {e}")
            return False

    def _publish_go(self, sdk_dir: Path, version: str) -> bool:
        """发布 Go SDK（打 tag 推送到 Git 仓库）"""
        logger.info(f"准备 Go SDK v{version} 发布...")

        try:
            result = subprocess.run(
                ["go", "build", "./..."],
                cwd=sdk_dir,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.error(f"Go 构建失败: {result.stderr}")
                return False

            logger.info("Go SDK 构建成功")

            if self.config.verbose:
                logger.info("Go SDK 通过 Git Tag 发布，需要手动打 tag 推送")
                logger.info(f"  git tag v{version}")
                logger.info(f"  git push origin v{version}")

            return True

        except Exception as e:
            logger.error(f"Go SDK 发布失败: {e}")
            return False

    def publish_all(
        self,
        output_dir: str | Path,
        version: str,
        languages: Optional[List[str]] = None,
    ) -> Dict[str, bool]:
        """
        发布所有语言的 SDK

        Args:
            output_dir: 输出根目录
            version: 版本号
            languages: 语言列表

        Returns:
            各语言发布结果
        """
        output_dir = Path(output_dir)

        if languages is None:
            languages = ["python", "typescript", "java", "go"]

        results = {}
        for lang in languages:
            lang_dir = output_dir / lang
            if lang_dir.exists():
                results[lang] = self.publish(lang_dir, lang, version)
            else:
                logger.warning(f"{lang} SDK 目录不存在，跳过")
                results[lang] = False

        return results


def create_publisher(config: Optional[PublishConfig] = None) -> SDKPublisher:
    """
    便捷函数：创建发布器

    Args:
        config: 发布配置

    Returns:
        SDK 发布器
    """
    return SDKPublisher(config)
