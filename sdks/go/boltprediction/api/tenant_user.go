package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// TenantUserClient TenantUser API 客户端
type TenantUserClient struct {
	client *BaseClient
}

// NewTenantUserClient 创建 TenantUser API 客户端
func NewTenantUserClient(client *BaseClient) *TenantUserClient {
	return &TenantUserClient{client: client}
}

// CreateTenantUserApiV1TenantsTenantIdUsersPost 创建租户用户
func (c *TenantUserClient) CreateTenantUserApiV1TenantsTenantIdUsersPost(
	ctx context.Context,
	tenantId int,
	body *models.TenantUserCreateRequest,
) (*models.TenantUserResponse, error) {
	params := url.Values{}

	var result models.TenantUserResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/users", tenantId),
		params,
		body,
		&result,
	)
	return &result, err
}

// ListTenantUsersApiV1TenantsTenantIdUsersGet 查询租户用户列表
func (c *TenantUserClient) ListTenantUsersApiV1TenantsTenantIdUsersGet(
	ctx context.Context,
	tenantId int,
	role *interface{},
	status *interface{},
	limit *int,
	offset *int,
) (*models.TenantUserListResponse, error) {
	params := url.Values{}
	if role != nil {
		params.Set("role", fmt.Sprintf("%v", *role))
	}
	if status != nil {
		params.Set("status", fmt.Sprintf("%v", *status))
	}
	if limit != nil {
		params.Set("limit", fmt.Sprintf("%v", *limit))
	}
	if offset != nil {
		params.Set("offset", fmt.Sprintf("%v", *offset))
	}

	var result models.TenantUserListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/users", tenantId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetTenantUserApiV1TenantsTenantIdUsersUserIdGet 获取租户用户详情
func (c *TenantUserClient) GetTenantUserApiV1TenantsTenantIdUsersUserIdGet(
	ctx context.Context,
	tenantId int,
	userId int,
) (*models.TenantUserResponse, error) {
	params := url.Values{}

	var result models.TenantUserResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/users/%s", tenantId, userId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// UpdateTenantUserApiV1TenantsTenantIdUsersUserIdPut 更新租户用户
func (c *TenantUserClient) UpdateTenantUserApiV1TenantsTenantIdUsersUserIdPut(
	ctx context.Context,
	tenantId int,
	userId int,
	body *models.TenantUserUpdateRequest,
) (*models.TenantUserResponse, error) {
	params := url.Values{}

	var result models.TenantUserResponse
	err := c.client.Request(
		ctx,
		"PUT",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/users/%s", tenantId, userId),
		params,
		body,
		&result,
	)
	return &result, err
}

// DeleteTenantUserApiV1TenantsTenantIdUsersUserIdDelete 禁用租户用户
func (c *TenantUserClient) DeleteTenantUserApiV1TenantsTenantIdUsersUserIdDelete(
	ctx context.Context,
	tenantId int,
	userId int,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"DELETE",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/users/%s", tenantId, userId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ChangeTenantUserPasswordApiV1TenantsTenantIdUsersUserIdPasswordPut 修改租户用户密码
func (c *TenantUserClient) ChangeTenantUserPasswordApiV1TenantsTenantIdUsersUserIdPasswordPut(
	ctx context.Context,
	tenantId int,
	userId int,
	body *models.TenantUserPasswordRequest,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"PUT",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/users/%s/password", tenantId, userId),
		params,
		body,
		&result,
	)
	return &result, err
}
