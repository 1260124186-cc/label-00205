"""
任务分片模块

为预测任务提供按 bolt_id 范围的分片并行处理能力。

主要功能:
1. BoltIdPartitioner: bolt_id 分片器，按范围或数量进行分片
2. ShardedTaskExecutor: 分片任务执行器，支持多线程/多进程并行
3. ShardResult: 分片结果聚合器

分片策略:
- 按 bolt_id 字典序范围分片（适用于数值型或字符串型ID）
- 支持配置分片数量、最小分片大小
- 支持动态调整分片数量

使用示例:
    from app.schedulers.task_sharding import ShardedTaskExecutor, get_bolt_id_partitioner
    
    executor = ShardedTaskExecutor()
    bolt_ids = get_all_bolt_ids()
    results = executor.execute_sharded(
        task_name='prediction_job',
        items=bolt_ids,
        process_func=predict_bolt,
        num_shards=4
    )
"""

import json
import math
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import (
    Dict, List, Optional, Any, Callable, Tuple,
    Generic, TypeVar, Union
)
from dataclasses import dataclass, field
from collections import defaultdict
from loguru import logger

from app.utils.config import config
from app.schedulers.job_execution import (
    JobExecutionContext, JobExecutionService,
    job_execution_context, ErrorSummary
)

T = TypeVar('T')
R = TypeVar('R')


@dataclass
class ShardInfo:
    """
    分片信息

    Attributes:
        shard_index: 分片索引（从0开始）
        shard_total: 总分片数
        items: 本分片包含的项目列表
        item_min: 分片内最小项目（用于范围分片）
        item_max: 分片内最大项目（用于范围分片）
    """
    shard_index: int
    shard_total: int
    items: List[Any]
    item_min: Optional[Any] = None
    item_max: Optional[Any] = None

    def __post_init__(self):
        if self.items and self.item_min is None:
            self.item_min = min(self.items)
            self.item_max = max(self.items)

    def __len__(self) -> int:
        return len(self.items)


@dataclass
class ShardResult(Generic[R]):
    """
    分片执行结果

    Attributes:
        shard_index: 分片索引
        shard_total: 总分片数
        total_count: 总处理数
        success_count: 成功数
        failed_count: 失败数
        skipped_count: 跳过数
        results: 成功结果列表
        error_summary: 错误摘要
        item_min: 处理的最小项目
        item_max: 处理的最大项目
        duration_seconds: 执行时长（秒）
    """
    shard_index: int
    shard_total: int
    total_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    results: List[R] = field(default_factory=list)
    error_summary: ErrorSummary = field(default_factory=ErrorSummary)
    item_min: Optional[Any] = None
    item_max: Optional[Any] = None
    duration_seconds: float = 0.0

    def merge(self, other: 'ShardResult[R]') -> None:
        """
        合并另一个分片的结果

        Args:
            other: 另一个分片结果
        """
        self.total_count += other.total_count
        self.success_count += other.success_count
        self.failed_count += other.failed_count
        self.skipped_count += other.skipped_count
        self.results.extend(other.results)

        if other.error_summary:
            for err_type, count in other.error_summary.error_types.items():
                self.error_summary.error_types[err_type] += count
            self.error_summary.total_errors += other.error_summary.total_errors
            self.error_summary.failed_node_ids.extend(other.error_summary.failed_node_ids)

        if other.item_min is not None:
            if self.item_min is None or other.item_min < self.item_min:
                self.item_min = other.item_min
        if other.item_max is not None:
            if self.item_max is None or other.item_max > self.item_max:
                self.item_max = other.item_max

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'shard_index': self.shard_index,
            'shard_total': self.shard_total,
            'total_count': self.total_count,
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'skipped_count': self.skipped_count,
            'item_min': str(self.item_min) if self.item_min else None,
            'item_max': str(self.item_max) if self.item_max else None,
            'duration_seconds': self.duration_seconds,
            'error_summary': self.error_summary.to_dict() if not self.error_summary.is_empty() else None,
        }


