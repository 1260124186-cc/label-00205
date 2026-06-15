import json
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from jose import JWTError, jwt
from jose.backends import RSAKey
from loguru import logger

from app.utils.database import get_db, JWTKeyStore
from app.utils.config import config


class JWTManager:
    """
    JWT 令牌管理器

    功能:
    1. 生成访问令牌和刷新令牌
    2. 验证令牌有效性
    3. 支持密钥轮换
    4. 支持 RS256/HS256 算法
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        self._current_kid: Optional[str] = None
        self._signing_key: Optional[Any] = None
        self._public_keys: Dict[str, Any] = {}
        self._init_keys()

    def _init_keys(self) -> None:
        """初始化签名密钥"""
        try:
            with get_db() as db:
                if db is None:
                    self._fallback_to_config_key()
                    return

                current_key = db.query(JWTKeyStore).filter(
                    JWTKeyStore.is_current == True,
                    JWTKeyStore.status == 'active'
                ).first()

                if current_key:
                    self._current_kid = current_key.kid
                    self._load_key(current_key)
                    self._load_all_public_keys(db)
                else:
                    self._generate_initial_key(db)
        except Exception as e:
            logger.warning(f"JWT 密钥加载失败，使用配置密钥: {e}")
            self._fallback_to_config_key()

    def _fallback_to_config_key(self) -> None:
        """使用配置中的密钥作为后备"""
        sso_config = config.get('sso', {})
        secret_key = sso_config.get('jwt_secret', secrets.token_hex(32))
        algorithm = sso_config.get('jwt_algorithm', 'HS256')

        self._current_kid = 'default'
        self._signing_key = secret_key
        self._public_keys = {'default': secret_key}
        self._default_algorithm = algorithm

    def _load_key(self, key_record: JWTKeyStore) -> None:
        """加载单个密钥"""
        if key_record.key_type == 'asymmetric':
            if key_record.private_key:
                try:
                    self._signing_key = RSAKey.import_key(key_record.private_key)
                except Exception as e:
                    logger.error(f"加载私钥失败: {e}")
        else:
            if key_record.secret_key:
                self._signing_key = key_record.secret_key

    def _load_all_public_keys(self, db) -> None:
        """加载所有公钥用于验证"""
        try:
            keys = db.query(JWTKeyStore).filter(
                JWTKeyStore.status.in_(['active', 'rotating'])
            ).all()

            for key in keys:
                if key.key_type == 'asymmetric' and key.public_key:
                    try:
                        pub_key = RSAKey.import_key(key.public_key)
                        self._public_keys[key.kid] = pub_key
                    except Exception as e:
                        logger.warning(f"加载公钥失败 kid={key.kid}: {e}")
                elif key.secret_key:
                    self._public_keys[key.kid] = key.secret_key
        except Exception as e:
            logger.error(f"加载公钥列表失败: {e}")

    def _generate_initial_key(self, db) -> None:
        """生成初始签名密钥"""
        try:
            sso_config = config.get('sso', {})
            algorithm = sso_config.get('jwt_algorithm', 'RS256')

            if algorithm.startswith('RS'):
                kid, private_pem, public_pem = self._generate_rsa_key()
                key_record = JWTKeyStore(
                    kid=kid,
                    algorithm=algorithm,
                    key_type='asymmetric',
                    private_key=private_pem,
                    public_key=public_pem,
                    status='active',
                    is_current=True,
                    activated_at=datetime.now(),
                )
            else:
                kid = secrets.token_hex(16)
                secret = secrets.token_hex(32)
                key_record = JWTKeyStore(
                    kid=kid,
                    algorithm=algorithm,
                    key_type='symmetric',
                    secret_key=secret,
                    status='active',
                    is_current=True,
                    activated_at=datetime.now(),
                )

            db.add(key_record)
            db.flush()

            self._current_kid = kid
            self._load_key(key_record)
            self._load_all_public_keys(db)

            logger.info(f"初始 JWT 密钥已生成 kid={kid}, algorithm={algorithm}")
        except Exception as e:
            logger.error(f"生成初始 JWT 密钥失败: {e}")
            self._fallback_to_config_key()

    @staticmethod
    def _generate_rsa_key() -> Tuple[str, str, str]:
        """生成 RSA 密钥对"""
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

        kid = hashlib.sha256(public_pem.encode()).hexdigest()[:16]

        return kid, private_pem, public_pem

    def create_access_token(
        self,
        subject: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """
        创建访问令牌

        Args:
            subject: 令牌主体（用户信息）
            expires_delta: 过期时间增量
            extra_claims: 额外声明

        Returns:
            (token, jti): 令牌字符串和令牌ID
        """
        sso_config = config.get('sso', {})
        if expires_delta is None:
            access_token_ttl = sso_config.get('access_token_ttl', 3600)
            expires_delta = timedelta(seconds=access_token_ttl)

        jti = secrets.token_hex(16)
        now = datetime.utcnow()

        claims = {
            'sub': json.dumps(subject, ensure_ascii=False),
            'iat': int(now.timestamp()),
            'exp': int((now + expires_delta).timestamp()),
            'jti': jti,
            'type': 'access',
        }

        if extra_claims:
            claims.update(extra_claims)

        algorithm = sso_config.get('jwt_algorithm', 'HS256')
        token = jwt.encode(claims, self._signing_key, algorithm=algorithm, headers={'kid': self._current_kid})

        return token, jti

    def create_refresh_token(
        self,
        user_id: int,
        tenant_id: int,
        session_id: str,
        expires_delta: Optional[timedelta] = None,
    ) -> Tuple[str, str]:
        """
        创建刷新令牌

        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            session_id: 会话ID
            expires_delta: 过期时间增量

        Returns:
            (token, jti): 令牌字符串和令牌ID
        """
        sso_config = config.get('sso', {})
        if expires_delta is None:
            refresh_token_ttl = sso_config.get('refresh_token_ttl', 604800)
            expires_delta = timedelta(seconds=refresh_token_ttl)

        jti = secrets.token_hex(16)
        now = datetime.utcnow()

        claims = {
            'sub': json.dumps({'user_id': user_id, 'tenant_id': tenant_id}),
            'iat': int(now.timestamp()),
            'exp': int((now + expires_delta).timestamp()),
            'jti': jti,
            'type': 'refresh',
            'session_id': session_id,
        }

        algorithm = sso_config.get('jwt_algorithm', 'HS256')
        token = jwt.encode(claims, self._signing_key, algorithm=algorithm, headers={'kid': self._current_kid})

        return token, jti

    def verify_token(self, token: str, token_type: str = 'access') -> Optional[Dict[str, Any]]:
        """
        验证 JWT 令牌

        Args:
            token: JWT 令牌字符串
            token_type: 令牌类型 access/refresh

        Returns:
            解码后的令牌声明，如果无效返回 None
        """
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get('kid', 'default')

            public_key = self._public_keys.get(kid)
            if public_key is None:
                logger.warning(f"未知的 kid: {kid}")
                return None

            algorithm = unverified_header.get('alg', 'HS256')
            payload = jwt.decode(token, public_key, algorithms=[algorithm])

            if payload.get('type') != token_type:
                logger.warning(f"令牌类型不匹配: 期望 {token_type}, 实际 {payload.get('type')}")
                return None

            return payload

        except JWTError as e:
            logger.debug(f"JWT 验证失败: {e}")
            return None
        except Exception as e:
            logger.warning(f"JWT 验证异常: {e}")
            return None

    def decode_token_unverified(self, token: str) -> Optional[Dict[str, Any]]:
        """
        不解密验证地解码令牌（仅用于获取声明）

        Args:
            token: JWT 令牌字符串

        Returns:
            解码后的令牌声明
        """
        try:
            return jwt.get_unverified_claims(token)
        except JWTError:
            return None

    def rotate_keys(self) -> bool:
        """
        密钥轮换

        Returns:
            是否轮换成功
        """
        try:
            with get_db() as db:
                if db is None:
                    return False

                old_key = db.query(JWTKeyStore).filter(
                    JWTKeyStore.is_current == True,
                    JWTKeyStore.status == 'active'
                ).first()

                if old_key:
                    old_key.status = 'rotating'
                    old_key.is_current = False
                    old_key.rotated_at = datetime.now()

                sso_config = config.get('sso', {})
                algorithm = sso_config.get('jwt_algorithm', 'RS256')

                if algorithm.startswith('RS'):
                    kid, private_pem, public_pem = self._generate_rsa_key()
                    new_key = JWTKeyStore(
                        kid=kid,
                        algorithm=algorithm,
                        key_type='asymmetric',
                        private_key=private_pem,
                        public_key=public_pem,
                        status='active',
                        is_current=True,
                        activated_at=datetime.now(),
                    )
                else:
                    kid = secrets.token_hex(16)
                    secret = secrets.token_hex(32)
                    new_key = JWTKeyStore(
                        kid=kid,
                        algorithm=algorithm,
                        key_type='symmetric',
                        secret_key=secret,
                        status='active',
                        is_current=True,
                        activated_at=datetime.now(),
                    )

                db.add(new_key)
                db.flush()

                self._current_kid = kid
                self._load_key(new_key)
                self._load_all_public_keys(db)

                logger.info(f"JWT 密钥轮换完成，新 kid={kid}")
                return True

        except Exception as e:
            logger.error(f"JWT 密钥轮换失败: {e}")
            return False

    def get_jwks(self) -> Dict[str, Any]:
        """
        获取 JWKS (JSON Web Key Set)

        Returns:
            JWKS 字典
        """
        keys = []
        for kid, key in self._public_keys.items():
            if hasattr(key, 'to_dict'):
                key_dict = key.to_dict()
                key_dict['kid'] = kid
                key_dict['use'] = 'sig'
                keys.append(key_dict)

        return {'keys': keys}

    def get_subject(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        从令牌载荷中解析 subject

        Args:
            payload: JWT 载荷

        Returns:
            subject 字典
        """
        try:
            sub_str = payload.get('sub')
            if sub_str:
                return json.loads(sub_str)
        except (json.JSONDecodeError, TypeError):
            pass
        return None


jwt_manager = JWTManager()
