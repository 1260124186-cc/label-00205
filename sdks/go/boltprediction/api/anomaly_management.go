package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// AnomalyManagementClient AnomalyManagement API 客户端
type AnomalyManagementClient struct {
	client *BaseClient
}

// NewAnomalyManagementClient 创建 AnomalyManagement API 客户端
func NewAnomalyManagementClient(client *BaseClient) *AnomalyManagementClient {
	return &AnomalyManagementClient{client: client}
}

// QueryAnomaliesApiV1AnomalyQueryPost 查询异常数据
func (c *AnomalyManagementClient) QueryAnomaliesApiV1AnomalyQueryPost(
	ctx context.Context,
	body *models.AnomalyQueryRequest,
) (*models.AnomalyListResponse, error) {
	params := url.Values{}

	var result models.AnomalyListResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/anomaly/query", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetAnomalyDetailApiV1AnomalyAnomalyIdGet 获取异常详情
func (c *AnomalyManagementClient) GetAnomalyDetailApiV1AnomalyAnomalyIdGet(
	ctx context.Context,
	anomalyId int,
) (*models.AnomalyDataResponse, error) {
	params := url.Values{}

	var result models.AnomalyDataResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/anomaly/%s", anomalyId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ConfirmAnomalyApiV1AnomalyConfirmPost 确认异常（真实异常）
func (c *AnomalyManagementClient) ConfirmAnomalyApiV1AnomalyConfirmPost(
	ctx context.Context,
	body *models.AnomalyConfirmRequest,
) (*models.AnomalyDataResponse, error) {
	params := url.Values{}

	var result models.AnomalyDataResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/anomaly/confirm", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// MarkAnomalyFalsePositiveApiV1AnomalyFalsePositivePost 标注异常为误报
func (c *AnomalyManagementClient) MarkAnomalyFalsePositiveApiV1AnomalyFalsePositivePost(
	ctx context.Context,
	body *models.AnomalyFalsePositiveRequest,
) (*models.AnomalyDataResponse, error) {
	params := url.Values{}

	var result models.AnomalyDataResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/anomaly/false-positive", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// BatchConfirmAnomaliesApiV1AnomalyBatchConfirmPost 批量确认异常
func (c *AnomalyManagementClient) BatchConfirmAnomaliesApiV1AnomalyBatchConfirmPost(
	ctx context.Context,
	body *models.AnomalyBatchConfirmRequest,
) (*models.AnomalyBatchResultResponse, error) {
	params := url.Values{}

	var result models.AnomalyBatchResultResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/anomaly/batch-confirm", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// BatchMarkFalsePositivesApiV1AnomalyBatchFalsePositivePost 批量标注误报
func (c *AnomalyManagementClient) BatchMarkFalsePositivesApiV1AnomalyBatchFalsePositivePost(
	ctx context.Context,
	body *models.AnomalyBatchFalsePositiveRequest,
) (*models.AnomalyBatchResultResponse, error) {
	params := url.Values{}

	var result models.AnomalyBatchResultResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/anomaly/batch-false-positive", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetAnomalyStatisticsApiV1AnomalyStatisticsSummaryGet 获取异常统计信息
func (c *AnomalyManagementClient) GetAnomalyStatisticsApiV1AnomalyStatisticsSummaryGet(
	ctx context.Context,
	sensorId *interface{},
	startTime *interface{},
	endTime *interface{},
) (*models.AnomalyStatisticsResponse, error) {
	params := url.Values{}
	if sensorId != nil {
		params.Set("sensor_id", fmt.Sprintf("%v", *sensorId))
	}
	if startTime != nil {
		params.Set("start_time", fmt.Sprintf("%v", *startTime))
	}
	if endTime != nil {
		params.Set("end_time", fmt.Sprintf("%v", *endTime))
	}

	var result models.AnomalyStatisticsResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/anomaly/statistics/summary", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// CheckAnomalyWarningImpactApiV1AnomalyWarningImpactSensorIdGet 检查异常对预警等级的影响
func (c *AnomalyManagementClient) CheckAnomalyWarningImpactApiV1AnomalyWarningImpactSensorIdGet(
	ctx context.Context,
	sensorId string,
	currentLevel *int,
) (*models.AnomalyWarningImpactResponse, error) {
	params := url.Values{}
	if currentLevel != nil {
		params.Set("current_level", fmt.Sprintf("%v", *currentLevel))
	}

	var result models.AnomalyWarningImpactResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/anomaly/warning-impact/%s", sensorId),
		params,
		nil,
		&result,
	)
	return &result, err
}
