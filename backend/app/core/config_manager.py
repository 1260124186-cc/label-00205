"""
配置持久化管理模块

提供配置的动态修改和持久化功能。

功能:
1. 配置动态更新
2. 配置持久化到文件
3. 配置版本管理
4. 配置验证

使用示例:
    from app.core.config_manager import ConfigManager
    
    manager = ConfigManager()
    manager.update('model.bolt_lstm.epochs', 100)
    manager.save()
"""

import os
import yaml
import json
import copy
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from threading import Lock
from loguru import logger


@dataclass
class ConfigChange:
    """
    配置变更记录
    
    Attributes:
        path: 配置路径
        old_value: 旧值
        new_value: 新值
        timestamp: 变更时间
        user: 操作用户
    """
    path: str
    old_value: Any
    new_value: Any
    timestamp: str
    user: str = "system"


class ConfigValidator:
    """
    配置验证器
    
    验证配置值的有效性。
    """
    
    # 配置规则定义
    RULES = {
        'database.pool_size': {
            'type': int,
            'min': 1,
            'max': 100
        },
        'model.bolt_lstm.epochs': {
            'type': int,
            'min': 1,
            'max': 1000
        },
        'model.bolt_lstm.learning_rate': {
            'type': float,
            'min': 1e-6,
            'max': 1.0
        },
        'training.batch_size': {
            'type': int,
            'min': 1,
            'max': 512
        },
        'logging.level': {
            'type': str,
            'allowed': ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        }
    }
    
    @classmethod
    def validate(cls, path: str, value: Any) -> Tuple[bool, Optional[str]]:
        """
        验证配置值
        
        Args:
            path: 配置路径
            value: 配置值
            
        Returns:
            Tuple: (是否有效, 错误信息)
        """
        if path not in cls.RULES:
            return True, None
        
        rule = cls.RULES[path]
        
        # 类型检查
        expected_type = rule.get('type')
        if expected_type and not isinstance(value, expected_type):
            try:
                value = expected_type(value)
            except (ValueError, TypeError):
                return False, f"类型错误，期望 {expected_type.__name__}"
        
        # 范围检查
        if 'min' in rule and value < rule['min']:
            return False, f"值太小，最小值为 {rule['min']}"
        
        if 'max' in rule and value > rule['max']:
            return False, f"值太大，最大值为 {rule['max']}"
        
        # 枚举检查
        if 'allowed' in rule and value not in rule['allowed']:
            return False, f"无效值，允许的值为 {rule['allowed']}"
        
        return True, None


