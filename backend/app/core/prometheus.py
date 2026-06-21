"""
Prometheus 指标管理模块

提供 Prometheus 格式的指标采集和暴露功能。

指标列表:
- http_requests_total: HTTP 请求总数（Counter）
- http_request_duration_seconds: HTTP 请求延迟直方图（Histogram）
- prediction_requests_total: 预测请求总数（Counter）
- prediction_duration_seconds: 预测延迟直方图（Histogram）
- prediction_status_total: 预测结果分布（Counter，按状态分类）
- model_loaded_count: 已加载模型数量（Gauge）
- gpu_utilization_percent: GPU 利用率（Gauge）
- gpu_memory_used_bytes: GPU 内存使用（Gauge）
- task_success_rate: 任务成功率（Gauge）
- prediction_task_total: 预测任务总数（Counter）
- prediction_task_success_total: 成功预测任务数（Counter）
- prediction_task_failed_total: 失败预测任务数（Counter）

使用示例:
    from app.core.prometheus import metrics

    metrics.request_count.labels(method="GET", path="/health", status="200").inc()
    metrics.prediction_count.labels(node_type="bolt", status_code="0").inc()
    metrics.model_loaded.set(5)
"""

import time
import threading
from typing import Dict, Any, Optional
from collections import defaultdict
from loguru import logger

from app.utils.config import config
from app.utils.device import check_cuda_available, get_gpu_count


class PrometheusMetric:
    """Prometheus 指标基类"""

    def __init__(self, name: str, help_text: str, labels: Optional[list] = None):
        self.name = name
        self.help = help_text
        self.labels = labels or []

    def format_help(self) -> str:
        return f"# HELP {self.name} {self.help}"

    def format_type(self, metric_type: str) -> str:
        return f"# TYPE {self.name} {metric_type}"


class Counter(PrometheusMetric):
    """计数器指标（单调递增）"""

    def __init__(self, name: str, help_text: str, labels: Optional[list] = None):
        super().__init__(name, help_text, labels)
        self._values: Dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()

    def inc(self, amount: float = 1.0, label_values: Optional[tuple] = None):
        """增加计数器值"""
        label_values = label_values or tuple()
        with self._lock:
            self._values[label_values] += amount

    def get(self, label_values: Optional[tuple] = None) -> float:
        """获取计数器值"""
        label_values = label_values or tuple()
        return self._values.get(label_values, 0.0)

    def format(self) -> str:
        """格式化为 Prometheus 文本格式"""
        lines = [self.format_help(), self.format_type("counter")]

        if not self._values:
            if not self.labels:
                lines.append(f"{self.name} 0")
            return "\n".join(lines) + "\n"

        for label_values, value in sorted(self._values.items()):
            if self.labels and label_values:
                label_str = ",".join(
                    f'{name}="{value}"'
                    for name, value in zip(self.labels, label_values)
                )
                lines.append(f"{self.name}{{{label_str}}} {value}")
            else:
                lines.append(f"{self.name} {value}")

        return "\n".join(lines) + "\n"


class Gauge(PrometheusMetric):
    """仪表盘指标（可增可减）"""

    def __init__(self, name: str, help_text: str, labels: Optional[list] = None):
        super().__init__(name, help_text, labels)
        self._values: Dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()

    def set(self, value: float, label_values: Optional[tuple] = None):
        """设置仪表盘值"""
        label_values = label_values or tuple()
        with self._lock:
            self._values[label_values] = value

    def inc(self, amount: float = 1.0, label_values: Optional[tuple] = None):
        """增加仪表盘值"""
        label_values = label_values or tuple()
        with self._lock:
            self._values[label_values] += amount

    def dec(self, amount: float = 1.0, label_values: Optional[tuple] = None):
        """减少仪表盘值"""
        label_values = label_values or tuple()
        with self._lock:
            self._values[label_values] -= amount

    def get(self, label_values: Optional[tuple] = None) -> float:
        """获取仪表盘值"""
        label_values = label_values or tuple()
        return self._values.get(label_values, 0.0)

    def format(self) -> str:
        """格式化为 Prometheus 文本格式"""
        lines = [self.format_help(), self.format_type("gauge")]

        if not self._values:
            if not self.labels:
                lines.append(f"{self.name} 0")
            return "\n".join(lines) + "\n"

        for label_values, value in sorted(self._values.items()):
            if self.labels and label_values:
                label_str = ",".join(
                    f'{name}="{value}"'
                    for name, value in zip(self.labels, label_values)
                )
                lines.append(f"{self.name}{{{label_str}}} {value}")
            else:
                lines.append(f"{self.name} {value}")

        return "\n".join(lines) + "\n"


