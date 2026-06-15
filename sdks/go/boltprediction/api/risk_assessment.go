package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// RiskAssessmentClient RiskAssessment API 客户端
type RiskAssessmentClient struct {
	client *BaseClient
}

// NewRiskAssessmentClient 创建 RiskAssessment API 客户端
func NewRiskAssessmentClient(client *BaseClient) *RiskAssessmentClient {
	return &RiskAssessmentClient{client: client}
}

// AssessRiskApiV1RiskAssessPost 风险评估
func (c *RiskAssessmentClient) AssessRiskApiV1RiskAssessPost(
	ctx context.Context,
	body *models.RiskAssessmentRequest,
	validationMode *string,
) (*models.RiskAssessmentResponse, error) {
	params := url.Values{}
	if validationMode != nil {
		params.Set("validation_mode", fmt.Sprintf("%v", *validationMode))
	}

	var result models.RiskAssessmentResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/risk/assess", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// AssessRiskExplainApiV1RiskAssessExplainPost 风险评估可解释性分析
func (c *RiskAssessmentClient) AssessRiskExplainApiV1RiskAssessExplainPost(
	ctx context.Context,
	body *models.RiskAssessExplainRequest,
	validationMode *string,
) (*models.RiskAssessExplainResponse, error) {
	params := url.Values{}
	if validationMode != nil {
		params.Set("validation_mode", fmt.Sprintf("%v", *validationMode))
	}

	var result models.RiskAssessExplainResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/risk/assess/explain", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// UpdateRiskCalibrationApiV1RiskCalibrationPost 更新节点级风险校准配置
func (c *RiskAssessmentClient) UpdateRiskCalibrationApiV1RiskCalibrationPost(
	ctx context.Context,
	body *models.RiskCalibrationUpdateRequest,
) (*models.RiskCalibrationResponse, error) {
	params := url.Values{}

	var result models.RiskCalibrationResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/risk/calibration", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetRiskCalibrationApiV1RiskCalibrationGet 查询节点级风险校准配置
func (c *RiskAssessmentClient) GetRiskCalibrationApiV1RiskCalibrationGet(
	ctx context.Context,
	nodeType string,
	nodeId string,
) (*models.RiskCalibrationResponse, error) {
	params := url.Values{}
	params.Set("node_type", fmt.Sprintf("%v", nodeType))
	params.Set("node_id", fmt.Sprintf("%v", nodeId))

	var result models.RiskCalibrationResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/risk/calibration", ),
		params,
		nil,
		&result,
	)
	return &result, err
}
