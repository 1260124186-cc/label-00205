package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// WorkOrderStatsClient WorkOrderStats API 客户端
type WorkOrderStatsClient struct {
	client *BaseClient
}

// NewWorkOrderStatsClient 创建 WorkOrderStats API 客户端
func NewWorkOrderStatsClient(client *BaseClient) *WorkOrderStatsClient {
	return &WorkOrderStatsClient{client: client}
}

// GetWorkOrderStatsApiV1WorkOrdersStatsSummaryGet 工单统计指标概览
func (c *WorkOrderStatsClient) GetWorkOrderStatsApiV1WorkOrdersStatsSummaryGet(
	ctx context.Context,
	startTime *interface{},
	endTime *interface{},
	nodeType *interface{},
	priority *interface{},
) (*models.WorkOrderStatsResponse, error) {
	params := url.Values{}
	if startTime != nil {
		params.Set("start_time", fmt.Sprintf("%v", *startTime))
	}
	if endTime != nil {
		params.Set("end_time", fmt.Sprintf("%v", *endTime))
	}
	if nodeType != nil {
		params.Set("node_type", fmt.Sprintf("%v", *nodeType))
	}
	if priority != nil {
		params.Set("priority", fmt.Sprintf("%v", *priority))
	}

	var result models.WorkOrderStatsResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/work-orders/stats/summary", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetMttrTrendApiV1WorkOrdersStatsMttrTrendGet MTTR趋势
func (c *WorkOrderStatsClient) GetMttrTrendApiV1WorkOrdersStatsMttrTrendGet(
	ctx context.Context,
	days *int,
	nodeType *interface{},
	priority *interface{},
) (*models.MttrTrendResponse, error) {
	params := url.Values{}
	if days != nil {
		params.Set("days", fmt.Sprintf("%v", *days))
	}
	if nodeType != nil {
		params.Set("node_type", fmt.Sprintf("%v", *nodeType))
	}
	if priority != nil {
		params.Set("priority", fmt.Sprintf("%v", *priority))
	}

	var result models.MttrTrendResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/work-orders/stats/mttr-trend", ),
		params,
		nil,
		&result,
	)
	return &result, err
}
