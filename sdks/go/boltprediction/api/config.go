package api

import "context"
import "fmt"
import "net/url"
import "github.com/bolt-prediction/sdk-go/boltprediction/models"

// ConfigClient Config API 客户端
type ConfigClient struct {
	client *BaseClient
}

// NewConfigClient 创建 Config API 客户端
func NewConfigClient(client *BaseClient) *ConfigClient {
	return &ConfigClient{client: client}
}

// GetStrategyConfigApiV1StrategyConfigGet 查询当前生效策略
func (c *ConfigClient) GetStrategyConfigApiV1StrategyConfigGet(
	ctx context.Context,
	nodeType *interface{},
	nodeId *interface{},
) (*models.EffectiveStrategyResponse, error) {
	params := url.Values{}
	if nodeType != nil {
		params.Set("node_type", fmt.Sprintf("%v", *nodeType))
	}
	if nodeId != nil {
		params.Set("node_id", fmt.Sprintf("%v", *nodeId))
	}

	var result models.EffectiveStrategyResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/strategy/config", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// UpdateStrategyConfigApiV1StrategyConfigPost 更新预警策略（立即生效）
func (c *ConfigClient) UpdateStrategyConfigApiV1StrategyConfigPost(
	ctx context.Context,
	body *models.StrategyConfigUpdateRequest,
) (*models.StrategyConfigItemResponse, error) {
	params := url.Values{}

	var result models.StrategyConfigItemResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/strategy/config", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// ListStrategyConfigsApiV1StrategyConfigListGet 列出策略配置（含历史版本）
func (c *ConfigClient) ListStrategyConfigsApiV1StrategyConfigListGet(
	ctx context.Context,
	scope *interface{},
	nodeType *interface{},
	nodeId *interface{},
	isActive *interface{},
	limit *int,
) (*models.StrategyConfigListResponse, error) {
	params := url.Values{}
	if scope != nil {
		params.Set("scope", fmt.Sprintf("%v", *scope))
	}
	if nodeType != nil {
		params.Set("node_type", fmt.Sprintf("%v", *nodeType))
	}
	if nodeId != nil {
		params.Set("node_id", fmt.Sprintf("%v", *nodeId))
	}
	if isActive != nil {
		params.Set("is_active", fmt.Sprintf("%v", *isActive))
	}
	if limit != nil {
		params.Set("limit", fmt.Sprintf("%v", *limit))
	}

	var result models.StrategyConfigListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/strategy/config/list", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// RollbackStrategyConfigApiV1StrategyConfigRollbackPost 回滚策略到历史版本
func (c *ConfigClient) RollbackStrategyConfigApiV1StrategyConfigRollbackPost(
	ctx context.Context,
	body *models.StrategyRollbackRequest,
) (*models.StrategyConfigItemResponse, error) {
	params := url.Values{}

	var result models.StrategyConfigItemResponse
	err := c.client.Request(
		ctx,
		"POST",
		fmt.Sprintf("/api/v1/api/v1/strategy/config/rollback", ),
		params,
		body,
		&result,
	)
	return &result, err
}

// GetStrategyAuditLogsApiV1StrategyConfigAuditGet 查询策略变更审计日志
func (c *ConfigClient) GetStrategyAuditLogsApiV1StrategyConfigAuditGet(
	ctx context.Context,
	scope *interface{},
	nodeType *interface{},
	nodeId *interface{},
	action *interface{},
	operatorId *interface{},
	limit *int,
	offset *int,
) (*models.StrategyAuditLogListResponse, error) {
	params := url.Values{}
	if scope != nil {
		params.Set("scope", fmt.Sprintf("%v", *scope))
	}
	if nodeType != nil {
		params.Set("node_type", fmt.Sprintf("%v", *nodeType))
	}
	if nodeId != nil {
		params.Set("node_id", fmt.Sprintf("%v", *nodeId))
	}
	if action != nil {
		params.Set("action", fmt.Sprintf("%v", *action))
	}
	if operatorId != nil {
		params.Set("operator_id", fmt.Sprintf("%v", *operatorId))
	}
	if limit != nil {
		params.Set("limit", fmt.Sprintf("%v", *limit))
	}
	if offset != nil {
		params.Set("offset", fmt.Sprintf("%v", *offset))
	}

	var result models.StrategyAuditLogListResponse
	err := c.client.Request(
		ctx,
		"GET",
		fmt.Sprintf("/api/v1/api/v1/strategy/config/audit", ),
		params,
		nil,
		&result,
	)
	return &result, err
}

// DeleteStrategyOverrideApiV1StrategyConfigOverrideDelete 删除节点级策略覆盖
func (c *ConfigClient) DeleteStrategyOverrideApiV1StrategyConfigOverrideDelete(
	ctx context.Context,
	body *models.StrategyNodeOverrideDeleteRequest,
) (*map[string]interface{}, error) {
	params := url.Values{}

	var result map[string]interface{}
	err := c.client.Request(
		ctx,
		"DELETE",
		fmt.Sprintf("/api/v1/api/v1/strategy/config/override", ),
		params,
		body,
		&result,
	)
	return &result, err
}
