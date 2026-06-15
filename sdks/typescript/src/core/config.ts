/**
 * SDK 配置
 */

export interface SDKConfig {
  /** API 基础 URL */
  baseUrl: string;
  /** API 密钥 */
  apiKey?: string;
  /** API 版本 */
  apiVersion: string;
  /** 请求超时时间（毫秒） */
  timeout: number;

  /** 最大重试次数 */
  maxRetries: number;
  /** 重试退避因子 */
  retryBackoffFactor: number;
  /** 需要重试的 HTTP 状态码 */
  retryStatusCodes: number[];

  /** API Key 请求头名称 */
  apiKeyHeader: string;

  /** 分页游标参数名 */
  paginationCursorParam: string;
  /** 分页数量参数名 */
  paginationLimitParam: string;
  /** 默认每页数量 */
  paginationDefaultLimit: number;
  /** 最大每页数量 */
  paginationMaxLimit: number;
}

/**
 * 默认配置
 */
export const defaultConfig: SDKConfig = {
  baseUrl: "https://api.example.com",
  apiVersion: "v1",
  timeout: 30000,

  maxRetries: 3,
  retryBackoffFactor: 0.5,
  retryStatusCodes: [429, 500, 502, 503, 504],

  apiKeyHeader: "X-API-Key",

  paginationCursorParam: "cursor",
  paginationLimitParam: "limit",
  paginationDefaultLimit: 20,
  paginationMaxLimit: 100,
};
