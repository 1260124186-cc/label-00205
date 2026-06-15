package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// SystemClient System API 客户端
type SystemClient struct {
	client *BaseClient
}

// NewSystemClient 创建 System API 客户端
func NewSystemClient(client *BaseClient) *SystemClient {
	return &SystemClient{client: client}
}

// HealthCheckHealthGet 健康检查（公开免鉴权）
func (c *SystemClient) HealthCheckHealthGet(
	ctx context.Context,
) (*models.HealthResponse, error) {
	params := url.Values{}

	var result models.HealthResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/health", ),
		params,
		nil,
		&result,
	)
	return &result, err
}
