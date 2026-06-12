"""
训练监控模块

提供模型训练过程的监控和日志记录功能。

功能:
1. 训练进度跟踪
2. 指标记录和可视化
3. 早停监控
4. 训练日志持久化

使用示例:
    from app.core.training_monitor import TrainingMonitor
    
    monitor = TrainingMonitor()
    monitor.start_training('bolt_B001')
    monitor.log_metrics(epoch=1, train_loss=0.5, val_acc=0.9)
    monitor.end_training()
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
from loguru import logger

from app.utils.config import config


class TrainingStatus(Enum):
    """训练状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class EpochMetrics:
    """单个epoch的指标"""
    epoch: int
    train_loss: float
    val_loss: Optional[float] = None
    train_acc: Optional[float] = None
    val_acc: Optional[float] = None
    learning_rate: Optional[float] = None
    duration_seconds: float = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TrainingSession:
    """
    训练会话信息
    
    Attributes:
        session_id: 会话ID
        model_id: 模型标识
        model_type: 模型类型
        status: 训练状态
        start_time: 开始时间
        end_time: 结束时间
        total_epochs: 总epoch数
        current_epoch: 当前epoch
        best_metrics: 最佳指标
        metrics_history: 指标历史
        config: 训练配置
        error_message: 错误信息
    """
    session_id: str
    model_id: str
    model_type: str
    status: TrainingStatus = TrainingStatus.PENDING
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_epochs: int = 0
    current_epoch: int = 0
    best_metrics: Dict[str, float] = field(default_factory=dict)
    metrics_history: List[EpochMetrics] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['status'] = self.status.value
        data['metrics_history'] = [m.to_dict() if isinstance(m, EpochMetrics) else m for m in self.metrics_history]
        return data


