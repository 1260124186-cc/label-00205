package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// ApiKeyManagementClient ApiKeyManagement API 客户端
type ApiKeyManagementClient struct {
	client *BaseClient
}

// NewApiKeyManagementClient 创建 ApiKeyManagement API 客户端
func NewApiKeyManagementClient(client *BaseClient) *ApiKeyManagementClient {
	return &ApiKeyManagementClient{client: client}
}

// ListApiKeysApiV1AuthKeysGet 列出所有API密钥
func (c *ApiKeyManagementClient) ListApiKeysApiV1AuthKeysGet(
	ctx context.Context,
) (*models.ApiKeyListResponse, error) {
	params := url.Values{}

	var result models.ApiKeyListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/auth/keys", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// CreateApiKeyApiV1AuthKeysPost 创建API密钥
func (c *ApiKeyManagementClient) CreateApiKeyApiV1AuthKeysPost(
	ctx context.Context,
	body *models.ApiKeyCreateRequest,
) (*models.ApiKeyCreateResponse, error) {
	params := url.Values{}

	var result models.ApiKeyCreateResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/auth/keys", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// RotateApiKeyApiV1AuthKeysKeyIdRotatePost 轮换API密钥
func (c *ApiKeyManagementClient) RotateApiKeyApiV1AuthKeysKeyIdRotatePost(
	ctx context.Context,
	keyId string,
) (*models.ApiKeyRotateResponse, error) {
	params := url.Values{}

	var result models.ApiKeyRotateResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/auth/keys/%s/rotate", keyId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// RevokeApiKeyApiV1AuthKeysKeyIdDelete 吊销API密钥
func (c *ApiKeyManagementClient) RevokeApiKeyApiV1AuthKeysKeyIdDelete(
	ctx context.Context,
	keyId string,
) (*models.ApiKeyRevokeResponse, error) {
	params := url.Values{}

	var result models.ApiKeyRevokeResponse
	err := c.client.Request(
		ctx,
		"DELETE",
		fmt.Sprintf("/api/v1/api/v1/auth/keys/%s", keyId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetRateLimitStatusApiV1AuthKeysKeyIdRateLimitGet 查询密钥限流状态
func (c *ApiKeyManagementClient) GetRateLimitStatusApiV1AuthKeysKeyIdRateLimitGet(
	ctx context.Context,
	keyId string,
) (*models.RateLimitStatusResponse, error) {
	params := url.Values{}

	var result models.RateLimitStatusResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/auth/keys/%s/rate-limit", keyId),
		params,
		nil,
		&result,
	)
	return &result, err
}
