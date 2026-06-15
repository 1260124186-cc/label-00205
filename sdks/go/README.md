# boltprediction

螺栓预紧力预测系统 Go SDK

## 安装

```bash
go get github.com/bolt-prediction/sdk-go
```

## 快速开始

```go
package main

import (
    "context"
    "fmt"
    "github.com/bolt-prediction/sdk-go/boltprediction"
)

func main() {
    config := boltprediction.DefaultConfig()
    config.BaseURL = "https://api.example.com"
    config.APIKey = "your-api-key"

    client := boltprediction.NewClient(config)

    // 调用 API
    result, err := client.PredictBolt(ctx, "B001", data)
    if err != nil {
        panic(err)
    }

    fmt.Println(result.Status)
}
```

## 特性

- **完整 API 覆盖**: 支持所有 API 端点
- **自动重试**: 指数退避重试，支持配置
- **API Key 鉴权**: 支持 X-API-Key 头部认证
- **游标分页**: 自动处理游标分页
- **Context 支持**: 完整的 context 传递支持

## 分页示例

```go
// 使用游标分页获取所有数据
paginator := client.ListItems(ctx)

var allItems []Item
for paginator.HasMore() {
    var page []Item
    if err := paginator.NextPage(ctx, &page); err != nil {
        panic(err)
    }
    allItems = append(allItems, page...)
}
```
