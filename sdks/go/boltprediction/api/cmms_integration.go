package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// CmmsIntegrationClient CMMSIntegration API 客户端
type CmmsIntegrationClient struct {
	client *BaseClient
}

// NewCmmsIntegrationClient 创建 CMMSIntegration API 客户端
func NewCmmsIntegrationClient(client *BaseClient) *CmmsIntegrationClient {
	return &CmmsIntegrationClient{client: client}
}

// ListCmmsConfigsApiV1CmmsConfigsGet 查询CMMS配置列表
func (c *CmmsIntegrationClient) ListCmmsConfigsApiV1CmmsConfigsGet(
	ctx context.Context,
	enabled *interface{},
	systemType *interface{},
	limit *int,
	offset *int,
) (*models.CmmsConfigListResponse, error) {
	params := url.Values{}
	if enabled != nil {
		params.Set("enabled", fmt.Sprintf("%v", *enabled))
	}
	if systemType != nil {
		params.Set("system_type", fmt.Sprintf("%v", *systemType))
	}
	if limit != nil {
		params.Set("limit", fmt.Sprintf("%v", *limit))
	}
	if offset != nil {
		params.Set("offset", fmt.Sprintf("%v", *offset))
	}

	var result models.CmmsConfigListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/cmms/configs", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// CreateCmmsConfigApiV1CmmsConfigsPost 创建CMMS配置
func (c *CmmsIntegrationClient) CreateCmmsConfigApiV1CmmsConfigsPost(
	ctx context.Context,
	body *models.CmmsConfigCreate,
) (*models.CmmsConfigResponse, error) {
	params := url.Values{}

	var result models.CmmsConfigResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/cmms/configs", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetCmmsConfigApiV1CmmsConfigsConfigIdGet 获取CMMS配置详情
func (c *CmmsIntegrationClient) GetCmmsConfigApiV1CmmsConfigsConfigIdGet(
	ctx context.Context,
	configId int,
) (*models.CmmsConfigResponse, error) {
	params := url.Values{}

	var result models.CmmsConfigResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/cmms/configs/%s", configId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// UpdateCmmsConfigApiV1CmmsConfigsConfigIdPut 更新CMMS配置
func (c *CmmsIntegrationClient) UpdateCmmsConfigApiV1CmmsConfigsConfigIdPut(
	ctx context.Context,
	configId int,
	body *models.CmmsConfigUpdate,
) (*models.CmmsConfigResponse, error) {
	params := url.Values{}

	var result models.CmmsConfigResponse
	err := c.client.Request(
		ctx,
		"PUT",
		fmt.Sprintf("/api/v1/api/v1/cmms/configs/%s", configId),
		params,
		body,
		&result,
	)
	return &result, err
}

// DeleteCmmsConfigApiV1CmmsConfigsConfigIdDelete 删除CMMS配置
func (c *CmmsIntegrationClient) DeleteCmmsConfigApiV1CmmsConfigsConfigIdDelete(
	ctx context.Context,
	configId int,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"DELETE",
		fmt.Sprintf("/api/v1/api/v1/cmms/configs/%s", configId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// SyncWorkOrderToCmmsApiV1CmmsSyncWorkOrderPost 同步工单到CMMS
func (c *CmmsIntegrationClient) SyncWorkOrderToCmmsApiV1CmmsSyncWorkOrderPost(
	ctx context.Context,
	body *models.CmmsSyncRequest,
) (*models.CmmsSyncResponse, error) {
	params := url.Values{}

	var result models.CmmsSyncResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/cmms/sync/work-order", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// CmmsWebhookCallbackApiV1CmmsWebhookConfigIdPost CMMS Webhook回调
func (c *CmmsIntegrationClient) CmmsWebhookCallbackApiV1CmmsWebhookConfigIdPost(
	ctx context.Context,
	configId int,
	body *map[string]interface{},
	xSignature *interface{},
) (*models.CmmsWebhookResponse, error) {
	params := url.Values{}
	if xSignature != nil {
		params.Set("X-Signature", fmt.Sprintf("%v", *xSignature))
	}

	var result models.CmmsWebhookResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/cmms/webhook/%s", configId),
		params,
		body,
		&result,
	)
	return &result, err
}

// ListCmmsSyncLogsApiV1CmmsSyncLogsGet 查询CMMS同步日志
func (c *CmmsIntegrationClient) ListCmmsSyncLogsApiV1CmmsSyncLogsGet(
	ctx context.Context,
	configId *interface{},
	workOrderId *interface{},
	status *interface{},
	syncDirection *interface{},
	limit *int,
	offset *int,
) (*models.CmmsSyncLogListResponse, error) {
	params := url.Values{}
	if configId != nil {
		params.Set("config_id", fmt.Sprintf("%v", *configId))
	}
	if workOrderId != nil {
		params.Set("work_order_id", fmt.Sprintf("%v", *workOrderId))
	}
	if status != nil {
		params.Set("status", fmt.Sprintf("%v", *status))
	}
	if syncDirection != nil {
		params.Set("sync_direction", fmt.Sprintf("%v", *syncDirection))
	}
	if limit != nil {
		params.Set("limit", fmt.Sprintf("%v", *limit))
	}
	if offset != nil {
		params.Set("offset", fmt.Sprintf("%v", *offset))
	}

	var result models.CmmsSyncLogListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/cmms/sync-logs", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// RetryCmmsSyncApiV1CmmsSyncLogsLogIdRetryPost 重试CMMS同步
func (c *CmmsIntegrationClient) RetryCmmsSyncApiV1CmmsSyncLogsLogIdRetryPost(
	ctx context.Context,
	logId int,
) (*models.CmmsSyncResponse, error) {
	params := url.Values{}

	var result models.CmmsSyncResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/cmms/sync-logs/%s/retry", logId),
		params,
		nil,
		&result,
	)
	return &result, err
}
