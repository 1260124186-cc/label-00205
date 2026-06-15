package api

import (
	"github.com/bolt-prediction/sdk-go/boltprediction/internal/client"
)

// BaseClient 基础 API 客户端
type BaseClient = client.BaseClient

// NewClient 创建新的 API 客户端
func NewClient(config client.Config) *BaseClient {
	return client.NewBaseClient(config)
}

// Config 类型别名
type Config = client.Config

// DefaultConfig 获取默认配置
func DefaultConfig() client.Config {
	return client.DefaultConfig()
}
