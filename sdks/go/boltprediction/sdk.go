package boltprediction

import (
	"github.com/bolt-prediction/sdk-go/boltprediction/api"
)

// SDK 入口别名
type Config = api.Config
type Client = api.BaseClient

// NewClient 创建 SDK 客户端
func NewClient(config Config) *Client {
	return api.NewClient(config)
}

// DefaultConfig 获取默认配置
func DefaultConfig() Config {
	return api.DefaultConfig()
}
