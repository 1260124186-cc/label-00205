# Bolt Prediction System - Kubernetes Helm Chart

## 概述

螺栓预紧力预测系统的Kubernetes Helm Chart，支持弹性伸缩、高可用部署和云原生最佳实践。

## 架构组件

| 组件 | 说明 | 副本策略 | 伸缩方式 |
|------|------|----------|----------|
| **API** | REST API服务，提供预测接口 | 多副本（2-10） | HPA + CPU/内存 + 自定义QPS指标 |
| **Worker** | 批处理预测任务 | 定时Job（每30分钟） | Indexed Job并行分片 |
| **Stream Consumer** | 流式预测消费者 | 多副本（2-8） | HPA + CPU + 自定义QPS指标 |
| **Scheduler** | 定时任务调度器 | 单副本 + Leader选举 | Recreate策略 |
| **MySQL** | 关系型数据库（依赖） | 单实例主从可选 | Bitnami Chart |
| **Redis** | 缓存/流存储（依赖） | 单实例集群可选 | Bitnami Chart |

## 快速开始

### 1. 添加Helm仓库

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### 2. 安装依赖

```bash
cd helm/bolt-prediction
helm dependency build
```

### 3. 部署应用

```bash
# 基础部署（开发环境）
helm install bolt-prediction . \
  --namespace bolt-prediction \
  --create-namespace

# 生产环境部署
helm install bolt-prediction . \
  --namespace bolt-prediction \
  --create-namespace \
  --set mysql.architecture=replication \
  --set redis.architecture=replication \
  --set global.storageClass=managed-premium \
  --set secret.stringData.database-password='your-strong-password' \
  --set secret.stringData.redis-password='your-strong-password' \
  --set secret.stringData.jwt-secret-key='your-super-secret-key'
```

## MySQL 依赖说明

### 配置选项

```yaml
mysql:
  enabled: true
  architecture: standalone  # standalone | replication
  auth:
    rootPassword: "root_password"
    username: "bolt_user"
    password: "bolt_password"
    database: "bolt_prediction"
  primary:
    persistence:
      enabled: true
      size: 50Gi
      storageClass: ""
    resources:
      limits:
        cpu: "2"
        memory: "4Gi"
      requests:
        cpu: "500m"
        memory: "1Gi"
```

### 生产环境推荐

- **架构**: 使用 `replication` 模式实现主从复制
- **存储**: 使用SSD类StorageClass，建议至少100Gi
- **资源**: 8Gi内存，4核CPU
- **备份**: 启用定时备份到对象存储

### 外部MySQL

如果使用外部MySQL服务：

```yaml
mysql:
  enabled: false

configMap:
  data:
    config.yaml: |
      database:
        host: your-external-mysql.example.com
        port: 3306
        name: bolt_prediction
        user: bolt_user
        # password from secret
```

## Redis 依赖说明

### 配置选项

```yaml
redis:
  enabled: true
  architecture: standalone  # standalone | replication
  auth:
    password: "redis_password"
  master:
    persistence:
      enabled: true
      size: 20Gi
      storageClass: ""
    resources:
      limits:
        cpu: "1"
        memory: "2Gi"
      requests:
        cpu: "200m"
        memory: "512Mi"
```

### 生产环境推荐

- **架构**: 使用 `replication` 模式实现高可用
- **持久化**: 启用RDB + AOF混合持久化
- **连接池**: 配置适当的最大连接数（建议100-500）

### Redis用途

1. **流式窗口存储**: 存储各螺栓的滑动窗口数据
2. **Leader选举**: 分布式锁实现调度器Leader选举
3. **缓存**: 热点预测结果缓存
4. **会话存储**: 用户会话管理

## 弹性伸缩 (HPA)

### API服务伸缩策略

```yaml
api:
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80
    customMetrics:
      - type: Pods
        pods:
          metric:
            name: stream_ingest_qps
          target:
            type: AverageValue
            averageValue: "1000"
```

### 伸缩行为配置

| 方向 | 稳定窗口 | 策略 | 说明 |
|------|----------|------|------|
| **扩容** | 60秒 | 每次最多扩容50%或2个Pod，取较大值 | 快速响应流量增长 |
| **缩容** | 300秒 | 每次最多缩容25%或1个Pod，取较小值 | 防止频繁抖动 |

### 自定义指标 `stream_ingest_qps`

指标 `stream_ingest_qps` 表示流式数据摄入的每秒查询率，基于最近60秒滑动窗口计算。

**前置条件**:
1. 安装 Prometheus Adapter
2. 部署 Prometheus ServiceMonitor
3. 配置指标注册规则

