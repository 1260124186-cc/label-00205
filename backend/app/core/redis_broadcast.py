"""
Redis 配置同步广播模块

支持多实例部署时通过 Redis Pub/Sub 广播配置版本号，
各实例收到版本号后自动触发配置重载。

使用示例:
    from app.core.redis_broadcast import config_sync

    # 启动监听（后台线程）
    config_sync.start()

    # 广播新版本号
    config_sync.broadcast_version(version=42, changes=["logging.level"])

    # 注册版本变更回调
    def on_version_change(version, changed_paths):
        print(f"配置版本变更: v{version}, 变更项: {changed_paths}")

    config_sync.register_callback(on_version_change)
"""

import threading
import time
import json
import hashlib
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass
from loguru import logger

from app.core.event_bus import event_bus, EventType
from app.utils.config import config


REDIS_CHANNEL_CONFIG_SYNC = "bolt_prediction:config_sync"
REDIS_KEY_CONFIG_VERSION = "bolt_prediction:config_version"
REDIS_KEY_CONFIG_CHECKSUM = "bolt_prediction:config_checksum"
REDIS_KEY_CONFIG_LOCK = "bolt_prediction:config_lock"


@dataclass
class ConfigSyncMessage:
    """
    配置同步消息结构

    Attributes:
        version: 配置版本号
        checksum: 配置内容校验和（MD5）
        changed_paths: 变更的配置路径列表
        operator: 操作者
        timestamp: 变更时间戳
        source_instance: 来源实例ID
        message_type: 消息类型 (version_announce / reload_request / ack)
    """
    version: int
    checksum: str
    changed_paths: List[str]
    operator: str
    timestamp: float
    source_instance: str
    message_type: str = "version_announce"


