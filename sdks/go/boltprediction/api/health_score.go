package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// HealthScoreClient HealthScore API 客户端
type HealthScoreClient struct {
	client *BaseClient
}

// NewHealthScoreClient 创建 HealthScore API 客户端
func NewHealthScoreClient(client *BaseClient) *HealthScoreClient {
	return &HealthScoreClient{client: client}
}

// CalculateHealthIndexApiV1HealthCalculatePost 计算螺栓健康度指数 HI
func (c *HealthScoreClient) CalculateHealthIndexApiV1HealthCalculatePost(
	ctx context.Context,
	body *models.HealthIndexCalculateRequest,
) (*models.HealthIndexResponse, error) {
	params := url.Values{}

	var result models.HealthIndexResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/health/calculate", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// CalculateHealthIndexBatchApiV1HealthCalculateBatchPost 批量计算螺栓健康度
func (c *HealthScoreClient) CalculateHealthIndexBatchApiV1HealthCalculateBatchPost(
	ctx context.Context,
	body *models.HealthIndexBatchCalculateRequest,
) (*models.HealthIndexBatchResponse, error) {
	params := url.Values{}

	var result models.HealthIndexBatchResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/health/calculate/batch", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetHealthHistoryApiV1HealthHistoryGet 查询健康度历史记录
func (c *HealthScoreClient) GetHealthHistoryApiV1HealthHistoryGet(
	ctx context.Context,
	nodeId string,
	nodeType *string,
	startTime *interface{},
	endTime *interface{},
	limit *int,
) (*models.HealthIndexHistoryResponse, error) {
	params := url.Values{}
	params.Set("node_id", fmt.Sprintf("%v", nodeId))
	if nodeType != nil {
		params.Set("node_type", fmt.Sprintf("%v", *nodeType))
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

	var result models.HealthIndexHistoryResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/health/history", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// PredictRulApiV1HealthRulPredictPost 预测剩余使用寿命 RUL
func (c *HealthScoreClient) PredictRulApiV1HealthRulPredictPost(
	ctx context.Context,
	body *models.RulPredictionRequest,
) (*models.RulPredictionResponse, error) {
	params := url.Values{}

	var result models.RulPredictionResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/health/rul/predict", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GenerateHealthRollupApiV1HealthRollupPost 生成产线/装置级健康度汇总报表
func (c *HealthScoreClient) GenerateHealthRollupApiV1HealthRollupPost(
	ctx context.Context,
	body *models.HealthRollupRequest,
) (*models.HealthRollupResponse, error) {
	params := url.Values{}

	var result models.HealthRollupResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/health/rollup", ),
		params,
		body,
		&result,
	)
	return &result, err
}
