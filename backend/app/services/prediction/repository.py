"""
预测数据仓库模块

封装所有与数据库相关的读写操作：
- 螺栓/法兰面历史数据查询（月度预测用）
- 批量预测数据查询（定时任务用）
- 预测结果持久化（异常预测、月度预测）

支持双数据源策略：
- 时序库启用时（timeseries.enabled=true, timeseries.prediction.use_for_prediction=true）：
  优先从时序库读取近 N 点窗口数据，回退到 MySQL
- 否则：只从 MySQL 读取
"""

import numpy as np
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger
from sqlalchemy import text

from app.utils.database import (
    get_db, get_flange_recent_data,
    AbnormalPrediction, MonthPrediction
)
from app.utils.config import config


def _is_timeseries_for_prediction() -> bool:
    """检查是否启用了时序库用于预测流水线"""
    return bool(config.get('timeseries.enabled', False)
                and config.get('timeseries.prediction.use_for_prediction', False))


def _get_prediction_window_size() -> int:
    """获取预测窗口大小配置"""
    return int(config.get('timeseries.prediction.window_size', 100))


def _get_timeseries_repo():
    """获取时序库实例（懒加载，避免循环依赖）"""
    try:
        from app.timeseries.factory import create_timeseries_repository
        return create_timeseries_repository()
    except Exception as e:
        logger.warning(f"时序库实例获取失败: {e}")
        return None


