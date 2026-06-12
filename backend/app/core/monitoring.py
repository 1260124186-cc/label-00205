"""
监控和告警模块

提供系统监控和异常告警功能。

功能:
1. 系统健康监控
2. 性能指标采集
3. 异常告警通知
4. 日志分析

使用示例:
    from app.core.monitoring import SystemMonitor, AlertManager
    
    monitor = SystemMonitor()
    status = monitor.get_status()
"""

import os
import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from loguru import logger

from app.utils.config import config


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """
    告警信息
    
    Attributes:
        level: 告警级别
        source: 告警来源
        message: 告警消息
        timestamp: 时间戳
        details: 详细信息
        resolved: 是否已解决
    """
    level: AlertLevel
    source: str
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    details: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False


@dataclass
class HealthStatus:
    """
    健康状态
    
    Attributes:
        healthy: 是否健康
        components: 各组件状态
        metrics: 性能指标
        alerts: 活动告警
    """
    healthy: bool
    components: Dict[str, bool]
    metrics: Dict[str, float]
    alerts: List[Alert]


class MetricsCollector:
    """
    指标采集器
    
    采集系统和应用性能指标。
    """
    
    def __init__(self, history_size: int = 100):
        """初始化指标采集器"""
        self.history_size = history_size
        
        # 指标历史
        self.cpu_history: deque = deque(maxlen=history_size)
        self.memory_history: deque = deque(maxlen=history_size)
        self.request_latency: deque = deque(maxlen=history_size)
        
        # 计数器
        self.request_count = 0
        self.error_count = 0
        self.prediction_count = 0
        
    def collect_system_metrics(self) -> Dict[str, float]:
        """
        采集系统指标
        
        Returns:
            Dict: 系统指标
        """
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        self.cpu_history.append(cpu_percent)
        self.memory_history.append(memory.percent)
        
        return {
            'cpu_percent': cpu_percent,
            'cpu_avg': sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else 0,
            'memory_percent': memory.percent,
            'memory_used_gb': memory.used / (1024 ** 3),
            'memory_available_gb': memory.available / (1024 ** 3),
            'disk_percent': disk.percent,
            'disk_free_gb': disk.free / (1024 ** 3)
        }
    
    def collect_process_metrics(self) -> Dict[str, float]:
        """
        采集进程指标
        
        Returns:
            Dict: 进程指标
        """
        try:
            process = psutil.Process(os.getpid())
            
            return {
                'process_cpu_percent': process.cpu_percent(),
                'process_memory_mb': process.memory_info().rss / (1024 ** 2),
                'process_threads': process.num_threads(),
                'process_open_files': len(process.open_files())
            }
        except Exception as e:
            logger.warning(f"采集进程指标失败: {e}")
            return {}
    
    def record_request(self, latency_ms: float, success: bool = True) -> None:
        """
        记录请求
        
        Args:
            latency_ms: 延迟（毫秒）
            success: 是否成功
        """
        self.request_count += 1
        self.request_latency.append(latency_ms)
        
        if not success:
            self.error_count += 1
    
    def record_prediction(self) -> None:
        """记录预测请求"""
        self.prediction_count += 1
    
    def get_request_stats(self) -> Dict[str, float]:
        """获取请求统计"""
        if not self.request_latency:
            return {
                'request_count': self.request_count,
                'error_count': self.error_count,
                'prediction_count': self.prediction_count,
                'avg_latency_ms': 0,
                'p95_latency_ms': 0,
                'error_rate': 0
            }
        
        latencies = list(self.request_latency)
        latencies.sort()
        
        p95_idx = int(len(latencies) * 0.95)
        
        return {
            'request_count': self.request_count,
            'error_count': self.error_count,
            'prediction_count': self.prediction_count,
            'avg_latency_ms': sum(latencies) / len(latencies),
            'p95_latency_ms': latencies[p95_idx] if p95_idx < len(latencies) else latencies[-1],
            'error_rate': self.error_count / self.request_count if self.request_count > 0 else 0
        }