class Histogram(PrometheusMetric):
    """直方图指标"""

    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    def __init__(
        self,
        name: str,
        help_text: str,
        labels: Optional[list] = None,
        buckets: Optional[tuple] = None
    ):
        super().__init__(name, help_text, labels)
        self.buckets = buckets or self.DEFAULT_BUCKETS
        self._bucket_counts: Dict[tuple, Dict[float, int]] = defaultdict(
            lambda: {b: 0 for b in self.buckets}
        )
        self._sums: Dict[tuple, float] = defaultdict(float)
        self._counts: Dict[tuple, int] = defaultdict(int)
        self._lock = threading.Lock()

    def observe(self, value: float, label_values: Optional[tuple] = None):
        """记录一个观测值"""
        label_values = label_values or tuple()
        with self._lock:
            self._counts[label_values] += 1
            self._sums[label_values] += value

            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[label_values][bucket] += 1

    def format(self) -> str:
        """格式化为 Prometheus 文本格式"""
        lines = [self.format_help(), self.format_type("histogram")]

        if not self._counts:
            return "\n".join(lines) + "\n"

        for label_values in sorted(self._counts.keys()):
            label_str = ""
            if self.labels and label_values:
                label_str = ",".join(
                    f'{name}="{value}"'
                    for name, value in zip(self.labels, label_values)
                )

            for bucket in self.buckets:
                count = self._bucket_counts[label_values].get(bucket, 0)
                if label_str:
                    lines.append(
                        f'{self.name}_bucket{{{label_str},le="{bucket}"}} {count}'
                    )
                else:
                    lines.append(f'{self.name}_bucket{{le="{bucket}"}} {count}')

            if label_str:
                lines.append(f'{self.name}_sum{{{label_str}}} {self._sums[label_values]}')
                lines.append(f'{self.name}_count{{{label_str}}} {self._counts[label_values]}')
            else:
                lines.append(f'{self.name}_sum {self._sums[label_values]}')
                lines.append(f'{self.name}_count {self._counts[label_values]}')

        return "\n".join(lines) + "\n"


class Summary(PrometheusMetric):
    """摘要指标（用于分位数）"""

    def __init__(
        self,
        name: str,
        help_text: str,
        labels: Optional[list] = None,
        window_seconds: int = 600
    ):
        super().__init__(name, help_text, labels)
        self.window_seconds = window_seconds
        self._observations: Dict[tuple, list] = defaultdict(list)
        self._sums: Dict[tuple, float] = defaultdict(float)
        self._counts: Dict[tuple, int] = defaultdict(int)
        self._lock = threading.Lock()

    def observe(self, value: float, label_values: Optional[tuple] = None):
        """记录一个观测值"""
        label_values = label_values or tuple()
        now = time.time()

        with self._lock:
            self._counts[label_values] += 1
            self._sums[label_values] += value
            self._observations[label_values].append((now, value))

            cutoff = now - self.window_seconds
            self._observations[label_values] = [
                (t, v) for t, v in self._observations[label_values] if t >= cutoff
            ]

    def get_quantile(self, q: float, label_values: Optional[tuple] = None) -> float:
        """获取分位数值"""
        label_values = label_values or tuple()

        with self._lock:
            values = [v for _, v in self._observations.get(label_values, [])]

        if not values:
            return 0.0

        values.sort()
        index = int(len(values) * q)
        index = min(index, len(values) - 1)
        return values[index]

    def format(self) -> str:
        """格式化为 Prometheus 文本格式"""
        lines = [self.format_help(), self.format_type("summary")]

        quantiles = [0.5, 0.9, 0.99]

        if not self._counts:
            return "\n".join(lines) + "\n"

        for label_values in sorted(self._counts.keys()):
            label_str = ""
            if self.labels and label_values:
                label_str = ",".join(
                    f'{name}="{value}"'
                    for name, value in zip(self.labels, label_values)
                )

            for q in quantiles:
                value = self.get_quantile(q, label_values)
                if label_str:
                    lines.append(
                        f'{self.name}{{{label_str},quantile="{q}"}} {value}'
                    )
                else:
                    lines.append(f'{self.name}{{quantile="{q}"}} {value}')

            if label_str:
                lines.append(f'{self.name}_sum{{{label_str}}} {self._sums[label_values]}')
                lines.append(f'{self.name}_count{{{label_str}}} {self._counts[label_values]}')
            else:
                lines.append(f'{self.name}_sum {self._sums[label_values]}')
                lines.append(f'{self.name}_count {self._counts[label_values]}')

        return "\n".join(lines) + "\n"