class PredictionRepository:
    """
    预测数据仓库（Repository Pattern）

    统一管理所有预测相关的数据库操作，
    将数据访问逻辑与业务逻辑分离。
    """

    # ---------- 历史数据查询 ----------

    def get_bolt_history(
        self,
        bolt_id: str,
        days: int = 30
    ) -> Optional[Dict[str, np.ndarray]]:
        """
        获取螺栓历史数据（用于 Prophet 月度预测）

        双数据源策略：若启用了时序库，优先时序库查询；否则 MySQL

        Args:
            bolt_id: 螺栓ID (sensor_id)
            days: 回溯天数，默认 30 天

        Returns:
            {'data': 预紧力数组, 'timestamps': 时间戳数组}，无数据时返回 None
        """
        if _is_timeseries_for_prediction():
            try:
                result = self._get_bolt_history_timeseries(bolt_id=bolt_id, days=days)
                if result is not None:
                    return result
                logger.warning(f"时序库无螺栓 {bolt_id} 历史数据，回退到 MySQL")
            except Exception as e:
                logger.warning(f"时序库读取螺栓 {bolt_id} 历史数据失败，回退 MySQL: {e}")

        return self._get_bolt_history_mysql(bolt_id=bolt_id, days=days)

    def _get_bolt_history_timeseries(
        self,
        bolt_id: str,
        days: int
    ) -> Optional[Dict[str, np.ndarray]]:
        """从时序库获取螺栓历史数据"""
        repo = _get_timeseries_repo()
        if repo is None:
            return None

        from datetime import timedelta
        from app.timeseries.base import AggregationLevel, TimeSeriesQuery

        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        # 数据量大时自动选择聚合级别
        if days <= 1:
            level = AggregationLevel.RAW
        elif days <= 7:
            level = AggregationLevel.MINUTE
        else:
            level = AggregationLevel.HOUR

        query = TimeSeriesQuery(
            sensor_id=str(bolt_id),
            start_time=start_time,
            end_time=end_time,
            aggregation_level=level,
        )

        points = repo.query_aggregated(query)
        if not points:
            # 回退到原始数据查询
            points = repo.query_raw(query)

        if not points:
            return None

        if level == AggregationLevel.RAW:
            values = np.array([p.value for p in points])
        else:
            values = np.array([p.mean for p in points])
        timestamps = np.array([p.timestamp for p in points])

        return {'data': values, 'timestamps': timestamps}

    def _get_bolt_history_mysql(
        self,
        bolt_id: str,
        days: int
    ) -> Optional[Dict[str, np.ndarray]]:
        """从 MySQL 获取螺栓历史数据（兼容旧实现）"""
        try:
            with get_db() as db:
                if db is None:
                    return None
                query = text("""
                    SELECT create_time, ptf
                    FROM sc_bolt_data
                    WHERE sensor_id = :sensor_id
                        AND create_time >= DATE_SUB(NOW(), INTERVAL :days DAY)
                    ORDER BY create_time ASC
                """)
                result = db.execute(query, {'sensor_id': bolt_id, 'days': days})
                rows = result.fetchall()

            if not rows:
                return None

            return {
                'data': np.array([r.ptf for r in rows]),
                'timestamps': np.array([r.create_time for r in rows])
            }
        except Exception as e:
            logger.warning(f"从 MySQL 获取螺栓历史数据失败: {e}")
            return None

    def get_flange_history(
        self,
        flange_id: str,
        days: int = 30
    ) -> Optional[Dict[str, np.ndarray]]:
        """
        获取法兰面历史数据（按时间取平均，用于 Prophet 月度预测）

        双数据源策略：若启用了时序库，优先时序库查询；否则 MySQL

        Args:
            flange_id: 法兰面ID
            days: 回溯天数，默认 30 天

        Returns:
            {'data': 平均预紧力数组, 'timestamps': 时间戳数组}，无数据时返回 None
        """
        # 时序库无法直接按 flange_id 查询（需先解出 bolt_id 再聚合）
        # 为简单起见，法兰面历史暂时走 MySQL；可后续扩展
        return self._get_flange_history_mysql(flange_id=flange_id, days=days)

    def _get_flange_history_mysql(
        self,
        flange_id: str,
        days: int
    ) -> Optional[Dict[str, np.ndarray]]:
        with get_db() as db:
            query = text("""
                SELECT create_time, AVG(ptf) as avg_ptf
                FROM sc_bolt_data
                WHERE CONCAT(collector_id, '-', splitter_num, '-', position) = :flange_id
                    AND create_time >= DATE_SUB(NOW(), INTERVAL :days DAY)
                GROUP BY create_time
                ORDER BY create_time ASC
            """)
            result = db.execute(query, {'flange_id': flange_id, 'days': days})
            rows = result.fetchall()

        if not rows:
            return None

        return {
            'data': np.array([r.avg_ptf for r in rows]),
            'timestamps': np.array([r.create_time for r in rows])
        }

    # ---------- 批量预测数据查询 ----------

    def fetch_batch_bolt_data(
        self,
        per_bolt_limit: int = 100,
        bolt_ids: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, List]]:
        """
        批量获取螺栓的最近 N 条数据（用于批量预测）

        双数据源策略：
        - 若启用了时序库用于预测，优先从时序库读取窗口数据
        - 时序库无数据或读取失败时，回退到 MySQL

        Args:
            per_bolt_limit: 每个螺栓取最近多少条
            bolt_ids: 可选，指定要获取的螺栓ID列表，None则获取所有

        Returns:
            {bolt_id: {'data': [...], 'timestamps': [...]}}
        """
        # ---- 路径1: 尝试使用时序库 ----
        if _is_timeseries_for_prediction():
            try:
                result = self._fetch_batch_bolt_data_timeseries(
                    per_bolt_limit=per_bolt_limit,
                    bolt_ids=bolt_ids
                )
                if result:
                    logger.info(
                        f"批量预测数据源: 时序库，获取螺栓数量: {len(result)}, "
                        f"窗口大小: {per_bolt_limit}"
                    )
                    return result
                else:
                    logger.warning(
                        "时序库未返回数据，回退到 MySQL"
                    )
            except Exception as e:
                logger.warning(
                    f"时序库读取批量预测数据失败，回退到 MySQL: {e}"
                )

        # ---- 路径2: 回退到 MySQL ----
        return self._fetch_batch_bolt_data_mysql(
            per_bolt_limit=per_bolt_limit,
            bolt_ids=bolt_ids
        )

    def _fetch_batch_bolt_data_timeseries(
        self,
        per_bolt_limit: int,
        bolt_ids: Optional[List[str]]
    ) -> Dict[str, Dict[str, List]]:
        """从时序库读取批量螺栓数据"""
        repo = _get_timeseries_repo()
        if repo is None:
            return {}

        # 如果指定了 bolt_ids，逐个读取
        if bolt_ids is not None and len(bolt_ids) > 0:
            sensor_ids = [str(bid) for bid in bolt_ids]
        else:
            # 从时序库查询所有有数据的传感器
            sensor_ids = repo.list_sensors()
            if not sensor_ids:
                return {}

        result: Dict[str, Dict[str, List]] = {}
        for sid in sensor_ids:
            try:
                window = repo.query_prediction_window(
                    sensor_id=sid,
                    window_size=per_bolt_limit
                )
                if window and len(window['data']) > 0:
                    data_list = [float(v) for v in window['data'].tolist()]
                    ts_list = [
                        t.isoformat() if hasattr(t, 'isoformat') else str(t)
                        for t in window['timestamps'].tolist()
                    ]
                    # 时间升序排列（预测流水线期望从旧→新）
                    result[sid] = {
                        'data': data_list,
                        'timestamps': ts_list,
                        'datasource': 'timeseries'
                    }
            except Exception as e:
                logger.warning(f"时序库读取传感器 {sid} 数据失败: {e}")
                continue

        return result

    def _fetch_batch_bolt_data_mysql(
        self,
        per_bolt_limit: int,
        bolt_ids: Optional[List[str]]
    ) -> Dict[str, Dict[str, List]]:
        """从 MySQL 读取批量螺栓数据（兼容旧实现）"""
        try:
            with get_db() as db:
                if db is None:
                    logger.warning("MySQL 连接不可用，返回空数据")
                    return {}
                if bolt_ids is not None and len(bolt_ids) > 0:
                    placeholders = ', '.join([f':id_{i}' for i in range(len(bolt_ids))])
                    params = {}
                    for i, bid in enumerate(bolt_ids):
                        params[f'id_{i}'] = str(bid)
                    params['limit'] = per_bolt_limit

                    query = text(f"""
                        SELECT id, create_time, sensor_id, ptf
                        FROM (
                            SELECT id, create_time, sensor_id, ptf,
                                @rank := IF(@current_sensor = sensor_id, @rank + 1, 1) AS sensor_rank,
                                @current_sensor := sensor_id
                            FROM sc_bolt_data
                            CROSS JOIN (SELECT @current_sensor := NULL, @rank := 0) AS vars
                            WHERE sensor_id IN ({placeholders})
                            ORDER BY sensor_id, create_time DESC
                        ) AS ranked_data
                        WHERE sensor_rank <= :limit
                        ORDER BY sensor_id, create_time DESC
                    """)
                    result = db.execute(query, params)
                else:
                    query = text("""
                        SELECT id, create_time, sensor_id, ptf
                        FROM (
                            SELECT id, create_time, sensor_id, ptf,
                                @rank := IF(@current_sensor = sensor_id, @rank + 1, 1) AS sensor_rank,
                                @current_sensor := sensor_id
                            FROM sc_bolt_data
                            CROSS JOIN (SELECT @current_sensor := NULL, @rank := 0) AS vars
                            ORDER BY sensor_id, create_time DESC
                        ) AS ranked_data
                        WHERE sensor_rank <= :limit
                        ORDER BY sensor_id, create_time DESC
                    """)
                    result = db.execute(query, {'limit': per_bolt_limit})
                rows = result.fetchall()

            bolt_data: Dict[str, Dict[str, List]] = {}
            for row in rows:
                sensor_id = str(row.sensor_id)
                if sensor_id not in bolt_data:
                    bolt_data[sensor_id] = {'data': [], 'timestamps': []}
                bolt_data[sensor_id]['data'].append(row.ptf)
                bolt_data[sensor_id]['timestamps'].append(row.create_time)

            return bolt_data
        except Exception as e:
            logger.warning(f"从 MySQL 读取批量预测数据失败: {e}")
            return {}

    def fetch_all_flange_ids(self) -> List[str]:
        """
        查询所有法兰面 ID

        Returns:
            法兰面 ID 列表
        """
        with get_db() as db:
            query = text("""
                SELECT DISTINCT CONCAT(collector_id, '-', splitter_num, '-', position) as flange_id
                FROM sc_bolt_data
            """)
            result = db.execute(query)
            return [row.flange_id for row in result.fetchall()]

    def fetch_flange_bolt_data(
        self,
        flange_id: str
    ) -> Optional[Dict[str, List[float]]]:
        """
        获取指定法兰面各螺栓的预紧力数据

        Args:
            flange_id: 法兰面 ID

        Returns:
            {sensor_id: [ptf, ...]}，无数据时返回 None
        """
        flange_data = get_flange_recent_data(flange_id)
        if not flange_data:
            return None

        bolt_series: Dict[str, List[float]] = {}
        for row in flange_data:
            sensor_id = str(row.sensor_id)
            if sensor_id not in bolt_series:
                bolt_series[sensor_id] = []
            bolt_series[sensor_id].append(row.ptf)

        return bolt_series

    # ---------- 结果持久化 ----------

    def save_bolt_prediction(self, bolt_id: str, result: Dict[str, Any]) -> None:
        try:
            with get_db() as db:
                fault_detail = result.get('fault_detail')
                fault_type_val = fault_detail.get('fault_type') if fault_detail else None
                fault_confidence_val = fault_detail.get('fault_confidence') if fault_detail else None
                fault_evidence_val = None
                if fault_detail:
                    fault_evidence_val = json.dumps(
                        {
                            'evidence': fault_detail.get('evidence', []),
                            'pattern': fault_detail.get('pattern', {}),
                            'recommendations': fault_detail.get('recommendations', []),
                            'fault_name': fault_detail.get('fault_name', ''),
                            'severity': fault_detail.get('severity', 0),
                        },
                        ensure_ascii=False,
                    )

                prediction = AbnormalPrediction(
                    bolt_id=int(bolt_id) if bolt_id.isdigit() else None,
                    node_type='螺栓',
                    year_month=datetime.now().strftime('%Y%m'),
                    pw_type=result['status'],
                    confidence=result['confidence'],
                    rec_measures=', '.join(result['recommendations']),
                    recent_time=result.get('recent_time'),
                    fault_type=fault_type_val,
                    fault_confidence=fault_confidence_val,
                    fault_evidence=fault_evidence_val,
                    create_time=datetime.now()
                )
                db.add(prediction)
                db.commit()
        except Exception as e:
            logger.error(f"保存螺栓预测失败 [{bolt_id}]: {e}")

    def save_flange_prediction(self, flange_id: str, result: Dict[str, Any]) -> None:
        try:
            with get_db() as db:
                recommendations = result.get('recommendations', [])
                root_cause_measures = result.get('root_cause_measures', '')

                all_measures = list(recommendations) if recommendations else []
                if root_cause_measures and root_cause_measures not in all_measures:
                    all_measures.append(root_cause_measures)

                rec_measures_str = '; '.join(all_measures) if all_measures else ''

                if len(rec_measures_str) > 1000:
                    rec_measures_str = rec_measures_str[:997] + '...'

                fault_detail = result.get('fault_detail')
                fault_type_val = fault_detail.get('fault_type') if fault_detail else None
                fault_confidence_val = fault_detail.get('fault_confidence') if fault_detail else None
                fault_evidence_val = None
                if fault_detail:
                    fault_evidence_val = json.dumps(
                        {
                            'evidence': fault_detail.get('evidence', []),
                            'pattern': fault_detail.get('pattern', {}),
                            'recommendations': fault_detail.get('recommendations', []),
                            'fault_name': fault_detail.get('fault_name', ''),
                            'severity': fault_detail.get('severity', 0),
                        },
                        ensure_ascii=False,
                    )

                prediction = AbnormalPrediction(
                    flm_id=flange_id,
                    node_type='法兰面',
                    year_month=datetime.now().strftime('%Y%m'),
                    pw_type=result['status'],
                    confidence=result['confidence'],
                    rec_measures=rec_measures_str,
                    fault_type=fault_type_val,
                    fault_confidence=fault_confidence_val,
                    fault_evidence=fault_evidence_val,
                    create_time=datetime.now()
                )
                db.add(prediction)
                db.commit()
        except Exception as e:
            logger.error(f"保存法兰面预测失败 [{flange_id}]: {e}")

    def save_monthly_prediction(
        self,
        node_id: str,
        node_type: str,
        result: Dict[str, Any]
    ) -> None:
        """
        保存月度预测结果

        Args:
            node_id: 节点ID
            node_type: 节点类型 ('bolt' / 'flange')
            result: 月度预测结果字典
        """
        try:
            with get_db() as db:
                prediction = MonthPrediction(
                    bolt_id=int(node_id) if node_type == 'bolt' and node_id.isdigit() else None,
                    flm_id=node_id if node_type == 'flange' else None,
                    node_type='螺栓' if node_type == 'bolt' else '法兰面',
                    year_month=datetime.now().strftime('%Y%m'),
                    pw_type=result['pw_type'],
                    begin_time=result.get('begin_time'),
                    end_time=result.get('end_time'),
                    confidence=result['confidence'],
                    rec_measures=result['rec_measures'],
                    create_time=datetime.now()
                )
                db.add(prediction)
                db.commit()
        except Exception as e:
            logger.error(f"保存月度预测失败 [{node_type}:{node_id}]: {e}")
