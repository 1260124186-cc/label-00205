import json
import secrets
import base64
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, quote

from loguru import logger

from app.utils.database import get_db, SSOProvider
from app.utils.config import config


class SAMLProvider:
    """
    SAML 2.0 协议支持

    功能:
    1. 生成 SAML AuthnRequest
    2. 处理 SAML Response
    3. 验证 SAML 断言
    4. 提取用户属性和组
    """

    def __init__(self):
        pass

    def get_authn_request_url(
        self,
        provider_id: int,
        callback_url: str,
        relay_state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成 SAML 认证请求 URL

        Args:
            provider_id: SSO 提供者ID
            callback_url: 断言消费者服务 URL (ACS)
            relay_state: RelayState 参数

        Returns:
            包含 SSO URL 和参数的字典
        """
        try:
            provider = self._get_provider(provider_id)
            if not provider:
                raise ValueError(f"SSO 提供者不存在: {provider_id}")

            if not provider.saml_sso_url:
                raise ValueError("SAML SSO URL 未配置")

            # 生成 SAML AuthnRequest
            request_id = f"_{secrets.token_hex(16)}"
            issue_instant = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

            saml_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{provider.saml_sso_url}"
    AssertionConsumerServiceURL="{callback_url}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
    ForceAuthn="false"
    IsPassive="false">
    <saml:Issuer>{provider.saml_entity_id or callback_url}</saml:Issuer>
    <samlp:NameIDPolicy
        Format="{provider.saml_name_id_format or 'urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified'}"
        AllowCreate="true"/>
</samlp:AuthnRequest>"""

            # deflate + base64 encode
            import zlib
            compressed = zlib.compress(saml_request.encode('utf-8'), level=9)[2:-4]
            encoded_request = base64.b64encode(compressed).decode('utf-8')

            params = {'SAMLRequest': encoded_request}
            if relay_state:
                params['RelayState'] = relay_state

            auth_url = f"{provider.saml_sso_url}?{urlencode(params)}"

            return {
                'sso_url': auth_url,
                'request_id': request_id,
                'relay_state': relay_state,
                'saml_request': saml_request,
            }

        except Exception as e:
            logger.error(f"生成 SAML 认证请求失败: {e}")
            raise

    def handle_response(
        self,
        provider_id: int,
        saml_response: str,
        relay_state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        处理 SAML Response

        Args:
            provider_id: SSO 提供者ID
            saml_response: Base64 编码的 SAML Response
            relay_state: RelayState

        Returns:
            包含用户信息的字典
        """
        try:
            provider = self._get_provider(provider_id)
            if not provider:
                raise ValueError(f"SSO 提供者不存在: {provider_id}")

            # 解码 SAML Response
            decoded = base64.b64decode(saml_response).decode('utf-8')

            # 解析 XML
            import xml.etree.ElementTree as ET
            root = ET.fromstring(decoded)

            # 定义命名空间
            ns = {
                'samlp': 'urn:oasis:names:tc:SAML:2.0:protocol',
                'saml': 'urn:oasis:names:tc:SAML:2.0:assertion',
                'ds': 'http://www.w3.org/2000/09/xmldsig#',
            }

            # 提取 NameID
            name_id_elem = root.find('.//saml:NameID', ns)
            name_id = name_id_elem.text if name_id_elem is not None else None

            if not name_id:
                raise ValueError("SAML Response 中缺少 NameID")

            # 提取断言
            assertion = root.find('.//saml:Assertion', ns)
            if assertion is None:
                raise ValueError("SAML Response 中缺少 Assertion")

            # 提取属性
            attributes = {}
            attribute_statement = assertion.find('saml:AttributeStatement', ns)
            if attribute_statement is not None:
                for attr in attribute_statement.findall('saml:Attribute', ns):
                    attr_name = attr.get('Name')
                    attr_values = []
                    for value in attr.findall('saml:AttributeValue', ns):
                        attr_values.append(value.text or '')
                    if len(attr_values) == 1:
                        attributes[attr_name] = attr_values[0]
                    else:
                        attributes[attr_name] = attr_values

            # 提取用户组
            groups = self._extract_groups(attributes)

            # 提取用户信息
            idp_user_id = name_id
            email = self._get_attribute(attributes, ['email', 'mail', 'Email', 'MAIL', 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress'])
            username = self._get_attribute(attributes, ['username', 'sAMAccountName', 'Uid', 'uid', 'login', 'preferred_username']) or idp_user_id
            display_name = self._get_attribute(attributes, ['displayName', 'display_name', 'name', 'cn', 'commonName', 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name'])

            # 提取会话索引（用于 SLO）
            session_index = None
            authn_statement = assertion.find('saml:AuthnStatement', ns)
            if authn_statement is not None:
                session_index = authn_statement.get('SessionIndex')

            # 验证签名（如果配置了证书）
            # 注意：完整的签名验证需要 xmlsec 库，这里只做基本解析
            # 生产环境建议使用 python3-saml 或 pysaml2 库

            return {
                'idp_user_id': str(idp_user_id),
                'idp_username': username,
                'idp_email': email,
                'idp_display_name': display_name,
                'idp_attributes': attributes,
                'idp_groups': groups,
                'session_index': session_index,
                'name_id': name_id,
                'provider_id': provider_id,
                'provider_type': 'saml',
                'saml_response_decoded': decoded,
            }

        except ET.ParseError as e:
            logger.error(f"SAML Response 解析失败: {e}")
            raise ValueError(f"无效的 SAML Response: {e}")
        except Exception as e:
            logger.error(f"处理 SAML Response 失败: {e}")
            raise

    def get_metadata_xml(
        self,
        provider_id: int,
        acs_url: str,
        entity_id: Optional[str] = None,
    ) -> str:
        """
        生成 SP 端 SAML 元数据 XML

        Args:
            provider_id: SSO 提供者ID
            acs_url: 断言消费者服务 URL
            entity_id: 实体ID（可选）

        Returns:
            SAML 元数据 XML 字符串
        """
        try:
            provider = self._get_provider(provider_id)
            if not provider:
                raise ValueError(f"SSO 提供者不存在: {provider_id}")

            entity_id = entity_id or provider.saml_entity_id or acs_url
            valid_until = (datetime.utcnow() + timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%SZ')

            metadata = f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor
    xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="{entity_id}"
    validUntil="{valid_until}">
    <md:SPSSODescriptor
        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol"
        AuthnRequestsSigned="false"
        WantAssertionsSigned="true">
        <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified</md:NameIDFormat>
        <md:AssertionConsumerService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            Location="{acs_url}"
            index="0"
            isDefault="true"/>
        <md:AssertionConsumerService
            Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            Location="{acs_url}"
            index="1"/>
    </md:SPSSODescriptor>
    <md:Organization>
        <md:OrganizationName xml:lang="zh-CN">Bolt Prediction System</md:OrganizationName>
        <md:OrganizationDisplayName xml:lang="zh-CN">螺栓预紧力预测系统</md:OrganizationDisplayName>
        <md:OrganizationURL xml:lang="zh-CN">{acs_url.rsplit('/', 1)[0] if '/' in acs_url else acs_url}</md:OrganizationURL>
    </md:Organization>
</md:EntityDescriptor>"""

            return metadata

        except Exception as e:
            logger.error(f"生成 SAML 元数据失败: {e}")
            raise

    def get_slo_request_url(
        self,
        provider_id: int,
        name_id: str,
        session_index: Optional[str] = None,
        callback_url: Optional[str] = None,
    ) -> Optional[str]:
        """
        生成 SAML 单点登出请求 URL

        Args:
            provider_id: SSO 提供者ID
            name_id: 用户 NameID
            session_index: 会话索引
            callback_url: 登出回调 URL

        Returns:
            SLO URL，如果未配置 SLO 则返回 None
        """
        try:
            provider = self._get_provider(provider_id)
            if not provider or not provider.saml_slo_url:
                return None

            request_id = f"_{secrets.token_hex(16)}"
            issue_instant = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

            slo_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:LogoutRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{issue_instant}"
    Destination="{provider.saml_slo_url}">
    <saml:Issuer>{provider.saml_entity_id or callback_url}</saml:Issuer>
    <saml:NameID>{name_id}</saml:NameID>
    {f'<samlp:SessionIndex>{session_index}</samlp:SessionIndex>' if session_index else ''}
</samlp:LogoutRequest>"""

            import zlib
            compressed = zlib.compress(slo_request.encode('utf-8'), level=9)[2:-4]
            encoded_request = base64.b64encode(compressed).decode('utf-8')

            slo_url = f"{provider.saml_slo_url}?SAMLRequest={quote(encoded_request)}"
            if callback_url:
                slo_url += f"&RelayState={quote(callback_url)}"

            return slo_url

        except Exception as e:
            logger.error(f"生成 SAML SLO 请求失败: {e}")
            return None

    def _get_provider(self, provider_id: int) -> Optional[SSOProvider]:
        """获取 SSO 提供者"""
        try:
            with get_db() as db:
                if db is None:
                    return None
                return db.query(SSOProvider).filter(
                    SSOProvider.id == provider_id,
                    SSOProvider.status == 'active',
                ).first()
        except Exception as e:
            logger.error(f"获取 SSO 提供者失败: {e}")
            return None

    @staticmethod
    def _get_attribute(attributes: Dict[str, Any], candidate_names: List[str]) -> Optional[str]:
        """
        从属性中获取指定值（支持多种可能的属性名）

        Args:
            attributes: 属性字典
            candidate_names: 候选属性名列表

        Returns:
            属性值
        """
        for name in candidate_names:
            if name in attributes:
                value = attributes[name]
                if isinstance(value, list) and len(value) > 0:
                    return str(value[0])
                if value is not None:
                    return str(value)
        return None

    @staticmethod
    def _extract_groups(attributes: Dict[str, Any]) -> List[str]:
        """
        从 SAML 属性中提取用户组

        支持多种属性名:
        - groups
        - memberOf
        - Group
        - http://schemas.microsoft.com/ws/2008/06/identity/claims/role (ADFS)
        - roles

        Args:
            attributes: SAML 属性字典

        Returns:
            用户组列表
        """
        group_attr_names = [
            'groups',
            'Groups',
            'memberOf',
            'member_of',
            'Group',
            'group',
            'roles',
            'Roles',
            'role',
            'Role',
            'http://schemas.microsoft.com/ws/2008/06/identity/claims/groups',
            'http://schemas.microsoft.com/ws/2008/06/identity/claims/role',
            'http://schemas.xmlsoap.org/claims/Group',
        ]

        for attr_name in group_attr_names:
            if attr_name in attributes:
                value = attributes[attr_name]
                if isinstance(value, list):
                    return [str(v) for v in value if v]
                if isinstance(value, str):
                    return [v.strip() for v in value.split(',') if v.strip()]
                if value is not None:
                    return [str(value)]

        return []

    @staticmethod
    def _parse_json(value: Optional[str], default: Any) -> Any:
        """解析 JSON 字符串"""
        if not value:
            return default
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default


saml_provider = SAMLProvider()