class ConfigManager:
    """
    配置管理器
    
    管理应用配置的读取、修改和持久化。
    
    Attributes:
        config_path: 配置文件路径
        backup_dir: 备份目录
        config: 当前配置
        changes: 未保存的变更
    """
    
    _instance: Optional['ConfigManager'] = None
    _lock = Lock()
    
    def __new__(cls) -> 'ConfigManager':
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化配置管理器"""
        if getattr(self, '_initialized', False):
            return
        
        self.config_path = Path(__file__).parent.parent.parent / 'config' / 'config.yaml'
        self.backup_dir = self.config_path.parent / 'backups'
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.config: Dict[str, Any] = {}
        self.changes: List[ConfigChange] = []
        self.max_backups = 10
        
        self._load()
        self._initialized = True
        
        logger.info(f"配置管理器初始化完成: {self.config_path}")
    
    def _load(self) -> None:
        """加载配置"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            path: 配置路径（点分隔）
            default: 默认值
            
        Returns:
            配置值
        """
        keys = path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, path: str, value: Any, validate: bool = True) -> Tuple[bool, Optional[str]]:
        """
        设置配置值
        
        Args:
            path: 配置路径
            value: 新值
            validate: 是否验证
            
        Returns:
            Tuple: (是否成功, 错误信息)
        """
        # 验证
        if validate:
            is_valid, error = ConfigValidator.validate(path, value)
            if not is_valid:
                return False, error
        
        # 获取旧值
        old_value = self.get(path)
        
        # 设置新值
        keys = path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
        
        # 记录变更
        self.changes.append(ConfigChange(
            path=path,
            old_value=old_value,
            new_value=value,
            timestamp=datetime.now().isoformat()
        ))
        
        logger.debug(f"配置已更新: {path} = {value}")
        return True, None
    
    def update(self, path: str, value: Any) -> Tuple[bool, Optional[str]]:
        """set的别名"""
        return self.set(path, value)
    
    def batch_update(self, updates: Dict[str, Any]) -> Dict[str, Tuple[bool, Optional[str]]]:
        """
        批量更新配置
        
        Args:
            updates: {path: value}
            
        Returns:
            Dict: {path: (success, error)}
        """
        results = {}
        for path, value in updates.items():
            results[path] = self.set(path, value)
        return results
    
    def save(self, create_backup: bool = True) -> bool:
        """
        保存配置到文件
        
        Args:
            create_backup: 是否创建备份
            
        Returns:
            bool: 是否成功
        """
        try:
            # 创建备份
            if create_backup and self.config_path.exists():
                self._create_backup()
            
            # 保存配置
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    self.config,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False
                )
            
            # 清空变更记录
            self.changes.clear()
            
            logger.info("配置已保存")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def _create_backup(self) -> None:
        """创建配置备份"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f"config_{timestamp}.yaml"
        
        shutil.copy2(self.config_path, backup_path)
        logger.debug(f"配置备份已创建: {backup_path}")
        
        # 清理旧备份
        self._cleanup_backups()
    
    def _cleanup_backups(self) -> None:
        """清理旧备份"""
        backups = sorted(
            self.backup_dir.glob("config_*.yaml"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        for backup in backups[self.max_backups:]:
            backup.unlink()
            logger.debug(f"删除旧备份: {backup}")
    
    def restore(self, backup_name: Optional[str] = None) -> bool:
        """
        恢复配置
        
        Args:
            backup_name: 备份文件名，None则使用最新备份
            
        Returns:
            bool: 是否成功
        """
        try:
            if backup_name:
                backup_path = self.backup_dir / backup_name
            else:
                # 获取最新备份
                backups = sorted(
                    self.backup_dir.glob("config_*.yaml"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True
                )
                
                if not backups:
                    logger.error("没有可用的备份")
                    return False
                
                backup_path = backups[0]
            
            if not backup_path.exists():
                logger.error(f"备份文件不存在: {backup_path}")
                return False
            
            # 先备份当前配置
            self._create_backup()
            
            # 恢复
            shutil.copy2(backup_path, self.config_path)
            self._load()
            
            logger.info(f"配置已恢复: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"恢复配置失败: {e}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份"""
        backups = []
        
        for backup in sorted(
            self.backup_dir.glob("config_*.yaml"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        ):
            backups.append({
                'name': backup.name,
                'path': str(backup),
                'size': backup.stat().st_size,
                'modified': datetime.fromtimestamp(
                    backup.stat().st_mtime
                ).isoformat()
            })
        
        return backups
    
    def get_changes(self) -> List[Dict[str, Any]]:
        """获取未保存的变更"""
        return [
            {
                'path': c.path,
                'old_value': c.old_value,
                'new_value': c.new_value,
                'timestamp': c.timestamp
            }
            for c in self.changes
        ]
    
    def discard_changes(self) -> None:
        """丢弃未保存的变更"""
        self._load()
        self.changes.clear()
        logger.info("未保存的变更已丢弃")
    
    def export_config(self, format: str = 'yaml') -> str:
        """
        导出配置
        
        Args:
            format: 导出格式 ('yaml', 'json')
            
        Returns:
            str: 配置内容
        """
        if format == 'json':
            return json.dumps(self.config, ensure_ascii=False, indent=2)
        else:
            return yaml.dump(
                self.config,
                default_flow_style=False,
                allow_unicode=True
            )


# 全局配置管理器
config_manager = ConfigManager()