class RedisConfigSync:
    """
    Redis 配置同步管理器

    核心功能:
    - 通过 Redis Pub/Sub 广播配置版本号
    - 维护全局配置版本号和校验和
    - 接收版本通知后触发本地配置重载
    - 支持分布式锁避免冲突更新
    """

    def __init__(self):
        self._redis_client: Optional[Any] = None
        self._pubsub: Optional[Any] = None
        self._listener_thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[int, List[str]], None]] = []
        self._lock = threading.RLock()
        self._running = False
        self._current_version: int = 0
        self._current_checksum: str = ""
        self._reconnect_interval: int = 5
        self._instance_id: str = event_bus.instance_id
        self._enabled: bool = False
        self._heartbeat_interval: int = 30
        self._heartbeat_thread: Optional[threading.Thread] = None

        self._init_from_config()

    def _init_from_config(self) -> None:
        """从配置文件初始化"""
        redis_cfg = config.get('stream_prediction.window', {})
        redis_url = redis_cfg.get('redis_url', '')
        self._enabled = bool(redis_url and redis_cfg.get('storage_type') == 'redis')
        if self._enabled:
            logger.info("Redis配置同步已启用（检测到Redis配置）")
        else:
            logger.info("Redis配置同步未启用（单实例模式），将仅使用内存事件总线")

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def current_version(self) -> int:
        return self._current_version

    @property
    def instance_id(self) -> str:
        return self._instance_id

    def _get_redis_client(self) -> Optional[Any]:
        """懒加载Redis客户端"""
        if self._redis_client is not None:
            return self._redis_client

        if not self._enabled:
            return None

        try:
            import redis
            redis_cfg = config.get('stream_prediction.window', {})
            redis_url = redis_cfg.get('redis_url', 'redis://localhost:6379/0')

            self._redis_client = redis.Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            self._redis_client.ping()
            logger.info(f"Redis连接成功: {redis_url}")
            return self._redis_client

        except ImportError:
            logger.warning("redis 库未安装，Redis配置同步不可用。请执行: pip install redis")
            self._enabled = False
            return None
        except Exception as e:
            logger.warning(f"Redis连接失败，配置同步不可用: {e}")
            self._enabled = False
            return None

    def start(self) -> bool:
        """
        启动Redis配置同步监听

        Returns:
            是否成功启动
        """
        if not self._enabled:
            logger.info("Redis配置同步未启用，跳过启动")
            return False

        if self._running:
            logger.warning("Redis配置同步已在运行中")
            return True

        redis_client = self._get_redis_client()
        if redis_client is None:
            return False

        try:
            self._running = True

            self._pubsub = redis_client.pubsub()
            self._pubsub.subscribe(**{REDIS_CHANNEL_CONFIG_SYNC: self._on_message})

            self._listener_thread = threading.Thread(
                target=self._listen_loop,
                daemon=True,
                name="redis-config-sync-listener",
            )
            self._listener_thread.start()

            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                daemon=True,
                name="redis-config-sync-heartbeat",
            )
            self._heartbeat_thread.start()

            self._sync_initial_version()

            logger.info("Redis配置同步监听已启动")
            return True

        except Exception as e:
            logger.error(f"启动Redis配置同步失败: {e}")
            self._running = False
            return False

    def stop(self) -> None:
        """停止Redis配置同步"""
        self._running = False

        if self._pubsub:
            try:
                self._pubsub.unsubscribe()
                self._pubsub.close()
            except Exception:
                pass
            self._pubsub = None

        if self._listener_thread:
            self._listener_thread.join(timeout=5)
            self._listener_thread = None

        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)
            self._heartbeat_thread = None

        logger.info("Redis配置同步已停止")

    def _listen_loop(self) -> None:
        """消息监听循环"""
        while self._running:
            try:
                if self._pubsub is None:
                    time.sleep(self._reconnect_interval)
                    self._reconnect()
                    continue

                message = self._pubsub.get_message(timeout=1.0)
                if message and message.get("type") == "message":
                    self._handle_message(message.get("data"))

            except Exception as e:
                logger.warning(f"Redis监听异常: {e}，{self._reconnect_interval}秒后尝试重连")
                time.sleep(self._reconnect_interval)
                self._reconnect()

    def _heartbeat_loop(self) -> None:
        """心跳循环，定期同步版本号"""
        while self._running:
            try:
                self._sync_initial_version()
                time.sleep(self._heartbeat_interval)
            except Exception as e:
                logger.warning(f"Redis心跳异常: {e}")
                time.sleep(self._heartbeat_interval)

    def _reconnect(self) -> None:
        """重连Redis"""
        try:
            if self._pubsub:
                try:
                    self._pubsub.close()
                except Exception:
                    pass
                self._pubsub = None
            self._redis_client = None

            redis_client = self._get_redis_client()
            if redis_client:
                self._pubsub = redis_client.pubsub()
                self._pubsub.subscribe(**{REDIS_CHANNEL_CONFIG_SYNC: self._on_message})
                logger.info("Redis配置同步重连成功")
        except Exception as e:
            logger.warning(f"Redis重连失败: {e}")

    def _sync_initial_version(self) -> None:
        """同步初始版本号"""
        redis_client = self._get_redis_client()
        if redis_client is None:
            return

        try:
            version_str = redis_client.get(REDIS_KEY_CONFIG_VERSION)
            checksum = redis_client.get(REDIS_KEY_CONFIG_CHECKSUM) or ""

            if version_str:
                remote_version = int(version_str)
                if self._current_version == 0:
                    self._current_version = remote_version
                    self._current_checksum = checksum
                    logger.info(f"初始同步配置版本: v{remote_version}")
                elif remote_version > self._current_version:
                    logger.info(
                        f"检测到配置版本落后: local=v{self._current_version}, "
                        f"remote=v{remote_version}，触发重载"
                    )
                    self._trigger_reload(remote_version, [], source="heartbeat")
        except Exception as e:
            logger.warning(f"同步初始版本号失败: {e}")

    def _on_message(self, message: Dict[str, Any]) -> None:
        """Redis消息回调"""
        raw_data = message.get("data")
        if isinstance(raw_data, (bytes, bytearray)):
            raw_data = raw_data.decode("utf-8")
        self._handle_message(raw_data)

    def _handle_message(self, raw_data: str) -> None:
        """处理收到的消息"""
        try:
            data = json.loads(raw_data)
            msg = ConfigSyncMessage(**data)
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"解析配置同步消息失败: {e}, data={raw_data[:100]}")
            return

        if msg.source_instance == self._instance_id:
            logger.debug(f"跳过自身发出的配置同步消息: v{msg.version}")
            return

        logger.info(
            f"收到配置同步消息: type={msg.message_type}, "
            f"version=v{msg.version}, from={msg.source_instance[:16]}"
        )

        if msg.message_type == "version_announce":
            if msg.version > self._current_version:
                self._trigger_reload(
                    msg.version,
                    msg.changed_paths,
                    source=f"redis:{msg.source_instance[:16]}",
                )
            elif msg.version < self._current_version:
                logger.warning(
                    f"收到旧版本消息: local=v{self._current_version}, "
                    f"remote=v{msg.version}，可能存在时钟问题"
                )

    def _trigger_reload(
        self,
        version: int,
        changed_paths: List[str],
        source: str = "redis",
    ) -> None:
        """
        触发本地配置重载（跨实例 Redis 广播同步闭环）。

        完整执行链路:
          1. 调用 ConfigManager.reload_from_disk() 从磁盘加载最新 config.yaml
             （A 实例已经写入文件，B 实例通过共享存储/NFS 拿到新版本）
          2. 调用 ConfigManager.dispatch_events_from_paths() 按路径分类派发
             细分事件（LOG / SCHEDULER / STREAM / STRATEGY / CONFIG_CHANGED），
             让已订阅这些事件的 scheduler / stream_engine / loguru 等服务
             自动执行 reload_config() 完成热更新
          3. 兼容旧回调接口：_callbacks 列表逐个调用
          4. 额外派发 REDIS_CONFIG_SYNC 通用事件供其他模块监听
        """
        self._current_version = version

        # 懒加载避免循环依赖
        try:
            from app.core.config_manager import config_manager
        except Exception as e:
            logger.exception(f"导入 ConfigManager 失败，无法触发热更新闭环: {e}")
            return

        # Step 1: 从磁盘重新加载配置 + 版本元数据
        try:
            disk_changed = config_manager.reload_from_disk(target_version=version)
            logger.info(
                f"[redis-sync] 磁盘重载完成: version=v{version}, "
                f"disk_changed={disk_changed}, paths={changed_paths}"
            )
        except Exception as e:
            logger.exception(f"从磁盘重载配置失败: {e}")
            # 即使 reload 失败也尝试派发事件，让服务按现有内存配置处理
            disk_changed = False

        # Step 2: 按 changed_paths 分类派发细分事件，触发各服务 reload_config()
        # 注意：即使 disk_changed=False（共享存储延迟）也仍然派发事件，
        # 因为服务的 reload_config() 本身是从 config_manager 读取最新值，
        # 下次心跳重试时会再次触发。
        try:
            config_manager.dispatch_events_from_paths(
                changed_paths=changed_paths,
                version=version,
                operator=f"redis-sync:{source}",
                description=f"跨实例Redis配置同步 (source={source})",
                source=source,
            )
        except Exception as e:
            logger.exception(f"派发细分热更新事件失败: {e}")

        # Step 3: 派发 REDIS_CONFIG_SYNC 通用事件，供需要区分来源的模块使用
        event_bus.publish(
            EventType.REDIS_CONFIG_SYNC,
            data={
                "version": version,
                "changed_paths": changed_paths,
                "source": source,
                "disk_changed": disk_changed,
            },
            asynchronous=True,
        )

        # Step 4: 兼容旧回调接口
        for callback in self._callbacks:
            try:
                callback(version, changed_paths)
            except Exception as e:
                logger.exception(f"配置版本回调执行异常: {e}")

        logger.info(
            f"跨实例配置热更新闭环完成: v{version}, "
            f"paths={len(changed_paths)}, disk_changed={disk_changed}"
        )

    def broadcast_version(
        self,
        version: int,
        changed_paths: List[str],
        operator: str = "system",
        config_dict: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        广播配置版本号到所有实例

        Args:
            version: 新版本号
            changed_paths: 变更的配置路径列表
            operator: 操作者
            config_dict: 配置内容字典（用于计算校验和）

        Returns:
            是否广播成功
        """
        if not self._enabled:
            logger.debug("Redis未启用，跳过版本广播（仅使用内存事件总线）")
            return True

        redis_client = self._get_redis_client()
        if redis_client is None:
            return False

        try:
            checksum = self._calculate_checksum(config_dict) if config_dict else self._current_checksum

            msg = ConfigSyncMessage(
                version=version,
                checksum=checksum,
                changed_paths=changed_paths,
                operator=operator,
                timestamp=time.time(),
                source_instance=self._instance_id,
                message_type="version_announce",
            )

            pipeline = redis_client.pipeline()
            pipeline.set(REDIS_KEY_CONFIG_VERSION, str(version))
            if checksum:
                pipeline.set(REDIS_KEY_CONFIG_CHECKSUM, checksum)
            pipeline.publish(REDIS_CHANNEL_CONFIG_SYNC, json.dumps(msg.__dict__, ensure_ascii=False))
            pipeline.execute()

            self._current_version = version
            self._current_checksum = checksum

            logger.info(
                f"配置版本已广播: v{version}, "
                f"changes={len(changed_paths)}, checksum={checksum[:8]}..."
            )
            return True

        except Exception as e:
            logger.error(f"广播配置版本失败: {e}")
            return False

    def acquire_update_lock(self, timeout_seconds: int = 10) -> bool:
        """
        获取配置更新分布式锁（避免并发更新冲突）

        Args:
            timeout_seconds: 锁超时时间

        Returns:
            是否获取成功
        """
        if not self._enabled:
            return True

        redis_client = self._get_redis_client()
        if redis_client is None:
            return True

        try:
            result = redis_client.set(
                REDIS_KEY_CONFIG_LOCK,
                self._instance_id,
                ex=timeout_seconds,
                nx=True,
            )
            return bool(result)
        except Exception as e:
            logger.warning(f"获取配置锁失败: {e}")
            return True

    def release_update_lock(self) -> None:
        """释放配置更新分布式锁"""
        if not self._enabled:
            return

        redis_client = self._get_redis_client()
        if redis_client is None:
            return

        try:
            lock_holder = redis_client.get(REDIS_KEY_CONFIG_LOCK)
            if lock_holder == self._instance_id:
                redis_client.delete(REDIS_KEY_CONFIG_LOCK)
        except Exception as e:
            logger.warning(f"释放配置锁失败: {e}")

    def register_callback(
        self,
        callback: Callable[[int, List[str]], None],
    ) -> None:
        """
        注册版本变更回调

        Args:
            callback: 回调函数 (version, changed_paths) -> None
        """
        with self._lock:
            self._callbacks.append(callback)

    def unregister_callback(
        self,
        callback: Callable[[int, List[str]], None],
    ) -> bool:
        """取消注册回调"""
        with self._lock:
            try:
                self._callbacks.remove(callback)
                return True
            except ValueError:
                return False

    @staticmethod
    def _calculate_checksum(config_dict: Dict[str, Any]) -> str:
        """计算配置内容的MD5校验和"""
        try:
            content = json.dumps(config_dict, sort_keys=True, ensure_ascii=False, default=str)
            return hashlib.md5(content.encode("utf-8")).hexdigest()
        except Exception:
            return ""


# 全局配置同步实例
config_sync = RedisConfigSync()