class MetricsRegistry:
    """指标注册表"""

    def __init__(self):
        self._metrics: Dict[str, PrometheusMetric] = {}
        self._lock = threading.Lock()

    def register(self, metric: PrometheusMetric):
        """注册指标"""
        with self._lock:
            self._metrics[metric.name] = metric

    def get(self, name: str) -> Optional[PrometheusMetric]:
        """获取指标"""
        return self._metrics.get(name)

    def generate_text(self) -> str:
        """生成 Prometheus 文本格式的所有指标"""
        lines = []
        with self._lock:
            for name in sorted(self._metrics.keys()):
                metric = self._metrics[name]
                lines.append(metric.format())

        return "".join(lines)


class AppMetrics:
    """应用指标集合"""

    def __init__(self):
        self.registry = MetricsRegistry()

        # HTTP 请求指标
        self.http_requests_total = Counter(
            "http_requests_total",
            "Total number of HTTP requests",
            ["method", "path", "status_code"]
        )
        self.registry.register(self.http_requests_total)

        self.http_request_duration_seconds = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "path"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
        )
        self.registry.register(self.http_request_duration_seconds)

        # 预测请求指标
        self.prediction_requests_total = Counter(
            "prediction_requests_total",
            "Total number of prediction requests",
            ["node_type", "model_type"]
        )
        self.registry.register(self.prediction_requests_total)

        self.prediction_duration_seconds = Histogram(
            "prediction_duration_seconds",
            "Prediction request duration in seconds",
            ["node_type", "model_type"],
            buckets=(0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0)
        )
        self.registry.register(self.prediction_duration_seconds)

        # 预测结果分布
        self.prediction_status_total = Counter(
            "prediction_status_total",
            "Total number of predictions by status code",
            ["node_type", "status_code", "status_label"]
        )
        self.registry.register(self.prediction_status_total)

        # 模型加载数
        self.model_loaded_count = Gauge(
            "model_loaded_count",
            "Number of loaded models",
            ["model_type"]
        )
        self.registry.register(self.model_loaded_count)

        # GPU 指标
        self.gpu_utilization_percent = Gauge(
            "gpu_utilization_percent",
            "GPU utilization percentage",
            ["gpu_id", "gpu_name"]
        )
        self.registry.register(self.gpu_utilization_percent)

        self.gpu_memory_used_bytes = Gauge(
            "gpu_memory_used_bytes",
            "GPU memory used in bytes",
            ["gpu_id", "gpu_name"]
        )
        self.registry.register(self.gpu_memory_used_bytes)

        self.gpu_memory_total_bytes = Gauge(
            "gpu_memory_total_bytes",
            "GPU total memory in bytes",
            ["gpu_id", "gpu_name"]
        )
        self.registry.register(self.gpu_memory_total_bytes)

        # 任务成功率
        self.prediction_task_total = Counter(
            "prediction_task_total",
            "Total number of prediction tasks",
            ["task_type"]
        )
        self.registry.register(self.prediction_task_total)

        self.prediction_task_success_total = Counter(
            "prediction_task_success_total",
            "Total number of successful prediction tasks",
            ["task_type"]
        )
        self.registry.register(self.prediction_task_success_total)

        self.prediction_task_failed_total = Counter(
            "prediction_task_failed_total",
            "Total number of failed prediction tasks",
            ["task_type", "error_type"]
        )
        self.registry.register(self.prediction_task_failed_total)

        self.task_success_rate = Gauge(
            "task_success_rate",
            "Task success rate (0-1)",
            ["task_type"]
        )
        self.registry.register(self.task_success_rate)

        # 延迟分位数（P99等）
        self.request_latency_summary = Summary(
            "request_latency_seconds",
            "Request latency summary with quantiles",
            ["method", "path"],
            window_seconds=600
        )
        self.registry.register(self.request_latency_summary)

        # 流式摄入QPS指标（用于HPA自定义指标）
        self.stream_ingest_qps = Gauge(
            "stream_ingest_qps",
            "Stream data ingestion QPS (queries per second)",
            ["component", "node_type"]
        )
        self.registry.register(self.stream_ingest_qps)

        # 流式摄入总量
        self.stream_ingest_total = Counter(
            "stream_ingest_total",
            "Total number of stream data points ingested",
            ["component", "node_type", "status"]
        )
        self.registry.register(self.stream_ingest_total)

        # 活跃流数
        self.stream_active_count = Gauge(
            "stream_active_count",
            "Number of active streaming connections",
            ["component"]
        )
        self.registry.register(self.stream_active_count)

        # 滑动窗口填充度
        self.stream_window_fill_ratio = Gauge(
            "stream_window_fill_ratio",
            "Sliding window fill ratio (0-1)",
            ["component", "bolt_id"]
        )
        self.registry.register(self.stream_window_fill_ratio)

        # Redis 窗口集群监控指标
        self.redis_window_memory_used_bytes = Gauge(
            "redis_window_memory_used_bytes",
            "Redis memory used for window storage in bytes",
            ["component"]
        )
        self.registry.register(self.redis_window_memory_used_bytes)

        self.redis_window_memory_limit_bytes = Gauge(
            "redis_window_memory_limit_bytes",
            "Redis memory limit for window storage in bytes",
            ["component"]
        )
        self.registry.register(self.redis_window_memory_limit_bytes)

        self.redis_window_key_count = Gauge(
            "redis_window_key_count",
            "Number of Redis keys used by window storage",
            ["component", "tenant_id"]
        )
        self.registry.register(self.redis_window_key_count)

        self.redis_window_expired_total = Counter(
            "redis_window_expired_total",
            "Total number of expired window keys in Redis",
            ["component"]
        )
        self.registry.register(self.redis_window_expired_total)

        self.redis_window_expire_rate = Gauge(
            "redis_window_expire_rate",
            "Window key expiration rate (expired / total) in Redis",
            ["component"]
        )
        self.registry.register(self.redis_window_expire_rate)

        # 数据库连接池指标
        self.db_pool_checkout_count = Gauge(
            "db_pool_checkout_count",
            "Total number of connection checkouts from the database pool",
            []
        )
        self.registry.register(self.db_pool_checkout_count)

        self.db_pool_overflow = Gauge(
            "db_pool_overflow",
            "Number of overflow connections in the database pool",
            []
        )
        self.registry.register(self.db_pool_overflow)

        self.db_pool_latency_ms = Gauge(
            "db_pool_latency_ms",
            "Average database query latency in milliseconds",
            []
        )
        self.registry.register(self.db_pool_latency_ms)

        self.db_pool_active = Gauge(
            "db_pool_active",
            "Number of active (checked out) connections in the database pool",
            []
        )
        self.registry.register(self.db_pool_active)

        self.db_pool_idle = Gauge(
            "db_pool_idle",
            "Number of idle (checked in) connections in the database pool",
            []
        )
        self.registry.register(self.db_pool_idle)

        self.db_pool_size = Gauge(
            "db_pool_size",
            "Total size of the database connection pool",
            []
        )
        self.registry.register(self.db_pool_size)

        self.db_pool_slow_query_count = Gauge(
            "db_pool_slow_query_count",
            "Total number of slow queries detected (>500ms)",
            []
        )
        self.registry.register(self.db_pool_slow_query_count)

        self.db_pool_n_plus_one_detected = Gauge(
            "db_pool_n_plus_one_detected",
            "Total number of N+1 query patterns detected",
            []
        )
        self.registry.register(self.db_pool_n_plus_one_detected)

        logger.info("Prometheus metrics initialized")

    # ========== 便捷方法 ==========

    def record_http_request(self, method: str, path: str, status_code: str, duration: float):
        """记录 HTTP 请求"""
        labels = (method, path, status_code)
        self.http_requests_total.inc(label_values=labels)
        self.http_request_duration_seconds.observe(duration, label_values=(method, path))
        self.request_latency_summary.observe(duration, label_values=(method, path))

    def record_prediction(
        self,
        node_type: str,
        status_code: int,
        status_label: str,
        duration: float,
        model_type: str = "lstm"
    ):
        """记录预测请求"""
        self.prediction_requests_total.inc(label_values=(node_type, model_type))
        self.prediction_duration_seconds.observe(duration, label_values=(node_type, model_type))
        self.prediction_status_total.inc(
            label_values=(node_type, str(status_code), status_label)
        )

    def record_prediction_task(self, task_type: str, success: bool, error_type: str = "unknown"):
        """记录预测任务结果"""
        self.prediction_task_total.inc(label_values=(task_type,))

        if success:
            self.prediction_task_success_total.inc(label_values=(task_type,))
        else:
            self.prediction_task_failed_total.inc(label_values=(task_type, error_type))

        # 更新成功率
        total = self.prediction_task_total.get((task_type,))
        success_count = self.prediction_task_success_total.get((task_type,))
        rate = success_count / total if total > 0 else 0.0
        self.task_success_rate.set(rate, label_values=(task_type,))

    def update_gpu_metrics(self):
        """更新 GPU 指标（从 PyTorch 获取）"""
        try:
            import torch

            if not check_cuda_available():
                return

            gpu_count = get_gpu_count()
            for gpu_id in range(gpu_count):
                props = torch.cuda.get_device_properties(gpu_id)
                gpu_name = props.name
                total_memory = props.total_memory
                used_memory = torch.cuda.memory_allocated(gpu_id)
                utilization = used_memory / total_memory if total_memory > 0 else 0.0

                self.gpu_utilization_percent.set(
                    utilization * 100,
                    label_values=(str(gpu_id), gpu_name)
                )
                self.gpu_memory_used_bytes.set(
                    float(used_memory),
                    label_values=(str(gpu_id), gpu_name)
                )
                self.gpu_memory_total_bytes.set(
                    float(total_memory),
                    label_values=(str(gpu_id), gpu_name)
                )
        except Exception as e:
            logger.debug(f"Failed to update GPU metrics: {e}")

    def update_model_count(self, model_type: str, count: int):
        """更新已加载模型数量"""
        self.model_loaded_count.set(count, label_values=(model_type,))

    def record_stream_ingest(
        self,
        component: str,
        node_type: str,
        success: bool = True,
        count: int = 1
    ):
        """记录流式数据摄入"""
        status = "success" if success else "failed"
        self.stream_ingest_total.inc(
            amount=float(count),
            label_values=(component, node_type, status)
        )

    def update_stream_qps(
        self,
        component: str,
        node_type: str,
        qps: float
    ):
        """更新流式摄入QPS指标（用于HPA）"""
        self.stream_ingest_qps.set(
            value=qps,
            label_values=(component, node_type)
        )

    def update_stream_active_count(self, component: str, count: int):
        """更新活跃流数量"""
        self.stream_active_count.set(
            value=float(count),
            label_values=(component,)
        )

    def update_window_fill_ratio(self, component: str, bolt_id: str, ratio: float):
        """更新滑动窗口填充度"""
        self.stream_window_fill_ratio.set(
            value=float(ratio),
            label_values=(component, bolt_id)
        )

    def update_redis_window_metrics(
        self,
        component: str,
        used_memory_bytes: float,
        memory_limit_bytes: float,
        key_count_by_tenant: Optional[Dict[str, int]] = None,
        expired_total: int = 0,
        total_keys: int = 0,
    ):
        """更新 Redis 窗口集群监控指标"""
        self.redis_window_memory_used_bytes.set(
            value=used_memory_bytes,
            label_values=(component,)
        )
        self.redis_window_memory_limit_bytes.set(
            value=memory_limit_bytes,
            label_values=(component,)
        )
        if key_count_by_tenant:
            for tenant_id, count in key_count_by_tenant.items():
                self.redis_window_key_count.set(
                    value=float(count),
                    label_values=(component, tenant_id)
                )
        if expired_total > 0:
            self.redis_window_expired_total.inc(
                amount=float(expired_total),
                label_values=(component,)
            )
        if total_keys > 0:
            rate = expired_total / total_keys if total_keys > 0 else 0.0
            self.redis_window_expire_rate.set(
                value=rate,
                label_values=(component,)
            )

    def _update_db_pool_metrics(self) -> None:
        """更新数据库连接池指标"""
        try:
            from app.utils.db_pool import db_pool
            snapshot = db_pool.get_metrics_snapshot()
            if not snapshot:
                return
            self.db_pool_checkout_count.set(snapshot.get('db_pool_checkout_count', 0))
            self.db_pool_overflow.set(snapshot.get('db_pool_overflow', 0))
            self.db_pool_latency_ms.set(snapshot.get('db_pool_latency_ms', 0.0))
            self.db_pool_active.set(snapshot.get('db_pool_active', 0))
            self.db_pool_idle.set(snapshot.get('db_pool_idle', 0))
            self.db_pool_size.set(snapshot.get('db_pool_size', 0))
            self.db_pool_slow_query_count.set(snapshot.get('db_pool_slow_query_count', 0))
            self.db_pool_n_plus_one_detected.set(snapshot.get('db_pool_n_plus_one_detected', 0))
        except Exception as e:
            logger.debug(f"Failed to update DB pool metrics: {e}")

    def generate_metrics_text(self) -> str:
        """生成 Prometheus 格式的指标文本"""
        self.update_gpu_metrics()
        self._update_db_pool_metrics()
        return self.registry.generate_text()


# 全局指标实例
metrics = AppMetrics()
