"""
数据校验层

所有预测/训练请求经 DataValidator 统一校验：
- 时间格式
- 数值范围
- 序列长度
- 缺失率
- 法兰螺栓数量一致性

校验失败返回结构化错误码（如 E1001: 序列长度不足 100）。
支持宽松模式（自动截断/填充）与严格模式（直接拒绝）。

使用示例:
    from app.api.validators import DataValidator, ValidationMode

    validator = DataValidator()
    result = validator.validate_bolt_prediction(
        bolt_id="B001",
        data=[["2025-01-01 00:00:00", 400.0], ...],
        mode=ValidationMode.STRICT
    )
    if not result.is_valid:
        for err in result.errors:
            print(f"{err.code}: {err.message}")
"""

import re
import numpy as np
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from app.utils.config import config


# ==================== 错误码定义 ====================

class ErrorCode(Enum):
    """
    校验错误码枚举

    编码规则:
    - E10xx: 基础数据错误
    - E11xx: 时间格式错误
    - E12xx: 数值范围错误
    - E13xx: 数据质量错误（缺失率等）
    - E14xx: 法兰螺栓一致性错误
    - E15xx: 训练数据错误
    """

    # E10xx: 基础数据错误
    DATA_EMPTY = ("E1001", "数据为空")
    SEQUENCE_TOO_SHORT = ("E1002", "序列长度不足")
    SEQUENCE_TOO_LONG = ("E1003", "序列长度超限")
    INVALID_FIELD = ("E1004", "字段格式错误")
    ID_REQUIRED = ("E1005", "ID不能为空")
    ID_TOO_LONG = ("E1006", "ID长度超限")
    INVALID_NODE_TYPE = ("E1007", "无效的节点类型")

    # E11xx: 时间格式错误
    INVALID_TIMESTAMP_FORMAT = ("E1101", "时间格式无效")
    TIMESTAMP_OUT_OF_ORDER = ("E1102", "时间顺序错误")
    TIMESTAMP_DUPLICATE = ("E1103", "时间戳重复")

    # E12xx: 数值范围错误
    VALUE_OUT_OF_RANGE = ("E1201", "数值超出范围")
    VALUE_TYPE_ERROR = ("E1202", "数值类型错误")
    VALUE_NAN_INF = ("E1203", "数值为NaN或Inf")
    VALUE_NEGATIVE = ("E1204", "数值不能为负")

    # E13xx: 数据质量错误
    MISSING_RATE_TOO_HIGH = ("E1301", "缺失率过高")
    INVALID_VALUE_RATIO_HIGH = ("E1302", "无效值比例过高")

    # E14xx: 法兰螺栓一致性错误
    FLANGE_BOLT_COUNT_MISMATCH = ("E1401", "法兰螺栓数量不一致")
    FLANGE_BOLT_COUNT_TOO_FEW = ("E1402", "法兰螺栓数量不足")
    FLANGE_BOLT_COUNT_TOO_MANY = ("E1403", "法兰螺栓数量超限")
    FLANGE_BOLT_SEQ_LEN_MISMATCH = ("E1404", "各螺栓序列长度不一致")

    # E15xx: 训练数据错误
    TRAINING_SAMPLES_INSUFFICIENT = ("E1501", "训练样本不足")
    TRAINING_LABELS_MISMATCH = ("E1502", "训练标签与数据不匹配")

    @property
    def code(self) -> str:
        """获取错误码字符串"""
        return self.value[0]

    @property
    def message(self) -> str:
        """获取错误默认消息"""
        return self.value[1]


# ==================== 校验模式 ====================

class ValidationMode(Enum):
    """校验模式"""
    STRICT = "strict"
    LENIENT = "lenient"


# ==================== 校验结果数据类 ====================

