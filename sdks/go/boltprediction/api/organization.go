package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// OrganizationClient Organization API 客户端
type OrganizationClient struct {
	client *BaseClient
}

// NewOrganizationClient 创建 Organization API 客户端
func NewOrganizationClient(client *BaseClient) *OrganizationClient {
	return &OrganizationClient{client: client}
}

// CreateOrgNodeApiV1TenantsTenantIdOrgNodesPost 创建组织节点
func (c *OrganizationClient) CreateOrgNodeApiV1TenantsTenantIdOrgNodesPost(
	ctx context.Context,
	tenantId int,
	body *models.OrgNodeCreateRequest,
) (*models.OrgNodeResponse, error) {
	params := url.Values{}

	var result models.OrgNodeResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/org/nodes", tenantId),
		params,
		body,
		&result,
	)
	return &result, err
}

// ListOrgNodesApiV1TenantsTenantIdOrgNodesGet 查询组织节点列表
func (c *OrganizationClient) ListOrgNodesApiV1TenantsTenantIdOrgNodesGet(
	ctx context.Context,
	tenantId int,
	parentId *interface{},
	nodeType *interface{},
	status *interface{},
) (*map[string]interface{}, error) {
	params := url.Values{}
	if parentId != nil {
		params.Set("parent_id", fmt.Sprintf("%v", *parentId))
	}
	if nodeType != nil {
		params.Set("node_type", fmt.Sprintf("%v", *nodeType))
	}
	if status != nil {
		params.Set("status", fmt.Sprintf("%v", *status))
	}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/org/nodes", tenantId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetOrgTreeApiV1TenantsTenantIdOrgTreeGet 获取组织架构树
func (c *OrganizationClient) GetOrgTreeApiV1TenantsTenantIdOrgTreeGet(
	ctx context.Context,
	tenantId int,
) (*models.OrgTreeResponse, error) {
	params := url.Values{}

	var result models.OrgTreeResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/org/tree", tenantId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetOrgNodeApiV1TenantsTenantIdOrgNodesNodeIdGet 获取组织节点详情
func (c *OrganizationClient) GetOrgNodeApiV1TenantsTenantIdOrgNodesNodeIdGet(
	ctx context.Context,
	tenantId int,
	nodeId int,
) (*models.OrgNodeResponse, error) {
	params := url.Values{}

	var result models.OrgNodeResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/org/nodes/%s", tenantId, nodeId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// UpdateOrgNodeApiV1TenantsTenantIdOrgNodesNodeIdPut 更新组织节点
func (c *OrganizationClient) UpdateOrgNodeApiV1TenantsTenantIdOrgNodesNodeIdPut(
	ctx context.Context,
	tenantId int,
	nodeId int,
	body *models.OrgNodeUpdateRequest,
) (*models.OrgNodeResponse, error) {
	params := url.Values{}

	var result models.OrgNodeResponse
	err := c.client.Request(
		ctx,
		"PUT",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/org/nodes/%s", tenantId, nodeId),
		params,
		body,
		&result,
	)
	return &result, err
}

// DeleteOrgNodeApiV1TenantsTenantIdOrgNodesNodeIdDelete 删除组织节点
func (c *OrganizationClient) DeleteOrgNodeApiV1TenantsTenantIdOrgNodesNodeIdDelete(
	ctx context.Context,
	tenantId int,
	nodeId int,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"DELETE",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/org/nodes/%s", tenantId, nodeId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetOrgAncestorsApiV1TenantsTenantIdOrgNodesNodeIdAncestorsGet 获取祖先节点
func (c *OrganizationClient) GetOrgAncestorsApiV1TenantsTenantIdOrgNodesNodeIdAncestorsGet(
	ctx context.Context,
	tenantId int,
	nodeId int,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/org/nodes/%s/ancestors", tenantId, nodeId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetOrgDescendantsApiV1TenantsTenantIdOrgNodesNodeIdDescendantsGet 获取后代节点
func (c *OrganizationClient) GetOrgDescendantsApiV1TenantsTenantIdOrgNodesNodeIdDescendantsGet(
	ctx context.Context,
	tenantId int,
	nodeId int,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/org/nodes/%s/descendants", tenantId, nodeId),
		params,
		nil,
		&result,
	)
	return &result, err
}
