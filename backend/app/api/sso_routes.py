"""
SSO 和认证 API 路由

提供 SSO 配置管理、登录回调、会话管理、服务账号管理等接口。
"""

import json
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import JSONResponse, RedirectResponse, Response
from loguru import logger

from app.api.unified_auth import (
    get_current_identity,
    require_authenticated,
    require_tenant_context,
    require_role,
)
from app.api.sso_schemas import (
    SSOProviderCreate,
    SSOProviderUpdate,
    SSOProviderResponse,
    SSOProviderListResponse,
    SSOLoginRequest,
    SSOLoginResponse,
    SSOCallbackRequest,
    SSOTokenResponse,
    UserSessionResponse,
    UserSessionListResponse,
    SessionRevokeRequest,
    TokenRefreshRequest,
    TokenRefreshResponse,
    RevokeUserSessionsRequest,
    ServiceAccountCreate,
    ServiceAccountUpdate,
    ServiceAccountResponse,
    ServiceAccountListResponse,
    ServiceAccountWithKeyResponse,
    APIKeyCreate,
    APIKeyResponse,
    APIKeyListResponse,
    APIKeyRotateRequest,
    JWKSResponse,
    SuccessResponse,
)
from app.services.sso import (
    SSOService,
    sso_service,
    SessionManager,
    session_manager,
    JWTManager,
    jwt_manager,
    ServiceAccountService,
    service_account_service,
    oidc_provider,
    saml_provider,
)


router = APIRouter(prefix="/api/v1/auth", tags=["认证与SSO"])


# ============================================================
# SSO Provider 管理
# ============================================================