@dataclass
class ValidationErrorItem:
    """
    校验错误项

    Attributes:
        code: 错误码（如 E1001）
        message: 错误消息
        field: 出错字段路径
        value: 出错的值
        severity: 严重程度 error/warning
    """
    code: str
    message: str
    field: str = ""
    value: Any = None
    severity: str = "error"

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


@dataclass
class ValidationResult:
    """
    校验结果

    Attributes:
        is_valid: 是否校验通过
        errors: 错误列表
        warnings: 警告列表
        cleaned_data: 清洗/修复后的数据（宽松模式下）
        mode: 使用的校验模式
        adjustments: 应用的调整说明（宽松模式下）
    """
    is_valid: bool
    errors: List[ValidationErrorItem] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    cleaned_data: Optional[Dict[str, Any]] = None
    mode: ValidationMode = ValidationMode.STRICT
    adjustments: List[str] = field(default_factory=list)

    def add_error(self, error_code: ErrorCode, field: str = "",
                  value: Any = None, detail: str = "") -> None:
        """添加错误"""
        msg = error_code.message
        if detail:
            msg = f"{msg}：{detail}"
        self.errors.append(ValidationErrorItem(
            code=error_code.code,
            message=msg,
            field=field,
            value=value,
            severity="error"
        ))
        self.is_valid = False

    def add_warning_msg(self, msg: str) -> None:
        """添加警告"""
        self.warnings.append(msg)

    def add_adjustment(self, adjustment: str) -> None:
        """记录宽松模式下的调整"""
        self.adjustments.append(adjustment)


# ==================== 数据校验器 ====================