class AlertManager:
    """
    告警管理器
    
    管理系统告警的生成和通知。
    """
    
    def __init__(self, max_alerts: int = 100):
        """初始化告警管理器"""
        self.max_alerts = max_alerts
        self.alerts: List[Alert] = []
        self.handlers: List[Callable[[Alert], None]] = []
        self._lock = threading.Lock()
        
        # 告警阈值
        self.thresholds = {
            'cpu_percent': 90,
            'memory_percent': 85,
            'disk_percent': 90,
            'error_rate': 0.1,
            'latency_p95_ms': 5000
        }
    
    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        """
        添加告警处理器
        
        Args:
            handler: 处理函数
        """
        self.handlers.append(handler)
    
    def create_alert(
        self,
        level: AlertLevel,
        source: str,
        message: str,
        details: Optional[Dict] = None
    ) -> Alert:
        """
        创建告警
        
        Args:
            level: 告警级别
            source: 来源
            message: 消息
            details: 详细信息
            
        Returns:
            Alert: 告警对象
        """
        alert = Alert(
            level=level,
            source=source,
            message=message,
            details=details or {}
        )
        
        with self._lock:
            self.alerts.append(alert)
            
            # 清理旧告警
            if len(self.alerts) > self.max_alerts:
                self.alerts = self.alerts[-self.max_alerts:]
        
        # 调用处理器
        for handler in self.handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"告警处理器执行失败: {e}")
        
        # 记录日志
        log_func = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical
        }.get(level, logger.warning)
        
        log_func(f"[告警] {source}: {message}")
        
        return alert
    
    def check_metrics(self, metrics: Dict[str, float]) -> List[Alert]:
        """
        检查指标并生成告警
        
        Args:
            metrics: 指标字典
            
        Returns:
            List[Alert]: 生成的告警
        """
        new_alerts = []
        
        # CPU告警
        if metrics.get('cpu_percent', 0) > self.thresholds['cpu_percent']:
            alert = self.create_alert(
                AlertLevel.WARNING,
                'system',
                f"CPU使用率过高: {metrics['cpu_percent']:.1f}%",
                {'cpu_percent': metrics['cpu_percent']}
            )
            new_alerts.append(alert)
        
        # 内存告警
        if metrics.get('memory_percent', 0) > self.thresholds['memory_percent']:
            alert = self.create_alert(
                AlertLevel.WARNING,
                'system',
                f"内存使用率过高: {metrics['memory_percent']:.1f}%",
                {'memory_percent': metrics['memory_percent']}
            )
            new_alerts.append(alert)
        
        # 磁盘告警
        if metrics.get('disk_percent', 0) > self.thresholds['disk_percent']:
            alert = self.create_alert(
                AlertLevel.ERROR,
                'system',
                f"磁盘空间不足: {metrics['disk_percent']:.1f}%",
                {'disk_percent': metrics['disk_percent']}
            )
            new_alerts.append(alert)
        
        return new_alerts
    
    def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[Alert]:
        """获取活动告警"""
        alerts = [a for a in self.alerts if not a.resolved]
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        return alerts
    
    def resolve_alert(self, index: int) -> bool:
        """解决告警"""
        if 0 <= index < len(self.alerts):
            self.alerts[index].resolved = True
            return True
        return False
    
    def clear_resolved(self) -> int:
        """清除已解决的告警"""
        with self._lock:
            original_count = len(self.alerts)
            self.alerts = [a for a in self.alerts if not a.resolved]
            return original_count - len(self.alerts)


class SystemMonitor:
    """
    系统监控器
    
    综合监控系统健康状态。
    """
    
    def __init__(self):
        """初始化系统监控器"""
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._check_interval = 60  # 秒
        
        logger.info("系统监控器初始化完成")
    
    def start(self) -> None:
        """启动后台监控"""
        if self._running:
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.info("系统监控已启动")
    
    def stop(self) -> None:
        """停止监控"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        logger.info("系统监控已停止")
    
    def _monitor_loop(self) -> None:
        """监控循环"""
        while self._running:
            try:
                # 采集指标
                system_metrics = self.metrics_collector.collect_system_metrics()
                process_metrics = self.metrics_collector.collect_process_metrics()
                
                # 检查并生成告警
                self.alert_manager.check_metrics(system_metrics)
                
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
            
            time.sleep(self._check_interval)
    
    def get_status(self) -> HealthStatus:
        """
        获取健康状态
        
        Returns:
            HealthStatus: 健康状态
        """
        # 采集指标
        system_metrics = self.metrics_collector.collect_system_metrics()
        process_metrics = self.metrics_collector.collect_process_metrics()
        request_stats = self.metrics_collector.get_request_stats()
        
        # 合并指标
        all_metrics = {**system_metrics, **process_metrics, **request_stats}
        
        # 检查各组件状态
        components = {
            'api': True,
            'database': self._check_database(),
            'model': self._check_model(),
            'scheduler': self._check_scheduler()
        }
        
        # 获取活动告警
        alerts = self.alert_manager.get_active_alerts()
        
        # 判断整体健康状态
        healthy = all(components.values()) and \
                  not any(a.level == AlertLevel.CRITICAL for a in alerts)
        
        return HealthStatus(
            healthy=healthy,
            components=components,
            metrics=all_metrics,
            alerts=alerts
        )
    
    def _check_database(self) -> bool:
        """检查数据库状态"""
        try:
            from app.utils.db_pool import db_pool
            health = db_pool.health_check()
            return health.get('healthy', False)
        except:
            return False
    
    def _check_model(self) -> bool:
        """检查模型状态"""
        # 简单检查模型目录是否存在
        model_path = Path(__file__).parent.parent.parent / 'trained_models'
        return model_path.exists()
    
    def _check_scheduler(self) -> bool:
        """检查调度器状态"""
        try:
            from app.schedulers.scheduler import task_scheduler
            return task_scheduler is not None
        except:
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        return {
            'system': self.metrics_collector.collect_system_metrics(),
            'process': self.metrics_collector.collect_process_metrics(),
            'requests': self.metrics_collector.get_request_stats()
        }
    
    def record_request(self, latency_ms: float, success: bool = True) -> None:
        """记录请求"""
        self.metrics_collector.record_request(latency_ms, success)
    
    def record_prediction(self) -> None:
        """记录预测"""
        self.metrics_collector.record_prediction()


# 导入Path
from pathlib import Path

# 全局监控器
system_monitor = SystemMonitor()
