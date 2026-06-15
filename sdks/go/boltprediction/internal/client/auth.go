package client

// AuthManager 认证管理器
type AuthManager struct {
	apiKey     string
	headerName string
}

// NewAuthManager 创建认证管理器
func NewAuthManager(apiKey, headerName string) *AuthManager {
	return &AuthManager{
		apiKey:     apiKey,
		headerName: headerName,
	}
}

// GetHeaders 获取认证请求头
func (a *AuthManager) GetHeaders() map[string]string {
	headers := make(map[string]string)
	if a.apiKey != "" {
		headers[a.headerName] = a.apiKey
	}
	return headers
}

// SetAPIKey 设置 API Key
func (a *AuthManager) SetAPIKey(apiKey string) {
	a.apiKey = apiKey
}
