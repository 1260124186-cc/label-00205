"""
人工标注数据导入模块

提供从 CSV 文件或数据库导入人工标注数据的功能。
人工标注数据的标签会覆盖基于规则自动生成的标签。

主要功能:
1. 从 CSV 文件导入标注数据
2. 从数据库表导入标注数据
3. 标签去重和合并（人工标签优先级高于规则标签）
4. 数据校验和审核流程

使用示例:
    from app.services.label_import import LabelImportService
    
    service = LabelImportService()
    result = service.import_from_csv('bolt_labels.csv', 'bolt')
    print(f"成功导入 {result['imported']} 条标注")
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd
from loguru import logger

from app.utils.config import config
from app.utils.database import get_db, ManualLabelData, BoltData


@dataclass
class ImportResult:
    """导入结果统计"""
    total: int = 0
    imported: int = 0
    skipped: int = 0
    duplicates: int = 0
    errors: int = 0
    error_details: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.error_details is None:
            self.error_details = []

    def to_dict(self) -> Dict:
        return asdict(self)


class LabelImportService:
    """
    人工标注数据导入服务

    负责从各种来源导入人工标注数据，并管理标注数据的生命周期。
    """

    VALID_LABELS = {0, 1, 2, 3, 4}
    LABEL_NAMES = {
        0: '正常',
        1: '关注级预警',
        2: '检查级预警',
        3: '紧急级预警',
        4: '故障'
    }

    def __init__(self):
        """初始化导入服务"""
        self.import_dir = Path(config.get('label_import.import_dir', './data/imports'))
        self.import_dir.mkdir(parents=True, exist_ok=True)
        logger.info("人工标注数据导入服务初始化完成")

    def _calculate_data_hash(self, node_id: str, data_points: Any) -> str:
        """
        计算数据内容哈希，用于去重

        Args:
            node_id: 节点ID
            data_points: 数据点内容

        Returns:
            str: SHA256哈希值
        """
        content = f"{node_id}:{str(data_points)}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _validate_label(self, label: Any) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        验证标签的有效性

        Args:
            label: 标签值

        Returns:
            Tuple: (是否有效, 标准化后的标签, 错误信息)
        """
        try:
            label_int = int(label)
            if label_int not in self.VALID_LABELS:
                return False, None, f"无效标签值: {label}，有效范围 0-4"
            return True, label_int, None
        except (ValueError, TypeError):
            label_str = str(label).strip()
            for k, v in self.LABEL_NAMES.items():
                if label_str == v or label_str.lower() == v.lower():
                    return True, k, None
            return False, None, f"无法解析标签: {label}"

    def import_from_csv(
        self,
        csv_path: str,
        node_type: str,
        label_column: Optional[str] = None,
        id_column: Optional[str] = None,
        data_column: Optional[str] = None,
        timestamp_column: Optional[str] = None,
        labeler_name: Optional[str] = None,
        auto_approve: bool = True,
        skip_errors: bool = True
    ) -> ImportResult:
        """
        从 CSV 文件导入人工标注数据

        CSV 格式要求:
        - 必须包含节点ID列（如 bolt_id、螺栓id、sensor_id 等）
        - 必须包含标签列（数字 0-4 或中文标签名）
        - 可选：数据点列、时间戳列、标注人列

        Args:
            csv_path: CSV 文件路径
            node_type: 节点类型 bolt/flange
            label_column: 标签列名，自动检测常见列名
            id_column: 节点ID列名，自动检测
            data_column: 数据点列名（JSON格式的数组）
            timestamp_column: 时间戳列名
            labeler_name: 标注人姓名
            auto_approve: 是否自动审核通过
            skip_errors: 是否跳过错误行

        Returns:
            ImportResult: 导入结果统计
        """
        result = ImportResult()
        csv_file = Path(csv_path)

        if not csv_file.exists():
            raise FileNotFoundError(f"CSV文件不存在: {csv_path}")

        if node_type not in ['bolt', 'flange']:
            raise ValueError(f"无效的节点类型: {node_type}，必须为 bolt 或 flange")

        logger.info(f"开始从CSV导入标注数据: {csv_path}, 类型: {node_type}")

        try:
            df = pd.read_csv(csv_file)
            result.total = len(df)
            logger.info(f"CSV读取成功，共 {result.total} 行数据")
        except Exception as e:
            logger.error(f"读取CSV失败: {e}")
            raise

        id_column = id_column or self._detect_id_column(df.columns)
        label_column = label_column or self._detect_label_column(df.columns)

        if id_column is None:
            raise ValueError("无法自动检测节点ID列名，请手动指定 id_column")
        if label_column is None:
            raise ValueError("无法自动检测标签列名，请手动指定 label_column")

        logger.info(f"检测到列 - ID列: {id_column}, 标签列: {label_column}")

        records_to_save = []

        for idx, row in df.iterrows():
            try:
                node_id = str(row[id_column]).strip()
                if not node_id or node_id.lower() in ('nan', 'none', 'null'):
                    if skip_errors:
                        result.skipped += 1
                        continue
                    raise ValueError(f"第{idx+1}行: 节点ID为空")

                label_valid, label_int, label_err = self._validate_label(row[label_column])
                if not label_valid:
                    if skip_errors:
                        result.errors += 1
                        result.error_details.append({'row': idx + 1, 'error': label_err})
                        continue
                    raise ValueError(f"第{idx+1}行: {label_err}")

                data_points = None
                if data_column and data_column in df.columns:
                    try:
                        dp = row[data_column]
                        if isinstance(dp, str):
                            data_points = json.loads(dp)
                        else:
                            data_points = dp
                    except (json.JSONDecodeError, TypeError):
                        pass

                data_timestamp = None
                if timestamp_column and timestamp_column in df.columns:
                    try:
                        ts = row[timestamp_column]
                        if isinstance(ts, str):
                            data_timestamp = pd.to_datetime(ts).to_pydatetime()
                        else:
                            data_timestamp = pd.Timestamp(ts).to_pydatetime()
                    except Exception:
                        pass

                data_hash = self._calculate_data_hash(node_id, data_points)

                if self._check_duplicate(data_hash):
                    result.duplicates += 1
                    continue

                records_to_save.append({
                    'node_id': node_id,
                    'node_type': node_type,
                    'data_hash': data_hash,
                    'label': label_int,
                    'label_source': 'csv',
                    'label_confidence': 1.0,
                    'data_points': json.dumps(data_points, ensure_ascii=False) if data_points else None,
                    'data_timestamp': data_timestamp,
                    'label_time': datetime.now(),
                    'labeler_name': labeler_name or row.get('labeler') or row.get('标注人'),
                    'review_status': 'approved' if auto_approve else 'pending'
                })
                result.imported += 1

            except Exception as e:
                if skip_errors:
                    result.errors += 1
                    result.error_details.append({'row': idx + 1, 'error': str(e)})
                    logger.warning(f"跳过第{idx+1}行: {e}")
                else:
                    logger.error(f"导入失败在第{idx+1}行: {e}")
                    raise

        self._save_records(records_to_save)
        logger.info(
            f"CSV导入完成: 总计{result.total}, "
            f"成功{result.imported}, 重复{result.duplicates}, "
            f"跳过{result.skipped}, 错误{result.errors}"
        )

        return result

    def import_from_db(
        self,
        source_table: str,
        node_type: str,
        id_field: str,
        label_field: str,
        data_field: Optional[str] = None,
        timestamp_field: Optional[str] = None,
        where_clause: Optional[str] = None,
        labeler_name: Optional[str] = None,
        auto_approve: bool = True
    ) -> ImportResult:
        """
        从数据库表导入人工标注数据

        Args:
            source_table: 源表名
            node_type: 节点类型 bolt/flange
            id_field: 节点ID字段名
            label_field: 标签字段名
            data_field: 数据点字段名
            timestamp_field: 时间戳字段名
            where_clause: WHERE条件（不带WHERE关键字）
            labeler_name: 标注人姓名
            auto_approve: 是否自动审核通过

        Returns:
            ImportResult: 导入结果统计
        """
        result = ImportResult()
        logger.info(f"开始从数据库表导入标注: {source_table}, 类型: {node_type}")

        try:
            with get_db() as db:
                if db is None:
                    raise ConnectionError("数据库连接不可用")

                query = f"SELECT {id_field}, {label_field}"
                if data_field:
                    query += f", {data_field}"
                if timestamp_field:
                    query += f", {timestamp_field}"
                query += f" FROM {source_table}"
                if where_clause:
                    query += f" WHERE {where_clause}"

                from sqlalchemy import text
                rows = db.execute(text(query)).fetchall()
                result.total = len(rows)

                records_to_save = []
                for row in rows:
                    try:
                        node_id = str(row[0]).strip()
                        label_valid, label_int, label_err = self._validate_label(row[1])

                        if not label_valid:
                            result.errors += 1
                            continue

                        col_idx = 2
                        data_points = None
                        if data_field:
                            try:
                                dp = row[col_idx]
                                if isinstance(dp, str):
                                    data_points = json.loads(dp)
                                else:
                                    data_points = dp
                            except Exception:
                                pass
                            col_idx += 1

                        data_timestamp = None
                        if timestamp_field:
                            try:
                                data_timestamp = row[col_idx]
                                if isinstance(data_timestamp, str):
                                    data_timestamp = pd.to_datetime(data_timestamp).to_pydatetime()
                            except Exception:
                                pass

                        data_hash = self._calculate_data_hash(node_id, data_points)

                        if self._check_duplicate(data_hash):
                            result.duplicates += 1
                            continue

                        records_to_save.append({
                            'node_id': node_id,
                            'node_type': node_type,
                            'data_hash': data_hash,
                            'label': label_int,
                            'label_source': 'db',
                            'label_confidence': 1.0,
                            'data_points': json.dumps(data_points, ensure_ascii=False) if data_points else None,
                            'data_timestamp': data_timestamp,
                            'label_time': datetime.now(),
                            'labeler_name': labeler_name,
                            'review_status': 'approved' if auto_approve else 'pending'
                        })
                        result.imported += 1

                    except Exception as e:
                        result.errors += 1
                        result.error_details.append({'row': str(row[:2]), 'error': str(e)})

                self._save_records(records_to_save)

        except Exception as e:
            logger.error(f"从数据库导入失败: {e}")
            raise

        logger.info(
            f"DB导入完成: 总计{result.total}, "
            f"成功{result.imported}, 重复{result.duplicates}, 错误{result.errors}"
        )

        return result

    def _save_records(self, records: List[Dict]) -> None:
        """
        批量保存标注记录到数据库

        Args:
            records: 记录列表
        """
        if not records:
            return

        try:
            with get_db() as db:
                if db is None:
                    logger.warning("数据库不可用，跳过保存标注记录")
                    return

                for rec in records:
                    obj = ManualLabelData(**rec)
                    db.add(obj)

                logger.info(f"已保存 {len(records)} 条标注记录到数据库")
        except Exception as e:
            logger.error(f"保存标注记录失败: {e}")
            raise

    def _check_duplicate(self, data_hash: str) -> bool:
        """
        检查是否为重复数据

        Args:
            data_hash: 数据哈希

        Returns:
            bool: 是否重复
        """
        try:
            with get_db() as db:
                if db is None:
                    return False
                exists = db.query(ManualLabelData).filter(
                    ManualLabelData.data_hash == data_hash
                ).first()
                return exists is not None
        except Exception:
            return False

    def _detect_id_column(self, columns: List[str]) -> Optional[str]:
        """自动检测节点ID列名"""
        candidates = [
            'bolt_id', '螺栓id', '螺栓ID', 'sensor_id', '传感器id',
            'flange_id', '法兰面id', '法兰面ID', 'node_id', '节点id',
            'id', 'ID', 'bolt', 'flange'
        ]
        for col in candidates:
            if col in columns:
                return col
        return None

    def _detect_label_column(self, columns: List[str]) -> Optional[str]:
        """自动检测标签列名"""
        candidates = [
            'label', 'Label', 'LABEL', 'labels',
            'status', 'Status', 'STATUS',
            '标签', '状态', '标注', '人工标签',
            'state', 'class', 'category'
        ]
        for col in candidates:
            if col in columns:
                return col
        return None

    def get_manual_labels(
        self,
        node_type: str,
        node_id: Optional[str] = None,
        only_approved: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取人工标注数据，按节点ID分组

        Args:
            node_type: 节点类型
            node_id: 可选，指定节点ID
            only_approved: 是否只返回审核通过的

        Returns:
            Dict: {node_id: [{'label': int, 'confidence': float, 'data_hash': str, ...}, ...]}
        """
        result = {}

        try:
            with get_db() as db:
                if db is None:
                    return result

                query = db.query(ManualLabelData).filter(
                    ManualLabelData.node_type == node_type
                )

                if node_id:
                    query = query.filter(ManualLabelData.node_id == node_id)

                if only_approved:
                    query = query.filter(ManualLabelData.review_status == 'approved')

                records = query.all()

                for rec in records:
                    if rec.node_id not in result:
                        result[rec.node_id] = []
                    result[rec.node_id].append({
                        'label': rec.label,
                        'confidence': rec.label_confidence,
                        'data_hash': rec.data_hash,
                        'data_points': rec.data_points,
                        'data_timestamp': rec.data_timestamp,
                        'label_time': rec.label_time,
                        'labeler_name': rec.labeler_name
                    })

        except Exception as e:
            logger.error(f"获取人工标注数据失败: {e}")

        return result

    def merge_labels_with_manual(
        self,
        node_type: str,
        node_id: str,
        auto_labels: np.ndarray,
        data_values: np.ndarray,
        sequence_length: int = 100
    ) -> np.ndarray:
        """
        将人工标注标签合并到自动生成的标签中

        人工标注标签具有更高优先级，会覆盖对应位置的自动标签。

        Args:
            node_type: 节点类型
            node_id: 节点ID
            auto_labels: 自动生成的标签数组
            data_values: 对应的原始数据值（用于匹配）
            sequence_length: 序列长度

        Returns:
            np.ndarray: 合并后的标签数组
        """
        merged = auto_labels.copy()
        manual_labels = self.get_manual_labels(node_type, node_id)

        if node_id not in manual_labels or not manual_labels[node_id]:
            return merged

        for lbl_info in manual_labels[node_id]:
            try:
                if lbl_info.get('data_points'):
                    dp = json.loads(lbl_info['data_points']) if isinstance(lbl_info['data_points'], str) else lbl_info['data_points']
                    dp_arr = np.array(dp).flatten()

                    match_idx = self._find_sequence_match(data_values, dp_arr)
                    if match_idx is not None:
                        seq_start = max(0, match_idx - sequence_length + len(dp_arr))
                        seq_end = min(len(merged), match_idx + sequence_length)
                        for i in range(seq_start, seq_end):
                            if i < len(merged):
                                merged[i] = lbl_info['label']
                        logger.debug(
                            f"人工标注覆盖: 节点{node_id}, "
                            f"位置{match_idx}, 标签{lbl_info['label']}"
                        )
            except Exception as e:
                logger.warning(f"合并人工标注失败: {e}")

        override_count = np.sum(merged != auto_labels)
        if override_count > 0:
            logger.info(
                f"标签合并完成: 节点{node_id}, "
                f"人工标注覆盖了 {override_count}/{len(merged)} 个标签"
            )

        return merged

    def _find_sequence_match(
        self,
        full_data: np.ndarray,
        sub_sequence: np.ndarray,
        tolerance: float = 1e-6
    ) -> Optional[int]:
        """
        在完整数据中查找子序列的匹配位置

        Args:
            full_data: 完整数据序列
            sub_sequence: 要查找的子序列
            tolerance: 数值容差

        Returns:
            Optional[int]: 匹配的起始位置，未找到返回None
        """
        if len(sub_sequence) > len(full_data):
            return None

        sub_len = len(sub_sequence)
        full_len = len(full_data)

        for i in range(full_len - sub_len + 1):
            window = full_data[i:i + sub_len]
            if len(window) == len(sub_sequence):
                diff = np.abs(window - sub_sequence)
                if np.all(diff < tolerance):
                    return i

        return None

    def list_import_files(self) -> List[Dict[str, Any]]:
        """
        列出导入目录中的所有CSV文件

        Returns:
            List: 文件信息列表
        """
        files = []
        for f in self.import_dir.glob('*.csv'):
            stat = f.stat()
            files.append({
                'filename': f.name,
                'path': str(f),
                'size_bytes': stat.st_size,
                'modified_time': datetime.fromtimestamp(stat.st_mtime)
            })
        return sorted(files, key=lambda x: x['modified_time'], reverse=True)


label_import_service = LabelImportService()
