/**
 * API 客户端基类
 */

import axios, { AxiosInstance, AxiosRequestConfig } from "axios";
import axiosRetry from "axios-retry";

import { SDKConfig, defaultConfig } from "./config";
import { AuthManager } from "./auth";
import { RetryManager } from "./retry";

export class BaseAPIClient {
  protected config: SDKConfig;
  protected auth: AuthManager;
  protected retry: RetryManager;
  private _client: AxiosInstance | null = null;

  constructor(config: Partial<SDKConfig>, auth: AuthManager, retry: RetryManager) {
    this.config = { ...defaultConfig, ...config };
    this.auth = auth;
    this.retry = retry;
  }

  /**
   * 获取 HTTP 客户端
   */
  protected get client(): AxiosInstance {
    if (!this._client) {
      this._client = axios.create({
        baseURL: this.config.baseUrl,
        timeout: this.config.timeout,
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
      });

      axiosRetry(this._client, {
        retries: this.config.maxRetries,
        retryDelay: axiosRetry.exponentialDelay,
        retryCondition: (error) => {
          return this.config.retryStatusCodes.includes(error.response?.status || 0);
        },
      });
    }
    return this._client;
  }

  /**
   * 发送 HTTP 请求
   */
  async _request(
    method: string,
    path: string,
    params?: Record<string, any>,
    data?: any,
    headers?: Record<string, string>
  ): Promise<any> {
    const requestHeaders = { ...this.auth.getHeaders(), ...headers };

    const config: AxiosRequestConfig = {
      method: method as any,
      url: path,
      params,
      data,
      headers: requestHeaders,
    };

    const response = await this.client.request(config);
    return response.data;
  }
}