class DataValidator:
    """
    统一数据校验器

    所有预测/训练请求的入口校验，支持严格模式和宽松模式。
    """

    def __init__(self):
        """初始化校验器，加载配置"""
        # 预紧力阈值
        preload_thresholds = config.get('risk_assessment.preload_thresholds', {})
        self.min_preload_normal = preload_thresholds.get('min_normal', 400)
        self.max_preload_normal = preload_thresholds.get('max_normal', 800)
        self.min_preload_abs = self.min_preload_normal * 0.1
        self.max_preload_abs = self.max_preload_normal * 3.0

        # 序列长度配置
        seq_config = config.get('validation.sequence_length', {})
        self.min_sequence_length = seq_config.get('min_predict', 10)
        self.recommended_sequence_length = seq_config.get('recommended', 100)
        self.max_sequence_length = seq_config.get('max_predict', 10000)

        # 数据质量配置
        quality_config = config.get('validation.data_quality', {})
        self.max_missing_rate = quality_config.get('max_missing_rate', 0.2)
        self.max_invalid_ratio = quality_config.get('max_invalid_ratio', 0.1)

        # 法兰螺栓配置
        flange_config = config.get('validation.flange', {})
        self.min_flange_bolts = flange_config.get('min_bolts', 2)
        self.max_flange_bolts = flange_config.get('max_bolts', 50)

        # 时间格式模式
        self.time_patterns = [
            (r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', '%Y-%m-%d %H:%M:%S'),
            (r'^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}$', '%Y/%m/%d %H:%M:%S'),
            (r'^\d{8} \d{2}:\d{2}:\d{2}$', '%Y%m%d %H:%M:%S'),
            (r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', '%Y-%m-%dT%H:%M:%S'),
            (r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}$', '%Y-%m-%d %H:%M:%S.%f'),
        ]

        logger.info("数据校验器初始化完成")

    # ==================== 螺栓预测校验 ====================

    def validate_bolt_prediction(
        self,
        bolt_id: str,
        data: List[List[Any]],
        mode: ValidationMode = ValidationMode.STRICT,
    ) -> ValidationResult:
        """
        校验螺栓预测请求

        Args:
            bolt_id: 螺栓ID
            data: 预紧力数据 [[时间, 预紧力], ...]
            mode: 校验模式

        Returns:
            ValidationResult: 校验结果
        """
        result = ValidationResult(is_valid=True, mode=mode)

        # 1. 校验螺栓ID
        self._validate_id(bolt_id, "bolt_id", result, max_length=50)
        if not result.is_valid and mode == ValidationMode.STRICT:
            return result

        # 2. 校验数据格式和长度
        self._validate_sequence_length(data, "data", result, mode)
        if not result.is_valid and mode == ValidationMode.STRICT:
            return result

        # 3. 校验每个数据点（时间 + 数值）
        timestamps, values = self._validate_timeseries_data(
            data, "data", result, mode
        )

        # 4. 计算缺失率
        self._validate_missing_rate(data, values, "data", result, mode)

        # 5. 宽松模式：处理序列长度
        if mode == ValidationMode.LENIENT:
            timestamps, values = self._adjust_sequence_length(
                timestamps, values, result,
                target_length=self.recommended_sequence_length,
                field="data"
            )

        # 6. 组装清洗后的数据
        if result.is_valid or mode == ValidationMode.LENIENT:
            result.cleaned_data = {
                'bolt_id': bolt_id,
                'timestamps': timestamps,
                'values': np.array(values, dtype=float),
                'data_points': len(values),
            }

        return result

    # ==================== 法兰面预测校验 ====================

    def validate_flange_prediction(
        self,
        flange_id: str,
        data: List[List[List[Any]]],
        mode: ValidationMode = ValidationMode.STRICT,
    ) -> ValidationResult:
        """
        校验法兰面预测请求

        Args:
            flange_id: 法兰面ID
            data: 多螺栓数据 [[[时间, 预紧力], ...], ...]
            mode: 校验模式

        Returns:
            ValidationResult: 校验结果
        """
        result = ValidationResult(is_valid=True, mode=mode)

        # 1. 校验法兰面ID
        self._validate_id(flange_id, "flange_id", result, max_length=100)
        if not result.is_valid and mode == ValidationMode.STRICT:
            return result

        # 2. 校验螺栓数量
        self._validate_flange_bolt_count(data, "data", result, mode)
        if not result.is_valid and mode == ValidationMode.STRICT:
            return result

        # 3. 逐个校验每个螺栓的时间序列数据
        all_timestamps = []
        all_values = []
        bolt_lengths = []

        for bolt_idx, bolt_data in enumerate(data):
            field = f"data[{bolt_idx}]"

            # 校验序列长度
            seq_result = ValidationResult(is_valid=True, mode=mode)
            self._validate_sequence_length(bolt_data, field, seq_result, mode)

            if not seq_result.is_valid and mode == ValidationMode.STRICT:
                result.errors.extend(seq_result.errors)
                result.is_valid = False
                continue

            # 校验时间和数值
            ts, vals = self._validate_timeseries_data(
                bolt_data, field, result, mode
            )

            bolt_lengths.append(len(vals))
            all_timestamps.append(ts)
            all_values.append(np.array(vals, dtype=float))

        # 4. 校验各螺栓序列长度一致性
        self._validate_flange_sequence_consistency(
            bolt_lengths, "data", result, mode
        )

        # 5. 宽松模式：统一各螺栓序列长度
        if mode == ValidationMode.LENIENT and all_values:
            all_timestamps, all_values = self._align_flange_sequences(
                all_timestamps, all_values, result, "data"
            )

        # 6. 校验缺失率（总体）
        if data:
            total_points = sum(len(bd) for bd in data)
            valid_points = sum(len(v) for v in all_values)
            missing_count = total_points - valid_points
            if total_points > 0:
                missing_rate = missing_count / total_points
                if missing_rate > self.max_missing_rate and mode == ValidationMode.STRICT:
                    result.add_error(
                        ErrorCode.MISSING_RATE_TOO_HIGH,
                        field="data",
                        value=f"{missing_rate:.2%}",
                        detail=f"缺失率 {missing_rate:.2%} > {self.max_missing_rate:.0%}"
                    )

        # 7. 组装清洗后的数据
        if result.is_valid or mode == ValidationMode.LENIENT:
            result.cleaned_data = {
                'flange_id': flange_id,
                'bolt_count': len(all_values),
                'all_timestamps': all_timestamps,
                'all_values': all_values,
                'bolt_lengths': [len(v) for v in all_values],
            }

        return result

    # ==================== 风险评估校验 ====================

    def validate_risk_assessment(
        self,
        node_id: str,
        node_type: str,
        data: List[List[Any]],
        mode: ValidationMode = ValidationMode.STRICT,
    ) -> ValidationResult:
        """
        校验风险评估请求

        Args:
            node_id: 节点ID
            node_type: 节点类型 bolt/flange
            data: 预紧力数据
            mode: 校验模式

        Returns:
            ValidationResult: 校验结果
        """
        result = ValidationResult(is_valid=True, mode=mode)

        # 1. 校验节点类型
        valid_types = ['bolt', 'flange', '螺栓', '法兰面']
        if node_type not in valid_types:
            result.add_error(
                ErrorCode.INVALID_NODE_TYPE,
                field="node_type",
                value=node_type,
                detail=f"有效值: {', '.join(valid_types)}"
            )
            if mode == ValidationMode.STRICT:
                return result

        # 2. 校验节点ID
        self._validate_id(node_id, "node_id", result, max_length=100)
        if not result.is_valid and mode == ValidationMode.STRICT:
            return result

        # 3. 校验数据
        self._validate_sequence_length(data, "data", result, mode)
        if not result.is_valid and mode == ValidationMode.STRICT:
            return result

        timestamps, values = self._validate_timeseries_data(
            data, "data", result, mode
        )

        # 4. 组装结果
        if result.is_valid or mode == ValidationMode.LENIENT:
            result.cleaned_data = {
                'node_id': node_id,
                'node_type': node_type,
                'timestamps': timestamps,
                'values': np.array(values, dtype=float),
            }

        return result

    # ==================== 训练数据校验 ====================

    def validate_training_data(
        self,
        data: np.ndarray,
        labels: Optional[np.ndarray] = None,
        min_samples: int = 100,
        mode: ValidationMode = ValidationMode.STRICT,
    ) -> ValidationResult:
        """
        校验训练数据

        Args:
            data: 训练数据
            labels: 训练标签
            min_samples: 最小样本数
            mode: 校验模式

        Returns:
            ValidationResult: 校验结果
        """
        result = ValidationResult(is_valid=True, mode=mode)

        # 1. 校验样本数量
        n_samples = len(data)
        if n_samples < min_samples:
            result.add_error(
                ErrorCode.TRAINING_SAMPLES_INSUFFICIENT,
                field="data",
                value=n_samples,
                detail=f"样本数 {n_samples} < 最小要求 {min_samples}"
            )
            if mode == ValidationMode.STRICT:
                return result

        # 2. 校验标签
        if labels is not None:
            if len(labels) != n_samples:
                result.add_error(
                    ErrorCode.TRAINING_LABELS_MISMATCH,
                    field="labels",
                    value=f"data={n_samples}, labels={len(labels)}",
                    detail="标签数量与数据不一致"
                )

        # 3. 校验数据值范围
        if data.size > 0:
            data_flat = data.flatten() if hasattr(data, 'flatten') else np.array(data)

            nan_count = np.isnan(data_flat).sum()
            inf_count = np.isinf(data_flat).sum()

            if nan_count > 0 or inf_count > 0:
                invalid_count = nan_count + inf_count
                invalid_ratio = invalid_count / len(data_flat)
                if invalid_ratio > self.max_invalid_ratio and mode == ValidationMode.STRICT:
                    result.add_error(
                        ErrorCode.INVALID_VALUE_RATIO_HIGH,
                        field="data",
                        value=f"{invalid_ratio:.2%}",
                        detail=f"无效值比例 {invalid_ratio:.2%} > {self.max_invalid_ratio:.0%}"
                    )
                else:
                    result.add_warning_msg(
                        f"训练数据中包含 {invalid_count} 个无效值 (NaN/Inf)，占比 {invalid_ratio:.2%}"
                    )

        # 4. 组装结果
        if result.is_valid or mode == ValidationMode.LENIENT:
            result.cleaned_data = {
                'samples': n_samples,
                'has_labels': labels is not None,
            }

        return result

    # ==================== 内部工具方法 ====================

    def _validate_id(
        self,
        id_value: str,
        field: str,
        result: ValidationResult,
        max_length: int = 50
    ) -> None:
        """校验ID字段"""
        if not id_value or not str(id_value).strip():
            result.add_error(
                ErrorCode.ID_REQUIRED,
                field=field,
                value=id_value
            )
        elif len(str(id_value)) > max_length:
            result.add_error(
                ErrorCode.ID_TOO_LONG,
                field=field,
                value=len(str(id_value)),
                detail=f"长度 {len(str(id_value))} > {max_length}"
            )

    def _validate_sequence_length(
        self,
        data: List[Any],
        field: str,
        result: ValidationResult,
        mode: ValidationMode = ValidationMode.STRICT,
    ) -> None:
        """校验序列长度"""
        if not data:
            result.add_error(
                ErrorCode.DATA_EMPTY,
                field=field,
                value=0
            )
            return

        length = len(data)

        if length < self.min_sequence_length:
            if mode == ValidationMode.STRICT:
                result.add_error(
                    ErrorCode.SEQUENCE_TOO_SHORT,
                    field=field,
                    value=length,
                    detail=f"长度 {length} < 最小要求 {self.min_sequence_length}"
                )
            else:
                result.add_warning_msg(
                    f"序列长度不足（{length}），宽松模式下将自动填充至 {self.recommended_sequence_length}"
                )

        if length > self.max_sequence_length:
            if mode == ValidationMode.STRICT:
                result.add_error(
                    ErrorCode.SEQUENCE_TOO_LONG,
                    field=field,
                    value=length,
                    detail=f"长度 {length} > 最大限制 {self.max_sequence_length}"
                )
            else:
                result.add_warning_msg(
                    f"序列长度超限（{length}），宽松模式下将自动截断至 {self.max_sequence_length}"
                )

        # 推荐长度警告
        if self.min_sequence_length <= length < self.recommended_sequence_length:
            result.add_warning_msg(
                f"数据点数量较少（{length}），建议提供至少 {self.recommended_sequence_length} 条数据以获得更准确的预测"
            )

    def _validate_timeseries_data(
        self,
        data: List[List[Any]],
        field: str,
        result: ValidationResult,
        mode: ValidationMode,
    ) -> Tuple[List[Any], List[float]]:
        """
        校验时间序列数据的每个数据点

        Returns:
            (timestamps, values): 有效的时间戳和值列表
        """
        timestamps = []
        values = []
        last_timestamp = None

        for i, item in enumerate(data):
            item_field = f"{field}[{i}]"

            # 格式校验
            if not isinstance(item, (list, tuple)):
                if mode == ValidationMode.STRICT:
                    result.add_error(
                        ErrorCode.INVALID_FIELD,
                        field=item_field,
                        value=type(item).__name__,
                        detail="应为[时间, 预紧力]格式"
                    )
                continue

            if len(item) < 2:
                if mode == ValidationMode.STRICT:
                    result.add_error(
                        ErrorCode.INVALID_FIELD,
                        field=item_field,
                        value=len(item),
                        detail="缺少必要字段"
                    )
                continue

            timestamp = item[0]
            value = item[1]

            # 时间格式校验
            ts_parsed = self._parse_timestamp(timestamp)
            if ts_parsed is None:
                if mode == ValidationMode.STRICT:
                    result.add_error(
                        ErrorCode.INVALID_TIMESTAMP_FORMAT,
                        field=f"{item_field}[0]",
                        value=str(timestamp)
                    )
                continue

            # 时间顺序校验
            if last_timestamp is not None:
                if ts_parsed < last_timestamp:
                    if mode == ValidationMode.STRICT:
                        result.add_error(
                            ErrorCode.TIMESTAMP_OUT_OF_ORDER,
                            field=f"{item_field}[0]",
                            value=str(timestamp),
                            detail="时间戳非递增"
                        )
                    # 宽松模式下不阻断，继续处理
                elif ts_parsed == last_timestamp:
                    result.add_warning_msg(
                        f"{item_field}: 时间戳重复 {timestamp}"
                    )

            # 数值校验
            val_error = self._validate_value(value, item_field, mode)
            if val_error is not None and mode == ValidationMode.STRICT:
                result.errors.append(val_error)
                continue

            # 宽松模式下跳过无效值
            try:
                val_float = float(value)
                if np.isnan(val_float) or np.isinf(val_float):
                    if mode == ValidationMode.STRICT:
                        result.add_error(
                            ErrorCode.VALUE_NAN_INF,
                            field=f"{item_field}[1]",
                            value=value
                        )
                    continue
            except (ValueError, TypeError):
                if mode == ValidationMode.STRICT:
                    result.add_error(
                        ErrorCode.VALUE_TYPE_ERROR,
                        field=f"{item_field}[1]",
                        value=value,
                        detail="无法转换为数字"
                    )
                continue

            # 范围校验
            if val_float < self.min_preload_abs or val_float > self.max_preload_abs:
                if mode == ValidationMode.STRICT:
                    result.add_error(
                        ErrorCode.VALUE_OUT_OF_RANGE,
                        field=f"{item_field}[1]",
                        value=val_float,
                        detail=f"范围 [{self.min_preload_abs}, {self.max_preload_abs}]"
                    )
                    continue
                else:
                    # 宽松模式下裁剪到边界
                    val_float = max(self.min_preload_abs, min(self.max_preload_abs, val_float))
                    result.add_adjustment(
                        f"{item_field}: 数值裁剪到边界 {val_float}"
                    )

            timestamps.append(timestamp)
            values.append(val_float)
            last_timestamp = ts_parsed

        return timestamps, values

    def _validate_value(
        self,
        value: Any,
        field: str,
        mode: ValidationMode,
    ) -> Optional[ValidationErrorItem]:
        """校验单个数值，返回错误项（如果有）"""
        try:
            val = float(value)
        except (ValueError, TypeError):
            return ValidationErrorItem(
                code=ErrorCode.VALUE_TYPE_ERROR.code,
                message=f"{ErrorCode.VALUE_TYPE_ERROR.message}：无法转换为数字",
                field=field,
                value=value,
                severity="error"
            )

        if np.isnan(val) or np.isinf(val):
            return ValidationErrorItem(
                code=ErrorCode.VALUE_NAN_INF.code,
                message=ErrorCode.VALUE_NAN_INF.message,
                field=field,
                value=value,
                severity="error"
            )

        return None

    def _validate_missing_rate(
        self,
        raw_data: List[Any],
        valid_values: List[Any],
        field: str,
        result: ValidationResult,
        mode: ValidationMode,
    ) -> None:
        """校验缺失率"""
        total = len(raw_data)
        if total == 0:
            return

        missing_count = total - len(valid_values)
        missing_rate = missing_count / total

        if missing_rate > self.max_missing_rate:
            if mode == ValidationMode.STRICT:
                result.add_error(
                    ErrorCode.MISSING_RATE_TOO_HIGH,
                    field=field,
                    value=f"{missing_rate:.2%}",
                    detail=f"缺失率 {missing_rate:.2%} > 允许阈值 {self.max_missing_rate:.0%}"
                )
            else:
                result.add_warning_msg(
                    f"数据缺失率较高 ({missing_rate:.2%})，可能影响预测准确性"
                )

        if missing_rate > 0 and missing_rate <= self.max_missing_rate:
            result.add_warning_msg(
                f"数据存在 {missing_count} 个无效点（缺失率 {missing_rate:.2%}），已自动跳过"
            )

    def _validate_flange_bolt_count(
        self,
        data: List[Any],
        field: str,
        result: ValidationResult,
        mode: ValidationMode,
    ) -> None:
        """校验法兰螺栓数量"""
        if not data:
            result.add_error(
                ErrorCode.DATA_EMPTY,
                field=field,
                value=0
            )
            return

        count = len(data)

        if count < self.min_flange_bolts:
            if mode == ValidationMode.STRICT:
                result.add_error(
                    ErrorCode.FLANGE_BOLT_COUNT_TOO_FEW,
                    field=field,
                    value=count,
                    detail=f"螺栓数 {count} < 最小要求 {self.min_flange_bolts}"
                )
            else:
                result.add_warning_msg(
                    f"法兰螺栓数量较少（{count}），建议至少提供 {self.min_flange_bolts} 个螺栓数据"
                )

        if count > self.max_flange_bolts:
            if mode == ValidationMode.STRICT:
                result.add_error(
                    ErrorCode.FLANGE_BOLT_COUNT_TOO_MANY,
                    field=field,
                    value=count,
                    detail=f"螺栓数 {count} > 最大限制 {self.max_flange_bolts}"
                )
            else:
                result.add_warning_msg(
                    f"法兰螺栓数量较多（{count}），宽松模式下仅使用前 {self.max_flange_bolts} 个"
                )

    def _validate_flange_sequence_consistency(
        self,
        bolt_lengths: List[int],
        field: str,
        result: ValidationResult,
        mode: ValidationMode,
    ) -> None:
        """校验各螺栓序列长度一致性"""
        if len(bolt_lengths) < 2:
            return

        min_len = min(bolt_lengths)
        max_len = max(bolt_lengths)

        if min_len != max_len:
            if mode == ValidationMode.STRICT:
                result.add_error(
                    ErrorCode.FLANGE_BOLT_SEQ_LEN_MISMATCH,
                    field=field,
                    value=f"min={min_len}, max={max_len}",
                    detail=f"各螺栓序列长度不一致，范围 [{min_len}, {max_len}]"
                )
            else:
                result.add_warning_msg(
                    f"各螺栓序列长度不一致 (min={min_len}, max={max_len})，宽松模式下将自动对齐"
                )

    # ==================== 宽松模式调整方法 ====================

    def _adjust_sequence_length(
        self,
        timestamps: List[Any],
        values: List[float],
        result: ValidationResult,
        target_length: int,
        field: str,
    ) -> Tuple[List[Any], List[float]]:
        """
        宽松模式下调整序列长度

        - 过长则截断（保留最新数据）
        - 过短则填充（向前复制）
        """
        current_length = len(values)

        if current_length == target_length:
            return timestamps, values

        if current_length > target_length:
            # 截断：保留最后的 target_length 个数据点
            result.add_adjustment(
                f"{field}: 序列过长，从 {current_length} 截断为 {target_length}（保留最新数据）"
            )
            return (
                timestamps[-target_length:],
                values[-target_length:]
            )

        if current_length < target_length and current_length > 0:
            # 填充：向前复制第一个值
            pad_count = target_length - current_length
            first_ts = timestamps[0]
            first_val = values[0]

            result.add_adjustment(
                f"{field}: 序列过短，从 {current_length} 填充为 {target_length}（向前填充）"
            )

            padded_ts = [first_ts] * pad_count + timestamps
            padded_vals = [first_val] * pad_count + values

            return padded_ts, padded_vals

        return timestamps, values

    def _align_flange_sequences(
        self,
        all_timestamps: List[List[Any]],
        all_values: List[np.ndarray],
        result: ValidationResult,
        field: str,
    ) -> Tuple[List[List[Any]], List[np.ndarray]]:
        """
        宽松模式下对齐所有螺栓的序列长度

        以最短的为准进行截断，或用均值填充
        """
        if not all_values:
            return all_timestamps, all_values

        min_length = min(len(v) for v in all_values)
        max_length = max(len(v) for v in all_values)

        if min_length == max_length:
            return all_timestamps, all_values

        # 以最短长度为基准截断
        aligned_ts = []
        aligned_vals = []

        for i, (ts, vals) in enumerate(zip(all_timestamps, all_values)):
            if len(vals) > min_length:
                aligned_ts.append(ts[-min_length:])
                aligned_vals.append(vals[-min_length:])
            else:
                aligned_ts.append(ts)
                aligned_vals.append(vals)

        result.add_adjustment(
            f"{field}: 各螺栓序列已对齐，统一长度为 {min_length}"
        )

        return aligned_ts, aligned_vals

    # ==================== 时间解析工具 ====================

    def _parse_timestamp(self, timestamp: Any) -> Optional[datetime]:
        """
        尝试解析时间戳

        Args:
            timestamp: 时间戳（字符串或datetime对象）

        Returns:
            解析后的datetime对象，解析失败返回None
        """
        if timestamp is None:
            return None

        if isinstance(timestamp, datetime):
            return timestamp

        ts_str = str(timestamp).strip()

        for pattern, fmt in self.time_patterns:
            if re.match(pattern, ts_str):
                try:
                    return datetime.strptime(ts_str, fmt)
                except ValueError:
                    continue

        # 尝试 ISO 格式
        try:
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except ValueError:
            pass

        # 尝试 Unix 时间戳
        try:
            ts_float = float(ts_str)
            if ts_float > 0:
                if ts_float > 1e12:  # 毫秒级
                    return datetime.fromtimestamp(ts_float / 1000)
                else:  # 秒级
                    return datetime.fromtimestamp(ts_float)
        except (ValueError, OSError):
            pass

        return None


# ==================== 全局实例 ====================

_default_validator: Optional[DataValidator] = None


def get_validator() -> DataValidator:
    """获取全局数据校验器实例（单例）"""
    global _default_validator
    if _default_validator is None:
        _default_validator = DataValidator()
    return _default_validator


# ==================== 便捷函数 ====================

def validate_bolt_prediction_request(
    bolt_id: str,
    data: List[List[Any]],
    mode: ValidationMode = ValidationMode.STRICT,
) -> ValidationResult:
    """便捷函数：校验螺栓预测请求"""
    validator = get_validator()
    return validator.validate_bolt_prediction(bolt_id, data, mode)


def validate_flange_prediction_request(
    flange_id: str,
    data: List[List[List[Any]]],
    mode: ValidationMode = ValidationMode.STRICT,
) -> ValidationResult:
    """便捷函数：校验法兰面预测请求"""
    validator = get_validator()
    return validator.validate_flange_prediction(flange_id, data, mode)


def validate_risk_assessment_request(
    node_id: str,
    node_type: str,
    data: List[List[Any]],
    mode: ValidationMode = ValidationMode.STRICT,
) -> ValidationResult:
    """便捷函数：校验风险评估请求"""
    validator = get_validator()
    return validator.validate_risk_assessment(node_id, node_type, data, mode)


def format_validation_errors(result: ValidationResult) -> Dict[str, Any]:
    """
    将校验结果格式化为 API 响应格式

    Args:
        result: 校验结果

    Returns:
        格式化的错误响应字典
    """
    return {
        "success": False,
        "error_count": len(result.errors),
        "errors": [
            {
                "code": err.code,
                "message": err.message,
                "field": err.field,
                "severity": err.severity,
            }
            for err in result.errors
        ],
        "warnings": result.warnings,
        "adjustments": result.adjustments,
        "mode": result.mode.value if hasattr(result.mode, 'value') else str(result.mode),
    }