**Prometheus Adapter配置示例**:

```yaml
rules:
  - seriesQuery: 'stream_ingest_qps{component!=""}'
    resources:
      overrides:
        namespace: {resource: "namespace"}
        pod: {resource: "pod"}
    name:
      matches: "stream_ingest_qps"
      as: "stream_ingest_qps"
    metricsQuery: 'avg_over_time(stream_ingest_qps[2m]) by (<<.GroupBy>>)'
```

## 健康检查策略

### 探针配置

所有服务都对接 `/health` 端点，返回详细的组件健康状态。

| 探针类型 | API服务 | Stream Consumer | Scheduler |
|----------|---------|-----------------|-----------|
| **Startup** | initialDelay: 60s, period: 10s, failure: 30 | initialDelay: 60s, period: 10s, failure: 30 | initialDelay: 60s, period: 10s, failure: 30 |
| **Liveness** | initialDelay: 30s, period: 30s, timeout: 10s | initialDelay: 45s, period: 30s, timeout: 10s | initialDelay: 60s, period: 30s, timeout: 10s |
| **Readiness** | initialDelay: 15s, period: 10s, timeout: 5s | initialDelay: 20s, period: 10s, timeout: 5s | initialDelay: 30s, period: 15s, timeout: 5s |

### /health 端点响应

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "message": "数据库连接正常，活跃连接: 15"
    },
    "model_directory": {
      "status": "healthy",
      "message": "模型目录正常，路径: /app/trained_models"
    },
    "recent_prediction": {
      "status": "healthy",
      "message": "预测任务正常，累计成功任务数: 1250"
    }
  }
}
```

### 探针失败处理

1. **Startup失败**: Pod被标记为未就绪，不会接收流量，持续重试直到成功或达到失败阈值后重启
2. **Liveness失败**: 连续失败3次后，Kubernetes重启Pod
3. **Readiness失败**: Pod被从Service端点中移除，不再接收新请求

## 滚动更新策略

### API服务

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 25%
    maxUnavailable: 25%
minReadySeconds: 30
```

**特性**:
- 最多同时新增25%的Pod
- 最多同时不可用25%的Pod
- 新Pod就绪30秒后才会继续更新下一批
- 配合 `preStop` hook（sleep 30s）优雅关闭

### Stream Consumer

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 1
minReadySeconds: 30
terminationGracePeriodSeconds: 90
```

**特性**:
- 谨慎滚动，每次只更新1个Pod
- 更长的优雅关闭时间（90秒），确保窗口数据处理完成
- `preStop` hook等待60秒，让正在处理的消息完成

### Scheduler

```yaml
strategy:
  type: Recreate
terminationGracePeriodSeconds: 120
```

**特性**:
- 使用 `Recreate` 策略，确保同一时间只有一个实例运行
- 先删除旧Pod，再创建新Pod
- 配合Leader选举机制，避免双实例同时运行
- 更长的终止宽限期，确保任务优雅停止

## 持久化卷 (PVC) 策略

### 模型卷 (Model Volume)

```yaml
persistence:
  modelVolume:
    enabled: true
    name: trained-models
    size: 20Gi
    accessModes:
      - ReadWriteMany
    storageClass: ""
    mountPath: /app/trained_models
```

**特性**:
- `ReadWriteMany`: 多Pod共享访问
- `helm.sh/resource-policy: keep`: Helm升级时保留数据
- 存储训练好的模型文件，支持版本管理
- 建议使用支持RWX的存储类（如NFS、GlusterFS、Portworx等）

### 数据卷 (Data Volume)

```yaml
persistence:
  dataVolume:
    enabled: true
    name: data
    size: 50Gi
    accessModes:
      - ReadWriteMany
    mountPath: /app/data
```

**特性**:
- 存储CSV数据文件、临时处理文件
- 支持多Pod共享访问
- 保留策略：`keep`

### 日志卷 (Logs Volume)

```yaml
persistence:
  logsVolume:
    enabled: true
    name: logs
    size: 10Gi
    accessModes:
      - ReadWriteOnce
    mountPath: /app/logs