class BoltIdPartitioner:
    """
    Bolt ID 分片器

    将 bolt_id 列表按范围或数量进行分片，支持:
    1. 按数量均分（默认）
    2. 按ID范围分片（适用于有序ID）
    3. 自定义分片键提取函数
    """

    def __init__(
        self,
        min_shard_size: int = 10,
        max_shards: int = 32,
        sort_before_partition: bool = True,
    ):
        """
        初始化分片器

        Args:
            min_shard_size: 最小分片大小，避免分片过小
            max_shards: 最大分片数
            sort_before_partition: 分片前是否排序（用于范围分片）
        """
        self.min_shard_size = config.get('scheduler.sharding.min_shard_size', min_shard_size)
        self.max_shards = config.get('scheduler.sharding.max_shards', max_shards)
        self.sort_before_partition = sort_before_partition

    def partition(
        self,
        items: List[T],
        num_shards: Optional[int] = None,
        key_extractor: Optional[Callable[[T], Any]] = None,
    ) -> List[ShardInfo]:
        """
        将项目列表分片

        Args:
            items: 待分片的项目列表
            num_shards: 期望的分片数，None则自动计算
            key_extractor: 从项目中提取分片键的函数，默认使用项目本身

        Returns:
            List[ShardInfo]: 分片信息列表
        """
        if not items:
            return []

        if key_extractor is None:
            key_extractor = lambda x: x

        total_items = len(items)

        if num_shards is None:
            num_shards = self._calculate_optimal_shards(total_items)

        num_shards = max(1, min(num_shards, self.max_shards))

        if self.sort_before_partition:
            items = sorted(items, key=key_extractor)

        avg_size = math.ceil(total_items / num_shards)
        avg_size = max(avg_size, self.min_shard_size)

        actual_shards = math.ceil(total_items / avg_size)

        shards = []
        for i in range(actual_shards):
            start_idx = i * avg_size
            end_idx = min(start_idx + avg_size, total_items)
            shard_items = items[start_idx:end_idx]

            if not shard_items:
                continue

            shard_keys = [key_extractor(item) for item in shard_items]
            shards.append(ShardInfo(
                shard_index=i,
                shard_total=actual_shards,
                items=shard_items,
                item_min=min(shard_keys),
                item_max=max(shard_keys),
            ))

        for i, shard in enumerate(shards):
            shard.shard_total = len(shards)
            shard.shard_index = i

        logger.info(
            f"分片完成: 总项目数={total_items}, 分片数={len(shards)}, "
            f"平均分片大小={avg_size}"
        )

        return shards

    def partition_by_range(
        self,
        items: List[T],
        range_boundaries: List[Any],
        key_extractor: Optional[Callable[[T], Any]] = None,
    ) -> List[ShardInfo]:
        """
        按指定的范围边界进行分片

        Args:
            items: 待分片的项目列表
            range_boundaries: 范围边界列表，如 [1000, 2000, 3000]
            key_extractor: 从项目中提取分片键的函数

        Returns:
            List[ShardInfo]: 分片信息列表
        """
        if key_extractor is None:
            key_extractor = lambda x: x

        boundaries = sorted(range_boundaries)
        shard_groups: Dict[int, List[T]] = defaultdict(list)

        for item in items:
            key = key_extractor(item)
            shard_idx = 0
            for i, boundary in enumerate(boundaries):
                if key <= boundary:
                    shard_idx = i
                    break
            else:
                shard_idx = len(boundaries)

            shard_groups[shard_idx].append(item)

        shards = []
        total_shards = len(boundaries) + 1

        for shard_idx in range(total_shards):
            shard_items = shard_groups.get(shard_idx, [])
            if shard_items:
                shard_keys = [key_extractor(item) for item in shard_items]
                shards.append(ShardInfo(
                    shard_index=shard_idx,
                    shard_total=total_shards,
                    items=shard_items,
                    item_min=min(shard_keys),
                    item_max=max(shard_keys),
                ))

        logger.info(
            f"按范围分片完成: 总项目数={len(items)}, 分片数={len(shards)}, "
            f"边界={boundaries}"
        )

        return shards

    def _calculate_optimal_shards(self, total_items: int) -> int:
        """
        根据项目总数计算最优分片数

        Args:
            total_items: 项目总数

        Returns:
            int: 最优分片数
        """
        if total_items <= self.min_shard_size:
            return 1

        optimal = math.ceil(total_items / self.min_shard_size)
        return min(optimal, self.max_shards)


