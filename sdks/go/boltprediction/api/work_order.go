package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// WorkOrderClient WorkOrder API 客户端
type WorkOrderClient struct {
	client *BaseClient
}

// NewWorkOrderClient 创建 WorkOrder API 客户端
func NewWorkOrderClient(client *BaseClient) *WorkOrderClient {
	return &WorkOrderClient{client: client}
}

// ListWorkOrdersApiV1WorkOrdersGet 查询工单列表
func (c *WorkOrderClient) ListWorkOrdersApiV1WorkOrdersGet(
	ctx context.Context,
	status *interface{},
	priority *interface{},
	assigneeId *interface{},
	alertId *interface{},
	nodeType *interface{},
	nodeId *interface{},
	limit *int,
	offset *int,
) (*models.WorkOrderListResponse, error) {
	params := url.Values{}
	if status != nil {
		params.Set("status", fmt.Sprintf("%v", *status))
	}
	if priority != nil {
		params.Set("priority", fmt.Sprintf("%v", *priority))
	}
	if assigneeId != nil {
		params.Set("assignee_id", fmt.Sprintf("%v", *assigneeId))
	}
	if alertId != nil {
		params.Set("alert_id", fmt.Sprintf("%v", *alertId))
	}
	if nodeType != nil {
		params.Set("node_type", fmt.Sprintf("%v", *nodeType))
	}
	if nodeId != nil {
		params.Set("node_id", fmt.Sprintf("%v", *nodeId))
	}
	if limit != nil {
		params.Set("limit", fmt.Sprintf("%v", *limit))
	}
	if offset != nil {
		params.Set("offset", fmt.Sprintf("%v", *offset))
	}

	var result models.WorkOrderListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/work-orders", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// CreateWorkOrderApiV1WorkOrdersPost 手动创建工单
func (c *WorkOrderClient) CreateWorkOrderApiV1WorkOrdersPost(
	ctx context.Context,
	body *models.WorkOrderCreate,
) (*models.WorkOrderResponse, error) {
	params := url.Values{}

	var result models.WorkOrderResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/work-orders", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetWorkOrderApiV1WorkOrdersWorkOrderIdGet 获取工单详情
func (c *WorkOrderClient) GetWorkOrderApiV1WorkOrdersWorkOrderIdGet(
	ctx context.Context,
	workOrderId int,
) (*models.WorkOrderResponse, error) {
	params := url.Values{}

	var result models.WorkOrderResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/work-orders/%s", workOrderId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// UpdateWorkOrderApiV1WorkOrdersWorkOrderIdPut 更新工单信息
func (c *WorkOrderClient) UpdateWorkOrderApiV1WorkOrdersWorkOrderIdPut(
	ctx context.Context,
	workOrderId int,
	body *models.WorkOrderUpdate,
) (*models.WorkOrderResponse, error) {
	params := url.Values{}

	var result models.WorkOrderResponse
	err := c.client.Request(
		ctx,
		"PUT",
		fmt.Sprintf("/api/v1/api/v1/work-orders/%s", workOrderId),
		params,
		body,
		&result,
	)
	return &result, err
}

// AssignWorkOrderApiV1WorkOrdersWorkOrderIdAssignPost 指派工单
func (c *WorkOrderClient) AssignWorkOrderApiV1WorkOrdersWorkOrderIdAssignPost(
	ctx context.Context,
	workOrderId int,
	body *models.WorkOrderAssignRequest,
) (*models.WorkOrderResponse, error) {
	params := url.Values{}

	var result models.WorkOrderResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/work-orders/%s/assign", workOrderId),
		params,
		body,
		&result,
	)
	return &result, err
}

// UpdateWorkOrderStatusApiV1WorkOrdersWorkOrderIdStatusPost 更新工单状态
func (c *WorkOrderClient) UpdateWorkOrderStatusApiV1WorkOrdersWorkOrderIdStatusPost(
	ctx context.Context,
	workOrderId int,
	body *models.WorkOrderStatusUpdateRequest,
) (*models.WorkOrderResponse, error) {
	params := url.Values{}

	var result models.WorkOrderResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/work-orders/%s/status", workOrderId),
		params,
		body,
		&result,
	)
	return &result, err
}

// ResolveWorkOrderApiV1WorkOrdersWorkOrderIdResolvePost 解决工单
func (c *WorkOrderClient) ResolveWorkOrderApiV1WorkOrdersWorkOrderIdResolvePost(
	ctx context.Context,
	workOrderId int,
	body *models.WorkOrderResolveRequest,
) (*models.WorkOrderResponse, error) {
	params := url.Values{}

	var result models.WorkOrderResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/work-orders/%s/resolve", workOrderId),
		params,
		body,
		&result,
	)
	return &result, err
}

