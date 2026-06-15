package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// LlmDiagnosisClient LLMDiagnosis API 客户端
type LlmDiagnosisClient struct {
	client *BaseClient
}

// NewLlmDiagnosisClient 创建 LLMDiagnosis API 客户端
func NewLlmDiagnosisClient(client *BaseClient) *LlmDiagnosisClient {
	return &LlmDiagnosisClient{client: client}
}

// GenerateDiagnosisReportApiV1ReportDiagnosisPost 生成单次诊断报告
func (c *LlmDiagnosisClient) GenerateDiagnosisReportApiV1ReportDiagnosisPost(
	ctx context.Context,
	body *models.DiagnosisReportRequest,
) (*models.DiagnosisReportResponse, error) {
	params := url.Values{}

	var result models.DiagnosisReportResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/report/diagnosis", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GeneratePeriodicReportApiV1ReportGeneratePost 生成周期报告（周报/月报）
func (c *LlmDiagnosisClient) GeneratePeriodicReportApiV1ReportGeneratePost(
	ctx context.Context,
	body *models.ReportGenerateRequest,
) (*models.PeriodicReportResponse, error) {
	params := url.Values{}

	var result models.PeriodicReportResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/report/generate", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// BatchGeneratePeriodicReportsApiV1ReportBatchGeneratePost 批量生成周期报告
func (c *LlmDiagnosisClient) BatchGeneratePeriodicReportsApiV1ReportBatchGeneratePost(
	ctx context.Context,
	body *models.BatchReportGenerateRequest,
) (*models.BatchReportResponse, error) {
	params := url.Values{}

	var result models.BatchReportResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/report/batch-generate", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetLlmConfigStatusApiV1ReportConfigGet 获取 LLM 配置状态
func (c *LlmDiagnosisClient) GetLlmConfigStatusApiV1ReportConfigGet(
	ctx context.Context,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/report/config", ),
		params,
		nil,
		&result,
	)
	return &result, err
}
