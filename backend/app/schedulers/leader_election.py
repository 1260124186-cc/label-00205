"""
调度器Leader选举模块

为大集群场景提供单实例Leader选举机制，避免多个实例同时执行相同任务导致重复预测。

实现原理:
- 基于数据库表 sc_scheduler_leader 的乐观锁（version字段）
- 租约机制（lease_expire_time），避免死锁
- 心跳续期机制，Leader定期更新租约

使用示例:
    from app.schedulers.leader_election import get_leader_election
    
    leader = get_leader_election()
    
    if leader.try_acquire_leadership('prediction_job'):
        try:
            # 执行任务
            run_prediction_job()
            # 定期心跳续期
            while running:
                leader.renew_lease('prediction_job')
                time.sleep(30)
        finally:
            leader.release_leadership('prediction_job')
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from loguru import logger

from app.utils.database import get_db, SchedulerLeader
from app.utils.config import config
from app.schedulers.job_execution import get_instance_id


class LeaderElection:
    """
    基于数据库的Leader选举器

    提供租约式Leader选举，支持:
    1. 尝试获取Leader地位
    2. 心跳续期
    3. 释放Leader地位
    4. 检查是否为Leader
    """

    def __init__(self, lease_ttl_seconds: int = 300, retry_count: int = 3, retry_delay_ms: int = 100):
        """
        初始化Leader选举器

        Args:
            lease_ttl_seconds: 租约有效期（秒），默认5分钟
            retry_count: 获取锁的重试次数
            retry_delay_ms: 重试间隔（毫秒）
        """
        self.lease_ttl = timedelta(seconds=config.get('scheduler.leader_lease_ttl', lease_ttl_seconds))
        self.retry_count = config.get('scheduler.leader_retry_count', retry_count)
        self.retry_delay = config.get('scheduler.leader_retry_delay_ms', retry_delay_ms) / 1000.0
        self.instance_id = get_instance_id()
        self._heartbeat_threads: Dict[str, threading.Thread] = {}
        self._heartbeat_stop_events: Dict[str, threading.Event] = {}

        logger.info(f"Leader选举器初始化完成，instance_id={self.instance_id}")

    def try_acquire_leadership(self, job_key: str) -> bool:
        """
        尝试获取指定任务的Leader地位

        只有当租约过期或当前实例已是Leader时才能成功获取。
        使用乐观锁（version字段）确保并发安全。

        Args:
            job_key: 任务键（如 'prediction_job'）

        Returns:
            bool: 是否成功获取Leader地位
        """
        for attempt in range(self.retry_count):
            try:
                with get_db() as db:
                    if db is None:
                        logger.warning(f"数据库不可用，无法获取Leader锁: {job_key}")
                        return False

                    leader = db.query(SchedulerLeader).filter(
                        SchedulerLeader.leader_key == job_key
                    ).first()

                    if not leader:
                        logger.warning(f"Leader选举记录不存在，创建新记录: {job_key}")
                        leader = SchedulerLeader(
                            leader_key=job_key,
                            leader_id='',
                            lease_expire_time=datetime.now() - timedelta(hours=1),
                            version=0,
                        )
                        db.add(leader)
                        db.flush()

                    now = datetime.now()
                    current_version = leader.version

                    if leader.leader_id == self.instance_id:
                        logger.debug(f"当前实例已是 {job_key} 的Leader，续期中...")
                        leader.lease_expire_time = now + self.lease_ttl
                        leader.last_heartbeat = now
                        leader.version = current_version + 1
                        self._start_heartbeat(job_key)
                        return True

                    if leader.lease_expire_time <= now:
                        logger.info(
                            f"尝试获取 {job_key} Leader锁，当前Leader={leader.leader_id}，"
                            f"租约已过期，第{attempt + 1}次尝试"
                        )

                        from sqlalchemy import and_
                        updated = db.query(SchedulerLeader).filter(
                            and_(
                                SchedulerLeader.leader_key == job_key,
                                SchedulerLeader.version == current_version,
                            )
                        ).update({
                            'leader_id': self.instance_id,
                            'lease_expire_time': now + self.lease_ttl,
                            'last_heartbeat': now,
                            'version': current_version + 1,
                        })

                        if updated > 0:
                            logger.success(
                                f"成功获取 {job_key} Leader锁，"
                                f"instance_id={self.instance_id}"
                            )
                            self._start_heartbeat(job_key)
                            return True
                        else:
                            logger.debug(f"获取 {job_key} Leader锁失败，并发冲突，重试中...")
                    else:
                        logger.debug(
                            f"{job_key} Leader锁被 {leader.leader_id} 持有，"
                            f"租约过期时间: {leader.lease_expire_time}"
                        )
                        return False

            except Exception as e:
                logger.error(f"获取 {job_key} Leader锁异常: {e}")

            if attempt < self.retry_count - 1:
                time.sleep(self.retry_delay)

        logger.warning(f"获取 {job_key} Leader锁失败，已重试 {self.retry_count} 次")
        return False

    def renew_lease(self, job_key: str) -> bool:
        """
        续期Leader租约

        只有当前Leader才能成功续期。

        Args:
            job_key: 任务键

        Returns:
            bool: 是否续期成功
        """
        try:
            with get_db() as db:
                if db is None:
                    return False

                from sqlalchemy import and_

                now = datetime.now()
                leader = db.query(SchedulerLeader).filter(
                    SchedulerLeader.leader_key == job_key
                ).first()

                if not leader or leader.leader_id != self.instance_id:
                    logger.warning(f"无法续期 {job_key} 租约，不是当前Leader")
                    self._stop_heartbeat(job_key)
                    return False

                current_version = leader.version
                updated = db.query(SchedulerLeader).filter(
                    and_(
                        SchedulerLeader.leader_key == job_key,
                        SchedulerLeader.version == current_version,
                        SchedulerLeader.leader_id == self.instance_id,
                    )
                ).update({
                    'lease_expire_time': now + self.lease_ttl,
                    'last_heartbeat': now,
                    'version': current_version + 1,
                })

                if updated > 0:
                    logger.debug(f"{job_key} 租约续期成功")
                    return True
                else:
                    logger.warning(f"{job_key} 租约续期失败，可能已失去Leader地位")
                    self._stop_heartbeat(job_key)
                    return False

        except Exception as e:
            logger.error(f"续期 {job_key} 租约异常: {e}")
            return False

    def release_leadership(self, job_key: str) -> bool:
        """
        释放Leader地位

        Args:
            job_key: 任务键

        Returns:
            bool: 是否释放成功
        """
        self._stop_heartbeat(job_key)

        try:
            with get_db() as db:
                if db is None:
                    return False

                from sqlalchemy import and_

                leader = db.query(SchedulerLeader).filter(
                    SchedulerLeader.leader_key == job_key
                ).first()

                if not leader or leader.leader_id != self.instance_id:
                    logger.debug(f"无需释放 {job_key} Leader锁，不是当前Leader")
                    return True

                current_version = leader.version
                updated = db.query(SchedulerLeader).filter(
                    and_(
                        SchedulerLeader.leader_key == job_key,
                        SchedulerLeader.version == current_version,
                        SchedulerLeader.leader_id == self.instance_id,
                    )
                ).update({
                    'leader_id': '',
                    'lease_expire_time': datetime.now() - timedelta(hours=1),
                    'version': current_version + 1,
                })

                if updated > 0:
                    logger.info(f"已释放 {job_key} Leader锁")
                    return True
                else:
                    logger.warning(f"释放 {job_key} Leader锁失败，并发冲突")
                    return False

        except Exception as e:
            logger.error(f"释放 {job_key} Leader锁异常: {e}")
            return False

    def is_leader(self, job_key: str) -> bool:
        """
        检查当前实例是否为指定任务的Leader

        Args:
            job_key: 任务键

        Returns:
            bool: 是否为Leader
        """
        try:
            with get_db() as db:
                if db is None:
                    return False

                leader = db.query(SchedulerLeader).filter(
                    SchedulerLeader.leader_key == job_key
                ).first()

                if not leader:
                    return False

                return (
                    leader.leader_id == self.instance_id
                    and leader.lease_expire_time > datetime.now()
                )

        except Exception as e:
            logger.error(f"检查 {job_key} Leader状态异常: {e}")
            return False

    def get_leader_info(self, job_key: str) -> Optional[Dict[str, Any]]:
        """
        获取指定任务的Leader信息

        Args:
            job_key: 任务键

        Returns:
            Dict: Leader信息，包含leader_id, lease_expire_time等
        """
        try:
            with get_db() as db:
                if db is None:
                    return None

                leader = db.query(SchedulerLeader).filter(
                    SchedulerLeader.leader_key == job_key
                ).first()

                if not leader:
                    return None

                return {
                    'leader_key': leader.leader_key,
                    'leader_id': leader.leader_id,
                    'lease_expire_time': leader.lease_expire_time,
                    'last_heartbeat': leader.last_heartbeat,
                    'version': leader.version,
                    'is_expired': leader.lease_expire_time <= datetime.now(),
                    'is_current_instance': leader.leader_id == self.instance_id,
                }

        except Exception as e:
            logger.error(f"获取 {job_key} Leader信息异常: {e}")
            return None

    def _start_heartbeat(self, job_key: str) -> None:
        """
        启动后台心跳线程，自动续期租约

        Args:
            job_key: 任务键
        """
        self._stop_heartbeat(job_key)

        stop_event = threading.Event()
        self._heartbeat_stop_events[job_key] = stop_event

        heartbeat_interval = self.lease_ttl.total_seconds() / 3

        def heartbeat_worker():
            logger.debug(f"{job_key} 心跳线程启动，间隔={heartbeat_interval:.1f}s")
            while not stop_event.is_set():
                try:
                    if not self.renew_lease(job_key):
                        logger.warning(f"{job_key} 心跳续期失败，停止心跳")
                        break
                except Exception as e:
                    logger.error(f"{job_key} 心跳异常: {e}")
                stop_event.wait(heartbeat_interval)
            logger.debug(f"{job_key} 心跳线程已停止")

        thread = threading.Thread(target=heartbeat_worker, daemon=True)
        self._heartbeat_threads[job_key] = thread
        thread.start()

    def _stop_heartbeat(self, job_key: str) -> None:
        """
        停止指定任务的心跳线程

        Args:
            job_key: 任务键
        """
        if job_key in self._heartbeat_stop_events:
            self._heartbeat_stop_events[job_key].set()
            self._heartbeat_stop_events.pop(job_key, None)

        if job_key in self._heartbeat_threads:
            thread = self._heartbeat_threads.pop(job_key)
            if thread.is_alive():
                thread.join(timeout=2.0)

    def stop_all_heartbeats(self) -> None:
        """停止所有心跳线程"""
        for job_key in list(self._heartbeat_stop_events.keys()):
            self._stop_heartbeat(job_key)

    def shutdown(self) -> None:
        """关闭Leader选举器，释放所有资源"""
        self.stop_all_heartbeats()
        logger.info("Leader选举器已关闭")


_leader_election: Optional[LeaderElection] = None


def get_leader_election() -> LeaderElection:
    """
    获取Leader选举器单例

    Returns:
        LeaderElection: Leader选举器实例
    """
    global _leader_election
    if _leader_election is None:
        _leader_election = LeaderElection()
    return _leader_election


class LeadershipContext:
    """
    Leader地位上下文管理器

    使用with语法自动管理Leader地位的获取和释放。

    Example:
        with LeadershipContext('prediction_job') as leader:
            if leader.acquired:
                run_prediction_job()
            else:
                logger.info("未获取Leader锁，跳过任务")
    """

    def __init__(self, job_key: str, auto_start: bool = True):
        """
        初始化Leader上下文

        Args:
            job_key: 任务键
            auto_start: 是否自动尝试获取Leader地位
        """
        self.job_key = job_key
        self.auto_start = auto_start
        self.leader_election = get_leader_election()
        self.acquired: bool = False

    def __enter__(self) -> 'LeadershipContext':
        if self.auto_start:
            self.acquired = self.leader_election.try_acquire_leadership(self.job_key)
            if self.acquired:
                logger.info(f"已获取 {self.job_key} Leader锁")
            else:
                logger.info(f"未获取 {self.job_key} Leader锁，任务将跳过")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if self.acquired:
            self.leader_election.release_leadership(self.job_key)
            self.acquired = False
        return False


# 兼容性单例导出
leader_election = get_leader_election()
