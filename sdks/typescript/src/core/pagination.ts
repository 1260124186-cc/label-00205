/**
 * 游标分页模块
 */

import { BaseAPIClient } from "./client";

export interface CursorPaginatorOptions {
  cursorParam?: string;
  limitParam?: string;
  defaultLimit?: number;
  responseCursorField?: string;
  responseItemsField?: string;
}

export class CursorPaginator<T> {
  private client: BaseAPIClient;
  private path: string;
  private method: string;
  private params: Record<string, any>;
  private body?: any;

  private cursorParam: string;
  private limitParam: string;
  private defaultLimit: number;
  private responseCursorField: string;
  private responseItemsField: string;

  private _cursor: string | null = null;
  private _hasMore: boolean = true;
  private _buffer: T[] = [];

  constructor(
    client: BaseAPIClient,
    path: string,
    method: string = "GET",
    params: Record<string, any> = {},
    body?: any,
    options: CursorPaginatorOptions = {}
  ) {
    this.client = client;
    this.path = path;
    this.method = method;
    this.params = params;
    this.body = body;

    this.cursorParam = options.cursorParam ?? "cursor";
    this.limitParam = options.limitParam ?? "limit";
    this.defaultLimit = options.defaultLimit ?? 20;
    this.responseCursorField = options.responseCursorField ?? "next_cursor";
    this.responseItemsField = options.responseItemsField ?? "items";
  }

  /**
   * 获取下一页数据
   */
  async nextPage(limit?: number): Promise<T[]> {
    if (!this._hasMore) {
      return [];
    }

    const params = { ...this.params };
    params[this.limitParam] = limit ?? this.defaultLimit;

    if (this._cursor) {
      params[this.cursorParam] = this._cursor;
    }

    const response: any = await this.client._request(
      this.method,
      this.path,
      params,
      this.body
    );

    if (Array.isArray(response)) {
      this._hasMore = false;
      return response as T[];
    }

    const items = response?.[this.responseItemsField] ?? [];
    this._cursor = response?.[this.responseCursorField] ?? null;
    this._hasMore = this._cursor !== null;

    return items as T[];
  }

  /**
   * 获取所有数据
   */
  async all(limit?: number): Promise<T[]> {
    const allItems: T[] = [];
    while (this._hasMore) {
      const items = await this.nextPage(limit);
      allItems.push(...items);
    }
    return allItems;
  }

  /**
   * 是否有更多数据
   */
  get hasMore(): boolean {
    return this._hasMore;
  }

  /**
   * 当前游标
   */
  get cursor(): string | null {
    return this._cursor;
  }

  /**
   * 异步迭代器支持
   */
  async *[Symbol.asyncIterator](): AsyncIterator<T> {
    while (this._hasMore) {
      const items = await this.nextPage();
      for (const item of items) {
        yield item;
      }
    }
  }
}