```

**特性**:
- 默认使用 `emptyDir` (ReadWriteOnce)
- 如需持久化日志，可修改为RWX PVC
- 建议生产环境使用EFK/ELK栈集中收集日志

### 存储类建议

| 环境 | 存储类 | 性能 | 说明 |
|------|--------|------|------|
| 开发 | standard | 普通 | 本地或云厂商标准存储 |
| 测试 | premium | 高性能 | SSD存储，保证IO性能 |
| 生产 | ultra | 超高性能 | 超低延迟SSD，支持高并发 |

## ConfigMap / Secret 管理

### ConfigMap

管理非敏感配置，如：
- 数据库连接配置（主机、端口、数据库名）
- Redis连接配置
- 调度器配置（Cron表达式、分片数）
- 流式预测配置（窗口大小、TTL）
- 日志级别配置

**热更新**: 修改ConfigMap后需重启Pod生效。

### Secret

管理敏感数据，如：
- 数据库密码
- Redis密码
- JWT密钥
- API加密密钥
- SSO客户端密钥

**生产环境最佳实践**:
1. 使用External Secret Operator从密钥管理系统同步
2. 禁止在values.yaml中硬编码密码
3. 使用Sealed Secrets加密存储
4. 定期轮换密钥

**示例 - 使用外部Secret**:

```yaml
secret:
  create: false
  name: existing-secret-name
```

## 安全配置

### Pod安全上下文

```yaml
podSecurityContext:
  fsGroup: 1000
  runAsNonRoot: true
  runAsUser: 1000

securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL
```

### 网络策略 (可选)

```yaml
networkPolicy:
  enabled: true
  ingressRules:
    api:
      - from:
          - namespaceSelector:
              matchLabels:
                kubernetes.io/metadata.name: ingress-nginx
        ports:
          - port: 8000
```

## 监控与告警

### ServiceMonitor

自动配置Prometheus监控：

```yaml
serviceMonitor:
  enabled: true
  namespace: monitoring
  interval: 30s
  scrapeTimeout: 10s
  labels:
    release: prometheus
```

### 关键指标

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| `stream_ingest_qps` | 流式摄入QPS | >5000 告警 |
| `prediction_task_success_rate` | 预测成功率 | <0.95 告警 |
| `task_success_rate{task_type="prediction"}` | 任务成功率 | <0.9 告警 |
| `http_request_duration_seconds` | HTTP延迟 | P99 > 2s 告警 |

### 告警规则示例

```yaml
groups:
  - name: bolt-prediction
    rules:
      - alert: HighPredictionLatency
        expr: histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High prediction latency"
          description: "P99 latency is {{ $value }}s"

      - alert: LowPredictionSuccessRate
        expr: task_success_rate{task_type="prediction"} < 0.9
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Low prediction success rate"
          description: "Success rate is {{ $value }}"
```

## 部署示例

### 开发环境

```bash
helm install bolt-prediction-dev . \
  --namespace dev \
  --create-namespace \
  --set api.replicaCount=1 \
  --set streamConsumer.replicaCount=1 \
  --set api.autoscaling.enabled=false \
  --set streamConsumer.autoscaling.enabled=false \
  --set persistence.modelVolume.size=5Gi \
  --set persistence.dataVolume.size=10Gi
```

### 预发布环境

```bash
helm install bolt-prediction-staging . \
  --namespace staging \
  --create-namespace \
  -f values-staging.yaml
```

### 生产环境

```bash
helm install bolt-prediction-prod . \
  --namespace prod \
  --create-namespace \
  -f values-prod.yaml \
  --set mysql.architecture=replication \
  --set redis.architecture=replication \
  --set global.storageClass=ssd-premium
```

## 故障排查

### 常见问题

**1. HPA无法获取自定义指标**

检查：
- Prometheus Adapter是否正常运行
- ServiceMonitor是否正确配置
- 指标是否在Prometheus中存在
- Adapter规则配置是否正确

**2. 健康检查失败**

检查：
- `/health` 端点是否正常响应
- 数据库连接是否正常
- 模型目录权限是否正确
- 探针超时时间设置是否合理

**3. 调度器重复执行任务**

检查：
- Leader选举是否正常工作
- 数据库连接是否正常
- `sc_scheduler_leader` 表是否存在且数据正确
- 实例ID是否正确生成

**4. 流式处理背压**

检查：
- `stream_ingest_qps` 指标是否过高
- Stream Consumer副本数是否足够
- 预测延迟是否在可接受范围内
- 考虑增加HPA的maxReplicas

## 升级与回滚

### 升级

```bash
helm upgrade bolt-prediction . -f values-prod.yaml
```

### 回滚

```bash
# 查看历史版本
helm history bolt-prediction

# 回滚到指定版本
helm rollback bolt-prediction <revision-number>
```

## 卸载

```bash
helm uninstall bolt-prediction --namespace bolt-prediction

# 注意：PVC默认保留，如需彻底删除：
kubectl delete pvc -l app.kubernetes.io/part-of=bolt-prediction -n bolt-prediction
```

## License

Apache-2.0
