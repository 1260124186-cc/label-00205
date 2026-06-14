"""
任务分片模块

实现预测任务的分片机制，按 bolt_id 范围将大任务拆分为多个分片，支持并行处理。

主要功能:
1. 按 bolt_id 数值范围进行分片
2. 支持自动计算分片数量
3. 支持手动指定分片参数
4. 分片状态跟踪

使用示例:
    from app.schedulers.job_sharding import JobSharding
    
    sharding = JobSharding()
    shards = sharding.create_shards(
        bolt_ids=['1001', '1002', '1003', ...],
        shard_count=4
    )
    for shard in shards:
        process_shard(shard)
"""

import math
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger

from app.utils.config import config


@dataclass
class ShardInfo:
    """
    分片信息

    Attributes:
        shard_index: 分片索引（从0开始）
        shard_total: 总分片数
        bolt_id_min: 分片最小bolt_id（数值）
        bolt_id_max: 分片最大bolt_id（数值）
        bolt_ids: 该分片包含的bolt_id列表
        bolt_count: 该分片的bolt数量
    """
    shard_index: int
    shard_total: int
    bolt_id_min: Optional[int]
    bolt_id_max: Optional[int]
    bolt_ids: List[str]
    bolt_count: int

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'shard_index': self.shard_index,
            'shard_total': self.shard_total,
            'bolt_id_min': self.bolt_id_min,
            'bolt_id_max': self.bolt_id_max,
            'bolt_ids': self.bolt_ids,
            'bolt_count': self.bolt_count,
        }


