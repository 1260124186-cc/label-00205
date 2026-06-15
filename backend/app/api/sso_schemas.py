"""
SSO 和认证相关 Schemas

定义 SSO 管理、服务账号、会话管理等接口的数据模型。
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field, validator


# ============================================================
# SSO Provider Schemas
# ============================================================

class SSOProviderCreate(BaseModel):
    """创建 SSO 提供者请求"""
    provider_name: str = Field(..., max_length=100, description="提供者名称")
    provider_type: str = Field(..., description="类型: oidc 或 saml")
    is_default: Optional[bool] = Field(False, description="是否为默认提供者")

    # OIDC 配置
    issuer_url: Optional[str] = Field(None, max_length=500, description="Issuer URL")
    client_id: Optional[str] = Field(None, max_length=200, description="客户端ID")
    client_secret: Optional[str] = Field(None, max_length=500, description="客户端密钥")
    authorization_endpoint: Optional[str] = Field(None, max_length=500, description="授权端点")
    token_endpoint: Optional[str] = Field(None, max_length=500, description="令牌端点")
    userinfo_endpoint: Optional[str] = Field(None, max_length=500, description="用户信息端点")
    jwks_uri: Optional[str] = Field(None, max_length=500, description="JWKS URI")

    # SAML 配置
    saml_entity_id: Optional[str] = Field(None, max_length=500, description="SAML 实体ID")
    saml_sso_url: Optional[str] = Field(None, max_length=500, description="SAML SSO URL")
    saml_slo_url: Optional[str] = Field(None, max_length=500, description="SAML SLO URL")
    saml_idp_certificate: Optional[str] = Field(None, description="IdP 证书")
    saml_name_id_format: Optional[str] = Field(
        'urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified',
        description="NameID 格式"
    )

    # 属性映射
    attribute_mapping: Optional[Dict[str, str]] = Field(
        None,
        description="属性映射: {本地字段: IdP字段}"
    )

    # 角色映射
    role_mapping: Optional[Dict[str, str]] = Field(
        None,
        description="角色映射: {IdP组名: 本地角色}"
    )

    # JIT 配置
    jit_enabled: Optional[bool] = Field(True, description="是否启用 JIT 建号")
    jit_default_role: Optional[str] = Field('viewer', description="JIT 默认角色")

    # 其他
    scopes: Optional[List[str]] = Field(
        None,
        description="请求的 scope 列表"
    )
    auto_create_users: Optional[bool] = Field(True, description="是否自动创建用户")
    sync_groups: Optional[bool] = Field(False, description="是否同步用户组")

    @validator('provider_type')
    def validate_provider_type(cls, v):
        if v not in ('oidc', 'saml'):
            raise ValueError('provider_type 必须是 oidc 或 saml')
        return v

    @validator('jit_default_role')
    def validate_default_role(cls, v):
        if v not in ('tenant_admin', 'admin', 'operator', 'viewer'):
            raise ValueError('jit_default_role 必须是 tenant_admin/admin/operator/viewer')
        return v


class SSOProviderUpdate(BaseModel):
    """更新 SSO 提供者请求"""
    provider_name: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, description="状态: active/disabled")
    is_default: Optional[bool] = None
    issuer_url: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    authorization_endpoint: Optional[str] = None
    token_endpoint: Optional[str] = None
    userinfo_endpoint: Optional[str] = None
    jwks_uri: Optional[str] = None
    saml_entity_id: Optional[str] = None
    saml_sso_url: Optional[str] = None
    saml_slo_url: Optional[str] = None
    saml_idp_certificate: Optional[str] = None
    saml_name_id_format: Optional[str] = None
    attribute_mapping: Optional[Dict[str, str]] = None
    role_mapping: Optional[Dict[str, str]] = None
    jit_enabled: Optional[bool] = None
    jit_default_role: Optional[str] = None
    scopes: Optional[List[str]] = None
    auto_create_users: Optional[bool] = None
    sync_groups: Optional[bool] = None
    sort_order: Optional[int] = None


class SSOProviderResponse(BaseModel):
    """SSO 提供者响应"""
    id: int
    tenant_id: int
    provider_name: str
    provider_type: str
    status: str
    is_default: bool = False
    issuer_url: Optional[str] = None
    client_id: Optional[str] = None
    authorization_endpoint: Optional[str] = None
    token_endpoint: Optional[str] = None
    userinfo_endpoint: Optional[str] = None
    jwks_uri: Optional[str] = None
    saml_entity_id: Optional[str] = None
    saml_sso_url: Optional[str] = None
    saml_slo_url: Optional[str] = None
    saml_name_id_format: Optional[str] = None
    attribute_mapping: Optional[Dict[str, str]] = None
    role_mapping: Optional[Dict[str, str]] = None
    jit_enabled: bool = True
    jit_default_role: str = 'viewer'
    scopes: Optional[List[str]] = None
    auto_create_users: bool = True
    sync_groups: bool = False
    sort_order: int = 0
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


class SSOProviderListResponse(BaseModel):
    """SSO 提供者列表响应"""
    items: List[SSOProviderResponse]
    total: int


# ============================================================
# SSO 登录相关 Schemas
# ============================================================

class SSOLoginRequest(BaseModel):
    """SSO 登录请求"""
    provider_id: Optional[int] = Field(None, description="SSO 提供者ID")
    redirect_uri: str = Field(..., description="回调地址")
    relay_state: Optional[str] = Field(None, description="中继状态")


class SSOLoginResponse(BaseModel):
    """SSO 登录响应"""
    authorization_url: str
    state: Optional[str] = None
    nonce: Optional[str] = None
    provider_id: int
    provider_type: str


class SSOCallbackRequest(BaseModel):
    """SSO 回调请求"""
    code: Optional[str] = Field(None, description="授权码 (OIDC)")
    state: Optional[str] = Field(None, description="状态参数")
    saml_response: Optional[str] = Field(None, description="SAML Response")
    relay_state: Optional[str] = Field(None, description="中继状态")


class SSOTokenResponse(BaseModel):
    """SSO 登录成功令牌响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    user_info: Dict[str, Any]
    session_id: int
    is_new_user: bool = False


