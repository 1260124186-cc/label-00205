"""
证书管理模块

管理网关的 TLS/SSL 证书，用于 OPC UA 安全连接。
支持证书生成、加载、验证和自动续期。
"""

import os
import ssl
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from loguru import logger

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, ec
    from cryptography.hazmat.backends import default_backend
    _has_cryptography = True
except ImportError:
    _has_cryptography = False
    logger.warning("cryptography 库未安装，证书管理功能受限")


@dataclass
class CertificateInfo:
    """
    证书信息

    Attributes:
        cert_path: 证书文件路径
        key_path: 私钥文件路径
        subject: 证书主题
        issuer: 颁发者
        valid_from: 生效时间
        valid_to: 过期时间
        serial_number: 序列号
        fingerprint: 指纹
    """
    cert_path: str
    key_path: str
    subject: str = ""
    issuer: str = ""
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    serial_number: str = ""
    fingerprint: str = ""

    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        if self.valid_to is None:
            return False
        return datetime.now() > self.valid_to

    @property
    def days_remaining(self) -> int:
        """剩余天数"""
        if self.valid_to is None:
            return 0
        remaining = self.valid_to - datetime.now()
        return max(0, remaining.days)


class CertificateManager:
    """
    证书管理器

    管理 OPC UA 等协议需要的 TLS 证书，
    支持自签名证书生成、证书加载和过期监控。
    """

    def __init__(self, cert_dir: str = "./certs/gateway"):
        """
        初始化证书管理器

        Args:
            cert_dir: 证书存放目录
        """
        self._cert_dir = Path(cert_dir)
        self._cert_dir.mkdir(parents=True, exist_ok=True)
        self._certificates: Dict[str, CertificateInfo] = {}
        self._default_cert_name: str = "gateway"

        logger.info(f"证书管理器初始化完成，证书目录: {cert_dir}")

    # ============ 证书生成 ============

    def generate_self_signed(
        self,
        cert_name: str = "gateway",
        common_name: str = "Industrial Gateway",
        organization: str = "Gateway Corp",
        country: str = "CN",
        validity_days: int = 365 * 2,
        key_size: int = 2048,
    ) -> Optional[CertificateInfo]:
        """
        生成自签名证书

        Args:
            cert_name: 证书名称（用于文件名）
            common_name: 通用名称
            organization: 组织名称
            country: 国家代码
            validity_days: 有效期（天）
            key_size: 密钥长度

        Returns:
            CertificateInfo or None
        """
        if not _has_cryptography:
            logger.error("cryptography 库未安装，无法生成证书")
            return None

        try:
            cert_path = self._cert_dir / f"{cert_name}.crt"
            key_path = self._cert_dir / f"{cert_name}.key"

            # 生成私钥
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=default_backend(),
            )

            # 生成证书
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, country),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            ])

            now = datetime.utcnow()
            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(private_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(now)
                .not_valid_after(now + timedelta(days=validity_days))
                .add_extension(
                    x509.SubjectAlternativeName([
                        x509.DNSName("localhost"),
                        x509.IPAddress("127.0.0.1"),
                    ]),
                    critical=False,
                )
                .sign(private_key, hashes.SHA256(), default_backend())
            )

            # 写入证书文件
            cert_bytes = cert.public_bytes(serialization.Encoding.PEM)
            with open(cert_path, "wb") as f:
                f.write(cert_bytes)

            # 写入私钥文件
            key_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            with open(key_path, "wb") as f:
                f.write(key_bytes)

            # 设置文件权限
            try:
                os.chmod(key_path, 0o600)
            except OSError:
                pass

            cert_info = self._load_certificate_info(cert_name, str(cert_path), str(key_path))
            self._certificates[cert_name] = cert_info

            logger.info(
                f"自签名证书生成成功: {cert_name}, "
                f"有效期: {validity_days}天"
            )
            return cert_info

        except Exception as e:
            logger.error(f"生成自签名证书失败: {e}")
            return None

    # ============ 证书加载 ============

    def load_certificate(
        self,
        cert_name: str,
        cert_path: str,
        key_path: str,
    ) -> Optional[CertificateInfo]:
        """
        加载证书

        Args:
            cert_name: 证书名称
            cert_path: 证书文件路径
            key_path: 私钥文件路径

        Returns:
            CertificateInfo or None
        """
        try:
            cert_file = Path(cert_path)
            key_file = Path(key_path)

            if not cert_file.exists():
                logger.error(f"证书文件不存在: {cert_path}")
                return None

            if not key_file.exists():
                logger.error(f"私钥文件不存在: {key_path}")
                return None

            cert_info = self._load_certificate_info(cert_name, cert_path, key_path)
            self._certificates[cert_name] = cert_info

            logger.info(f"证书加载成功: {cert_name}")
            return cert_info

        except Exception as e:
            logger.error(f"加载证书失败: {e}")
            return None

    def _load_certificate_info(
        self,
        cert_name: str,
        cert_path: str,
        key_path: str,
    ) -> CertificateInfo:
        """
        加载证书详细信息

        Args:
            cert_name: 证书名称
            cert_path: 证书路径
            key_path: 私钥路径

        Returns:
            CertificateInfo
        """
        info = CertificateInfo(
            cert_path=cert_path,
            key_path=key_path,
        )

        if not _has_cryptography:
            return info

        try:
            with open(cert_path, "rb") as f:
                cert_data = f.read()

            cert = x509.load_pem_x509_certificate(cert_data, default_backend())

            info.subject = cert.subject.rfc4514_string()
            info.issuer = cert.issuer.rfc4514_string()
            info.valid_from = cert.not_valid_before_utc.replace(tzinfo=None)
            info.valid_to = cert.not_valid_after_utc.replace(tzinfo=None)
            info.serial_number = str(cert.serial_number)
            info.fingerprint = cert.fingerprint(hashes.SHA256()).hex()

        except Exception as e:
            logger.warning(f"解析证书详情失败: {e}")

        return info

    # ============ 证书查询 ============

    def get_certificate(self, cert_name: str) -> Optional[CertificateInfo]:
        """
        获取证书信息

        Args:
            cert_name: 证书名称

        Returns:
            CertificateInfo or None
        """
        return self._certificates.get(cert_name)

    def list_certificates(self) -> Dict[str, CertificateInfo]:
        """
        列出所有证书

        Returns:
            证书字典
        """
        return self._certificates.copy()

    def get_default_certificate(self) -> Optional[CertificateInfo]:
        """
        获取默认证书

        Returns:
            CertificateInfo or None
        """
        if self._default_cert_name in self._certificates:
            return self._certificates[self._default_cert_name]

        cert_path = self._cert_dir / f"{self._default_cert_name}.crt"
        key_path = self._cert_dir / f"{self._default_cert_name}.key"

        if cert_path.exists() and key_path.exists():
            return self.load_certificate(
                self._default_cert_name,
                str(cert_path),
                str(key_path),
            )

        return None

    # ============ SSL 上下文 ============

    def create_ssl_context(
        self,
        cert_name: Optional[str] = None,
        verify_mode: int = ssl.CERT_NONE,
    ) -> Optional[ssl.SSLContext]:
        """
        创建 SSL 上下文

        Args:
            cert_name: 证书名称（None则使用默认证书）
            verify_mode: 验证模式

        Returns:
            ssl.SSLContext or None
        """
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = verify_mode

            cert_info = None
            if cert_name:
                cert_info = self.get_certificate(cert_name)
            else:
                cert_info = self.get_default_certificate()

            if cert_info:
                context.load_cert_chain(
                    certfile=cert_info.cert_path,
                    keyfile=cert_info.key_path,
                )
                logger.debug(f"SSL 上下文已加载证书: {cert_name or 'default'}")

            return context

        except Exception as e:
            logger.error(f"创建 SSL 上下文失败: {e}")
            return None

    # ============ 证书验证 ============

    def validate_certificate(self, cert_name: str) -> Tuple[bool, str]:
        """
        验证证书

        Args:
            cert_name: 证书名称

        Returns:
            (是否有效, 消息)
        """
        cert = self.get_certificate(cert_name)
        if cert is None:
            return False, "证书不存在"

        if cert.is_expired:
            return False, f"证书已过期（过期时间: {cert.valid_to}）"

        if cert.days_remaining < 30:
            return True, f"证书即将过期（剩余 {cert.days_remaining} 天）"

        return True, "证书有效"

    def check_expiring_certificates(self, days: int = 30) -> list:
        """
        检查即将过期的证书

        Args:
            days: 提前警告天数

        Returns:
            即将过期的证书列表
        """
        expiring = []
        for name, cert in self._certificates.items():
            if cert.days_remaining <= days:
                expiring.append({
                    'name': name,
                    'days_remaining': cert.days_remaining,
                    'valid_to': cert.valid_to,
                    'is_expired': cert.is_expired,
                })
        return expiring

    # ============ 证书续期 ============

    def renew_certificate(
        self,
        cert_name: str,
        validity_days: int = 365 * 2,
    ) -> bool:
        """
        续期证书（重新生成自签名证书）

        Args:
            cert_name: 证书名称
            validity_days: 新的有效期（天）

        Returns:
            bool
        """
        if not _has_cryptography:
            logger.error("cryptography 库未安装，无法续期证书")
            return False

        cert = self.get_certificate(cert_name)
        if cert is None:
            logger.warning(f"证书不存在，无法续期: {cert_name}")
            return False

        # 备份旧证书
        try:
            old_cert_path = Path(cert.cert_path)
            old_key_path = Path(cert.key_path)
            backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")

            old_cert_path.rename(
                old_cert_path.with_suffix(f".crt.bak_{backup_suffix}")
            )
            old_key_path.rename(
                old_key_path.with_suffix(f".key.bak_{backup_suffix}")
            )
        except Exception as e:
            logger.warning(f"备份旧证书失败: {e}")

        # 重新生成
        try:
            # 从现有证书提取信息
            with open(cert.cert_path, "rb") as f:
                old_cert = x509.load_pem_x509_certificate(
                    f.read(), default_backend()
                )

            common_name = ""
            organization = ""
            country = ""

            for attr in old_cert.subject:
                if attr.oid == NameOID.COMMON_NAME:
                    common_name = attr.value
                elif attr.oid == NameOID.ORGANIZATION_NAME:
                    organization = attr.value
                elif attr.oid == NameOID.COUNTRY_NAME:
                    country = attr.value

            new_cert = self.generate_self_signed(
                cert_name=cert_name,
                common_name=common_name or "Industrial Gateway",
                organization=organization or "Gateway Corp",
                country=country or "CN",
                validity_days=validity_days,
            )

            if new_cert:
                logger.info(f"证书续期成功: {cert_name}, 新有效期: {validity_days}天")
                return True

        except Exception as e:
            logger.error(f"续期证书失败: {e}")

        return False

    # ============ 信任证书 ============

    def add_trusted_certificate(self, cert_path: str, cert_name: str) -> bool:
        """
        添加受信任的证书（用于验证服务器证书）

        Args:
            cert_path: 证书文件路径
            cert_name: 证书名称

        Returns:
            bool
        """
        try:
            src = Path(cert_path)
            if not src.exists():
                logger.error(f"证书文件不存在: {cert_path}")
                return False

            dest = self._cert_dir / "trusted" / f"{cert_name}.crt"
            dest.parent.mkdir(parents=True, exist_ok=True)

            import shutil
            shutil.copy2(src, dest)

            logger.info(f"已添加受信任证书: {cert_name}")
            return True

        except Exception as e:
            logger.error(f"添加受信任证书失败: {e}")
            return False

    def get_trusted_certs_dir(self) -> str:
        """
        获取受信任证书目录

        Returns:
            目录路径
        """
        trusted_dir = self._cert_dir / "trusted"
        trusted_dir.mkdir(parents=True, exist_ok=True)
        return str(trusted_dir)


# 全局单例
_cert_manager: Optional[CertificateManager] = None


def get_certificate_manager(cert_dir: str = "./certs/gateway") -> CertificateManager:
    """
    获取证书管理器单例

    Args:
        cert_dir: 证书目录（首次调用时使用）

    Returns:
        CertificateManager
    """
    global _cert_manager
    if _cert_manager is None:
        _cert_manager = CertificateManager(cert_dir)
    return _cert_manager
