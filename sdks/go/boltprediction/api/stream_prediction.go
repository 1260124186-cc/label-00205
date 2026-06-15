package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// StreamPredictionClient StreamPrediction API 客户端
type StreamPredictionClient struct {
	client *BaseClient
}

// NewStreamPredictionClient 创建 StreamPrediction API 客户端
func NewStreamPredictionClient(client *BaseClient) *StreamPredictionClient {
	return &StreamPredictionClient{client: client}
}

// StreamIngestApiV1StreamIngestPost 流式数据注入
func (c *StreamPredictionClient) StreamIngestApiV1StreamIngestPost(
	ctx context.Context,
	body *models.StreamDataIngestRequest,
) (*models.StreamDataIngestResponse, error) {
	params := url.Values{}

	var result models.StreamDataIngestResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/stream/ingest", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// StreamIngestBatchApiV1StreamIngestBatchPost 批量流式数据注入
func (c *StreamPredictionClient) StreamIngestBatchApiV1StreamIngestBatchPost(
	ctx context.Context,
	body *models.StreamBatchIngestRequest,
) (*models.StreamBatchIngestResponse, error) {
	params := url.Values{}

	var result models.StreamBatchIngestResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/stream/ingest/batch", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetStreamWindowApiV1StreamWindowBoltIdGet 获取窗口状态
func (c *StreamPredictionClient) GetStreamWindowApiV1StreamWindowBoltIdGet(
	ctx context.Context,
	boltId string,
) (*models.StreamWindowStatusResponse, error) {
	params := url.Values{}

	var result models.StreamWindowStatusResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/stream/window/%s", boltId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ClearStreamWindowApiV1StreamWindowBoltIdDelete 清空指定螺栓窗口
func (c *StreamPredictionClient) ClearStreamWindowApiV1StreamWindowBoltIdDelete(
	ctx context.Context,
	boltId string,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"DELETE",
		fmt.Sprintf("/api/v1/api/v1/stream/window/%s", boltId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetStreamEngineStatusApiV1StreamStatusGet 获取流式预测引擎状态
func (c *StreamPredictionClient) GetStreamEngineStatusApiV1StreamStatusGet(
	ctx context.Context,
) (*models.StreamEngineStatusResponse, error) {
	params := url.Values{}

	var result models.StreamEngineStatusResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/stream/status", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// SwitchPredictionModeApiV1StreamModePost 切换预测模式
func (c *StreamPredictionClient) SwitchPredictionModeApiV1StreamModePost(
	ctx context.Context,
	body *models.StreamModeSwitchRequest,
) (*models.StreamModeSwitchResponse, error) {
	params := url.Values{}

	var result models.StreamModeSwitchResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/stream/mode", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// StartStreamEngineApiV1StreamStartPost 启动流式预测引擎
func (c *StreamPredictionClient) StartStreamEngineApiV1StreamStartPost(
	ctx context.Context,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/stream/start", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// StopStreamEngineApiV1StreamStopPost 停止流式预测引擎
func (c *StreamPredictionClient) StopStreamEngineApiV1StreamStopPost(
	ctx context.Context,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/stream/stop", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// UpdateStreamConfigApiV1StreamConfigPost 更新流式预测配置
func (c *StreamPredictionClient) UpdateStreamConfigApiV1StreamConfigPost(
	ctx context.Context,
	body *models.StreamConfigUpdateRequest,
) (*models.StreamConfigResponse, error) {
	params := url.Values{}

	var result models.StreamConfigResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/stream/config", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// ClearAllStreamWindowsApiV1StreamWindowsDelete 清空所有窗口
func (c *StreamPredictionClient) ClearAllStreamWindowsApiV1StreamWindowsDelete(
	ctx context.Context,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"DELETE",
		fmt.Sprintf("/api/v1/api/v1/stream/windows", ),
		params,
		nil,
		&result,
	)
	return &result, err
}
