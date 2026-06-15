package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// QuotaManagementClient QuotaManagement API 客户端
type QuotaManagementClient struct {
	client *BaseClient
}

// NewQuotaManagementClient 创建 QuotaManagement API 客户端
func NewQuotaManagementClient(client *BaseClient) *QuotaManagementClient {
	return &QuotaManagementClient{client: client}
}

// GetTenantQuotaApiV1TenantsTenantIdQuotaGet 获取租户配额
func (c *QuotaManagementClient) GetTenantQuotaApiV1TenantsTenantIdQuotaGet(
	ctx context.Context,
	tenantId int,
) (*models.QuotaResponse, error) {
	params := url.Values{}

	var result models.QuotaResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/quota", tenantId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// UpdateTenantQuotaApiV1TenantsTenantIdQuotaPut 更新租户配额
func (c *QuotaManagementClient) UpdateTenantQuotaApiV1TenantsTenantIdQuotaPut(
	ctx context.Context,
	tenantId int,
	body *models.QuotaUpdateRequest,
) (*models.QuotaResponse, error) {
	params := url.Values{}

	var result models.QuotaResponse
	err := c.client.Request(
		ctx,
		"PUT",
		fmt.Sprintf("/api/v1/api/v1/tenants/%s/quota", tenantId),
		params,
		body,
		&result,
	)
	return &result, err
}
