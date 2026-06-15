package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// ApiAuditLogClient ApiAuditLog API 客户端
type ApiAuditLogClient struct {
	client *BaseClient
}

// NewApiAuditLogClient 创建 ApiAuditLog API 客户端
func NewApiAuditLogClient(client *BaseClient) *ApiAuditLogClient {
	return &ApiAuditLogClient{client: client}
}

// QueryAuditLogsApiV1AuthAuditLogsGet 查询API审计日志
func (c *ApiAuditLogClient) QueryAuditLogsApiV1AuthAuditLogsGet(
	ctx context.Context,
	keyId *interface{},
	path *interface{},
	method *interface{},
	startTime *interface{},
	endTime *interface{},
	limit *int,
	offset *int,
) (*models.ApiAuditLogListResponse, error) {
	params := url.Values{}
	if keyId != nil {
		params.Set("key_id", fmt.Sprintf("%v", *keyId))
	}
	if path != nil {
		params.Set("path", fmt.Sprintf("%v", *path))
	}
	if method != nil {
		params.Set("method", fmt.Sprintf("%v", *method))
	}
	if startTime != nil {
		params.Set("start_time", fmt.Sprintf("%v", *startTime))
	}
	if endTime != nil {
		params.Set("end_time", fmt.Sprintf("%v", *endTime))
	}
	if limit != nil {
		params.Set("limit", fmt.Sprintf("%v", *limit))
	}
	if offset != nil {
		params.Set("offset", fmt.Sprintf("%v", *offset))
	}

	var result models.ApiAuditLogListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/auth/audit-logs", ),
		params,
		nil,
		&result,
	)
	return &result, err
}
