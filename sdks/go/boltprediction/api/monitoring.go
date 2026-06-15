package api

import "context"
import "fmt"
import "net/url"

// MonitoringClient Monitoring API 客户端
type MonitoringClient struct {
	client *BaseClient
}

// NewMonitoringClient 创建 Monitoring API 客户端
func NewMonitoringClient(client *BaseClient) *MonitoringClient {
	return &MonitoringClient{client: client}
}

// GetMetricsMetricsGet Get Metrics
func (c *MonitoringClient) GetMetricsMetricsGet(
	ctx context.Context,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/metrics", ),
		params,
		nil,
		&result,
	)
	return &result, err
}
