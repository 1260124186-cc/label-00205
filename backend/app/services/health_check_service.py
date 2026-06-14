"""
健康检查服务模块

提供详细的组件健康状态检查：
- 数据库连通性
- 模型目录可写性
- 最近预测任务状态
"""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Tuple
from loguru import logger

from app.utils.config import config


class HealthCheckService:
    """
    健康检查服务类
    
    提供各个组件的健康状态检查。
    """
    
    def __init__(self):
        self.model_save_path = Path(config.get('model.save_path', './trained_models'))
        self._last_prediction_success = None
        self._last_prediction_time = None
    
    def check_all(self) -> Dict[str, Dict[str, Any]]:
        """
        检查所有组件的健康状态
        
        Returns:
            各组件健康状态字典
        """
        components = {}
        
        # 检查数据库
        db_status, db_msg = self._check_database()
        components['database'] = {
            'status': 'healthy' if db_status else 'unhealthy',
            'message': db_msg
        }
        
        # 检查模型目录
        model_status, model_msg = self._check_model_directory()
        components['model_directory'] = {
            'status': 'healthy' if model_status else 'unhealthy',
            'message': model_msg
        }
        
        # 检查最近预测任务
        pred_status, pred_msg = self._check_recent_prediction()
        components['recent_prediction'] = {
            'status': 'healthy' if pred_status else 'unhealthy',
            'message': pred_msg
        }
        
        return components
    
    def _check_database(self) -> Tuple[bool, str]:
        """
        检查数据库连通性
        
        Returns:
            (是否健康, 状态消息)
        """
        try:
            from app.utils.db_pool import db_pool
            health = db_pool.health_check()
            if health.get('healthy', False):
                return True, f"数据库连接正常，活跃连接: {health.get('active_connections', 0)}"
            else:
                return False, f"数据库连接异常: {health.get('message', 'unknown')}"
        except ImportError:
            try:
                from app.utils.database import get_db
                with get_db() as db:
                    result = db.execute("SELECT 1 as test")
                    row = result.fetchone()
                    if row and row.test == 1:
                        return True, "数据库连接正常"
                    else:
                        return False, "数据库查询失败"
            except Exception as e:
                return False, f"数据库连接失败: {str(e)}"
        except Exception as e:
            return False, f"数据库检查异常: {str(e)}"
    
    def _check_model_directory(self) -> Tuple[bool, str]:
        """
        检查模型目录可写性
        
        Returns:
            (是否健康, 状态消息)
        """
        try:
            model_path = self.model_save_path
            
            # 检查目录是否存在
            if not model_path.exists():
                try:
                    model_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    return False, f"模型目录不存在且无法创建: {str(e)}"
            
            # 检查目录是否可写
            if not os.access(str(model_path), os.W_OK):
                return False, f"模型目录不可写: {model_path}"
            
            # 尝试写入测试文件
            try:
                test_file = model_path / '.health_check_test'
                with open(test_file, 'w') as f:
                    f.write(f"health_check_{datetime.now().isoformat()}")
                
                # 读取验证
                with open(test_file, 'r') as f:
                    content = f.read()
                    if not content.startswith('health_check_'):
                        return False, "模型目录写入验证失败"
                
                # 清理测试文件
                test_file.unlink()
                
                return True, f"模型目录正常，路径: {model_path}"
            except Exception as e:
                return False, f"模型目录写入测试失败: {str(e)}"
                
        except Exception as e:
            return False, f"模型目录检查异常: {str(e)}"
    
    def _check_recent_prediction(self) -> Tuple[bool, str]:
        """
        检查最近预测任务是否成功
        
        Returns:
            (是否健康, 状态消息)
        """
        # 优先从 Prometheus 指标获取
        try:
            from app.core.prometheus import metrics
            
            # 检查是否有成功的预测任务
            bolt_success = metrics.prediction_task_success_total.get(('batch_bolt',))
            flange_success = metrics.prediction_task_success_total.get(('batch_flange',))
            
            if bolt_success > 0 or flange_success > 0:
                total = bolt_success + flange_success
                return True, f"预测任务正常，累计成功任务数: {total}"
            
        except Exception as e:
            logger.debug(f"从Prometheus指标获取预测状态失败: {e}")
        
        # 检查内存中的最近预测状态
        if self._last_prediction_success is not None and self._last_prediction_time is not None:
            time_diff = datetime.now() - self._last_prediction_time
            if time_diff < timedelta(hours=24):
                if self._last_prediction_success:
                    return True, f"最近预测任务成功，时间: {self._last_prediction_time.isoformat()}"
                else:
                    return False, f"最近预测任务失败，时间: {self._last_prediction_time.isoformat()}"
        
        # 尝试从数据库查询最近的预测记录
        try:
            from app.services.prediction.repository import PredictionRepository
            from app.utils.database import get_db, AbnormalPrediction
            
            with get_db() as db:
                from sqlalchemy import text
                query = text("""
                    SELECT create_time, status_code
                    FROM sc_abnormal_prediction
                    ORDER BY create_time DESC
                    LIMIT 1
                """)
                result = db.execute(query)
                row = result.fetchone()
                
                if row:
                    time_str = str(row.create_time) if hasattr(row, 'create_time') else 'unknown'
                    status_code = row.status_code if hasattr(row, 'status_code') else None
                    return True, f"最近预测记录存在，时间: {time_str}, 状态: {status_code}"
                else:
                    return True, "暂无预测记录（首次运行）"
                    
        except Exception as e:
            logger.debug(f"从数据库查询预测记录失败: {e}")
        
        # 如果没有任何数据，返回未知但不视为失败
        return True, "暂无预测数据（首次运行或调度未执行）"
    
    def record_prediction_result(self, success: bool) -> None:
        """
        记录预测任务结果
        
        Args:
            success: 是否成功
        """
        self._last_prediction_success = success
        self._last_prediction_time = datetime.now()


# 全局健康检查服务实例
_health_check_service = None


def get_health_check_service() -> HealthCheckService:
    """获取健康检查服务单例"""
    global _health_check_service
    if _health_check_service is None:
        _health_check_service = HealthCheckService()
    return _health_check_service
