package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// AlertManagementClient AlertManagement API 客户端
type AlertManagementClient struct {
	client *BaseClient
}

// NewAlertManagementClient 创建 AlertManagement API 客户端
func NewAlertManagementClient(client *BaseClient) *AlertManagementClient {
	return &AlertManagementClient{client: client}
}

// ListAlertRulesApiV1AlertRulesGet 查询告警规则列表
func (c *AlertManagementClient) ListAlertRulesApiV1AlertRulesGet(
	ctx context.Context,
	enabled *interface{},
	alertLevel *interface{},
) (*[]models.AlertRuleResponse, error) {
	params := url.Values{}
	if enabled != nil {
		params.Set("enabled", fmt.Sprintf("%v", *enabled))
	}
	if alertLevel != nil {
		params.Set("alert_level", fmt.Sprintf("%v", *alertLevel))
	}

	var result []models.AlertRuleResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/alert/rules", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// CreateAlertRuleApiV1AlertRulesPost 创建告警规则
func (c *AlertManagementClient) CreateAlertRuleApiV1AlertRulesPost(
	ctx context.Context,
	body *models.AlertRuleCreate,
) (*models.AlertRuleResponse, error) {
	params := url.Values{}

	var result models.AlertRuleResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/alert/rules", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// UpdateAlertRuleApiV1AlertRulesRuleIdPut 更新告警规则
func (c *AlertManagementClient) UpdateAlertRuleApiV1AlertRulesRuleIdPut(
	ctx context.Context,
	ruleId int,
	body *models.AlertRuleUpdate,
) (*models.AlertRuleResponse, error) {
	params := url.Values{}

	var result models.AlertRuleResponse
	err := c.client.Request(
		ctx,
		"PUT",
		fmt.Sprintf("/api/v1/api/v1/alert/rules/%s", ruleId),
		params,
		body,
		&result,
	)
	return &result, err
}

// DeleteAlertRuleApiV1AlertRulesRuleIdDelete 删除告警规则
func (c *AlertManagementClient) DeleteAlertRuleApiV1AlertRulesRuleIdDelete(
	ctx context.Context,
	ruleId int,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"DELETE",
		fmt.Sprintf("/api/v1/api/v1/alert/rules/%s", ruleId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ListAlertEventsApiV1AlertEventsGet 查询告警事件列表
func (c *AlertManagementClient) ListAlertEventsApiV1AlertEventsGet(
	ctx context.Context,
	status *interface{},
	alertLevel *interface{},
	nodeType *interface{},
	nodeId *interface{},
	limit *int,
	offset *int,
) (*models.AlertListResponse, error) {
	params := url.Values{}
	if status != nil {
		params.Set("status", fmt.Sprintf("%v", *status))
	}
	if alertLevel != nil {
		params.Set("alert_level", fmt.Sprintf("%v", *alertLevel))
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

	var result models.AlertListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/alert/events", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// GetAlertEventApiV1AlertEventsAlertIdGet 获取告警详情
func (c *AlertManagementClient) GetAlertEventApiV1AlertEventsAlertIdGet(
	ctx context.Context,
	alertId int,
) (*models.AlertEventResponse, error) {
	params := url.Values{}

	var result models.AlertEventResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/alert/events/%s", alertId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// HandleAlertEventApiV1AlertEventsAlertIdHandlePost 处理告警
func (c *AlertManagementClient) HandleAlertEventApiV1AlertEventsAlertIdHandlePost(
	ctx context.Context,
	alertId int,
	body *models.AlertHandleRequest,
) (*models.AlertEventResponse, error) {
	params := url.Values{}

	var result models.AlertEventResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/alert/events/%s/handle", alertId),
		params,
		body,
		&result,
	)
	return &result, err
}

// TriggerAlertUpgradeApiV1AlertUpgradeTriggerPost 手动触发告警升级检查
func (c *AlertManagementClient) TriggerAlertUpgradeApiV1AlertUpgradeTriggerPost(
	ctx context.Context,
) (*models.AlertUpgradeTriggerResponse, error) {
	params := url.Values{}

	var result models.AlertUpgradeTriggerResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/alert/upgrade/trigger", ),
		params,
		nil,
		&result,
	)
	return &result, err
}
