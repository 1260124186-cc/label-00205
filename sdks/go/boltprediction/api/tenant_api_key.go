package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// TenantApiKeyClient TenantApiKey API 客户端
type TenantApiKeyClient struct {
	client *BaseClient
}

// NewTenantApiKeyClient 创建 TenantApiKey API 客户端
func NewTenantApiKeyClient(client *BaseClient) *TenantApiKeyClient {
	return &TenantApiKeyClient{client: client}
}

// CreateTenantApiKeyApiV1TenantsTenantIdApiKeysPost 创建租户API Key
func (c *TenantApiKeyClient) CreateTenantApiKeyApiV1TenantsTenantIdApiKeysPost(
	ctx context.Context,
	tenantId int,
	body *models.TenantApiKeyCreateRequest,
) (*models.TenantApiKeyCreateResponse, error) {
	params := url.Values{}

	var result models.TenantApiKeyCreateResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/api-keys", tenantId),
		params,
		body,
		&result,
	)
	return &result, err
}

// ListTenantApiKeysApiV1TenantsTenantIdApiKeysGet 查询租户API Key列表
func (c *TenantApiKeyClient) ListTenantApiKeysApiV1TenantsTenantIdApiKeysGet(
	ctx context.Context,
	tenantId int,
	status *interface{},
) (*map[string]interface{}, error) {
	params := url.Values{}
	if status != nil {
		params.Set("status", fmt.Sprintf("%v", *status))
	}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/api-keys", tenantId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetTenantApiKeyApiV1TenantsTenantIdApiKeysKeyIdGet 获取API Key详情
func (c *TenantApiKeyClient) GetTenantApiKeyApiV1TenantsTenantIdApiKeysKeyIdGet(
	ctx context.Context,
	tenantId int,
	keyId int,
) (*models.TenantApiKeyResponse, error) {
	params := url.Values{}

	var result models.TenantApiKeyResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/api-keys/%s", tenantId, keyId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// UpdateTenantApiKeyApiV1TenantsTenantIdApiKeysKeyIdPut 更新API Key
func (c *TenantApiKeyClient) UpdateTenantApiKeyApiV1TenantsTenantIdApiKeysKeyIdPut(
	ctx context.Context,
	tenantId int,
	keyId int,
	body *models.TenantApiKeyUpdateRequest,
) (*models.TenantApiKeyResponse, error) {
	params := url.Values{}

	var result models.TenantApiKeyResponse
	err := c.client.Request(
		ctx,
		"PUT",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/api-keys/%s", tenantId, keyId),
		params,
		body,
		&result,
	)
	return &result, err
}

// RevokeTenantApiKeyApiV1TenantsTenantIdApiKeysKeyIdDelete 吊销API Key
func (c *TenantApiKeyClient) RevokeTenantApiKeyApiV1TenantsTenantIdApiKeysKeyIdDelete(
	ctx context.Context,
	tenantId int,
	keyId int,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"DELETE",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/api-keys/%s", tenantId, keyId),
		params,
		nil,
		&result,
	)
	return &result, err
}
