package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// AlertSubscriptionClient AlertSubscription API 客户端
type AlertSubscriptionClient struct {
	client *BaseClient
}

// NewAlertSubscriptionClient 创建 AlertSubscription API 客户端
func NewAlertSubscriptionClient(client *BaseClient) *AlertSubscriptionClient {
	return &AlertSubscriptionClient{client: client}
}

// ListAlertSubscriptionsApiV1AlertSubscriptionsGet 查询订阅列表
func (c *AlertSubscriptionClient) ListAlertSubscriptionsApiV1AlertSubscriptionsGet(
	ctx context.Context,
	subscriberType *interface{},
	subscriberId *interface{},
	enabled *interface{},
) (*[]models.AlertSubscriptionResponse, error) {
	params := url.Values{}
	if subscriberType != nil {
		params.Set("subscriber_type", fmt.Sprintf("%v", *subscriberType))
	}
	if subscriberId != nil {
		params.Set("subscriber_id", fmt.Sprintf("%v", *subscriberId))
	}
	if enabled != nil {
		params.Set("enabled", fmt.Sprintf("%v", *enabled))
	}

	var result []models.AlertSubscriptionResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/alert/subscriptions", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// CreateAlertSubscriptionApiV1AlertSubscriptionsPost 创建订阅
func (c *AlertSubscriptionClient) CreateAlertSubscriptionApiV1AlertSubscriptionsPost(
	ctx context.Context,
	body *models.AlertSubscriptionCreate,
) (*models.AlertSubscriptionResponse, error) {
	params := url.Values{}

	var result models.AlertSubscriptionResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/alert/subscriptions", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetAlertSubscriptionApiV1AlertSubscriptionsSubIdGet 获取订阅详情
func (c *AlertSubscriptionClient) GetAlertSubscriptionApiV1AlertSubscriptionsSubIdGet(
	ctx context.Context,
	subId int,
) (*models.AlertSubscriptionResponse, error) {
	params := url.Values{}

	var result models.AlertSubscriptionResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/alert/subscriptions/%s", subId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// UpdateAlertSubscriptionApiV1AlertSubscriptionsSubIdPut 更新订阅
func (c *AlertSubscriptionClient) UpdateAlertSubscriptionApiV1AlertSubscriptionsSubIdPut(
	ctx context.Context,
	subId int,
	body *models.AlertSubscriptionUpdate,
) (*models.AlertSubscriptionResponse, error) {
	params := url.Values{}

	var result models.AlertSubscriptionResponse
	err := c.client.Request(
		ctx,
		"PUT",
		fmt.Sprintf("/api/v1/api/v1/alert/subscriptions/%s", subId),
		params,
		body,
		&result,
	)
	return &result, err
}

// DeleteAlertSubscriptionApiV1AlertSubscriptionsSubIdDelete 删除订阅
func (c *AlertSubscriptionClient) DeleteAlertSubscriptionApiV1AlertSubscriptionsSubIdDelete(
	ctx context.Context,
	subId int,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"DELETE",
		fmt.Sprintf("/api/v1/api/v1/alert/subscriptions/%s", subId),
		params,
		nil,
		&result,
	)
	return &result, err
}