class SSOUserInfo(BaseModel):
    """SSO 用户信息"""
    idp_user_id: str
    idp_username: str
    idp_email: Optional[str] = None
    idp_display_name: Optional[str] = None
    idp_groups: List[str] = []


# ============================================================
# 用户会话 Schemas
# ============================================================

class UserSessionResponse(BaseModel):
    """用户会话响应"""
    id: int
    tenant_id: int
    user_id: int
    username: str
    session_type: str
    status: str
    device_info: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    auth_method: Optional[str] = None
    sso_provider_id: Optional[int] = None

    class Config:
        from_attributes = True


class UserSessionListResponse(BaseModel):
    """用户会话列表响应"""
    items: List[UserSessionResponse]
    total: int


class SessionRevokeRequest(BaseModel):
    """会话撤销请求"""
    reason: Optional[str] = Field(None, max_length=500, description="撤销原因")
    revoked_by: Optional[str] = Field(None, max_length=100, description="撤销人")


class TokenRefreshRequest(BaseModel):
    """令牌刷新请求"""
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """令牌刷新响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class RevokeUserSessionsRequest(BaseModel):
    """批量撤销用户会话请求"""
    user_id: Optional[int] = Field(None, description="用户ID，不传则撤销当前用户所有会话")
    reason: Optional[str] = Field(None, max_length=500, description="撤销原因")
    include_current: Optional[bool] = Field(False, description="是否包含当前会话")


# ============================================================
# 服务账号 Schemas
# ============================================================

class ServiceAccountCreate(BaseModel):
    """创建服务账号请求"""
    account_name: str = Field(..., max_length=100, description="账号名称")
    display_name: Optional[str] = Field(None, max_length=200, description="显示名称")
    description: Optional[str] = Field(None, max_length=1000, description="描述")
    role: str = Field('viewer', description="角色: tenant_admin/admin/operator/viewer")
    rate_limit: int = Field(1000, description="速率限制（次/小时）")
    allowed_ips: Optional[List[str]] = Field(None, description="IP 白名单")
    allowed_scopes: Optional[List[str]] = Field(None, description="允许的 scopes")
    expires_in_days: Optional[int] = Field(None, description="过期天数")
    owner_id: Optional[int] = Field(None, description="负责人用户ID")
    owner_name: Optional[str] = Field(None, max_length=100, description="负责人姓名")
    owner_email: Optional[str] = Field(None, max_length=200, description="负责人邮箱")

    @validator('role')
    def validate_role(cls, v):
        if v not in ('tenant_admin', 'admin', 'operator', 'viewer'):
            raise ValueError('角色必须是 tenant_admin/admin/operator/viewer')
        return v


class ServiceAccountUpdate(BaseModel):
    """更新服务账号请求"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    role: Optional[str] = None
    rate_limit: Optional[int] = None
    allowed_ips: Optional[List[str]] = None
    allowed_scopes: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None


class ServiceAccountResponse(BaseModel):
    """服务账号响应"""
    id: int
    tenant_id: int
    account_name: str
    display_name: str
    description: Optional[str] = None
    status: str
    role: str
    rate_limit: int
    allowed_ips: Optional[List[str]] = None
    allowed_scopes: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    current_api_key_id: Optional[int] = None
    last_used_at: Optional[datetime] = None
    last_used_ip: Optional[str] = None
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True


class ServiceAccountListResponse(BaseModel):
    """服务账号列表响应"""
    items: List[ServiceAccountResponse]
    total: int


class ServiceAccountWithKeyResponse(ServiceAccountResponse):
    """服务账号创建响应（含 API Key）"""
    api_key: Optional[Dict[str, Any]] = None


class APIKeyCreate(BaseModel):
    """创建 API Key 请求"""
    key_name: Optional[str] = Field('default', max_length=100, description="密钥名称")
    expires_in_days: Optional[int] = Field(None, description="过期天数")


class APIKeyResponse(BaseModel):
    """API Key 响应（创建时含明文）"""
    key_id: int
    key_name: str
    key_prefix: str
    key_plain: Optional[str] = None
    status: str
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    last_used_ip: Optional[str] = None
    create_time: datetime


class APIKeyListResponse(BaseModel):
    """API Key 列表响应"""
    items: List[APIKeyResponse]


class APIKeyRotateRequest(BaseModel):
    """API Key 轮换请求"""
    expiration_grace_days: Optional[int] = Field(7, description="旧密钥宽限天数")


# ============================================================
# JWT / JWKS Schemas
# ============================================================

class JWKSResponse(BaseModel):
    """JWKS 响应"""
    keys: List[Dict[str, Any]]


# ============================================================
# 通用响应
# ============================================================

class SuccessResponse(BaseModel):
    """通用成功响应"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
