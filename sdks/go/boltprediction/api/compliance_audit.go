package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// ComplianceAuditClient ComplianceAudit API 客户端
type ComplianceAuditClient struct {
	client *BaseClient
}

// NewComplianceAuditClient 创建 ComplianceAudit API 客户端
func NewComplianceAuditClient(client *BaseClient) *ComplianceAuditClient {
	return &ComplianceAuditClient{client: client}
}

// ListAuditRecordsApiV1AuditRecordsGet 查询审计记录列表
func (c *ComplianceAuditClient) ListAuditRecordsApiV1AuditRecordsGet(
	ctx context.Context,
	nodeType *interface{},
	nodeId *interface{},
	modelVersion *interface{},
	startTime *interface{},
	endTime *interface{},
	limit *int,
	offset *int,
) (*models.AuditListResponse, error) {
	params := url.Values{}
	if nodeType != nil {
		params.Set("node_type", fmt.Sprintf("%v", *nodeType))
	}
	if nodeId != nil {
		params.Set("node_id", fmt.Sprintf("%v", *nodeId))
	}
	if modelVersion != nil {
		params.Set("model_version", fmt.Sprintf("%v", *modelVersion))
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
	if offset != nil {
		params.Set("offset", fmt.Sprintf("%v", *offset))
	}

	var result models.AuditListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/audit/records", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetAuditRecordApiV1AuditRecordsAuditIdGet 获取审计记录详情
func (c *ComplianceAuditClient) GetAuditRecordApiV1AuditRecordsAuditIdGet(
	ctx context.Context,
	auditId int,
) (*models.AuditRecordResponse, error) {
	params := url.Values{}

	var result models.AuditRecordResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/audit/records/%s", auditId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// UpdateAuditRetentionApiV1AuditRecordsAuditIdRetentionPut 更新审计记录保留年限
func (c *ComplianceAuditClient) UpdateAuditRetentionApiV1AuditRecordsAuditIdRetentionPut(
	ctx context.Context,
	auditId int,
	body *models.AuditRetentionUpdateRequest,
) (*models.AuditRecordResponse, error) {
	params := url.Values{}

	var result models.AuditRecordResponse
	err := c.client.Request(
		ctx,
		"PUT",
		fmt.Sprintf("/api/v1/api/v1/audit/records/%s/retention", auditId),
		params,
		body,
		&result,
	)
	return &result, err
}

// CleanupExpiredAuditsApiV1AuditCleanupPost 清理过期审计记录
func (c *ComplianceAuditClient) CleanupExpiredAuditsApiV1AuditCleanupPost(
	ctx context.Context,
) (*models.AuditCleanupResponse, error) {
	params := url.Values{}

	var result models.AuditCleanupResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/audit/cleanup", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ExportAuditPackageApiV1AuditExportPost 导出审计包
func (c *ComplianceAuditClient) ExportAuditPackageApiV1AuditExportPost(
	ctx context.Context,
	body *models.AuditExportRequest,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/audit/export", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetExplainabilityReportApiV1AuditRecordsAuditIdExplainabilityGet 获取可解释性报告
func (c *ComplianceAuditClient) GetExplainabilityReportApiV1AuditRecordsAuditIdExplainabilityGet(
	ctx context.Context,
	auditId int,
) (*models.ExplainabilityReportResponse, error) {
	params := url.Values{}

	var result models.ExplainabilityReportResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/audit/records/%s/explainability", auditId),
		params,
		nil,
		&result,
	)
	return &result, err
}
