package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// FederatedLearningClient FederatedLearning API 客户端
type FederatedLearningClient struct {
	client *BaseClient
}

// NewFederatedLearningClient 创建 FederatedLearning API 客户端
func NewFederatedLearningClient(client *BaseClient) *FederatedLearningClient {
	return &FederatedLearningClient{client: client}
}

// RegisterFederatedClientApiV1FederatedClientRegisterPost 注册联邦学习客户端
func (c *FederatedLearningClient) RegisterFederatedClientApiV1FederatedClientRegisterPost(
	ctx context.Context,
	body *models.FederatedClientRegisterRequest,
) (*models.FederatedClientRegisterResponse, error) {
	params := url.Values{}

	var result models.FederatedClientRegisterResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/federated/client/register", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetFederatedServerStatusApiV1FederatedServerStatusGet 获取联邦学习服务器状态
func (c *FederatedLearningClient) GetFederatedServerStatusApiV1FederatedServerStatusGet(
	ctx context.Context,
) (*models.FederatedServerStatusResponse, error) {
	params := url.Values{}

	var result models.FederatedServerStatusResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/federated/server/status", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// StartFederatedRoundApiV1FederatedRoundStartPost 开始联邦学习轮次
func (c *FederatedLearningClient) StartFederatedRoundApiV1FederatedRoundStartPost(
	ctx context.Context,
	body *models.FederatedRoundStartRequest,
) (*models.FederatedRoundStartResponse, error) {
	params := url.Values{}

	var result models.FederatedRoundStartResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/federated/round/start", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetFederatedRoundStatusApiV1FederatedRoundStatusGet 获取当前轮次状态
func (c *FederatedLearningClient) GetFederatedRoundStatusApiV1FederatedRoundStatusGet(
	ctx context.Context,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/federated/round/status", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// AggregateFederatedUpdatesApiV1FederatedRoundAggregatePost 聚合并更新全局模型
func (c *FederatedLearningClient) AggregateFederatedUpdatesApiV1FederatedRoundAggregatePost(
	ctx context.Context,
	body *models.FederatedRoundAggregateRequest,
) (*models.FederatedRoundAggregateResponse, error) {
	params := url.Values{}

	var result models.FederatedRoundAggregateResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/federated/round/aggregate", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetFederatedModelHistoryApiV1FederatedModelHistoryModelTypeNodeIdGet 获取全局模型历史
func (c *FederatedLearningClient) GetFederatedModelHistoryApiV1FederatedModelHistoryModelTypeNodeIdGet(
	ctx context.Context,
	modelType string,
	nodeId string,
) (*models.FederatedModelHistoryResponse, error) {
	params := url.Values{}

	var result models.FederatedModelHistoryResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/federated/model/history/%s/%s", modelType, nodeId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// DownloadGlobalModelApiV1FederatedClientModelDownloadPost 下载全局模型
func (c *FederatedLearningClient) DownloadGlobalModelApiV1FederatedClientModelDownloadPost(
	ctx context.Context,
	body *models.FederatedGlobalModelRequest,
) (*models.FederatedGlobalModelResponse, error) {
	params := url.Values{}

	var result models.FederatedGlobalModelResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/federated/client/model/download", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// UploadModelUpdateApiV1FederatedClientUpdateUploadPost 上传模型更新
func (c *FederatedLearningClient) UploadModelUpdateApiV1FederatedClientUpdateUploadPost(
	ctx context.Context,
	body *models.FederatedUpdateUploadRequest,
) (*models.FederatedUpdateUploadResponse, error) {
	params := url.Values{}

	var result models.FederatedUpdateUploadResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/federated/client/update/upload", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// DistributeGlobalModelApiV1FederatedClientModelDistributeModelTypeNodeIdPost 分发最新全局模型
func (c *FederatedLearningClient) DistributeGlobalModelApiV1FederatedClientModelDistributeModelTypeNodeIdPost(
	ctx context.Context,
	modelType string,
	nodeId string,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/federated/client/model/distribute/%s/%s", modelType, nodeId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetFederatedClientStatusApiV1FederatedClientStatusClientIdGet 获取客户端状态
func (c *FederatedLearningClient) GetFederatedClientStatusApiV1FederatedClientStatusClientIdGet(
	ctx context.Context,
	clientId string,
) (*models.FederatedClientStatusResponse, error) {
	params := url.Values{}

	var result models.FederatedClientStatusResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/federated/client/status/%s", clientId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// LocalTrainFederatedApiV1FederatedClientTrainLocalPost 执行本地训练
func (c *FederatedLearningClient) LocalTrainFederatedApiV1FederatedClientTrainLocalPost(
	ctx context.Context,
	body *models.FederatedLocalTrainRequest,
) (*models.FederatedLocalTrainResponse, error) {
	params := url.Values{}

	var result models.FederatedLocalTrainResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/federated/client/train/local", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetClientModelUpdateApiV1FederatedClientUpdateGetClientIdPost 获取客户端模型更新（用于上传）
func (c *FederatedLearningClient) GetClientModelUpdateApiV1FederatedClientUpdateGetClientIdPost(
	ctx context.Context,
	clientId string,
	applyPrivacy *bool,
) (*map[string]interface{}, error) {
	params := url.Values{}
	if applyPrivacy != nil {
		params.Set("apply_privacy", fmt.Sprintf("%v", *applyPrivacy))
	}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/federated/client/update/get/%s", clientId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ConfigurePrivacyApiV1FederatedConfigPrivacyPost 配置隐私保护参数
func (c *FederatedLearningClient) ConfigurePrivacyApiV1FederatedConfigPrivacyPost(
	ctx context.Context,
	body *models.FederatedPrivacyConfig,
	clientId string,
) (*map[string]interface{}, error) {
	params := url.Values{}
	params.Set("client_id", fmt.Sprintf("%v", clientId))

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/federated/config/privacy", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// ConfigureAggregatorApiV1FederatedConfigAggregatorPost 配置聚合器参数
func (c *FederatedLearningClient) ConfigureAggregatorApiV1FederatedConfigAggregatorPost(
	ctx context.Context,
	body *models.FederatedAggregatorConfig,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/federated/config/aggregator", ),
		params,
		body,
		&result,
	)
	return &result, err
}
