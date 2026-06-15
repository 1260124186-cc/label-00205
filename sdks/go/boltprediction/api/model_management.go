package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// ModelManagementClient ModelManagement API 客户端
type ModelManagementClient struct {
	client *BaseClient
}

// NewModelManagementClient 创建 ModelManagement API 客户端
func NewModelManagementClient(client *BaseClient) *ModelManagementClient {
	return &ModelManagementClient{client: client}
}

// TrainModelApiV1ModelTrainPost 训练模型
func (c *ModelManagementClient) TrainModelApiV1ModelTrainPost(
	ctx context.Context,
	body *models.TrainingRequest,
) (*models.TrainingResponse, error) {
	params := url.Values{}

	var result models.TrainingResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/model/train", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetModelInfoApiV1ModelInfoModelTypeNodeIdGet 获取模型信息
func (c *ModelManagementClient) GetModelInfoApiV1ModelInfoModelTypeNodeIdGet(
	ctx context.Context,
	modelType string,
	nodeId string,
) (*models.ModelInfoResponse, error) {
	params := url.Values{}

	var result models.ModelInfoResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/model/info/%s/%s", modelType, nodeId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// TrainModelEnhancedApiV1ModelTrainEnhancedPost 增强版训练模型（增量训练/学习率调度/类不平衡等）
func (c *ModelManagementClient) TrainModelEnhancedApiV1ModelTrainEnhancedPost(
	ctx context.Context,
	body *models.EnhancedTrainingRequest,
) (*models.EnhancedTrainingResponse, error) {
	params := url.Values{}

	var result models.EnhancedTrainingResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/model/train/enhanced", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetTrainingStatusEndpointApiV1ModelTrainStatusSessionIdGet 查询训练状态
func (c *ModelManagementClient) GetTrainingStatusEndpointApiV1ModelTrainStatusSessionIdGet(
	ctx context.Context,
	sessionId string,
) (*models.TrainingStatusResponse, error) {
	params := url.Values{}

	var result models.TrainingStatusResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/model/train/status/%s", sessionId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ListTrainingSessionsApiV1ModelTrainSessionsGet 列出训练会话历史
func (c *ModelManagementClient) ListTrainingSessionsApiV1ModelTrainSessionsGet(
	ctx context.Context,
	modelType *interface{},
	status *interface{},
	limit *int,
) (*models.TrainingSessionListResponse, error) {
	params := url.Values{}
	if modelType != nil {
		params.Set("model_type", fmt.Sprintf("%v", *modelType))
	}
	if status != nil {
		params.Set("status", fmt.Sprintf("%v", *status))
	}
	if limit != nil {
		params.Set("limit", fmt.Sprintf("%v", *limit))
	}

	var result models.TrainingSessionListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/model/train/sessions", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ListModelVersionsApiV1ModelVersionsModelTypeNodeIdGet 列出模型版本历史
func (c *ModelManagementClient) ListModelVersionsApiV1ModelVersionsModelTypeNodeIdGet(
	ctx context.Context,
	modelType string,
	nodeId string,
) (*models.ModelVersionListResponse, error) {
	params := url.Values{}

	var result models.ModelVersionListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/model/versions/%s/%s", modelType, nodeId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ActivateModelVersionApiV1ModelActivatePost 激活指定模型版本
func (c *ModelManagementClient) ActivateModelVersionApiV1ModelActivatePost(
	ctx context.Context,
	body *models.ModelVersionActivateRequest,
) (*models.ModelVersionSchema, error) {
	params := url.Values{}

	var result models.ModelVersionSchema
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/model/activate", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// RollbackModelVersionApiV1ModelRollbackPost 回滚模型版本
func (c *ModelManagementClient) RollbackModelVersionApiV1ModelRollbackPost(
	ctx context.Context,
	body *models.ModelVersionRollbackRequest,
) (*models.ModelVersionSchema, error) {
	params := url.Values{}

	var result models.ModelVersionSchema
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/model/rollback", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// CleanupOldVersionsApiV1ModelVersionsModelTypeNodeIdCleanupPost 手动清理旧版本
func (c *ModelManagementClient) CleanupOldVersionsApiV1ModelVersionsModelTypeNodeIdCleanupPost(
	ctx context.Context,
	modelType string,
	nodeId string,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/model/versions/%s/%s/cleanup", modelType, nodeId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ListImportFilesApiV1ModelLabelImportFilesGet 列出可导入的标注CSV文件
func (c *ModelManagementClient) ListImportFilesApiV1ModelLabelImportFilesGet(
	ctx context.Context,
) (*models.LabelImportFileListResponse, error) {
	params := url.Values{}

	var result models.LabelImportFileListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/model/label/import/files", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ImportLabelsFromCsvApiV1ModelLabelImportCsvPost 从CSV导入人工标注数据
func (c *ModelManagementClient) ImportLabelsFromCsvApiV1ModelLabelImportCsvPost(
	ctx context.Context,
	body *models.LabelImportCsvRequest,
) (*models.LabelImportResponse, error) {
	params := url.Values{}

	var result models.LabelImportResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/model/label/import/csv", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// ImportLabelsFromDbApiV1ModelLabelImportDbPost 从数据库表导入人工标注数据
func (c *ModelManagementClient) ImportLabelsFromDbApiV1ModelLabelImportDbPost(
	ctx context.Context,
	body *models.LabelImportDbRequest,
) (*models.LabelImportResponse, error) {
	params := url.Values{}

	var result models.LabelImportResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/model/label/import/db", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetModelVersionsApiV1ModelVersionsModelTypeModelIdGet 获取模型版本列表
func (c *ModelManagementClient) GetModelVersionsApiV1ModelVersionsModelTypeModelIdGet(
	ctx context.Context,
	modelType string,
	modelId string,
) (*models.ModelVersionListResponse, error) {
	params := url.Values{}

	var result models.ModelVersionListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/model/versions/%s/%s", modelType, modelId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetActiveModelVersionApiV1ModelVersionsModelTypeModelIdActiveGet 获取当前活动版本
func (c *ModelManagementClient) GetActiveModelVersionApiV1ModelVersionsModelTypeModelIdActiveGet(
	ctx context.Context,
	modelType string,
	modelId string,
) (*models.ModelVersionSchema, error) {
	params := url.Values{}

	var result models.ModelVersionSchema
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/model/versions/%s/%s/active", modelType, modelId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ActivateModelVersionApiV1ModelVersionsModelTypeModelIdActivatePost 激活/回滚模型版本
func (c *ModelManagementClient) ActivateModelVersionApiV1ModelVersionsModelTypeModelIdActivatePost(
	ctx context.Context,
	modelType string,
	modelId string,
	body *models.ModelVersionActivateRequest,
) (*models.ModelVersionSchema, error) {
	params := url.Values{}

	var result models.ModelVersionSchema
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/model/versions/%s/%s/activate", modelType, modelId),
		params,
		body,
		&result,
	)
	return &result, err
}

// CompareModelVersionsApiV1ModelVersionsModelTypeModelIdComparePost 对比两个模型版本
func (c *ModelManagementClient) CompareModelVersionsApiV1ModelVersionsModelTypeModelIdComparePost(
	ctx context.Context,
	modelType string,
	modelId string,
	body *models.ModelVersionCompareRequest,
) (*models.ModelVersionCompareResponse, error) {
	params := url.Values{}

	var result models.ModelVersionCompareResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/model/versions/%s/%s/compare", modelType, modelId),
		params,
		body,
		&result,
	)
	return &result, err
}

// DeleteModelVersionApiV1ModelVersionsModelTypeModelIdVersionDelete 删除模型版本
func (c *ModelManagementClient) DeleteModelVersionApiV1ModelVersionsModelTypeModelIdVersionDelete(
	ctx context.Context,
	modelType string,
	modelId string,
	version string,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"DELETE",
		fmt.Sprintf("/api/v1/api/v1/model/versions/%s/%s/%s", modelType, modelId, version),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetTrainingStatusApiV1ModelTrainingStatusGet 获取训练状态
func (c *ModelManagementClient) GetTrainingStatusApiV1ModelTrainingStatusGet(
	ctx context.Context,
) (*models.TrainingStatusResponse, error) {
	params := url.Values{}

	var result models.TrainingStatusResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/model/training/status", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ListTrainingSessionsApiV1ModelTrainingSessionsGet 获取训练会话列表
func (c *ModelManagementClient) ListTrainingSessionsApiV1ModelTrainingSessionsGet(
	ctx context.Context,
	limit *int,
) (*models.TrainingSessionListResponse, error) {
	params := url.Values{}
	if limit != nil {
		params.Set("limit", fmt.Sprintf("%v", *limit))
	}

	var result models.TrainingSessionListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/model/training/sessions", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetTrainingSessionApiV1ModelTrainingSessionsSessionIdGet 获取训练会话详情
func (c *ModelManagementClient) GetTrainingSessionApiV1ModelTrainingSessionsSessionIdGet(
	ctx context.Context,
	sessionId string,
) (*models.TrainingSessionSchema, error) {
	params := url.Values{}

	var result models.TrainingSessionSchema
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/model/training/sessions/%s", sessionId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ListAllModelsApiV1ModelListGet 获取所有模型列表
func (c *ModelManagementClient) ListAllModelsApiV1ModelListGet(
	ctx context.Context,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/model/list", ),
		params,
		nil,
		&result,
	)
	return &result, err
}