// ListWorkOrderDisposalsApiV1WorkOrdersWorkOrderIdDisposalsGet 查询工单处置记录列表
func (c *WorkOrderClient) ListWorkOrderDisposalsApiV1WorkOrdersWorkOrderIdDisposalsGet(
	ctx context.Context,
	workOrderId int,
	disposalType *interface{},
	limit *int,
	offset *int,
) (*models.DisposalRecordListResponse, error) {
	params := url.Values{}
	if disposalType != nil {
		params.Set("disposal_type", fmt.Sprintf("%v", *disposalType))
	}
	if limit != nil {
		params.Set("limit", fmt.Sprintf("%v", *limit))
	}
	if offset != nil {
		params.Set("offset", fmt.Sprintf("%v", *offset))
	}

	var result models.DisposalRecordListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/work-orders/%s/disposals", workOrderId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// CreateDisposalRecordApiV1WorkOrdersDisposalsPost 创建处置记录
func (c *WorkOrderClient) CreateDisposalRecordApiV1WorkOrdersDisposalsPost(
	ctx context.Context,
	body *models.DisposalRecordCreate,
) (*models.DisposalRecordResponse, error) {
	params := url.Values{}

	var result models.DisposalRecordResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/work-orders/disposals", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetDisposalRecordApiV1WorkOrdersDisposalsRecordIdGet 获取处置记录详情
func (c *WorkOrderClient) GetDisposalRecordApiV1WorkOrdersDisposalsRecordIdGet(
	ctx context.Context,
	recordId int,
) (*models.DisposalRecordResponse, error) {
	params := url.Values{}

	var result models.DisposalRecordResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/work-orders/disposals/%s", recordId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// UpdateDisposalRecordApiV1WorkOrdersDisposalsRecordIdPut 更新处置记录
func (c *WorkOrderClient) UpdateDisposalRecordApiV1WorkOrdersDisposalsRecordIdPut(
	ctx context.Context,
	recordId int,
	body *models.DisposalRecordUpdate,
) (*models.DisposalRecordResponse, error) {
	params := url.Values{}

	var result models.DisposalRecordResponse
	err := c.client.Request(
		ctx,
		"PUT",
		fmt.Sprintf("/api/v1/api/v1/work-orders/disposals/%s", recordId),
		params,
		body,
		&result,
	)
	return &result, err
}

// DeleteDisposalRecordApiV1WorkOrdersDisposalsRecordIdDelete 删除处置记录
func (c *WorkOrderClient) DeleteDisposalRecordApiV1WorkOrdersDisposalsRecordIdDelete(
	ctx context.Context,
	recordId int,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"DELETE",
		fmt.Sprintf("/api/v1/api/v1/work-orders/disposals/%s", recordId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ListWorkOrderRetestsApiV1WorkOrdersWorkOrderIdRetestsGet 查询工单复测记录列表
func (c *WorkOrderClient) ListWorkOrderRetestsApiV1WorkOrdersWorkOrderIdRetestsGet(
	ctx context.Context,
	workOrderId int,
	retestResult *interface{},
	limit *int,
	offset *int,
) (*models.RetestRecordListResponse, error) {
	params := url.Values{}
	if retestResult != nil {
		params.Set("retest_result", fmt.Sprintf("%v", *retestResult))
	}
	if limit != nil {
		params.Set("limit", fmt.Sprintf("%v", *limit))
	}
	if offset != nil {
		params.Set("offset", fmt.Sprintf("%v", *offset))
	}

	var result models.RetestRecordListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/work-orders/%s/retests", workOrderId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// CreateRetestRecordApiV1WorkOrdersRetestsPost 创建复测记录
func (c *WorkOrderClient) CreateRetestRecordApiV1WorkOrdersRetestsPost(
	ctx context.Context,
	body *models.RetestRecordCreate,
) (*models.RetestRecordResponse, error) {
	params := url.Values{}

	var result models.RetestRecordResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/work-orders/retests", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetRetestRecordApiV1WorkOrdersRetestsRecordIdGet 获取复测记录详情
func (c *WorkOrderClient) GetRetestRecordApiV1WorkOrdersRetestsRecordIdGet(
	ctx context.Context,
	recordId int,
) (*models.RetestRecordResponse, error) {
	params := url.Values{}

	var result models.RetestRecordResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/work-orders/retests/%s", recordId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// UpdateRetestRecordApiV1WorkOrdersRetestsRecordIdPut 更新复测记录
func (c *WorkOrderClient) UpdateRetestRecordApiV1WorkOrdersRetestsRecordIdPut(
	ctx context.Context,
	recordId int,
	body *models.RetestRecordUpdate,
) (*models.RetestRecordResponse, error) {
	params := url.Values{}

	var result models.RetestRecordResponse
	err := c.client.Request(
		ctx,
		"PUT",
		fmt.Sprintf("/api/v1/api/v1/work-orders/retests/%s", recordId),
		params,
		body,
		&result,
	)
	return &result, err
}

// TriggerRetestRepredictApiV1WorkOrdersRetestsRecordIdRepredictPost 触发复测后再预测
func (c *WorkOrderClient) TriggerRetestRepredictApiV1WorkOrdersRetestsRecordIdRepredictPost(
	ctx context.Context,
	recordId int,
) (*models.PredictionCompareResponse, error) {
	params := url.Values{}

	var result models.PredictionCompareResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/work-orders/retests/%s/repredict", recordId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ListWorkOrderPredictionComparesApiV1WorkOrdersWorkOrderIdPredictionComparesGet 查询工单预测对比列表
func (c *WorkOrderClient) ListWorkOrderPredictionComparesApiV1WorkOrdersWorkOrderIdPredictionComparesGet(
	ctx context.Context,
	workOrderId int,
	isFalsePositive *interface{},
	isRecurring *interface{},
	riskChange *interface{},
	limit *int,
	offset *int,
) (*models.PredictionCompareListResponse, error) {
	params := url.Values{}
	if isFalsePositive != nil {
		params.Set("is_false_positive", fmt.Sprintf("%v", *isFalsePositive))
	}
	if isRecurring != nil {
		params.Set("is_recurring", fmt.Sprintf("%v", *isRecurring))
	}
	if riskChange != nil {
		params.Set("risk_change", fmt.Sprintf("%v", *riskChange))
	}
	if limit != nil {
		params.Set("limit", fmt.Sprintf("%v", *limit))
	}
	if offset != nil {
		params.Set("offset", fmt.Sprintf("%v", *offset))
	}

	var result models.PredictionCompareListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/work-orders/%s/prediction-compares", workOrderId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetPredictionCompareApiV1WorkOrdersPredictionComparesCompareIdGet 获取预测对比详情
func (c *WorkOrderClient) GetPredictionCompareApiV1WorkOrdersPredictionComparesCompareIdGet(
	ctx context.Context,
	compareId int,
) (*models.PredictionCompareResponse, error) {
	params := url.Values{}

	var result models.PredictionCompareResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/work-orders/prediction-compares/%s", compareId),
		params,
		nil,
		&result,
	)
	return &result, err
}
