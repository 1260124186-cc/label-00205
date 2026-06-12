"""
模型版本管理模块

实现模型的版本控制、回滚和管理功能。

功能:
1. 模型版本记录
2. 模型回滚
3. 版本比较
4. 自动清理旧版本

使用示例:
    from app.core.model_version import ModelVersionManager
    
    manager = ModelVersionManager()
    manager.save_version(model, 'bolt_B001', metrics={'accuracy': 0.95})
    manager.rollback('bolt_B001', version='v1.0.0')
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import hashlib
from loguru import logger

from app.utils.config import config


@dataclass
class ModelVersion:
    """
    模型版本信息
    
    Attributes:
        version: 版本号
        model_id: 模型标识
        model_type: 模型类型 (bolt/flange)
        created_at: 创建时间
        file_path: 模型文件路径
        file_hash: 文件哈希
        metrics: 训练指标
        config: 训练配置
        is_active: 是否为当前活动版本
        description: 版本描述
    """
    version: str
    model_id: str
    model_type: str
    created_at: str
    file_path: str
    file_hash: str
    metrics: Dict[str, float]
    config: Dict[str, Any]
    is_active: bool = False
    description: str = ""


class ModelVersionManager:
    """
    模型版本管理器
    
    Attributes:
        base_path: 模型存储基础路径
        versions_file: 版本记录文件
        max_versions: 最大保留版本数
    """
    
    def __init__(
        self,
        base_path: Optional[str] = None,
        max_versions: int = 10
    ):
        """
        初始化版本管理器
        
        Args:
            base_path: 模型存储路径
            max_versions: 最大保留版本数
        """
        self.base_path = Path(base_path or config.get('model.save_path', './trained_models'))
        self.versions_path = self.base_path / 'versions'
        self.versions_file = self.base_path / 'model_versions.json'
        self.max_versions = max_versions
        
        # 确保目录存在
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.versions_path.mkdir(parents=True, exist_ok=True)
        
        # 加载版本记录
        self._versions: Dict[str, List[ModelVersion]] = self._load_versions()
        
        logger.info(f"模型版本管理器初始化完成: {self.base_path}")
    
    def _load_versions(self) -> Dict[str, List[ModelVersion]]:
        """加载版本记录"""
        if self.versions_file.exists():
            try:
                with open(self.versions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                versions = {}
                for model_id, version_list in data.items():
                    versions[model_id] = [
                        ModelVersion(**v) for v in version_list
                    ]
                return versions
                
            except Exception as e:
                logger.error(f"加载版本记录失败: {e}")
                return {}
        return {}
    
    def _save_versions(self) -> None:
        """保存版本记录"""
        try:
            data = {}
            for model_id, versions in self._versions.items():
                data[model_id] = [asdict(v) for v in versions]
            
            with open(self.versions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"保存版本记录失败: {e}")
    
    def _calculate_hash(self, file_path: Path) -> str:
        """计算文件哈希"""
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _generate_version(self, model_id: str) -> str:
        """生成新版本号"""
        if model_id not in self._versions or not self._versions[model_id]:
            return "v1.0.0"
        
        # 获取最新版本
        latest = self._versions[model_id][-1]
        parts = latest.version.replace('v', '').split('.')
        
        # 增加补丁版本
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        patch += 1
        
        return f"v{major}.{minor}.{patch}"
    
    def save_version(
        self,
        model_file: str,
        model_id: str,
        model_type: str,
        metrics: Optional[Dict[str, float]] = None,
        training_config: Optional[Dict[str, Any]] = None,
        description: str = ""
    ) -> ModelVersion:
        """
        保存模型版本
        
        Args:
            model_file: 原始模型文件路径
            model_id: 模型标识
            model_type: 模型类型
            metrics: 训练指标
            training_config: 训练配置
            description: 版本描述
            
        Returns:
            ModelVersion: 版本信息
        """
        model_path = Path(model_file)
        if not model_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {model_file}")
        
        # 生成版本号
        version = self._generate_version(model_id)
        
        # 创建版本目录
        version_dir = self.versions_path / model_id / version
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制模型文件
        versioned_file = version_dir / model_path.name
        shutil.copy2(model_path, versioned_file)
        
        # 计算哈希
        file_hash = self._calculate_hash(versioned_file)
        
        # 创建版本记录
        model_version = ModelVersion(
            version=version,
            model_id=model_id,
            model_type=model_type,
            created_at=datetime.now().isoformat(),
            file_path=str(versioned_file),
            file_hash=file_hash,
            metrics=metrics or {},
            config=training_config or {},
            is_active=True,
            description=description
        )
        
        # 设置之前的版本为非活动
        if model_id in self._versions:
            for v in self._versions[model_id]:
                v.is_active = False
        else:
            self._versions[model_id] = []
        
        self._versions[model_id].append(model_version)
        
        # 清理旧版本
        self._cleanup_old_versions(model_id)
        
        # 保存记录
        self._save_versions()
        
        logger.info(f"模型版本已保存: {model_id} {version}")
        
        return model_version
    
    def _cleanup_old_versions(self, model_id: str) -> None:
        """清理旧版本"""
        if model_id not in self._versions:
            return
        
        versions = self._versions[model_id]
        
        while len(versions) > self.max_versions:
            # 删除最旧的非活动版本
            oldest = versions[0]
            
            # 删除文件
            if os.path.exists(oldest.file_path):
                try:
                    os.remove(oldest.file_path)
                    # 尝试删除空目录
                    parent = Path(oldest.file_path).parent
                    if parent.exists() and not any(parent.iterdir()):
                        parent.rmdir()
                except Exception as e:
                    logger.warning(f"删除旧版本文件失败: {e}")
            
            versions.pop(0)
            logger.debug(f"清理旧版本: {model_id} {oldest.version}")
    
    def get_version(
        self,
        model_id: str,
        version: Optional[str] = None
    ) -> Optional[ModelVersion]:
        """
        获取模型版本
        
        Args:
            model_id: 模型标识
            version: 版本号，None则返回当前活动版本
            
        Returns:
            ModelVersion: 版本信息
        """
        if model_id not in self._versions:
            return None
        
        versions = self._versions[model_id]
        
        if version is None:
            # 返回活动版本
            for v in reversed(versions):
                if v.is_active:
                    return v
            # 没有活动版本，返回最新
            return versions[-1] if versions else None
        
        # 查找指定版本
        for v in versions:
            if v.version == version:
                return v
        
        return None
    
    def get_all_versions(self, model_id: str) -> List[ModelVersion]:
        """获取模型的所有版本"""
        return self._versions.get(model_id, [])
    
    def rollback(
        self,
        model_id: str,
        version: str
    ) -> Optional[ModelVersion]:
        """
        回滚到指定版本
        
        Args:
            model_id: 模型标识
            version: 目标版本号
            
        Returns:
            ModelVersion: 回滚后的版本信息
        """
        target = self.get_version(model_id, version)
        
        if target is None:
            logger.error(f"版本不存在: {model_id} {version}")
            return None
        
        if not os.path.exists(target.file_path):
            logger.error(f"版本文件不存在: {target.file_path}")
            return None
        
        # 复制到当前模型位置
        current_path = self.base_path / f"{target.model_type}_{model_id}.pt"
        shutil.copy2(target.file_path, current_path)
        
        # 更新活动状态
        for v in self._versions[model_id]:
            v.is_active = (v.version == version)
        
        self._save_versions()
        
        logger.info(f"模型已回滚: {model_id} -> {version}")
        
        return target
    
    def compare_versions(
        self,
        model_id: str,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """
        比较两个版本
        
        Args:
            model_id: 模型标识
            version1: 版本1
            version2: 版本2
            
        Returns:
            Dict: 比较结果
        """
        v1 = self.get_version(model_id, version1)
        v2 = self.get_version(model_id, version2)
        
        if v1 is None or v2 is None:
            return {'error': '版本不存在'}
        
        # 比较指标
        metrics_diff = {}
        all_metrics = set(v1.metrics.keys()) | set(v2.metrics.keys())
        
        for metric in all_metrics:
            val1 = v1.metrics.get(metric, 0)
            val2 = v2.metrics.get(metric, 0)
            metrics_diff[metric] = {
                version1: val1,
                version2: val2,
                'diff': val2 - val1,
                'improved': val2 > val1
            }
        
        return {
            'model_id': model_id,
            'version1': version1,
            'version2': version2,
            'metrics_comparison': metrics_diff,
            'config_diff': {
                version1: v1.config,
                version2: v2.config
            }
        }
    
    def get_best_version(
        self,
        model_id: str,
        metric: str = 'val_acc'
    ) -> Optional[ModelVersion]:
        """
        获取最佳版本
        
        Args:
            model_id: 模型标识
            metric: 评价指标
            
        Returns:
            ModelVersion: 最佳版本
        """
        versions = self.get_all_versions(model_id)
        
        if not versions:
            return None
        
        best = max(
            versions,
            key=lambda v: v.metrics.get(metric, 0)
        )
        
        return best
    
    def delete_version(self, model_id: str, version: str) -> bool:
        """
        删除指定版本
        
        Args:
            model_id: 模型标识
            version: 版本号
            
        Returns:
            bool: 是否成功
        """
        if model_id not in self._versions:
            return False
        
        versions = self._versions[model_id]
        
        for i, v in enumerate(versions):
            if v.version == version:
                # 不能删除活动版本
                if v.is_active:
                    logger.warning("不能删除活动版本")
                    return False
                
                # 删除文件
                if os.path.exists(v.file_path):
                    os.remove(v.file_path)
                
                versions.pop(i)
                self._save_versions()
                
                logger.info(f"版本已删除: {model_id} {version}")
                return True
        
        return False


# 全局版本管理器
version_manager = ModelVersionManager()