@router.post("/sso/providers", response_model=SSOProviderResponse, summary="创建 SSO 提供者")
async def create_sso_provider(
    request: Request,
    data: SSOProviderCreate,
    identity: dict = Depends(require_role("tenant_admin")),
):
    """
    创建新的 SSO 身份提供者（OIDC 或 SAML）。

    需要 `tenant_admin` 角色。
    """
    try:
        tenant_id = identity.get('tenant_id')
        if not tenant_id:
            raise HTTPException(status_code=403, detail="需要租户上下文")

        provider = sso_service.create_provider(
            tenant_id=tenant_id,
            provider_name=data.provider_name,
            provider_type=data.provider_type,
            is_default=data.is_default,
            issuer_url=data.issuer_url,
            client_id=data.client_id,
            client_secret=data.client_secret,
            authorization_endpoint=data.authorization_endpoint,
            token_endpoint=data.token_endpoint,
            userinfo_endpoint=data.userinfo_endpoint,
            jwks_uri=data.jwks_uri,
            saml_entity_id=data.saml_entity_id,
            saml_sso_url=data.saml_sso_url,
            saml_slo_url=data.saml_slo_url,
            saml_idp_certificate=data.saml_idp_certificate,
            saml_name_id_format=data.saml_name_id_format,
            attribute_mapping=data.attribute_mapping,
            role_mapping=data.role_mapping,
            jit_enabled=data.jit_enabled,
            jit_default_role=data.jit_default_role,
            scopes=data.scopes,
            auto_create_users=data.auto_create_users,
            sync_groups=data.sync_groups,
            created_by=identity.get('username', ''),
        )

        if not provider:
            raise HTTPException(status_code=500, detail="创建 SSO 提供者失败")

        return provider

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建 SSO 提供者失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sso/providers", response_model=SSOProviderListResponse, summary="列出 SSO 提供者")
async def list_sso_providers(
    status: Optional[str] = Query(None, description="状态过滤"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    identity: dict = Depends(require_tenant_context),
):
    """
    列出当前租户的所有 SSO 提供者。
    """
    try:
        tenant_id = identity['tenant_id']
        providers = sso_service.list_providers(
            tenant_id=tenant_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        total = sso_service.count_providers(tenant_id=tenant_id, status=status)

        return SSOProviderListResponse(items=providers, total=total)

    except Exception as e:
        logger.error(f"列出 SSO 提供者失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sso/providers/default", response_model=SSOProviderResponse, summary="获取默认 SSO 提供者")
async def get_default_sso_provider(
    identity: dict = Depends(require_tenant_context),
):
    """
    获取当前租户的默认 SSO 提供者。
    """
    try:
        tenant_id = identity['tenant_id']
        provider = sso_service.get_default_provider(tenant_id=tenant_id)

        if not provider:
            raise HTTPException(status_code=404, detail="未找到默认 SSO 提供者")

        return provider

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取默认 SSO 提供者失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sso/providers/{provider_id}", response_model=SSOProviderResponse, summary="获取 SSO 提供者详情")
async def get_sso_provider(
    provider_id: int,
    identity: dict = Depends(require_tenant_context),
):
    """
    获取指定 SSO 提供者的详细信息。
    """
    try:
        tenant_id = identity['tenant_id']
        provider = sso_service.get_provider(
            tenant_id=tenant_id,
            provider_id=provider_id,
        )

        if not provider:
            raise HTTPException(status_code=404, detail="SSO 提供者不存在")

        return provider

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 SSO 提供者失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/sso/providers/{provider_id}", response_model=SSOProviderResponse, summary="更新 SSO 提供者")
async def update_sso_provider(
    provider_id: int,
    data: SSOProviderUpdate,
    identity: dict = Depends(require_role("tenant_admin")),
):
    """
    更新 SSO 提供者配置。

    需要 `tenant_admin` 角色。
    """
    try:
        tenant_id = identity['tenant_id']
        if not tenant_id:
            raise HTTPException(status_code=403, detail="需要租户上下文")

        update_data = data.dict(exclude_unset=True)
        provider = sso_service.update_provider(
            tenant_id=tenant_id,
            provider_id=provider_id,
            **update_data,
        )

        if not provider:
            raise HTTPException(status_code=404, detail="SSO 提供者不存在")

        return provider

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新 SSO 提供者失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sso/providers/{provider_id}", response_model=SuccessResponse, summary="删除 SSO 提供者")
async def delete_sso_provider(
    provider_id: int,
    identity: dict = Depends(require_role("tenant_admin")),
):
    """
    删除（禁用）SSO 提供者。

    需要 `tenant_admin` 角色。
    """
    try:
        tenant_id = identity['tenant_id']
        if not tenant_id:
            raise HTTPException(status_code=403, detail="需要租户上下文")

        success = sso_service.delete_provider(
            tenant_id=tenant_id,
            provider_id=provider_id,
        )

        if not success:
            raise HTTPException(status_code=404, detail="SSO 提供者不存在")

        return SuccessResponse(success=True, message="SSO 提供者已删除")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除 SSO 提供者失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# SSO 登录与回调
# ============================================================

@router.post("/sso/login", response_model=SSOLoginResponse, summary="SSO 登录发起")
async def sso_login(
    request: Request,
    data: SSOLoginRequest,
):
    """
    发起 SSO 登录，返回授权重定向 URL。

    无需认证即可访问。
    """
    try:
        provider_id = data.provider_id

        if not provider_id:
            # TODO: 支持通过租户查找默认提供者
            raise HTTPException(status_code=400, detail="请指定 provider_id")

        # 尝试 OIDC 登录
        try:
            oidc_result = oidc_provider.get_authorization_url(
                provider_id=provider_id,
                redirect_uri=data.redirect_uri,
                state=data.relay_state,
            )
            return SSOLoginResponse(
                authorization_url=oidc_result['authorization_url'],
                state=oidc_result.get('state'),
                nonce=oidc_result.get('nonce'),
                provider_id=provider_id,
                provider_type='oidc',
            )
        except Exception:
            pass

        # 尝试 SAML 登录
        try:
            saml_result = saml_provider.get_authn_request_url(
                provider_id=provider_id,
                callback_url=data.redirect_uri,
                relay_state=data.relay_state,
            )
            return SSOLoginResponse(
                authorization_url=saml_result['sso_url'],
                state=saml_result.get('relay_state'),
                provider_id=provider_id,
                provider_type='saml',
            )
        except Exception:
            pass

        raise HTTPException(status_code=400, detail="不支持的 SSO 提供者类型或配置错误")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SSO 登录发起失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sso/callback/{provider_id}", response_model=SSOTokenResponse, summary="SSO 回调处理")
async def sso_callback(
    request: Request,
    provider_id: int,
    data: SSOCallbackRequest,
):
    """
    SSO 回调处理，验证身份并颁发系统令牌。

    无需认证即可访问。
    """
    try:
        client_ip = request.client.host if request.client else ''
        user_agent = request.headers.get('user-agent', '')

        user_info = None
        is_new_user = False

        # 处理 OIDC 回调
        if data.code:
            try:
                oidc_user = oidc_provider.handle_callback(
                    provider_id=provider_id,
                    code=data.code,
                    redirect_uri=data.state or '',  # TODO: 从 state 中还原 redirect_uri
                    state=data.state,
                )
                user_info = oidc_user
            except Exception as e:
                logger.warning(f"OIDC 回调处理失败: {e}")

        # 处理 SAML 回调
        if data.saml_response and not user_info:
            try:
                saml_user = saml_provider.handle_response(
                    provider_id=provider_id,
                    saml_response=data.saml_response,
                    relay_state=data.relay_state,
                )
                user_info = saml_user
            except Exception as e:
                logger.warning(f"SAML 回调处理失败: {e}")

        if not user_info:
            raise HTTPException(status_code=401, detail="SSO 认证失败")

        # JIT 建号或查找用户
        tenant_user = None
        try:
            from app.services.sso.sso_service import sso_service as ss
            tenant_user, is_new_user = ss.jit_provision_user(
                tenant_id=None,  # TODO: 需要确定租户
                sso_provider_id=provider_id,
                idp_user_id=user_info['idp_user_id'],
                idp_attributes=user_info.get('idp_attributes', {}),
                idp_groups=user_info.get('idp_groups', []),
            )
        except Exception as e:
            logger.error(f"JIT 建号失败: {e}")
            raise HTTPException(status_code=500, detail="用户置备失败")

        if not tenant_user:
            raise HTTPException(status_code=401, detail="用户不存在且 JIT 已禁用")

        # 创建会话
        user_id = tenant_user.get('id') if isinstance(tenant_user, dict) else tenant_user.id
        tenant_id = tenant_user.get('tenant_id') if isinstance(tenant_user, dict) else tenant_user.tenant_id
        username = tenant_user.get('username') if isinstance(tenant_user, dict) else tenant_user.username
        role = tenant_user.get('role') if isinstance(tenant_user, dict) else tenant_user.role

        session_info = session_manager.create_session(
            tenant_id=tenant_id,
            user_id=user_id,
            username=username,
            session_type='sso',
            sso_provider_id=provider_id,
            ip_address=client_ip,
            user_agent=user_agent,
            device_info={
                'user_agent': user_agent,
                'sso_provider_id': provider_id,
                'idp_user_id': user_info['idp_user_id'],
            },
        )

        return SSOTokenResponse(
            access_token=session_info['access_token'],
            token_type='bearer',
            expires_in=session_info['expires_in'],
            refresh_token=session_info.get('refresh_token'),
            user_info={
                'id': user_id,
                'username': username,
                'email': user_info.get('idp_email', ''),
                'display_name': user_info.get('idp_display_name', ''),
                'role': role,
                'tenant_id': tenant_id,
            },
            session_id=session_info['session_id'],
            is_new_user=is_new_user,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SSO 回调处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sso/saml/metadata/{provider_id}", summary="获取 SAML SP 元数据")
async def get_saml_metadata(
    provider_id: int,
    request: Request,
):
    """
    获取 SAML 服务提供者（SP）元数据 XML。

    用于在 IdP 端配置 SP。
    """
    try:
        # 构建 ACS URL
        base_url = str(request.base_url).rstrip('/')
        acs_url = f"{base_url}/api/v1/auth/sso/callback/{provider_id}"

        metadata_xml = saml_provider.get_metadata_xml(
            provider_id=provider_id,
            acs_url=acs_url,
        )

        return Response(
            content=metadata_xml,
            media_type="application/xml",
            headers={
                "Content-Disposition": f"attachment; filename=saml-metadata-{provider_id}.xml"
            }
        )

    except Exception as e:
        logger.error(f"获取 SAML 元数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 令牌与会话管理
# ============================================================

@router.post("/token/refresh", response_model=TokenRefreshResponse, summary="刷新访问令牌")
async def refresh_token(
    data: TokenRefreshRequest,
):
    """
    使用 Refresh Token 刷新 Access Token。
    """
    try:
        session_info = session_manager.refresh_session(data.refresh_token)

        if not session_info:
            raise HTTPException(status_code=401, detail="无效或过期的 refresh token")

        return TokenRefreshResponse(
            access_token=session_info['access_token'],
            token_type='bearer',
            expires_in=session_info['expires_in'],
            refresh_token=session_info.get('refresh_token'),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刷新令牌失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=UserSessionListResponse, summary="获取当前用户会话列表")
async def list_my_sessions(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    identity: dict = Depends(require_authenticated),
):
    """
    获取当前用户的所有活跃会话。
    """
    try:
        tenant_id = identity.get('tenant_id')
        user_id = identity.get('user_id')

        if not user_id:
            raise HTTPException(status_code=400, detail="需要用户上下文")

        sessions = session_manager.list_user_sessions(
            tenant_id=tenant_id,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

        total = len(sessions)  # TODO: 分页总数需要单独统计

        return UserSessionListResponse(
            items=[
                UserSessionResponse(**s)
                for s in sessions
            ],
            total=total,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/revoke", response_model=SuccessResponse, summary="撤销指定会话")
async def revoke_session(
    session_id: int,
    data: Optional[SessionRevokeRequest] = None,
    identity: dict = Depends(require_authenticated),
):
    """
    撤销（登出）指定的会话。
    用户只能撤销自己的会话，管理员可以撤销任何会话。
    """
    try:
        user_id = identity.get('user_id')
        role = identity.get('role')

        # 验证会话是否属于当前用户（非管理员）
        if role not in ('tenant_admin', 'admin'):
            session_info = session_manager.validate_session(session_id)
            if not session_info or session_info.get('user_id') != user_id:
                raise HTTPException(status_code=403, detail="无权撤销此会话")

        success = session_manager.revoke_session(
            session_id=session_id,
            reason=data.reason if data else None,
            revoked_by=identity.get('username', ''),
        )

        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")

        return SuccessResponse(success=True, message="会话已撤销")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"撤销会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/revoke-all", response_model=SuccessResponse, summary="撤销用户所有会话")
async def revoke_all_user_sessions(
    request: Request,
    data: RevokeUserSessionsRequest,
    identity: dict = Depends(require_authenticated),
):
    """
    撤销用户的所有会话（强制登出）。

    - 普通用户：撤销自己的所有会话
    - 管理员：可以撤销指定用户的所有会话
    """
    try:
        tenant_id = identity.get('tenant_id')
        role = identity.get('role')

        target_user_id = data.user_id

        # 非管理员只能撤销自己的
        if role not in ('tenant_admin', 'admin'):
            target_user_id = identity.get('user_id')

        if not target_user_id:
            raise HTTPException(status_code=400, detail="需要指定用户ID")

        count = session_manager.revoke_user_sessions(
            tenant_id=tenant_id,
            user_id=target_user_id,
            reason=data.reason,
            revoked_by=identity.get('username', ''),
            except_session_id=None if data.include_current else identity.get('session_id'),
        )

        return SuccessResponse(
            success=True,
            message=f"已撤销 {count} 个会话",
            data={"revoked_count": count},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量撤销会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/.well-known/jwks.json", response_model=JWKSResponse, summary="获取 JWKS 公钥集")
async def get_jwks():
    """
    获取 JWT 签名公钥集（JWKS）。

    用于外部系统验证我们签发的 JWT。
    """
    try:
        jwks = jwt_manager.get_jwks()
        return JWKSResponse(keys=jwks.get('keys', []))

    except Exception as e:
        logger.error(f"获取 JWKS 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 服务账号管理
# ============================================================

@router.post("/service-accounts", response_model=ServiceAccountWithKeyResponse, summary="创建服务账号")
async def create_service_account(
    data: ServiceAccountCreate,
    identity: dict = Depends(require_role("tenant_admin")),
):
    """
    创建新的服务账号，并生成第一个 API Key。

    需要 `tenant_admin` 角色。
    """
    try:
        tenant_id = identity.get('tenant_id')
        if not tenant_id:
            raise HTTPException(status_code=403, detail="需要租户上下文")

        expires_at = None
        if data.expires_in_days:
            expires_at = datetime.now() + timedelta(days=data.expires_in_days)

        sa_info = service_account_service.create_service_account(
            tenant_id=tenant_id,
            account_name=data.account_name,
            display_name=data.display_name,
            description=data.description,
            role=data.role,
            rate_limit=data.rate_limit,
            allowed_ips=data.allowed_ips,
            allowed_scopes=data.allowed_scopes,
            expires_at=expires_at,
            owner_id=data.owner_id,
            owner_name=data.owner_name,
            owner_email=data.owner_email,
        )

        if not sa_info:
            raise HTTPException(status_code=500, detail="创建服务账号失败")

        return sa_info

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建服务账号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/service-accounts", response_model=ServiceAccountListResponse, summary="列出服务账号")
async def list_service_accounts(
    status: Optional[str] = Query(None, description="状态过滤"),
    role: Optional[str] = Query(None, description="角色过滤"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    identity: dict = Depends(require_tenant_context),
):
    """
    列出当前租户的所有服务账号。
    """
    try:
        tenant_id = identity['tenant_id']

        accounts = service_account_service.list_service_accounts(
            tenant_id=tenant_id,
            status=status,
            role=role,
            limit=limit,
            offset=offset,
        )

        total = service_account_service.count_service_accounts(
            tenant_id=tenant_id,
            status=status,
        )

        return ServiceAccountListResponse(items=accounts, total=total)

    except Exception as e:
        logger.error(f"列出服务账号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/service-accounts/{account_id}", response_model=ServiceAccountResponse, summary="获取服务账号详情")
async def get_service_account(
    account_id: int,
    identity: dict = Depends(require_tenant_context),
):
    """
    获取指定服务账号的详细信息。
    """
    try:
        tenant_id = identity['tenant_id']
        sa = service_account_service.get_service_account(
            tenant_id=tenant_id,
            service_account_id=account_id,
        )

        if not sa:
            raise HTTPException(status_code=404, detail="服务账号不存在")

        return sa

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取服务账号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/service-accounts/{account_id}", response_model=ServiceAccountResponse, summary="更新服务账号")
async def update_service_account(
    account_id: int,
    data: ServiceAccountUpdate,
    identity: dict = Depends(require_role("tenant_admin")),
):
    """
    更新服务账号配置。

    需要 `tenant_admin` 角色。
    """
    try:
        tenant_id = identity['tenant_id']
        if not tenant_id:
            raise HTTPException(status_code=403, detail="需要租户上下文")

        update_data = data.dict(exclude_unset=True)
        sa = service_account_service.update_service_account(
            tenant_id=tenant_id,
            service_account_id=account_id,
            **update_data,
        )

        if not sa:
            raise HTTPException(status_code=404, detail="服务账号不存在")

        return sa

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新服务账号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/service-accounts/{account_id}", response_model=SuccessResponse, summary="删除服务账号")
async def delete_service_account(
    account_id: int,
    identity: dict = Depends(require_role("tenant_admin")),
):
    """
    删除（禁用）服务账号，并吊销其所有 API Key。

    需要 `tenant_admin` 角色。
    """
    try:
        tenant_id = identity['tenant_id']
        if not tenant_id:
            raise HTTPException(status_code=403, detail="需要租户上下文")

        success = service_account_service.delete_service_account(
            tenant_id=tenant_id,
            service_account_id=account_id,
        )

        if not success:
            raise HTTPException(status_code=404, detail="服务账号不存在")

        return SuccessResponse(success=True, message="服务账号已删除")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除服务账号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 服务账号 API Key 管理
# ============================================================

@router.post("/service-accounts/{account_id}/keys", response_model=APIKeyResponse, summary="创建 API Key")
async def create_service_account_key(
    account_id: int,
    data: APIKeyCreate,
    identity: dict = Depends(require_role("tenant_admin")),
):
    """
    为服务账号创建新的 API Key。

    需要 `tenant_admin` 角色。
    """
    try:
        tenant_id = identity['tenant_id']
        if not tenant_id:
            raise HTTPException(status_code=403, detail="需要租户上下文")

        key_info = service_account_service.create_api_key(
            tenant_id=tenant_id,
            service_account_id=account_id,
            key_name=data.key_name,
            expires_in_days=data.expires_in_days,
        )

        if not key_info:
            raise HTTPException(status_code=404, detail="服务账号不存在")

        return APIKeyResponse(**key_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建 API Key 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/service-accounts/{account_id}/keys", response_model=APIKeyListResponse, summary="列出 API Key")
async def list_service_account_keys(
    account_id: int,
    status: Optional[str] = Query(None, description="状态过滤"),
    identity: dict = Depends(require_tenant_context),
):
    """
    列出服务账号的所有 API Key（不含明文）。
    """
    try:
        tenant_id = identity['tenant_id']

        keys = service_account_service.list_api_keys(
            tenant_id=tenant_id,
            service_account_id=account_id,
            status=status,
        )

        return APIKeyListResponse(items=[APIKeyResponse(**k) for k in keys])

    except Exception as e:
        logger.error(f"列出 API Key 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/service-accounts/{account_id}/keys/{key_id}/revoke", response_model=SuccessResponse, summary="吊销 API Key")
async def revoke_service_account_key(
    account_id: int,
    key_id: int,
    identity: dict = Depends(require_role("tenant_admin")),
):
    """
    吊销指定的 API Key。

    需要 `tenant_admin` 角色。
    """
    try:
        tenant_id = identity['tenant_id']
        if not tenant_id:
            raise HTTPException(status_code=403, detail="需要租户上下文")

        success = service_account_service.revoke_api_key(
            tenant_id=tenant_id,
            service_account_id=account_id,
            key_id=key_id,
        )

        if not success:
            raise HTTPException(status_code=404, detail="API Key 不存在")

        return SuccessResponse(success=True, message="API Key 已吊销")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"吊销 API Key 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/service-accounts/{account_id}/keys/{key_id}/rotate", response_model=APIKeyResponse, summary="轮换 API Key")
async def rotate_service_account_key(
    account_id: int,
    key_id: int,
    data: APIKeyRotateRequest,
    identity: dict = Depends(require_role("tenant_admin")),
):
    """
    轮换 API Key：创建新密钥，旧密钥在宽限期后失效。

    需要 `tenant_admin` 角色。
    """
    try:
        tenant_id = identity['tenant_id']
        if not tenant_id:
            raise HTTPException(status_code=403, detail="需要租户上下文")

        new_key = service_account_service.rotate_api_key(
            tenant_id=tenant_id,
            service_account_id=account_id,
            key_id=key_id,
            expiration_grace_days=data.expiration_grace_days,
        )

        if not new_key:
            raise HTTPException(status_code=404, detail="API Key 不存在或已吊销")

        return APIKeyResponse(**new_key)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"轮换 API Key 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 用户信息
# ============================================================

@router.get("/me", summary="获取当前用户信息")
async def get_current_user_info(
    identity: dict = Depends(require_authenticated),
):
    """
    获取当前认证用户的信息。
    """
    return {
        'authenticated': True,
        'tenant_id': identity.get('tenant_id'),
        'user_id': identity.get('user_id'),
        'username': identity.get('username'),
        'role': identity.get('role'),
        'permissions': identity.get('permissions', []),
        'auth_method': identity.get('auth_method'),
        'is_service_account': identity.get('is_service_account', False),
        'service_account_id': identity.get('service_account_id'),
        'session_id': identity.get('session_id'),
    }