class TrainingMonitor:
    """
    训练监控器
    
    监控和记录模型训练过程。
    
    Attributes:
        log_dir: 日志目录
        sessions: 训练会话字典
        current_session: 当前会话
    """
    
    def __init__(self, log_dir: Optional[str] = None):
        """
        初始化训练监控器
        
        Args:
            log_dir: 日志目录
        """
        self.log_dir = Path(log_dir or config.get('logging.training_dir', './logs/training'))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.sessions: Dict[str, TrainingSession] = {}
        self.current_session: Optional[TrainingSession] = None
        
        self._callbacks: List[callable] = []
        
        logger.info(f"训练监控器初始化完成: {self.log_dir}")
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
    
    def start_training(
        self,
        model_id: str,
        model_type: str,
        total_epochs: int,
        training_config: Optional[Dict] = None
    ) -> str:
        """
        开始训练会话
        
        Args:
            model_id: 模型标识
            model_type: 模型类型
            total_epochs: 总epoch数
            training_config: 训练配置
            
        Returns:
            str: 会话ID
        """
        session_id = self._generate_session_id()
        
        session = TrainingSession(
            session_id=session_id,
            model_id=model_id,
            model_type=model_type,
            status=TrainingStatus.RUNNING,
            start_time=datetime.now().isoformat(),
            total_epochs=total_epochs,
            config=training_config or {}
        )
        
        self.sessions[session_id] = session
        self.current_session = session
        
        logger.info(f"训练开始: session={session_id}, model={model_id}")
        
        # 触发回调
        self._trigger_callbacks('on_training_start', session)
        
        return session_id
    
    def log_epoch(
        self,
        epoch: int,
        train_loss: float,
        val_loss: Optional[float] = None,
        train_acc: Optional[float] = None,
        val_acc: Optional[float] = None,
        learning_rate: Optional[float] = None,
        duration: float = 0,
        **extra_metrics
    ) -> None:
        """
        记录epoch指标
        
        Args:
            epoch: 当前epoch
            train_loss: 训练损失
            val_loss: 验证损失
            train_acc: 训练准确率
            val_acc: 验证准确率
            learning_rate: 学习率
            duration: epoch耗时
            **extra_metrics: 额外指标
        """
        if self.current_session is None:
            logger.warning("没有活动的训练会话")
            return
        
        metrics = EpochMetrics(
            epoch=epoch,
            train_loss=train_loss,
            val_loss=val_loss,
            train_acc=train_acc,
            val_acc=val_acc,
            learning_rate=learning_rate,
            duration_seconds=duration
        )
        
        self.current_session.current_epoch = epoch
        self.current_session.metrics_history.append(metrics)
        
        # 更新最佳指标
        if val_acc is not None:
            if 'best_val_acc' not in self.current_session.best_metrics or \
               val_acc > self.current_session.best_metrics['best_val_acc']:
                self.current_session.best_metrics['best_val_acc'] = val_acc
                self.current_session.best_metrics['best_epoch'] = epoch
        
        if val_loss is not None:
            if 'best_val_loss' not in self.current_session.best_metrics or \
               val_loss < self.current_session.best_metrics['best_val_loss']:
                self.current_session.best_metrics['best_val_loss'] = val_loss
        
        # 日志输出
        log_msg = f"Epoch {epoch}/{self.current_session.total_epochs}: "
        log_msg += f"train_loss={train_loss:.4f}"
        if val_loss is not None:
            log_msg += f", val_loss={val_loss:.4f}"
        if train_acc is not None:
            log_msg += f", train_acc={train_acc:.4f}"
        if val_acc is not None:
            log_msg += f", val_acc={val_acc:.4f}"
        
        logger.info(log_msg)
        
        # 触发回调
        self._trigger_callbacks('on_epoch_end', self.current_session, metrics)
    
    def end_training(
        self,
        status: TrainingStatus = TrainingStatus.COMPLETED,
        error_message: Optional[str] = None
    ) -> TrainingSession:
        """
        结束训练会话
        
        Args:
            status: 最终状态
            error_message: 错误信息
            
        Returns:
            TrainingSession: 训练会话
        """
        if self.current_session is None:
            logger.warning("没有活动的训练会话")
            return None
        
        self.current_session.status = status
        self.current_session.end_time = datetime.now().isoformat()
        self.current_session.error_message = error_message
        
        # 保存训练日志
        self._save_session(self.current_session)
        
        status_msg = "成功" if status == TrainingStatus.COMPLETED else status.value
        logger.info(
            f"训练结束: session={self.current_session.session_id}, "
            f"status={status_msg}, "
            f"best_val_acc={self.current_session.best_metrics.get('best_val_acc', 'N/A')}"
        )
        
        # 触发回调
        self._trigger_callbacks('on_training_end', self.current_session)
        
        session = self.current_session
        self.current_session = None
        
        return session
    
    def _save_session(self, session: TrainingSession) -> None:
        """保存训练会话到文件"""
        try:
            log_file = self.log_dir / f"{session.session_id}.json"
            
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
            
            logger.debug(f"训练日志已保存: {log_file}")
            
        except Exception as e:
            logger.error(f"保存训练日志失败: {e}")
    
    def load_session(self, session_id: str) -> Optional[TrainingSession]:
        """加载训练会话"""
        log_file = self.log_dir / f"{session_id}.json"
        
        if not log_file.exists():
            return None
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data['status'] = TrainingStatus(data['status'])
            data['metrics_history'] = [
                EpochMetrics(**m) for m in data['metrics_history']
            ]
            
            return TrainingSession(**data)
            
        except Exception as e:
            logger.error(f"加载训练日志失败: {e}")
            return None
    
    def get_recent_sessions(self, limit: int = 10) -> List[TrainingSession]:
        """获取最近的训练会话"""
        log_files = sorted(
            self.log_dir.glob("train_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:limit]
        
        sessions = []
        for log_file in log_files:
            session = self.load_session(log_file.stem)
            if session:
                sessions.append(session)
        
        return sessions
    
    def register_callback(self, callback: callable) -> None:
        """
        注册回调函数
        
        回调函数签名:
        - on_training_start(session: TrainingSession)
        - on_epoch_end(session: TrainingSession, metrics: EpochMetrics)
        - on_training_end(session: TrainingSession)
        """
        self._callbacks.append(callback)
    
    def _trigger_callbacks(self, event: str, *args, **kwargs) -> None:
        """触发回调"""
        for callback in self._callbacks:
            if hasattr(callback, event):
                try:
                    getattr(callback, event)(*args, **kwargs)
                except Exception as e:
                    logger.error(f"回调执行失败: {event}, {e}")


class EarlyStopping:
    """
    早停监控器
    
    监控验证指标，在性能不再提升时停止训练。
    """
    
    def __init__(
        self,
        patience: int = 10,
        min_delta: float = 0.001,
        mode: str = 'min'
    ):
        """
        初始化早停监控器
        
        Args:
            patience: 容忍epoch数
            min_delta: 最小改进阈值
            mode: 'min'监控损失, 'max'监控准确率
        """
        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        
        self.best_value = float('inf') if mode == 'min' else float('-inf')
        self.counter = 0
        self.best_epoch = 0
        self.should_stop = False
    
    def __call__(self, value: float, epoch: int) -> bool:
        """
        检查是否应该停止
        
        Args:
            value: 监控指标值
            epoch: 当前epoch
            
        Returns:
            bool: 是否应该停止
        """
        if self.mode == 'min':
            is_improvement = value < (self.best_value - self.min_delta)
        else:
            is_improvement = value > (self.best_value + self.min_delta)
        
        if is_improvement:
            self.best_value = value
            self.counter = 0
            self.best_epoch = epoch
        else:
            self.counter += 1
            
            if self.counter >= self.patience:
                self.should_stop = True
                logger.info(
                    f"早停触发: 在epoch {self.best_epoch}后{self.patience}个epoch无改进"
                )
        
        return self.should_stop
    
    def reset(self) -> None:
        """重置监控器"""
        self.best_value = float('inf') if self.mode == 'min' else float('-inf')
        self.counter = 0
        self.best_epoch = 0
        self.should_stop = False


# 全局训练监控器
training_monitor = TrainingMonitor()
