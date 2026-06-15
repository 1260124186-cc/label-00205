package com.boltprediction.sdk.api;

import com.boltprediction.sdk.core.ApiClientConfig;
import com.boltprediction.sdk.core.BaseAPIClient;
import com.boltprediction.sdk.core.CursorPaginator;
import com.boltprediction.sdk.model.*;

import okhttp3.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;

/** Organization API 客户端 */
public class OrganizationClient extends BaseAPIClient {

    public OrganizationClient(ApiClientConfig config) {
        super(config);
    }

    /** 创建组织节点 */
    public OrgNodeResponse createOrgNodeApiV1TenantsTenantIdOrgNodesPost(
            Integer tenantId,
            OrgNodeCreateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "POST",
                "/api/v1/api/v1/tenants/" + tenantId + "/org/nodes",
                params,
                body,
                OrgNodeResponse.class
        );
    }

    /** 查询组织节点列表 */
    public Map<String, Object> listOrgNodesApiV1TenantsTenantIdOrgNodesGet(
            Integer tenantId,
            Object parentId,
            Object nodeType,
            Object status
    ) throws IOException {
        Map<String, String> params = new HashMap<>();
        if (parentId != null) params.put("parent_id", String.valueOf(parentId));
        if (nodeType != null) params.put("node_type", String.valueOf(nodeType));
        if (status != null) params.put("status", String.valueOf(status));

        return _request(
                "GET",
                "/api/v1/api/v1/tenants/" + tenantId + "/org/nodes",
                params,
                null,
                Map.class
        );
    }

    /** 获取组织架构树 */
    public OrgTreeResponse getOrgTreeApiV1TenantsTenantIdOrgTreeGet(
            Integer tenantId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/tenants/" + tenantId + "/org/tree",
                params,
                null,
                OrgTreeResponse.class
        );
    }

    /** 获取组织节点详情 */
    public OrgNodeResponse getOrgNodeApiV1TenantsTenantIdOrgNodesNodeIdGet(
            Integer tenantId,
            Integer nodeId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/tenants/" + tenantId + "/org/nodes/" + nodeId + "",
                params,
                null,
                OrgNodeResponse.class
        );
    }

    /** 更新组织节点 */
    public OrgNodeResponse updateOrgNodeApiV1TenantsTenantIdOrgNodesNodeIdPut(
            Integer tenantId,
            Integer nodeId,
            OrgNodeUpdateRequest body
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "PUT",
                "/api/v1/api/v1/tenants/" + tenantId + "/org/nodes/" + nodeId + "",
                params,
                body,
                OrgNodeResponse.class
        );
    }

    /** 删除组织节点 */
    public Map<String, Object> deleteOrgNodeApiV1TenantsTenantIdOrgNodesNodeIdDelete(
            Integer tenantId,
            Integer nodeId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "DELETE",
                "/api/v1/api/v1/tenants/" + tenantId + "/org/nodes/" + nodeId + "",
                params,
                null,
                Map.class
        );
    }

    /** 获取祖先节点 */
    public Map<String, Object> getOrgAncestorsApiV1TenantsTenantIdOrgNodesNodeIdAncestorsGet(
            Integer tenantId,
            Integer nodeId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/tenants/" + tenantId + "/org/nodes/" + nodeId + "/ancestors",
                params,
                null,
                Map.class
        );
    }

    /** 获取后代节点 */
    public Map<String, Object> getOrgDescendantsApiV1TenantsTenantIdOrgNodesNodeIdDescendantsGet(
            Integer tenantId,
            Integer nodeId
    ) throws IOException {
        Map<String, String> params = new HashMap<>();

        return _request(
                "GET",
                "/api/v1/api/v1/tenants/" + tenantId + "/org/nodes/" + nodeId + "/descendants",
                params,
                null,
                Map.class
        );
    }

}