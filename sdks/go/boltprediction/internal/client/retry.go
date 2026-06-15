package client

import (
	"context"
	"math"
	"net/http"
	"time"
)

// RetryManager 重试管理器
type RetryManager struct {
	maxRetries         int
	backoffFactor      float64
	retryStatusCodes   []int
}

// NewRetryManager 创建重试管理器
func NewRetryManager(maxRetries int, backoffFactor float64, retryStatusCodes []int) *RetryManager {
	return &RetryManager{
		maxRetries:       maxRetries,
		backoffFactor:    backoffFactor,
		retryStatusCodes: retryStatusCodes,
	}
}

// RetryableFunc 可重试的函数类型
type RetryableFunc func(ctx context.Context) (*http.Response, error)

// ShouldRetry 判断是否应该重试
func (r *RetryManager) ShouldRetry(statusCode int) bool {
	for _, code := range r.retryStatusCodes {
		if code == statusCode {
			return true
		}
	}
	return false
}

// Execute 执行带重试的请求
func (r *RetryManager) Execute(ctx context.Context, fn RetryableFunc) (*http.Response, error) {
	var lastErr error

	for attempt := 0; attempt <= r.maxRetries; attempt++ {
		resp, err := fn(ctx)
		if err != nil {
			lastErr = err
			if attempt >= r.maxRetries {
				return nil, err
			}
		} else if !r.ShouldRetry(resp.StatusCode) {
			return resp, nil
		} else {
			lastErr = nil
			if attempt >= r.maxRetries {
				return resp, nil
			}
			resp.Body.Close()
		}

		waitTime := time.Duration(r.backoffFactor * math.Pow(2, float64(attempt)) * float64(time.Second))
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(waitTime):
		}
	}

	return nil, lastErr
}