class JobSharding:
    """
    任务分片类

    负责将大量bolt_id拆分为多个分片，支持并行处理。
    分片策略：按bolt_id的数值范围均匀划分。
    """

    def __init__(self):
        """初始化任务分片器"""
        sharding_config = config.get('scheduler.sharding', {})
        self.default_shard_count = sharding_config.get('default_shard_count', 4)
        self.max_shard_count = sharding_config.get('max_shard_count', 16)
        self.min_bolts_per_shard = sharding_config.get('min_bolts_per_shard', 10)
        logger.info(f"任务分片器初始化完成，默认分片数: {self.default_shard_count}")

    def _parse_bolt_id(self, bolt_id: str) -> Optional[int]:
        """
        尝试将bolt_id解析为整数

        Args:
            bolt_id: bolt_id字符串

        Returns:
            Optional[int]: 解析后的整数，如果解析失败返回None
        """
        try:
            return int(bolt_id)
        except (ValueError, TypeError):
            return None

    def create_shards(
        self,
        bolt_ids: List[str],
        shard_count: Optional[int] = None,
        min_bolts_per_shard: Optional[int] = None
    ) -> List[ShardInfo]:
        """
        创建分片

        Args:
            bolt_ids: 需要分片的bolt_id列表
            shard_count: 分片数量，默认使用配置值
            min_bolts_per_shard: 每个分片最少的bolt数量，默认使用配置值

        Returns:
            List[ShardInfo]: 分片列表
        """
        if not bolt_ids:
            logger.warning("bolt_id列表为空，无法分片")
            return []

        shard_count = shard_count or self.default_shard_count
        min_bolts_per_shard = min_bolts_per_shard or self.min_bolts_per_shard

        total_bolts = len(bolt_ids)

        max_possible_shards = max(1, total_bolts // min_bolts_per_shard)
        shard_count = min(shard_count, max_possible_shards, self.max_shard_count)
        shard_count = max(1, shard_count)

        logger.info(
            f"开始创建分片: 总bolt数={total_bolts}, "
            f"分片数={shard_count}, 最少每片bolt数={min_bolts_per_shard}"
        )

        numeric_ids = []
        non_numeric_ids = []
        for bid in bolt_ids:
            nid = self._parse_bolt_id(bid)
            if nid is not None:
                numeric_ids.append((nid, bid))
            else:
                non_numeric_ids.append(bid)

        numeric_ids.sort(key=lambda x: x[0])

        shards = []
        if numeric_ids:
            base_size = len(numeric_ids) // shard_count
            remainder = len(numeric_ids) % shard_count

            current_idx = 0
            for i in range(shard_count):
                shard_size = base_size + (1 if i < remainder else 0)
                if shard_size == 0:
                    continue

                shard_numeric = numeric_ids[current_idx:current_idx + shard_size]
                shard_bolt_ids = [bid for _, bid in shard_numeric]
                shard_min = shard_numeric[0][0]
                shard_max = shard_numeric[-1][0]

                shards.append(ShardInfo(
                    shard_index=i,
                    shard_total=shard_count,
                    bolt_id_min=shard_min,
                    bolt_id_max=shard_max,
                    bolt_ids=shard_bolt_ids,
                    bolt_count=len(shard_bolt_ids)
                ))

                current_idx += shard_size

        if non_numeric_ids:
            shards.append(ShardInfo(
                shard_index=len(shards),
                shard_total=len(shards) + 1,
                bolt_id_min=None,
                bolt_id_max=None,
                bolt_ids=non_numeric_ids,
                bolt_count=len(non_numeric_ids)
            ))
            for shard in shards:
                shard.shard_total = len(shards)

        logger.info(f"分片创建完成: 共{len(shards)}个分片")
        for shard in shards:
            logger.debug(
                f"分片[{shard.shard_index}]: "
                f"bolt数={shard.bolt_count}, "
                f"范围=[{shard.bolt_id_min}, {shard.bolt_id_max}]"
            )

        return shards

    def get_shard_for_bolt(
        self,
        bolt_id: str,
        shard_count: int,
        all_bolt_ids: Optional[List[str]] = None
    ) -> Optional[int]:
        """
        计算某个bolt_id属于哪个分片

        Args:
            bolt_id: 要查询的bolt_id
            shard_count: 分片总数
            all_bolt_ids: 所有bolt_id列表（用于计算分片边界）

        Returns:
            Optional[int]: 分片索引，如果无法确定返回None
        """
        nid = self._parse_bolt_id(bolt_id)
        if nid is None:
            return None

        if all_bolt_ids is None:
            logger.warning("需要提供所有bolt_id列表才能计算分片归属")
            return None

        numeric_ids = [self._parse_bolt_id(bid) for bid in all_bolt_ids]
        numeric_ids = [nid for nid in numeric_ids if nid is not None]
        if not numeric_ids:
            return None

        min_id = min(numeric_ids)
        max_id = max(numeric_ids)
        range_size = max_id - min_id + 1

        if range_size <= 0:
            return 0

        shard_size = math.ceil(range_size / shard_count)
        shard_index = (nid - min_id) // shard_size
        return max(0, min(shard_index, shard_count - 1))

    def get_shard_range(
        self,
        shard_index: int,
        shard_count: int,
        all_bolt_ids: List[str]
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        获取指定分片的bolt_id数值范围

        Args:
            shard_index: 分片索引
            shard_count: 分片总数
            all_bolt_ids: 所有bolt_id列表

        Returns:
            Tuple[Optional[int], Optional[int]]: (min_id, max_id)
        """
        if shard_count <= 0 or shard_index < 0 or shard_index >= shard_count:
            return None, None

        numeric_ids = [self._parse_bolt_id(bid) for bid in all_bolt_ids]
        numeric_ids = [nid for nid in numeric_ids if nid is not None]
        if not numeric_ids:
            return None, None

        numeric_ids.sort()
        total = len(numeric_ids)

        base_size = total // shard_count
        remainder = total % shard_count

        start = base_size * shard_index + min(remainder, shard_index)
        end = start + base_size + (1 if shard_index < remainder else 0)

        if start >= total:
            return None, None

        end = min(end, total)
        return numeric_ids[start], numeric_ids[end - 1]


job_sharding = JobSharding()
