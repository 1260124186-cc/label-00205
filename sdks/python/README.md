# bolt_prediction_sdk

螺栓预紧力预测系统 Python SDK

## 安装

```bash
pip install bolt_prediction_sdk
```

## 快速开始

```python
import asyncio
from bolt_prediction_sdk import SDKConfig, 预测Client

async def main():
    config = SDKConfig(
        base_url="https://api.example.com",
        api_key="your-api-key",
    )

    # 创建客户端
    client = 预测Client(config)

    # 调用 API
    result = await client.predict_bolt(
        bolt_id="B001",
        data=[["2025-01-01", 400.0]]
    )
    print(result)

    await client.close()

asyncio.run(main())
```

## 特性

- **完整 API 覆盖**: 支持所有 API 端点
- **自动重试**: 指数退避重试，支持配置
- **API Key 鉴权**: 支持 X-API-Key 头部认证
- **游标分页**: 自动处理游标分页，支持异步迭代
- **类型提示**: 完整的类型定义和 Pydantic 模型

## 配置

通过环境变量配置:

- `SDK_BASE_URL`: API 基础 URL
- `SDK_API_KEY`: API 密钥
- `SDK_MAX_RETRIES`: 最大重试次数

## 分页示例

```python
# 使用游标分页迭代所有数据
paginator = client.list_items(limit=20)
all_items = await paginator.all()

# 或者使用异步迭代
async for item in client.list_items():
    process_item(item)
```
