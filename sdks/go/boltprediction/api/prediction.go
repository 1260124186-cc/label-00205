package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// PredictionClient Prediction API 客户端
type PredictionClient struct {
	client *BaseClient
}

// NewPredictionClient 创建 Prediction API 客户端
func NewPredictionClient(client *BaseClient) *PredictionClient {
	return &PredictionClient{client: client}
}

// PredictBoltApiV1PredictBoltPost 螺栓状态预测
func (c *PredictionClient) PredictBoltApiV1PredictBoltPost(
	ctx context.Context,
	body *models.BoltPredictionRequest,
	validationMode *string,
	version *interface{},
	shadowVersion *interface{},
) (*models.BoltPredictionResponse, error) {
	params := url.Values{}
	if validationMode != nil {
		params.Set("validation_mode", fmt.Sprintf("%v", *validationMode))
	}
	if version != nil {
		params.Set("version", fmt.Sprintf("%v", *version))
	}
	if shadowVersion != nil {
		params.Set("shadow_version", fmt.Sprintf("%v", *shadowVersion))
	}

	var result models.BoltPredictionResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/predict/bolt", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// PredictBoltEnsembleApiV1PredictBoltEnsemblePost 螺栓集成学习预测调试
func (c *PredictionClient) PredictBoltEnsembleApiV1PredictBoltEnsemblePost(
	ctx context.Context,
	body *models.BoltEnsemblePredictionRequest,
	validationMode *string,
) (*models.BoltEnsemblePredictionResponse, error) {
	params := url.Values{}
	if validationMode != nil {
		params.Set("validation_mode", fmt.Sprintf("%v", *validationMode))
	}

	var result models.BoltEnsemblePredictionResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/predict/bolt/ensemble", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// PredictBoltMultivariateApiV1PredictBoltMultivariatePost 螺栓多变量耦合预测（温度/振动/扭矩等联合输入）
func (c *PredictionClient) PredictBoltMultivariateApiV1PredictBoltMultivariatePost(
	ctx context.Context,
	body *models.BoltMultivariatePredictionRequest,
	saveToDb *bool,
) (*models.BoltMultivariatePredictionResponse, error) {
	params := url.Values{}
	if saveToDb != nil {
		params.Set("save_to_db", fmt.Sprintf("%v", *saveToDb))
	}

	var result models.BoltMultivariatePredictionResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/predict/bolt/multivariate", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// PredictFlangeApiV1PredictFlangePost 法兰面状态预测
func (c *PredictionClient) PredictFlangeApiV1PredictFlangePost(
	ctx context.Context,
	body *models.FlangePredictionRequest,
	validationMode *string,
	version *interface{},
	shadowVersion *interface{},
) (*models.FlangePredictionResponse, error) {
	params := url.Values{}
	if validationMode != nil {
		params.Set("validation_mode", fmt.Sprintf("%v", *validationMode))
	}
	if version != nil {
		params.Set("version", fmt.Sprintf("%v", *version))
	}
	if shadowVersion != nil {
		params.Set("shadow_version", fmt.Sprintf("%v", *shadowVersion))
	}

	var result models.FlangePredictionResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/predict/flange", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// ForecastMonthlyApiV1ForecastMonthlyPost 月度趋势预测
func (c *PredictionClient) ForecastMonthlyApiV1ForecastMonthlyPost(
	ctx context.Context,
	body *models.MonthlyForecastRequest,
) (*models.MonthlyForecastResponse, error) {
	params := url.Values{}

	var result models.MonthlyForecastResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/forecast/monthly", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// BatchPredictApiV1PredictBatchPost 批量预测
func (c *PredictionClient) BatchPredictApiV1PredictBatchPost(
	ctx context.Context,
	nodeType string,
) (*map[string]interface{}, error) {
	params := url.Values{}
	params.Set("node_type", fmt.Sprintf("%v", nodeType))

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/predict/batch", ),
		params,
		nil,
		&result,
	)
	return &result, err
}
