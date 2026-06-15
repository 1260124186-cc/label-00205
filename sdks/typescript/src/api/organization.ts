/** Organization API 客户端 */

import { BaseAPIClient } from "../core/client";
import { CursorPaginator } from "../core/pagination";
import * as Models from "../models";

export class OrganizationClient extends BaseAPIClient {

  /**
   * 创建组织节点
   */
  async createOrgNodeApiV1TenantsTenantIdOrgNodesPost(
    tenantId: number,
    body: Models.OrgNodeCreateRequest
  ): Promise<Models.OrgNodeResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "POST",
      `/api/v1/api/v1/tenants/${tenantId}/org/nodes`,
      params,
      body
    );
  }

  /**
   * 查询组织节点列表
   */
  async listOrgNodesApiV1TenantsTenantIdOrgNodesGet(
    tenantId: number,
    parentId?: any,
    nodeType?: any,
    status?: any
  ): Promise<any> {
    const params: Record<string, any> = {};
    if (parentId !== undefined) params['parent_id'] = parentId;
    if (nodeType !== undefined) params['node_type'] = nodeType;
    if (status !== undefined) params['status'] = status;

    return this._request(
      "GET",
      `/api/v1/api/v1/tenants/${tenantId}/org/nodes`,
      params,
      undefined
    );
  }

  /**
   * 获取组织架构树
   */
  async getOrgTreeApiV1TenantsTenantIdOrgTreeGet(
    tenantId: number
  ): Promise<Models.OrgTreeResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/tenants/${tenantId}/org/tree`,
      params,
      undefined
    );
  }

  /**
   * 获取组织节点详情
   */
  async getOrgNodeApiV1TenantsTenantIdOrgNodesNodeIdGet(
    tenantId: number,
    nodeId: number
  ): Promise<Models.OrgNodeResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/tenants/${tenantId}/org/nodes/${nodeId}`,
      params,
      undefined
    );
  }

  /**
   * 更新组织节点
   */
  async updateOrgNodeApiV1TenantsTenantIdOrgNodesNodeIdPut(
    tenantId: number,
    nodeId: number,
    body: Models.OrgNodeUpdateRequest
  ): Promise<Models.OrgNodeResponse> {
    const params: Record<string, any> = {};

    return this._request(
      "PUT",
      `/api/v1/api/v1/tenants/${tenantId}/org/nodes/${nodeId}`,
      params,
      body
    );
  }

  /**
   * 删除组织节点
   */
  async deleteOrgNodeApiV1TenantsTenantIdOrgNodesNodeIdDelete(
    tenantId: number,
    nodeId: number
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "DELETE",
      `/api/v1/api/v1/tenants/${tenantId}/org/nodes/${nodeId}`,
      params,
      undefined
    );
  }

  /**
   * 获取祖先节点
   */
  async getOrgAncestorsApiV1TenantsTenantIdOrgNodesNodeIdAncestorsGet(
    tenantId: number,
    nodeId: number
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/tenants/${tenantId}/org/nodes/${nodeId}/ancestors`,
      params,
      undefined
    );
  }

  /**
   * 获取后代节点
   */
  async getOrgDescendantsApiV1TenantsTenantIdOrgNodesNodeIdDescendantsGet(
    tenantId: number,
    nodeId: number
  ): Promise<any> {
    const params: Record<string, any> = {};

    return this._request(
      "GET",
      `/api/v1/api/v1/tenants/${tenantId}/org/nodes/${nodeId}/descendants`,
      params,
      undefined
    );
  }
}