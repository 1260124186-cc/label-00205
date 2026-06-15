package client

import "time"

// Config SDK 配置
type Config struct {
	BaseURL     string
	APIKey      string
	APIVersion  string
	Timeout     time.Duration

	MaxRetries         int
	RetryBackoffFactor float64
	RetryStatusCodes   []int

	APIKeyHeader string

	PaginationCursorParam  string
	PaginationLimitParam   string
	PaginationDefaultLimit int
	PaginationMaxLimit     int
}

// DefaultConfig 默认配置
func DefaultConfig() Config {
	return Config{
		BaseURL:     "https://api.example.com",
		APIVersion:  "v1",
		Timeout:     30 * time.Second,

		MaxRetries:         3,
		RetryBackoffFactor: 0.5,
		RetryStatusCodes:   []int{429, 500, 502, 503, 504},

		APIKeyHeader: "X-API-Key",

		PaginationCursorParam:  "cursor",
		PaginationLimitParam:   "limit",
		PaginationDefaultLimit: 20,
		PaginationMaxLimit:     100,
	}
}
