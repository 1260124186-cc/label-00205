# bolt-prediction-sdk

螺栓预紧力预测系统 Java SDK

## 安装

Maven 依赖:

```xml
<dependency>
    <groupId>com.boltprediction</groupId>
    <artifactId>bolt-prediction-sdk</artifactId>
    <version>1.0.0</version>
</dependency>
```

## 快速开始

```java
import com.boltprediction.sdk.api.预测Client;
import com.boltprediction.sdk.core.ApiClientConfig;

public class Example {
    public static void main(String[] args) throws Exception {
        ApiClientConfig config = new ApiClientConfig();
        config.setBaseUrl("https://api.example.com");
        config.setApiKey("your-api-key");

        预测Client client = new 预测Client(config);

        BoltPredictionResponse result = client.predictBolt("B001", data);
        System.out.println(result.getStatus());
    }
}
```

## 特性

- **完整 API 覆盖**: 支持所有 API 端点
- **自动重试**: 指数退避重试，支持配置
- **API Key 鉴权**: 支持 X-API-Key 头部认证
- **游标分页**: 自动处理游标分页，支持迭代器模式
- **Java 11+ 兼容**: 兼容 Java 11 及以上版本

## 分页示例

```java
CursorPaginator<Item> paginator = client.listItems();

// 获取所有数据
List<Item> allItems = paginator.all();

// 或者使用迭代器
for (Item item : paginator) {
    System.out.println(item);
}

// 逐页获取
while (paginator.hasMore()) {
    List<Item> page = paginator.nextPage();
    // 处理当前页
}
```
