package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// DataQualityClient DataQuality API 客户端
type DataQualityClient struct {
	client *BaseClient
}

// NewDataQualityClient 创建 DataQuality API 客户端
func NewDataQualityClient(client *BaseClient) *DataQualityClient {
	return &DataQualityClient{client: client}
}

// CheckDataQualityApiV1DataQualityCheckPost 评估传感器数据质量
func (c *DataQualityClient) CheckDataQualityApiV1DataQualityCheckPost(
	ctx context.Context,
	body *models.DataQualityCheckRequest,
) (*models.QualityEvaluationResponse, error) {
	params := url.Values{}

	var result models.QualityEvaluationResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/data-quality/check", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// BatchCheckDataQualityApiV1DataQualityBatchCheckPost 批量评估传感器数据质量
func (c *DataQualityClient) BatchCheckDataQualityApiV1DataQualityBatchCheckPost(
	ctx context.Context,
	body *models.DataQualityCheckBatchRequest,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/data-quality/batch-check", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetSensorQualityScoreApiV1DataQualityScoreSensorIdGet 获取传感器质量评分
func (c *DataQualityClient) GetSensorQualityScoreApiV1DataQualityScoreSensorIdGet(
	ctx context.Context,
	sensorId string,
	recentDataLimit *int,
) (*models.SensorQualityScoreSchema, error) {
	params := url.Values{}
	if recentDataLimit != nil {
		params.Set("recent_data_limit", fmt.Sprintf("%v", *recentDataLimit))
	}

	var result models.SensorQualityScoreSchema
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/data-quality/score/%s", sensorId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// AdjustPredictionConfidenceApiV1DataQualityAdjustConfidencePost 调整预测置信度
func (c *DataQualityClient) AdjustPredictionConfidenceApiV1DataQualityAdjustConfidencePost(
	ctx context.Context,
	body *models.ConfidenceAdjustmentRequest,
) (*models.ConfidenceAdjustmentResponse, error) {
	params := url.Values{}

	var result models.ConfidenceAdjustmentResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/data-quality/adjust-confidence", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GenerateQualityReportApiV1DataQualityReportGeneratePost 生成每日质量报告
func (c *DataQualityClient) GenerateQualityReportApiV1DataQualityReportGeneratePost(
	ctx context.Context,
	body *models.QualityReportRequest,
) (*models.DailyQualityReportSchema, error) {
	params := url.Values{}

	var result models.DailyQualityReportSchema
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/data-quality/report/generate", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetLatestQualityReportApiV1DataQualityReportLatestGet 获取最新质量报告
func (c *DataQualityClient) GetLatestQualityReportApiV1DataQualityReportLatestGet(
	ctx context.Context,
) (*models.DailyQualityReportSchema, error) {
	params := url.Values{}

	var result models.DailyQualityReportSchema
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/data-quality/report/latest", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetSensorQualityHistoryApiV1DataQualityHistorySensorIdGet 获取传感器质量历史记录
func (c *DataQualityClient) GetSensorQualityHistoryApiV1DataQualityHistorySensorIdGet(
	ctx context.Context,
	body *models.DataQualityHistoryRequest,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/data-quality/history/{sensor_id}", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetProblemSensorsApiV1DataQualityProblemSensorsGet 获取问题传感器列表
func (c *DataQualityClient) GetProblemSensorsApiV1DataQualityProblemSensorsGet(
	ctx context.Context,
	minScore *float64,
	limit *int,
) (*map[string]interface{}, error) {
	params := url.Values{}
	if minScore != nil {
		params.Set("min_score", fmt.Sprintf("%v", *minScore))
	}
	if limit != nil {
		params.Set("limit", fmt.Sprintf("%v", *limit))
	}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/data-quality/problem-sensors", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ClassifySensorAnomaliesApiV1DataQualityAnomaliesSensorIdClassifyGet 分类传感器异常
func (c *DataQualityClient) ClassifySensorAnomaliesApiV1DataQualityAnomaliesSensorIdClassifyGet(
	ctx context.Context,
	sensorId string,
	startTime *interface{},
	endTime *interface{},
	recentDataLimit *int,
) (*map[string]interface{}, error) {
	params := url.Values{}
	if startTime != nil {
		params.Set("start_time", fmt.Sprintf("%v", *startTime))
	}
	if endTime != nil {
		params.Set("end_time", fmt.Sprintf("%v", *endTime))
	}
	if recentDataLimit != nil {
		params.Set("recent_data_limit", fmt.Sprintf("%v", *recentDataLimit))
	}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/data-quality/anomalies/%s/classify", sensorId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetDataQualitySummaryApiV1DataQualitySummaryGet 获取数据质量总览
func (c *DataQualityClient) GetDataQualitySummaryApiV1DataQualitySummaryGet(
	ctx context.Context,
	days *int,
) (*map[string]interface{}, error) {
	params := url.Values{}
	if days != nil {
		params.Set("days", fmt.Sprintf("%v", *days))
	}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/data-quality/summary", ),
		params,
		nil,
		&result,
	)
	return &result, err
}
