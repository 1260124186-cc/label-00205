"""
断线缓存与续传模块

当网络或目标系统不可用时，将采集数据缓存到本地，
恢复后自动续传，确保数据不丢失。
"""

import os
import json
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from collections import deque
from loguru import logger

from app.gateway.models import DataPoint


class OfflineCache:
    """
    离线缓存管理器

    支持内存缓存和磁盘持久化缓存，
    在网络恢复后自动重传。
    """

    def __init__(
        self,
        cache_dir: str = "./data/gateway_cache",
        max_memory_size: int = 10000,
        max_disk_size: int = 100000,
        flush_interval: float = 5.0,
    ):
        """
        初始化离线缓存

        Args:
            cache_dir: 缓存目录
            max_memory_size: 内存缓存最大条数
            max_disk_size: 磁盘缓存最大条数
            flush_interval: 内存刷盘间隔（秒）
        """
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        self._max_memory_size = max_memory_size
        self._max_disk_size = max_disk_size
        self._flush_interval = flush_interval

        # 内存缓存
        self._memory_cache: deque = deque(maxlen=max_memory_size)
        self._lock = threading.Lock()

        # 磁盘缓存管理
        self._disk_cache_files: List[Path] = []
        self._disk_cache_count: int = 0
        self._current_cache_file: Optional[Path] = None
        self._current_cache_count: int = 0
        self._max_file_size: int = 1000  # 每个缓存文件最多条数

        # 续传状态
        self._is_replaying: bool = False
        self._replay_thread: Optional[threading.Thread] = None
        self._is_running: bool = False

        # 统计信息
        self._total_cached: int = 0
        self._total_replayed: int = 0
        self._total_dropped: int = 0
        self._cache_hit_count: int = 0

        # 续传回调
        self._replay_callback: Optional[Callable[[List[DataPoint]], bool]] = None

        self._load_disk_cache_index()
        logger.info(
            f"离线缓存管理器初始化完成，目录: {cache_dir}, "
            f"内存缓存: {max_memory_size}条, 磁盘缓存: {max_disk_size}条"
        )

    # ============ 缓存写入 ============

    def add_points(self, points: List[DataPoint]) -> int:
        """
        添加数据点到缓存

        Args:
            points: 数据点列表

        Returns:
            int: 成功缓存的数量
        """
        if not points:
            return 0

        count = 0
        with self._lock:
            for point in points:
                if len(self._memory_cache) >= self._max_memory_size:
                    self._flush_memory_to_disk()

                self._memory_cache.append(point)
                count += 1
                self._total_cached += 1

        if count > 0:
            logger.debug(f"缓存添加: {count} 条, 当前缓存: {self.size} 条")
        return count

    def add_point(self, point: DataPoint) -> bool:
        """
        添加单个数据点到缓存

        Args:
            point: 数据点

        Returns:
            bool
        """
        return self.add_points([point]) > 0

    # ============ 缓存读取 ============

    def get_points(self, count: int = 100) -> List[DataPoint]:
        """
        从缓存中获取数据点（不移除）

        Args:
            count: 获取数量

        Returns:
            数据点列表
        """
        with self._lock:
            points = []
            for i, point in enumerate(self._memory_cache):
                if i >= count:
                    break
                points.append(point)

            # 如果内存缓存不够，从磁盘加载
            remaining = count - len(points)
            if remaining > 0:
                disk_points = self._load_from_disk(remaining)
                points.extend(disk_points)

            return points

    def pop_points(self, count: int = 100) -> List[DataPoint]:
        """
        从缓存中取出并移除数据点

        Args:
            count: 取出数量

        Returns:
            数据点列表
        """
        with self._lock:
            points = []
            for _ in range(min(count, len(self._memory_cache))):
                points.append(self._memory_cache.popleft())

            # 如果内存缓存不够，从磁盘加载
            remaining = count - len(points)
            if remaining > 0:
                disk_points = self._pop_from_disk(remaining)
                points.extend(disk_points)

            self._total_replayed += len(points)
            return points

    # ============ 磁盘缓存 ============

    def _flush_memory_to_disk(self) -> None:
        """将内存缓存刷到磁盘"""
        if not self._memory_cache:
            return

        try:
            # 准备写入的数据
            points_to_write = list(self._memory_cache)
            self._memory_cache.clear()

            # 确保磁盘缓存不超过上限
            if self._disk_cache_count >= self._max_disk_size:
                drop_count = min(len(points_to_write), self._max_file_size)
                self._total_dropped += drop_count
                logger.warning(
                    f"磁盘缓存已满，丢弃 {drop_count} 条数据"
                )
                return

            # 写入当前缓存文件
            if (self._current_cache_file is None
                    or self._current_cache_count >= self._max_file_size):
                self._rotate_cache_file()

            if self._current_cache_file:
                data = [self._point_to_dict(p) for p in points_to_write]

                # 追加到文件
                with open(self._current_cache_file, 'a', encoding='utf-8') as f:
                    for item in data:
                        f.write(json.dumps(item, ensure_ascii=False) + '\n')

                self._current_cache_count += len(data)
                self._disk_cache_count += len(data)
                self._cache_hit_count += len(data)

                logger.debug(
                    f"内存缓存刷盘: {len(data)} 条, "
                    f"当前磁盘缓存: {self._disk_cache_count} 条"
                )

        except Exception as e:
            logger.error(f"内存缓存刷盘失败: {e}")

    def _rotate_cache_file(self) -> None:
        """轮换缓存文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"cache_{timestamp}.jsonl"
        self._current_cache_file = self._cache_dir / filename
        self._current_cache_count = 0
        self._disk_cache_files.append(self._current_cache_file)
        logger.debug(f"创建新的缓存文件: {filename}")

    def _load_disk_cache_index(self) -> None:
        """加载磁盘缓存索引"""
        try:
            cache_files = sorted(
                self._cache_dir.glob("cache_*.jsonl"),
                key=lambda p: p.name,
            )

            self._disk_cache_files = cache_files
            self._disk_cache_count = 0

            # 统计总条数（粗略统计，按行数）
            for f in cache_files:
                try:
                    with open(f, 'r', encoding='utf-8') as fp:
                        line_count = sum(1 for _ in fp)
                        self._disk_cache_count += line_count
                except Exception:
                    pass

            # 设置当前文件
            if cache_files:
                self._current_cache_file = cache_files[-1]
                try:
                    with open(self._current_cache_file, 'r', encoding='utf-8') as fp:
                        self._current_cache_count = sum(1 for _ in fp)
                except Exception:
                    self._current_cache_count = 0

            logger.info(
                f"加载磁盘缓存索引: {len(cache_files)} 个文件, "
                f"共 {self._disk_cache_count} 条数据"
            )

        except Exception as e:
            logger.error(f"加载磁盘缓存索引失败: {e}")

    def _load_from_disk(self, count: int) -> List[DataPoint]:
        """从磁盘加载数据（只读，不删除）"""
        points = []
        if not self._disk_cache_files:
            return points

        try:
            # 从最旧的文件开始读取
            for cache_file in self._disk_cache_files:
                if len(points) >= count:
                    break

                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if len(points) >= count:
                                break
                            line = line.strip()
                            if line:
                                try:
                                    data = json.loads(line)
                                    point = self._dict_to_point(data)
                                    points.append(point)
                                except (json.JSONDecodeError, KeyError):
                                    continue
                except Exception as e:
                    logger.warning(f"读取缓存文件失败 {cache_file}: {e}")
                    continue

        except Exception as e:
            logger.error(f"从磁盘加载缓存失败: {e}")

        return points

    def _pop_from_disk(self, count: int) -> List[DataPoint]:
        """从磁盘取出并删除数据"""
        points = []
        if not self._disk_cache_files:
            return points

        try:
            remaining = count

            while remaining > 0 and self._disk_cache_files:
                cache_file = self._disk_cache_files[0]
                file_points = []

                try:
                    # 读取文件所有内容
                    all_lines = []
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        all_lines = f.readlines()

                    # 解析前 N 条
                    lines_to_remove = 0
                    for line in all_lines:
                        if len(file_points) >= remaining:
                            break
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                point = self._dict_to_point(data)
                                file_points.append(point)
                                lines_to_remove += 1
                            except (json.JSONDecodeError, KeyError):
                                lines_to_remove += 1
                                continue

                    points.extend(file_points)
                    remaining -= len(file_points)

                    # 更新文件
                    if lines_to_remove >= len(all_lines):
                        # 文件已空，删除
                        cache_file.unlink()
                        self._disk_cache_files.pop(0)
                        self._disk_cache_count -= len(all_lines)
                    else:
                        # 重写文件
                        remaining_lines = all_lines[lines_to_remove:]
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            f.writelines(remaining_lines)
                        self._disk_cache_count -= lines_to_remove

                except Exception as e:
                    logger.warning(f"处理缓存文件失败 {cache_file}: {e}")
                    if cache_file.exists():
                        try:
                            cache_file.unlink()
                        except Exception:
                            pass
                    self._disk_cache_files.pop(0)
                    continue

        except Exception as e:
            logger.error(f"从磁盘取出缓存失败: {e}")

        return points

    # ============ 自动续传 ============

    def start_auto_replay(
        self,
        callback: Callable[[List[DataPoint]], bool],
        replay_interval: float = 10.0,
        batch_size: int = 100,
    ) -> None:
        """
        启动自动续传

        Args:
            callback: 续传回调函数，返回 True 表示成功
            replay_interval: 续传间隔（秒）
            batch_size: 每批续传数量
        """
        if self._is_running:
            logger.warning("自动续传已在运行")
            return

        self._replay_callback = callback
        self._replay_interval = replay_interval
        self._replay_batch_size = batch_size
        self._is_running = True

        self._replay_thread = threading.Thread(
            target=self._replay_loop,
            daemon=True,
            name="gateway-cache-replay",
        )
        self._replay_thread.start()

        logger.info("自动续传已启动")

    def stop_auto_replay(self) -> None:
        """停止自动续传"""
        self._is_running = False
        if self._replay_thread:
            self._replay_thread.join(timeout=5.0)
            self._replay_thread = None
        logger.info("自动续传已停止")

    def _replay_loop(self) -> None:
        """续传循环"""
        while self._is_running:
            try:
                if self.size > 0 and self._replay_callback:
                    self._is_replaying = True
                    logger.info(f"开始续传，缓存大小: {self.size} 条")

                    while self.size > 0 and self._is_running:
                        batch = self.pop_points(self._replay_batch_size)
                        if not batch:
                            break

                        success = self._replay_callback(batch)
                        if not success:
                            # 续传失败，将数据重新放回缓存头部
                            with self._lock:
                                for point in reversed(batch):
                                    self._memory_cache.appendleft(point)
                            logger.warning("续传失败，数据已放回缓存")
                            break

                        logger.debug(f"续传成功: {len(batch)} 条")

                    self._is_replaying = False
                    if self.size == 0:
                        logger.info("续传完成，缓存已清空")

                time.sleep(self._replay_interval)

            except Exception as e:
                logger.error(f"续传循环异常: {e}")
                self._is_replaying = False
                time.sleep(self._replay_interval)

    def trigger_replay(self) -> bool:
        """
        触发一次续传

        Returns:
            bool: 是否成功触发
        """
        if self.size == 0:
            return False

        if self._is_replaying:
            logger.warning("续传正在进行中")
            return False

        # 在单独线程中执行续传
        replay_thread = threading.Thread(
            target=self._do_replay,
            daemon=True,
        )
        replay_thread.start()
        return True

    def _do_replay(self) -> None:
        """执行一次续传"""
        if self._replay_callback is None:
            return

        try:
            self._is_replaying = True
            batch = self.pop_points(self._replay_batch_size)
            if batch:
                success = self._replay_callback(batch)
                if not success:
                    with self._lock:
                        for point in reversed(batch):
                            self._memory_cache.appendleft(point)
                    logger.warning("手动续传失败，数据已放回")
                else:
                    logger.info(f"手动续传成功: {len(batch)} 条")
        finally:
            self._is_replaying = False

    # ============ 数据转换 ============

    def _point_to_dict(self, point: DataPoint) -> Dict[str, Any]:
        """数据点转字典"""
        return {
            'device_id': point.device_id,
            'point_id': point.point_id,
            'sensor_id': point.sensor_id,
            'value': point.value,
            'raw_value': point.raw_value,
            'timestamp': point.timestamp.isoformat(),
            'quality': point.quality,
            'unit': point.unit,
        }

    def _dict_to_point(self, data: Dict[str, Any]) -> DataPoint:
        """字典转数据点"""
        return DataPoint(
            device_id=data.get('device_id', ''),
            point_id=data.get('point_id', ''),
            sensor_id=str(data.get('sensor_id', '')),
            value=float(data.get('value', 0)),
            raw_value=data.get('raw_value'),
            timestamp=datetime.fromisoformat(data['timestamp'])
            if isinstance(data.get('timestamp'), str)
            else datetime.now(),
            quality=data.get('quality', 'good'),
            unit=data.get('unit', ''),
        )

    # ============ 缓存管理 ============

    def flush(self) -> None:
        """强制将内存缓存刷到磁盘"""
        with self._lock:
            self._flush_memory_to_disk()

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._memory_cache.clear()

            # 删除所有磁盘缓存文件
            for f in self._disk_cache_files:
                try:
                    f.unlink()
                except Exception:
                    pass

            self._disk_cache_files.clear()
            self._disk_cache_count = 0
            self._current_cache_file = None
            self._current_cache_count = 0

        logger.info("缓存已清空")

    @property
    def size(self) -> int:
        """当前缓存总条数"""
        with self._lock:
            return len(self._memory_cache) + self._disk_cache_count

    @property
    def memory_size(self) -> int:
        """内存缓存条数"""
        return len(self._memory_cache)

    @property
    def disk_size(self) -> int:
        """磁盘缓存条数"""
        return self._disk_cache_count

    @property
    def is_replaying(self) -> bool:
        """是否正在续传"""
        return self._is_replaying

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计字典
        """
        with self._lock:
            return {
                'is_running': self._is_running,
                'is_replaying': self._is_replaying,
                'total_size': self.size,
                'memory_size': len(self._memory_cache),
                'disk_size': self._disk_cache_count,
                'disk_files': len(self._disk_cache_files),
                'total_cached': self._total_cached,
                'total_replayed': self._total_replayed,
                'total_dropped': self._total_dropped,
                'max_memory_size': self._max_memory_size,
                'max_disk_size': self._max_disk_size,
            }

    def set_max_sizes(self, max_memory: int, max_disk: int) -> None:
        """
        设置缓存大小上限

        Args:
            max_memory: 内存缓存最大条数
            max_disk: 磁盘缓存最大条数
        """
        self._max_memory_size = max_memory
        self._max_disk_size = max_disk
        logger.info(f"缓存大小上限已更新: 内存={max_memory}, 磁盘={max_disk}")
