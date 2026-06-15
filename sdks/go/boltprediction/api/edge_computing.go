package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// EdgeComputingClient EdgeComputing API 客户端
type EdgeComputingClient struct {
	client *BaseClient
}

// NewEdgeComputingClient 创建 EdgeComputing API 客户端
func NewEdgeComputingClient(client *BaseClient) *EdgeComputingClient {
	return &EdgeComputingClient{client: client}
}

// RegisterEdgeDeviceApiV1EdgeDeviceRegisterPost 注册边缘设备
func (c *EdgeComputingClient) RegisterEdgeDeviceApiV1EdgeDeviceRegisterPost(
	ctx context.Context,
	body *models.EdgeDeviceRegisterRequest,
) (*models.EdgeDeviceRegisterResponse, error) {
	params := url.Values{}

	var result models.EdgeDeviceRegisterResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/edge/device/register", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// EdgeDeviceHeartbeatApiV1EdgeDeviceHeartbeatPost 边缘设备心跳
func (c *EdgeComputingClient) EdgeDeviceHeartbeatApiV1EdgeDeviceHeartbeatPost(
	ctx context.Context,
	body *models.EdgeDeviceHeartbeatRequest,
) (*models.EdgeDeviceHeartbeatResponse, error) {
	params := url.Values{}

	var result models.EdgeDeviceHeartbeatResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/edge/device/heartbeat", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetEdgeModelLatestApiV1EdgeModelLatestPost 获取最新模型版本信息
func (c *EdgeComputingClient) GetEdgeModelLatestApiV1EdgeModelLatestPost(
	ctx context.Context,
	body *models.EdgeModelLatestRequest,
) (*models.EdgeModelLatestResponse, error) {
	params := url.Values{}

	var result models.EdgeModelLatestResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/edge/model/latest", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// DownloadEdgeModelApiV1EdgeModelDownloadVersionGet 下载模型包
func (c *EdgeComputingClient) DownloadEdgeModelApiV1EdgeModelDownloadVersionGet(
	ctx context.Context,
	version string,
	modelType *string,
	nodeId *interface{},
	format *string,
) (*map[string]interface{}, error) {
	params := url.Values{}
	if modelType != nil {
		params.Set("model_type", fmt.Sprintf("%v", *modelType))
	}
	if nodeId != nil {
		params.Set("node_id", fmt.Sprintf("%v", *nodeId))
	}
	if format != nil {
		params.Set("format", fmt.Sprintf("%v", *format))
	}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/edge/model/download/%s", version),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ExportEdgeModelApiV1EdgeModelExportPost 导出边缘模型包
func (c *EdgeComputingClient) ExportEdgeModelApiV1EdgeModelExportPost(
	ctx context.Context,
	body *models.EdgeModelExportRequest,
) (*models.EdgeModelExportResponse, error) {
	params := url.Values{}

	var result models.EdgeModelExportResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/edge/model/export", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// UploadEdgePredictionsApiV1EdgePredictionsUploadPost 批量上报边缘预测结果
func (c *EdgeComputingClient) UploadEdgePredictionsApiV1EdgePredictionsUploadPost(
	ctx context.Context,
	body *models.EdgePredictionUploadRequest,
) (*models.EdgePredictionUploadResponse, error) {
	params := url.Values{}

	var result models.EdgePredictionUploadResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/edge/predictions/upload", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// ListEdgeDevicesApiV1EdgeDeviceStatusGet 获取所有边缘设备状态
func (c *EdgeComputingClient) ListEdgeDevicesApiV1EdgeDeviceStatusGet(
	ctx context.Context,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/edge/device/status", ),
		params,
		nil,
		&result,
	)
	return &result, err
}
