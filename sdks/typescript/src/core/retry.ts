/**
 * 重试模块
 */

export interface RetryManagerOptions {
  maxRetries?: number;
  backoffFactor?: number;
  statusCodes?: number[];
}

export class RetryManager {
  private maxRetries: number;
  private backoffFactor: number;
  private statusCodes: number[];

  constructor(options: RetryManagerOptions = {}) {
    this.maxRetries = options.maxRetries ?? 3;
    this.backoffFactor = options.backoffFactor ?? 0.5;
    this.statusCodes = options.statusCodes ?? [429, 500, 502, 503, 504];
  }

  /**
   * 执行带重试的异步函数
   */
  async execute<T>(fn: () => Promise<T>): Promise<T> {
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        return await fn();
      } catch (error: any) {
        lastError = error;

        const statusCode = error?.response?.status || error?.statusCode;
        if (!this.statusCodes.includes(statusCode)) {
          throw error;
        }

        if (attempt >= this.maxRetries) {
          console.warn(`Max retries (${this.maxRetries}) reached, giving up`);
          throw error;
        }

        const waitTime = this.backoffFactor * Math.pow(2, attempt) * 1000;
        console.warn(
          `Retry attempt ${attempt + 1}/${this.maxRetries}, ` +
          `waiting ${waitTime}ms before retry. Error: ${error.message}`
        );

        await this.sleep(waitTime);
      }
    }

    throw lastError!;
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
