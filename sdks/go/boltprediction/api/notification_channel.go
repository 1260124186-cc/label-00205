package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// NotificationChannelClient NotificationChannel API 客户端
type NotificationChannelClient struct {
	client *BaseClient
}

// NewNotificationChannelClient 创建 NotificationChannel API 客户端
func NewNotificationChannelClient(client *BaseClient) *NotificationChannelClient {
	return &NotificationChannelClient{client: client}
}

// ListNotificationChannelsApiV1NotificationChannelsGet 查询通知渠道列表
func (c *NotificationChannelClient) ListNotificationChannelsApiV1NotificationChannelsGet(
	ctx context.Context,
) (*[]models.NotificationChannelResponse, error) {
	params := url.Values{}

	var result []models.NotificationChannelResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/notification/channels", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// CreateNotificationChannelApiV1NotificationChannelsPost 创建通知渠道
func (c *NotificationChannelClient) CreateNotificationChannelApiV1NotificationChannelsPost(
	ctx context.Context,
	body *models.NotificationChannelCreate,
) (*models.NotificationChannelResponse, error) {
	params := url.Values{}

	var result models.NotificationChannelResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/notification/channels", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// UpdateNotificationChannelApiV1NotificationChannelsChannelIdPut 更新通知渠道
func (c *NotificationChannelClient) UpdateNotificationChannelApiV1NotificationChannelsChannelIdPut(
	ctx context.Context,
	channelId int,
	body *models.NotificationChannelUpdate,
) (*models.NotificationChannelResponse, error) {
	params := url.Values{}

	var result models.NotificationChannelResponse
	err := c.client.Request(
		ctx,
		"PUT",
		fmt.Sprintf("/api/v1/api/v1/notification/channels/%s", channelId),
		params,
		body,
		&result,
	)
	return &result, err
}

// DeleteNotificationChannelApiV1NotificationChannelsChannelIdDelete 删除通知渠道
func (c *NotificationChannelClient) DeleteNotificationChannelApiV1NotificationChannelsChannelIdDelete(
	ctx context.Context,
	channelId int,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"DELETE",
		fmt.Sprintf("/api/v1/api/v1/notification/channels/%s", channelId),
		params,
		nil,
		&result,
	)
	return &result, err
}

// ListNotificationLogsApiV1NotificationLogsGet 查询通知发送日志
func (c *NotificationChannelClient) ListNotificationLogsApiV1NotificationLogsGet(
	ctx context.Context,
	alertId *interface{},
	status *interface{},
	limit *int,
) (*[]models.NotificationLogResponse, error) {
	params := url.Values{}
	if alertId != nil {
		params.Set("alert_id", fmt.Sprintf("%v", *alertId))
	}
	if status != nil {
		params.Set("status", fmt.Sprintf("%v", *status))
	}
	if limit != nil {
		params.Set("limit", fmt.Sprintf("%v", *limit))
	}

	var result []models.NotificationLogResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/notification/logs", ),
		params,
		nil,
		&result,
	)
	return &result, err
}