class ShardedTaskExecutor:
    """
    分片任务执行器

    支持多线程并行执行分片任务，并自动记录任务执行日志。
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        job_service: Optional[JobExecutionService] = None,
        partitioner: Optional[BoltIdPartitioner] = None,
    ):
        """
        初始化分片任务执行器

        Args:
            max_workers: 最大工作线程数，None则使用默认值
            job_service: 任务执行服务实例
            partitioner: 分片器实例
        """
        self.max_workers = max_workers or config.get('scheduler.sharding.max_workers', 4)
        self.job_service = job_service or JobExecutionService()
        self.partitioner = partitioner or BoltIdPartitioner()
        self._thread_lock = threading.Lock()

    def execute_sharded(
        self,
        task_name: str,
        task_type: str,
        items: List[T],
        process_func: Callable[[T], R],
        num_shards: Optional[int] = None,
        trigger_type: str = 'scheduled',
        key_extractor: Optional[Callable[[T], Any]] = None,
        error_filter: Optional[Callable[[T, Exception], bool]] = None,
    ) -> ShardResult[R]:
        """
        执行分片任务

        Args:
            task_name: 任务名称
            task_type: 任务类型
            items: 待处理的项目列表
            process_func: 处理单个项目的函数
            num_shards: 分片数，None则自动计算
            trigger_type: 触发类型
            key_extractor: 分片键提取函数
            error_filter: 错误过滤函数，返回True表示此错误可忽略（记为跳过）

        Returns:
            ShardResult: 聚合后的执行结果
        """
        if not items:
            logger.info(f"任务 {task_name} 没有待处理项目，跳过")
            return ShardResult(shard_index=0, shard_total=1)

        shards = self.partitioner.partition(items, num_shards, key_extractor)

        if len(shards) == 1:
            return self._execute_single_shard(
                task_name=task_name,
                task_type=task_type,
                shard=shards[0],
                process_func=process_func,
                trigger_type=trigger_type,
                error_filter=error_filter,
            )

        return self._execute_parallel_shards(
            task_name=task_name,
            task_type=task_type,
            shards=shards,
            process_func=process_func,
            trigger_type=trigger_type,
            error_filter=error_filter,
        )

    def _execute_single_shard(
        self,
        task_name: str,
        task_type: str,
        shard: ShardInfo,
        process_func: Callable[[T], R],
        trigger_type: str,
        error_filter: Optional[Callable[[T, Exception], bool]],
    ) -> ShardResult[R]:
        """
        单线程执行单个分片任务

        Args:
            task_name: 任务名称
            task_type: 任务类型
            shard: 分片信息
            process_func: 处理函数
            trigger_type: 触发类型
            error_filter: 错误过滤函数

        Returns:
            ShardResult: 执行结果
        """
        with job_execution_context(
            job_name=task_name,
            job_type=task_type,
            trigger_type=trigger_type,
            service=self.job_service,
            shard_index=shard.shard_index,
            shard_total=shard.shard_total,
        ) as ctx:
            result = self._process_shard(
                shard=shard,
                process_func=process_func,
                ctx=ctx,
                error_filter=error_filter,
            )

            ctx.bolt_id_min = str(shard.item_min) if shard.item_min else None
            ctx.bolt_id_max = str(shard.item_max) if shard.item_max else None

            return result

    def _execute_parallel_shards(
        self,
        task_name: str,
        task_type: str,
        shards: List[ShardInfo],
        process_func: Callable[[T], R],
        trigger_type: str,
        error_filter: Optional[Callable[[T, Exception], bool]],
    ) -> ShardResult[R]:
        """
        多线程并行执行多个分片任务

        Args:
            task_name: 任务名称
            task_type: 任务类型
            shards: 分片列表
            process_func: 处理函数
            trigger_type: 触发类型
            error_filter: 错误过滤函数

        Returns:
            ShardResult: 聚合后的执行结果
        """
        aggregated_result = ShardResult(
            shard_index=-1,
            shard_total=len(shards),
        )

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures_to_shard: Dict[Future, Tuple[ShardInfo, int]] = {}

            for i, shard in enumerate(shards):
                future = executor.submit(
                    self._execute_shard_worker,
                    task_name=task_name,
                    task_type=task_type,
                    shard=shard,
                    process_func=process_func,
                    trigger_type=trigger_type,
                    error_filter=error_filter,
                )
                futures_to_shard[future] = (shard, i)

            for future in as_completed(futures_to_shard):
                shard, shard_idx = futures_to_shard[future]
                try:
                    shard_result = future.result()
                    aggregated_result.merge(shard_result)
                    logger.info(
                        f"分片 {shard_idx + 1}/{len(shards)} 执行完成: "
                        f"total={shard_result.total_count}, "
                        f"success={shard_result.success_count}, "
                        f"failed={shard_result.failed_count}"
                    )
                except Exception as e:
                    logger.error(f"分片 {shard_idx + 1}/{len(shards)} 执行异常: {e}")
                    with self._thread_lock:
                        aggregated_result.failed_count += len(shard)
                        aggregated_result.total_count += len(shard)

        logger.info(
            f"分片任务 {task_name} 全部完成: "
            f"total={aggregated_result.total_count}, "
            f"success={aggregated_result.success_count}, "
            f"failed={aggregated_result.failed_count}"
        )

        return aggregated_result

    def _execute_shard_worker(
        self,
        task_name: str,
        task_type: str,
        shard: ShardInfo,
        process_func: Callable[[T], R],
        trigger_type: str,
        error_filter: Optional[Callable[[T, Exception], bool]],
    ) -> ShardResult[R]:
        """
        分片工作线程函数

        Args:
            task_name: 任务名称
            task_type: 任务类型
            shard: 分片信息
            process_func: 处理函数
            trigger_type: 触发类型
            error_filter: 错误过滤函数

        Returns:
            ShardResult: 分片执行结果
        """
        from app.utils.db_pool import db_pool

        quota_name = "shard_task"
        quota = db_pool.get_quota(quota_name)
        quota_acquired = False

        if quota:
            quota_acquired = quota.acquire(timeout=30.0)
            if not quota_acquired:
                logger.warning(
                    f"分片 {shard.shard_index} 连接池配额获取超时 "
                    f"({quota.current}/{quota.max_connections}), 继续执行但可能影响连接池"
                )

        try:
            with job_execution_context(
                job_name=f"{task_name}_shard_{shard.shard_index}",
                job_type=task_type,
                trigger_type=trigger_type,
                service=self.job_service,
                shard_index=shard.shard_index,
                shard_total=shard.shard_total,
            ) as ctx:
                result = self._process_shard(
                    shard=shard,
                    process_func=process_func,
                    ctx=ctx,
                    error_filter=error_filter,
                )

                ctx.bolt_id_min = str(shard.item_min) if shard.item_min else None
                ctx.bolt_id_max = str(shard.item_max) if shard.item_max else None

                return result
        finally:
            if quota and quota_acquired:
                quota.release()

    def _process_shard(
        self,
        shard: ShardInfo,
        process_func: Callable[[T], R],
        ctx: JobExecutionContext,
        error_filter: Optional[Callable[[T, Exception], bool]],
    ) -> ShardResult[R]:
        """
        处理单个分片内的所有项目

        Args:
            shard: 分片信息
            process_func: 处理函数
            ctx: 任务执行上下文
            error_filter: 错误过滤函数

        Returns:
            ShardResult: 分片执行结果
        """
        import time
        start_time = time.time()

        result = ShardResult(
            shard_index=shard.shard_index,
            shard_total=shard.shard_total,
            item_min=shard.item_min,
            item_max=shard.item_max,
        )

        for item in shard.items:
            try:
                item_result = process_func(item)
                result.success_count += 1
                result.results.append(item_result)
                ctx.record_success(str(item))
            except Exception as e:
                if error_filter and error_filter(item, e):
                    result.skipped_count += 1
                    ctx.record_skipped(str(item), str(e))
                else:
                    result.failed_count += 1
                    ctx.record_failure(str(item), str(e), type(e).__name__)
                    result.error_summary.add_error(
                        str(item), type(e).__name__, str(e)
                    )
            finally:
                result.total_count += 1

        result.duration_seconds = time.time() - start_time

        return result


_partitioner: Optional[BoltIdPartitioner] = None
_executor: Optional[ShardedTaskExecutor] = None


def get_bolt_id_partitioner() -> BoltIdPartitioner:
    """
    获取 Bolt ID 分片器单例

    Returns:
        BoltIdPartitioner: 分片器实例
    """
    global _partitioner
    if _partitioner is None:
        _partitioner = BoltIdPartitioner()
    return _partitioner


def get_sharded_task_executor() -> ShardedTaskExecutor:
    """
    获取分片任务执行器单例

    Returns:
        ShardedTaskExecutor: 执行器实例
    """
    global _executor
    if _executor is None:
        _executor = ShardedTaskExecutor()
    return _executor
