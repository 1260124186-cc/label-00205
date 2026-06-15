package api

import (
	"context"
	"encoding/json"
	"fmt"
	"net/url"
)

// CursorPaginator 游标分页器
type CursorPaginator struct {
	client    *BaseClient
	path      string
	method    string
	params    url.Values
	body      interface{}

	cursorParam  string
	limitParam   string
	defaultLimit int

	responseCursorField string
	responseItemsField  string

	cursor   string
	hasMore  bool
}

// NewCursorPaginator 创建游标分页器
func NewCursorPaginator(
	client *BaseClient,
	path string,
	method string,
	params url.Values,
	body interface{},
) *CursorPaginator {
	return &CursorPaginator{
		client:              client,
		path:                path,
		method:              method,
		params:              params,
		body:                body,
		cursorParam:         "cursor",
		limitParam:          "limit",
		defaultLimit:        20,
		responseCursorField: "next_cursor",
		responseItemsField:  "items",
		hasMore:             true,
	}
}

// NextPage 获取下一页数据
func (p *CursorPaginator) NextPage(ctx context.Context, items interface{}, limit ...int) error {
	if !p.hasMore {
		return nil
	}

	params := url.Values{}
	for k, v := range p.params {
		params[k] = v
	}

	pageLimit := p.defaultLimit
	if len(limit) > 0 && limit[0] > 0 {
		pageLimit = limit[0]
	}
	params.Set(p.limitParam, fmt.Sprintf("%d", pageLimit))

	if p.cursor != "" {
		params.Set(p.cursorParam, p.cursor)
	}

	var rawResponse map[string]json.RawMessage
	err := p.client.Request(ctx, p.method, p.path, params, p.body, &rawResponse)
	if err != nil {
		return err
	}

	if itemsField, ok := rawResponse[p.responseItemsField]; ok {
		if err := json.Unmarshal(itemsField, items); err != nil {
			return fmt.Errorf("failed to unmarshal items: %w", err)
		}
	}

	if cursorField, ok := rawResponse[p.responseCursorField]; ok {
		var cursor string
		if err := json.Unmarshal(cursorField, &cursor); err == nil {
			p.cursor = cursor
			p.hasMore = cursor != ""
		} else {
			p.hasMore = false
		}
	} else {
		p.hasMore = false
	}

	return nil
}

// HasMore 是否有更多数据
func (p *CursorPaginator) HasMore() bool {
	return p.hasMore
}

// Cursor 当前游标
func (p *CursorPaginator) Cursor() string {
	return p.cursor
}

// All 获取所有数据
func (p *CursorPaginator) All(ctx context.Context, items interface{}, limit ...int) error {
	var allItems []interface{}

	for p.hasMore {
		var pageItems []interface{}
		if err := p.NextPage(ctx, &pageItems, limit...); err != nil {
			return err
		}
		allItems = append(allItems, pageItems...)
	}

	// 将所有数据序列化再反序列化到目标类型
	bytes, err := json.Marshal(allItems)
	if err != nil {
		return err
	}
	return json.Unmarshal(bytes, items)
}
