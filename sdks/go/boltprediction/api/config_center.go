package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// ConfigCenterClient ConfigCenter API 客户端
type ConfigCenterClient struct {
	client *BaseClient
}

// NewConfigCenterClient 创建 ConfigCenter API 客户端
func NewConfigCenterClient(client *BaseClient) *ConfigCenterClient {
	return &ConfigCenterClient{client: client}
}

// GetConfigCenterApiV1ConfigCenterGet 获取所有配置中心数据
func (c *ConfigCenterClient) GetConfigCenterApiV1ConfigCenterGet(
	ctx context.Context,
) (*models.ConfigCenterResponse, error) {
	params := url.Values{}

	var result models.ConfigCenterResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/config/center", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// UpdateWarningStrategyApiV1ConfigWarningStrategyPut 更新预警策略配置
func (c *ConfigCenterClient) UpdateWarningStrategyApiV1ConfigWarningStrategyPut(
	ctx context.Context,
	body *models.WarningStrategyConfigSchema,
) (*models.WarningStrategyConfigSchema, error) {
	params := url.Values{}

	var result models.WarningStrategyConfigSchema
	err := c.client.Request(
		ctx,
		"PUT",
		fmt.Sprintf("/api/v1/api/v1/config/warning-strategy", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// UpdateThresholdsApiV1ConfigThresholdsPut 更新阈值配置
func (c *ConfigCenterClient) UpdateThresholdsApiV1ConfigThresholdsPut(
	ctx context.Context,
	body *models.ThresholdConfigSchema,
) (*models.ThresholdConfigSchema, error) {
	params := url.Values{}

	var result models.ThresholdConfigSchema
	err := c.client.Request(
		ctx,
		"PUT",
		fmt.Sprintf("/api/v1/api/v1/config/thresholds", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// ListSchedulerJobsApiV1ConfigSchedulerJobsGet 获取调度任务列表
func (c *ConfigCenterClient) ListSchedulerJobsApiV1ConfigSchedulerJobsGet(
	ctx context.Context,
) (*[]models.ScheduledJobSchema, error) {
	params := url.Values{}

	var result []models.ScheduledJobSchema
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/config/scheduler/jobs", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// UpdateSchedulerJobApiV1ConfigSchedulerJobsJobIdPut 更新调度任务配置
func (c *ConfigCenterClient) UpdateSchedulerJobApiV1ConfigSchedulerJobsJobIdPut(
	ctx context.Context,
	jobId string,
	body *models.SchedulerJobUpdateRequest,
) (*models.ScheduledJobSchema, error) {
	params := url.Values{}

	var result models.ScheduledJobSchema
	err := c.client.Request(
		ctx,
		"PUT",
		fmt.Sprintf("/api/v1/api/v1/config/scheduler/jobs/%s", jobId),
		params,
		body,
		&result,
	)
	return &result, err
}

// TriggerSchedulerJobApiV1ConfigSchedulerJobsJobIdTriggerPost 手动触发调度任务
func (c *ConfigCenterClient) TriggerSchedulerJobApiV1ConfigSchedulerJobsJobIdTriggerPost(
	ctx context.Context,
	jobId string,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/config/scheduler/jobs/%s/trigger", jobId),
		params,
		nil,
		&result,
	)
	return &result, err
}
