# @bolt-prediction/sdk

螺栓预紧力预测系统 TypeScript SDK

## 安装

```bash
npm install @bolt-prediction/sdk
```

## 快速开始

```typescript
import { SDKConfig, 预测Client } from '@bolt-prediction/sdk';

const config: SDKConfig = {
  baseUrl: "https://api.example.com",
  apiKey: "your-api-key",
};

const client = new 预测Client(config);

// 调用 API
const result = await client.predictBolt({
  boltId: "B001",
  data: [["2025-01-01", 400.0]]
});

console.log(result);
```

## 特性

- **完整 API 覆盖**: 支持所有 API 端点
- **自动重试**: 指数退避重试，支持配置
- **API Key 鉴权**: 支持 X-API-Key 头部认证
- **游标分页**: 自动处理游标分页，支持异步迭代
- **TypeScript 类型**: 完整的类型定义

## 分页示例

```typescript
// 使用游标分页获取所有数据
const paginator = client.listItems({ limit: 20 });
const allItems = await paginator.all();

// 或者使用异步迭代
for await (const item of client.listItems()) {
  console.log(item);
}
```
