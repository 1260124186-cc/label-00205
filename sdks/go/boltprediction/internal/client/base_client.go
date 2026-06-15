package client

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
)

// HTTPClient HTTP 客户端接口
type HTTPClient interface {
	Do(req *http.Request) (*http.Response, error)
}

// BaseClient 基础客户端
type BaseClient struct {
	config  Config
	auth    *AuthManager
	retry   *RetryManager
	http    HTTPClient
}

// NewBaseClient 创建基础客户端
func NewBaseClient(config Config) *BaseClient {
	return &BaseClient{
		config: config,
		auth:   NewAuthManager(config.APIKey, config.APIKeyHeader),
		retry:  NewRetryManager(config.MaxRetries, config.RetryBackoffFactor, config.RetryStatusCodes),
		http:   &http.Client{Timeout: config.Timeout},
	}
}

// Request 发送 HTTP 请求
func (c *BaseClient) Request(
	ctx context.Context,
	method string,
	path string,
	queryParams url.Values,
	body interface{},
	result interface{},
) error {
	fullURL := c.config.BaseURL + path
	if queryParams != nil && len(queryParams) > 0 {
		fullURL += "?" + queryParams.Encode()
	}

	var bodyReader io.Reader
	if body != nil {
		bodyBytes, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("failed to marshal request body: %w", err)
		}
		bodyReader = bytes.NewReader(bodyBytes)
	}

	req, err := http.NewRequestWithContext(ctx, method, fullURL, bodyReader)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	for key, value := range c.auth.GetHeaders() {
		req.Header.Set(key, value)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")

	retryFn := func(ctx context.Context) (*http.Response, error) {
		return c.http.Do(req)
	}

	resp, err := c.retry.Execute(ctx, retryFn)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("API error (status %d): %s", resp.StatusCode, string(bodyBytes))
	}

	if result != nil {
		bodyBytes, err := io.ReadAll(resp.Body)
		if err != nil {
			return fmt.Errorf("failed to read response body: %w", err)
		}
		if len(bodyBytes) > 0 {
			if err := json.Unmarshal(bodyBytes, result); err != nil {
				return fmt.Errorf("failed to unmarshal response: %w", err)
			}
		}
	}

	return nil
}
