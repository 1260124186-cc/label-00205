package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// MultiTenantClient MultiTenant API 客户端
type MultiTenantClient struct {
	client *BaseClient
}

// NewMultiTenantClient 创建 MultiTenant API 客户端
func NewMultiTenantClient(client *BaseClient) *MultiTenantClient {
	return &MultiTenantClient{client: client}
}

// TenantLoginApiV1TenantLoginPost 租户用户登录
func (c *MultiTenantClient) TenantLoginApiV1TenantLoginPost(
	ctx context.Context,
	body *models.TenantLoginRequest,
) (*models.TenantLoginResponse, error) {
	params := url.Values{}

	var result models.TenantLoginResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/tenant/login", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetCurrentTenantUserApiV1TenantMeGet 获取当前登录用户信息
func (c *MultiTenantClient) GetCurrentTenantUserApiV1TenantMeGet(
	ctx context.Context,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/tenant/me", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// TenantLogoutApiV1TenantLogoutPost 租户用户登出
func (c *MultiTenantClient) TenantLogoutApiV1TenantLogoutPost(
	ctx context.Context,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/tenant/logout", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// CreateTenantApiV1TenantsPost 创建租户
func (c *MultiTenantClient) CreateTenantApiV1TenantsPost(
	ctx context.Context,
	body *models.TenantCreateRequest,
) (*models.TenantResponse, error) {
	params := url.Values{}

	var result models.TenantResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/tenants", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// ListTenantsApiV1TenantsGet 查询租户列表
func (c *MultiTenantClient) ListTenantsApiV1TenantsGet(
	ctx context.Context,
	status *interface{},
	limit *int,
	offset *int,
) (*models.TenantListResponse, error) {
	params := url.Values{}
	if status != nil {
		params.Set("status", fmt.Sprintf("%v", *status))
	}
	if limit != nil {
		params.Set("limit", fmt.Sprintf("%v", *limit))
	}
	if offset != nil {
		params.Set("offset", fmt.Sprintf("%v", *offset))
	}

	var result models.TenantListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/tenants", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetTenantApiV1TenantsTenantIdGet 获取租户详情
func (c *MultiTenantClient) GetTenantApiV1TenantsTenantIdGet(
	ctx context.Context,
	tenantId int,
) (*models.TenantResponse, error) {
	params := url.Values{}

	var result models.TenantResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s", tenantId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// UpdateTenantApiV1TenantsTenantIdPut 更新租户
func (c *MultiTenantClient) UpdateTenantApiV1TenantsTenantIdPut(
	ctx context.Context,
	tenantId int,
	body *models.TenantUpdateRequest,
) (*models.TenantResponse, error) {
	params := url.Values{}

	var result models.TenantResponse
	err := c.client.Request(
		ctx,
		"PUT",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s", tenantId),
		params,
		body,
		&result,
	)
	return &result, err
}

// DeleteTenantApiV1TenantsTenantIdDelete 删除租户
func (c *MultiTenantClient) DeleteTenantApiV1TenantsTenantIdDelete(
	ctx context.Context,
	tenantId int,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"DELETE",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s", tenantId),
		params,
		nil,
		&result,
	)
	return &result, err
}
