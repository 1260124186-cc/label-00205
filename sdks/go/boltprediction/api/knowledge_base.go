package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// KnowledgeBaseClient KnowledgeBase API 客户端
type KnowledgeBaseClient struct {
	client *BaseClient
}

// NewKnowledgeBaseClient 创建 KnowledgeBase API 客户端
func NewKnowledgeBaseClient(client *BaseClient) *KnowledgeBaseClient {
	return &KnowledgeBaseClient{client: client}
}

// CreateKnowledgeCaseApiV1KnowledgeCasesPost 创建案例
func (c *KnowledgeBaseClient) CreateKnowledgeCaseApiV1KnowledgeCasesPost(
	ctx context.Context,
	body *models.KnowledgeCaseCreateRequest,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/knowledge/cases", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// ListKnowledgeCasesApiV1KnowledgeCasesGet 查询案例列表
func (c *KnowledgeBaseClient) ListKnowledgeCasesApiV1KnowledgeCasesGet(
	ctx context.Context,
	status *interface{},
	nodeType *interface{},
	faultType *interface{},
	faultLevel *interface{},
	tenantId *interface{},
	keyword *interface{},
	limit *int,
	offset *int,
) (*models.KnowledgeCaseListResponse, error) {
	params := url.Values{}
	if status != nil {
		params.Set("status", fmt.Sprintf("%v", *status))
	}
	if nodeType != nil {
		params.Set("node_type", fmt.Sprintf("%v", *nodeType))
	}
	if faultType != nil {
		params.Set("fault_type", fmt.Sprintf("%v", *faultType))
	}
	if faultLevel != nil {
		params.Set("fault_level", fmt.Sprintf("%v", *faultLevel))
	}
	if tenantId != nil {
		params.Set("tenant_id", fmt.Sprintf("%v", *tenantId))
	}
	if keyword != nil {
		params.Set("keyword", fmt.Sprintf("%v", *keyword))
	}
	if limit != nil {
		params.Set("limit", fmt.Sprintf("%v", *limit))
	}
	if offset != nil {
		params.Set("offset", fmt.Sprintf("%v", *offset))
	}

	var result models.KnowledgeCaseListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/knowledge/cases", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetKnowledgeCaseApiV1KnowledgeCasesCaseIdGet 获取案例详情
func (c *KnowledgeBaseClient) GetKnowledgeCaseApiV1KnowledgeCasesCaseIdGet(
	ctx context.Context,
	caseId int,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/knowledge/cases/%s", caseId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// UpdateKnowledgeCaseApiV1KnowledgeCasesCaseIdPut 更新案例
func (c *KnowledgeBaseClient) UpdateKnowledgeCaseApiV1KnowledgeCasesCaseIdPut(
	ctx context.Context,
	caseId int,
	body *models.KnowledgeCaseUpdateRequest,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"PUT",
		fmt.Sprintf("/api/v1/api/v1/knowledge/cases/%s", caseId),
		params,
		body,
		&result,
	)
	return &result, err
}

// DeleteKnowledgeCaseApiV1KnowledgeCasesCaseIdDelete 删除案例
func (c *KnowledgeBaseClient) DeleteKnowledgeCaseApiV1KnowledgeCasesCaseIdDelete(
	ctx context.Context,
	caseId int,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"DELETE",
		fmt.Sprintf("/api/v1/api/v1/knowledge/cases/%s", caseId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// SubmitCaseForReviewApiV1KnowledgeCasesCaseIdSubmitReviewPost 提交审核
func (c *KnowledgeBaseClient) SubmitCaseForReviewApiV1KnowledgeCasesCaseIdSubmitReviewPost(
	ctx context.Context,
	caseId int,
	operatorId *interface{},
	operatorName *interface{},
) (*map[string]interface{}, error) {
	params := url.Values{}
	if operatorId != nil {
		params.Set("operator_id", fmt.Sprintf("%v", *operatorId))
	}
	if operatorName != nil {
		params.Set("operator_name", fmt.Sprintf("%v", *operatorName))
	}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/knowledge/cases/%s/submit-review", caseId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ReviewKnowledgeCaseApiV1KnowledgeCasesCaseIdReviewPost 审核案例
func (c *KnowledgeBaseClient) ReviewKnowledgeCaseApiV1KnowledgeCasesCaseIdReviewPost(
	ctx context.Context,
	caseId int,
	body *models.CaseReviewRequest,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/knowledge/cases/%s/review", caseId),
		params,
		body,
		&result,
	)
	return &result, err
}

// ListCaseReviewsApiV1KnowledgeCasesCaseIdReviewsGet 获取审核记录
func (c *KnowledgeBaseClient) ListCaseReviewsApiV1KnowledgeCasesCaseIdReviewsGet(
	ctx context.Context,
	caseId int,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/knowledge/cases/%s/reviews", caseId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ListCaseVersionsApiV1KnowledgeCasesCaseIdVersionsGet 获取版本历史
func (c *KnowledgeBaseClient) ListCaseVersionsApiV1KnowledgeCasesCaseIdVersionsGet(
	ctx context.Context,
	caseId int,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/knowledge/cases/%s/versions", caseId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetCaseVersionApiV1KnowledgeCasesCaseIdVersionsVersionGet 获取指定版本
func (c *KnowledgeBaseClient) GetCaseVersionApiV1KnowledgeCasesCaseIdVersionsVersionGet(
	ctx context.Context,
	caseId int,
	version int,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/knowledge/cases/%s/versions/%s", caseId, version),
		params,
		nil,
		&result,
	)
	return &result, err
}

// CompareCaseVersionsApiV1KnowledgeCasesCaseIdVersionsCompareGet 对比版本差异
func (c *KnowledgeBaseClient) CompareCaseVersionsApiV1KnowledgeCasesCaseIdVersionsCompareGet(
	ctx context.Context,
	caseId int,
	versionFrom int,
	versionTo int,
) (*map[string]interface{}, error) {
	params := url.Values{}
	params.Set("version_from", fmt.Sprintf("%v", versionFrom))
	params.Set("version_to", fmt.Sprintf("%v", versionTo))

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/knowledge/cases/%s/versions/compare", caseId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// RevertCaseToVersionApiV1KnowledgeCasesCaseIdVersionsVersionRevertPost 回退到指定版本
func (c *KnowledgeBaseClient) RevertCaseToVersionApiV1KnowledgeCasesCaseIdVersionsVersionRevertPost(
	ctx context.Context,
	caseId int,
	version int,
	operatorId *interface{},
	operatorName *interface{},
) (*map[string]interface{}, error) {
	params := url.Values{}
	if operatorId != nil {
		params.Set("operator_id", fmt.Sprintf("%v", *operatorId))
	}
	if operatorName != nil {
		params.Set("operator_name", fmt.Sprintf("%v", *operatorName))
	}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/knowledge/cases/%s/versions/%s/revert", caseId, version),
		params,
		nil,
		&result,
	)
	return &result, err
}

// SearchSimilarCasesApiV1KnowledgeCasesSearchSimilarPost 检索相似案例 (Top-K)
func (c *KnowledgeBaseClient) SearchSimilarCasesApiV1KnowledgeCasesSearchSimilarPost(
	ctx context.Context,
	body *models.CaseSimilaritySearchRequest,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/knowledge/cases/search/similar", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetCaseRecommendationsApiV1KnowledgeCasesRecommendPost 获取案例推荐 (推荐措施 + RAG上下文)
func (c *KnowledgeBaseClient) GetCaseRecommendationsApiV1KnowledgeCasesRecommendPost(
	ctx context.Context,
	body *models.CaseSimilaritySearchRequest,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/knowledge/cases/recommend", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetKnowledgeStatisticsApiV1KnowledgeStatisticsGet 获取知识库统计
func (c *KnowledgeBaseClient) GetKnowledgeStatisticsApiV1KnowledgeStatisticsGet(
	ctx context.Context,
	tenantId *interface{},
) (*map[string]interface{}, error) {
	params := url.Values{}
	if tenantId != nil {
		params.Set("tenant_id", fmt.Sprintf("%v", *tenantId))
	}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/knowledge/statistics", ),
		params,
		nil,
		&result,
	)
	return &result, err
}
