package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// CarbonAnalysisClient CarbonAnalysis API 客户端
type CarbonAnalysisClient struct {
	client *BaseClient
}

// NewCarbonAnalysisClient 创建 CarbonAnalysis API 客户端
func NewCarbonAnalysisClient(client *BaseClient) *CarbonAnalysisClient {
	return &CarbonAnalysisClient{client: client}
}

// GetCarbonMonthlyRankingApiV1CarbonRankingMonthlyPost 装置级月度碳排风险贡献排行
func (c *CarbonAnalysisClient) GetCarbonMonthlyRankingApiV1CarbonRankingMonthlyPost(
	ctx context.Context,
	body *models.CarbonMonthlyRankingRequest,
) (*models.CarbonMonthlyRankingResponse, error) {
	params := url.Values{}

	var result models.CarbonMonthlyRankingResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/carbon/ranking/monthly", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetHiCarbonDualViewApiV1CarbonHiDualViewPost HI rollup 与碳排并列展示
func (c *CarbonAnalysisClient) GetHiCarbonDualViewApiV1CarbonHiDualViewPost(
	ctx context.Context,
	body *models.HiCarbonDualViewRequest,
) (*models.HiCarbonDualViewResponse, error) {
	params := url.Values{}

	var result models.HiCarbonDualViewResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/carbon/hi-dual-view", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// ExportEsgReportFragmentApiV1CarbonEsgExportPost 导出 ESG 报表片段
func (c *CarbonAnalysisClient) ExportEsgReportFragmentApiV1CarbonEsgExportPost(
	ctx context.Context,
	body *models.EsgReportExportRequest,
) (*models.EsgReportFragmentResponse, error) {
	params := url.Values{}

	var result models.EsgReportFragmentResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/carbon/esg/export", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetCarbonModelConfigApiV1CarbonConfigGet 获取碳排模型系数配置
func (c *CarbonAnalysisClient) GetCarbonModelConfigApiV1CarbonConfigGet(
	ctx context.Context,
) (*models.CarbonModelConfigResponse, error) {
	params := url.Values{}

	var result models.CarbonModelConfigResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/carbon/config", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// UpdateCarbonModelConfigApiV1CarbonConfigPost 更新碳排模型系数配置
func (c *CarbonAnalysisClient) UpdateCarbonModelConfigApiV1CarbonConfigPost(
	ctx context.Context,
	body *models.CarbonModelConfigUpdateRequest,
) (*models.CarbonModelConfigResponse, error) {
	params := url.Values{}

	var result models.CarbonModelConfigResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/carbon/config", ),
		params,
		body,
		&result,
	)
	return &result, err
}
