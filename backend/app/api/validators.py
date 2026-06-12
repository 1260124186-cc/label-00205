"""
API参数校验模块

提供严格的输入数据验证功能。

功能:
1. 请求数据格式验证
2. 数据范围校验
3. 业务规则校验
4. 自定义验证器

使用示例:
    from app.api.validators import DataValidator
    
    validator = DataValidator()
    errors = validator.validate_bolt_data(data)
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import numpy as np
from loguru import logger

from app.utils.config import config


class ValidationErrorType(Enum):
    """验证错误类型"""
    REQUIRED = "required"
    TYPE_ERROR = "type_error"
    RANGE_ERROR = "range_error"
    FORMAT_ERROR = "format_error"
    LENGTH_ERROR = "length_error"
    BUSINESS_RULE = "business_rule"


@dataclass
class ValidationError:
    """
    验证错误
    
    Attributes:
        field: 字段名
        error_type: 错误类型
        message: 错误消息
        value: 错误的值
    """
    field: str
    error_type: ValidationErrorType
    message: str
    value: Any = None


@dataclass
class ValidationResult:
    """
    验证结果
    
    Attributes:
        is_valid: 是否有效
        errors: 错误列表
        warnings: 警告列表
        cleaned_data: 清洗后的数据
    """
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[str]
    cleaned_data: Optional[Dict[str, Any]] = None


class DataValidator:
    """
    数据验证器
    
    提供各种数据验证方法。
    """
    
    def __init__(self):
        """初始化验证器"""
        self.preload_thresholds = config.get('risk_assessment.preload_thresholds', {})
        self.min_preload = self.preload_thresholds.get('min_normal', 400) * 0.1
        self.max_preload = self.preload_thresholds.get('max_normal', 800) * 3
        
        # 时间格式模式
        self.time_patterns = [
            r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
            r'\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}',
            r'\d{8} \d{2}:\d{2}:\d{2}',
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
        ]
    
    def validate_bolt_prediction_request(
        self,
        bolt_id: str,
        data: List[List[Any]]
    ) -> ValidationResult:
        """
        验证螺栓预测请求
        
        Args:
            bolt_id: 螺栓ID
            data: 预紧力数据 [[时间, 预紧力], ...]
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []
        cleaned_data = {'bolt_id': bolt_id, 'data': []}
        
        # 验证螺栓ID
        if not bolt_id or not bolt_id.strip():
            errors.append(ValidationError(
                field='bolt_id',
                error_type=ValidationErrorType.REQUIRED,
                message='螺栓ID不能为空'
            ))
        elif len(bolt_id) > 50:
            errors.append(ValidationError(
                field='bolt_id',
                error_type=ValidationErrorType.LENGTH_ERROR,
                message='螺栓ID长度不能超过50个字符',
                value=bolt_id
            ))
        
        # 验证数据
        if not data:
            errors.append(ValidationError(
                field='data',
                error_type=ValidationErrorType.REQUIRED,
                message='数据不能为空'
            ))
        elif len(data) < 10:
            warnings.append(f'数据点数量较少（{len(data)}），建议提供至少100条数据以获得更准确的预测')
        elif len(data) > 10000:
            errors.append(ValidationError(
                field='data',
                error_type=ValidationErrorType.LENGTH_ERROR,
                message='数据点数量不能超过10000',
                value=len(data)
            ))
        
        # 验证每个数据点
        for i, item in enumerate(data):
            if not isinstance(item, (list, tuple)):
                errors.append(ValidationError(
                    field=f'data[{i}]',
                    error_type=ValidationErrorType.TYPE_ERROR,
                    message=f'第{i}个数据点格式错误，应为[时间, 预紧力]',
                    value=item
                ))
                continue
            
            if len(item) < 2:
                errors.append(ValidationError(
                    field=f'data[{i}]',
                    error_type=ValidationErrorType.FORMAT_ERROR,
                    message=f'第{i}个数据点缺少必要字段',
                    value=item
                ))
                continue
            
            # 验证时间格式
            timestamp = item[0]
            if not self._validate_timestamp(timestamp):
                errors.append(ValidationError(
                    field=f'data[{i}][0]',
                    error_type=ValidationErrorType.FORMAT_ERROR,
                    message=f'第{i}个数据点的时间格式无效',
                    value=timestamp
                ))
            
            # 验证预紧力值
            preload = item[1]
            preload_error = self._validate_preload_value(preload, i)
            if preload_error:
                errors.append(preload_error)
            else:
                cleaned_data['data'].append([timestamp, float(preload)])
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            cleaned_data=cleaned_data if is_valid else None
        )
    
    def validate_flange_prediction_request(
        self,
        flange_id: str,
        data: List[List[List[Any]]]
    ) -> ValidationResult:
        """
        验证法兰面预测请求
        
        Args:
            flange_id: 法兰面ID
            data: 多螺栓数据 [[[时间, 预紧力], ...], ...]
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []
        cleaned_data = {'flange_id': flange_id, 'data': []}
        
        # 验证法兰面ID
        if not flange_id or not flange_id.strip():
            errors.append(ValidationError(
                field='flange_id',
                error_type=ValidationErrorType.REQUIRED,
                message='法兰面ID不能为空'
            ))
        elif len(flange_id) > 100:
            errors.append(ValidationError(
                field='flange_id',
                error_type=ValidationErrorType.LENGTH_ERROR,
                message='法兰面ID长度不能超过100个字符',
                value=flange_id
            ))
        
        # 验证数据
        if not data:
            errors.append(ValidationError(
                field='data',
                error_type=ValidationErrorType.REQUIRED,
                message='数据不能为空'
            ))
        elif len(data) > 50:
            errors.append(ValidationError(
                field='data',
                error_type=ValidationErrorType.LENGTH_ERROR,
                message='螺栓数量不能超过50个',
                value=len(data)
            ))
        
        # 验证每个螺栓的数据
        for bolt_idx, bolt_data in enumerate(data):
            if not isinstance(bolt_data, (list, tuple)):
                errors.append(ValidationError(
                    field=f'data[{bolt_idx}]',
                    error_type=ValidationErrorType.TYPE_ERROR,
                    message=f'第{bolt_idx}个螺栓数据格式错误',
                    value=type(bolt_data).__name__
                ))
                continue
            
            cleaned_bolt_data = []
            
            for i, item in enumerate(bolt_data):
                if not isinstance(item, (list, tuple)) or len(item) < 2:
                    continue
                
                timestamp = item[0]
                preload = item[1]
                
                # 简化验证，只检查关键错误
                try:
                    cleaned_bolt_data.append([timestamp, float(preload)])
                except (ValueError, TypeError):
                    errors.append(ValidationError(
                        field=f'data[{bolt_idx}][{i}][1]',
                        error_type=ValidationErrorType.TYPE_ERROR,
                        message=f'螺栓{bolt_idx}第{i}个数据点的预紧力值无效',
                        value=preload
                    ))
            
            if cleaned_bolt_data:
                cleaned_data['data'].append(cleaned_bolt_data)
        
        if len(cleaned_data['data']) == 0 and len(data) > 0:
            errors.append(ValidationError(
                field='data',
                error_type=ValidationErrorType.BUSINESS_RULE,
                message='没有有效的螺栓数据'
            ))
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            cleaned_data=cleaned_data if is_valid else None
        )
    
    def _validate_timestamp(self, timestamp: Any) -> bool:
        """验证时间戳格式"""
        if timestamp is None:
            return False
        
        timestamp_str = str(timestamp)
        
        # 检查是否匹配任一格式
        for pattern in self.time_patterns:
            if re.match(pattern, timestamp_str):
                return True
        
        # 尝试解析
        try:
            if isinstance(timestamp, datetime):
                return True
            datetime.fromisoformat(timestamp_str.replace(' ', 'T'))
            return True
        except:
            pass
        
        return False
    
    def _validate_preload_value(
        self,
        value: Any,
        index: int
    ) -> Optional[ValidationError]:
        """验证预紧力值"""
        try:
            preload = float(value)
        except (ValueError, TypeError):
            return ValidationError(
                field=f'data[{index}][1]',
                error_type=ValidationErrorType.TYPE_ERROR,
                message=f'第{index}个数据点的预紧力值必须是数字',
                value=value
            )
        
        if preload < self.min_preload:
            return ValidationError(
                field=f'data[{index}][1]',
                error_type=ValidationErrorType.RANGE_ERROR,
                message=f'第{index}个数据点的预紧力值过小（{preload} < {self.min_preload}）',
                value=preload
            )
        
        if preload > self.max_preload:
            return ValidationError(
                field=f'data[{index}][1]',
                error_type=ValidationErrorType.RANGE_ERROR,
                message=f'第{index}个数据点的预紧力值过大（{preload} > {self.max_preload}）',
                value=preload
            )
        
        if np.isnan(preload) or np.isinf(preload):
            return ValidationError(
                field=f'data[{index}][1]',
                error_type=ValidationErrorType.TYPE_ERROR,
                message=f'第{index}个数据点的预紧力值无效（NaN或Inf）',
                value=preload
            )
        
        return None
    
    def validate_risk_assessment_request(
        self,
        node_id: str,
        node_type: str,
        data: List[List[Any]]
    ) -> ValidationResult:
        """验证风险评估请求"""
        errors = []
        warnings = []
        
        # 验证节点类型
        valid_types = ['bolt', 'flange', '螺栓', '法兰面']
        if node_type not in valid_types:
            errors.append(ValidationError(
                field='node_type',
                error_type=ValidationErrorType.BUSINESS_RULE,
                message=f'节点类型无效，应为: {", ".join(valid_types)}',
                value=node_type
            ))
        
        # 验证节点ID
        if not node_id or not node_id.strip():
            errors.append(ValidationError(
                field='node_id',
                error_type=ValidationErrorType.REQUIRED,
                message='节点ID不能为空'
            ))
        
        # 验证数据
        if not data:
            errors.append(ValidationError(
                field='data',
                error_type=ValidationErrorType.REQUIRED,
                message='数据不能为空'
            ))
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )


def validate_request(validator_func):
    """
    请求验证装饰器
    
    Usage:
        @validate_request
        async def predict_bolt(request: BoltPredictionRequest):
            pass
    """
    from functools import wraps
    from fastapi import HTTPException
    
    @wraps(validator_func)
    async def wrapper(*args, **kwargs):
        try:
            return await validator_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"请求验证失败: {e}")
            raise HTTPException(status_code=400, detail=str(e))
    
    return wrapper
