package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// SchedulerClient Scheduler API 客户端
type SchedulerClient struct {
	client *BaseClient
}

// NewSchedulerClient 创建 Scheduler API 客户端
func NewSchedulerClient(client *BaseClient) *SchedulerClient {
	return &SchedulerClient{client: client}
}

// TriggerSchedulerJobByNameApiV1SchedulerTriggerJobNamePost 手动触发调度任务（按任务名称）
func (c *SchedulerClient) TriggerSchedulerJobByNameApiV1SchedulerTriggerJobNamePost(
	ctx context.Context,
	jobName string,
	requireLeader *bool,
	numShards *interface{},
) (*models.SchedulerTriggerResponse, error) {
	params := url.Values{}
	if requireLeader != nil {
		params.Set("require_leader", fmt.Sprintf("%v", *requireLeader))
	}
	if numShards != nil {
		params.Set("num_shards", fmt.Sprintf("%v", *numShards))
	}

	var result models.SchedulerTriggerResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/scheduler/trigger/%s", jobName),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetJobExecutionLogsApiV1SchedulerLogsGet 查询任务执行日志列表
func (c *SchedulerClient) GetJobExecutionLogsApiV1SchedulerLogsGet(
	ctx context.Context,
	jobName *interface{},
	jobType *interface{},
	status *interface{},
	triggerType *interface{},
	startTimeFrom *interface{},
	startTimeTo *interface{},
	instanceId *interface{},
	hasErrors *interface{},
	page *int,
	pageSize *int,
) (*models.JobExecutionLogListResponse, error) {
	params := url.Values{}
	if jobName != nil {
		params.Set("job_name", fmt.Sprintf("%v", *jobName))
	}
	if jobType != nil {
		params.Set("job_type", fmt.Sprintf("%v", *jobType))
	}
	if status != nil {
		params.Set("status", fmt.Sprintf("%v", *status))
	}
	if triggerType != nil {
		params.Set("trigger_type", fmt.Sprintf("%v", *triggerType))
	}
	if startTimeFrom != nil {
		params.Set("start_time_from", fmt.Sprintf("%v", *startTimeFrom))
	}
	if startTimeTo != nil {
		params.Set("start_time_to", fmt.Sprintf("%v", *startTimeTo))
	}
	if instanceId != nil {
		params.Set("instance_id", fmt.Sprintf("%v", *instanceId))
	}
	if hasErrors != nil {
		params.Set("has_errors", fmt.Sprintf("%v", *hasErrors))
	}
	if page != nil {
		params.Set("page", fmt.Sprintf("%v", *page))
	}
	if pageSize != nil {
		params.Set("page_size", fmt.Sprintf("%v", *pageSize))
	}

	var result models.JobExecutionLogListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/scheduler/logs", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetJobExecutionLogDetailApiV1SchedulerLogsLogIdGet 获取任务执行日志详情
func (c *SchedulerClient) GetJobExecutionLogDetailApiV1SchedulerLogsLogIdGet(
	ctx context.Context,
	logId int,
) (*models.JobExecutionLogSchema, error) {
	params := url.Values{}

	var result models.JobExecutionLogSchema
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/scheduler/logs/%s", logId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetLeaderStatusApiV1SchedulerLeaderJobKeyGet 获取Leader选举状态
func (c *SchedulerClient) GetLeaderStatusApiV1SchedulerLeaderJobKeyGet(
	ctx context.Context,
	jobKey string,
) (*models.LeaderStatusSchema, error) {
	params := url.Values{}

	var result models.LeaderStatusSchema
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/scheduler/leader/%s", jobKey),
		params,
		nil,
		&result,
	)
	return &result, err
}
