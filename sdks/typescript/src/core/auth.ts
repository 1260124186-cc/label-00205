/**
 * 鉴权模块
 */

export interface AuthManagerOptions {
  apiKey?: string;
  headerName?: string;
}

export class AuthManager {
  private apiKey?: string;
  private headerName: string;

  constructor(options: AuthManagerOptions = {}) {
    this.apiKey = options.apiKey;
    this.headerName = options.headerName || "X-API-Key";
  }

  /**
   * 获取认证请求头
   */
  getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {};
    if (this.apiKey) {
      headers[this.headerName] = this.apiKey;
    }
    return headers;
  }

  /**
   * 设置 API Key
   */
  setApiKey(apiKey: string): void {
    this.apiKey = apiKey;
  }
}
