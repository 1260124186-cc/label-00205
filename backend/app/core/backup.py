"""
自动备份和恢复模块

提供系统数据和模型的自动备份功能。

功能:
1. 数据库备份
2. 模型文件备份
3. 配置文件备份
4. 自动恢复

使用示例:
    from app.core.backup import BackupManager
    
    manager = BackupManager()
    manager.create_backup()
    manager.restore_latest()
"""

import os
import shutil
import gzip
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import subprocess
from loguru import logger

from app.utils.config import config


@dataclass
class BackupInfo:
    """
    备份信息
    
    Attributes:
        backup_id: 备份ID
        backup_type: 备份类型
        created_at: 创建时间
        size_bytes: 文件大小
        path: 备份路径
        components: 包含的组件
    """
    backup_id: str
    backup_type: str
    created_at: str
    size_bytes: int
    path: str
    components: List[str]


class BackupManager:
    """
    备份管理器
    
    管理系统各组件的备份和恢复。
    
    Attributes:
        backup_dir: 备份目录
        max_backups: 最大备份数
        compress: 是否压缩
    """
    
    def __init__(
        self,
        backup_dir: Optional[str] = None,
        max_backups: int = 10,
        compress: bool = True
    ):
        """
        初始化备份管理器
        
        Args:
            backup_dir: 备份目录
            max_backups: 最大保留备份数
            compress: 是否压缩备份
        """
        self.backup_dir = Path(backup_dir or './backups')
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_backups = max_backups
        self.compress = compress
        
        # 项目路径
        self.project_root = Path(__file__).parent.parent.parent
        self.models_dir = self.project_root / 'trained_models'
        self.config_dir = self.project_root / 'config'
        self.logs_dir = self.project_root / 'logs'
        
        logger.info(f"备份管理器初始化: backup_dir={self.backup_dir}")
    
    def _generate_backup_id(self) -> str:
        """生成备份ID"""
        return datetime.now().strftime('backup_%Y%m%d_%H%M%S')
    
    def create_backup(
        self,
        include_models: bool = True,
        include_config: bool = True,
        include_logs: bool = False,
        include_database: bool = True
    ) -> Optional[BackupInfo]:
        """
        创建完整备份
        
        Args:
            include_models: 包含模型文件
            include_config: 包含配置文件
            include_logs: 包含日志文件
            include_database: 包含数据库
            
        Returns:
            BackupInfo: 备份信息
        """
        backup_id = self._generate_backup_id()
        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(parents=True, exist_ok=True)
        
        components = []
        
        try:
            # 备份模型
            if include_models and self.models_dir.exists():
                self._backup_directory(self.models_dir, backup_path / 'models')
                components.append('models')
            
            # 备份配置
            if include_config and self.config_dir.exists():
                self._backup_directory(self.config_dir, backup_path / 'config')
                components.append('config')
            
            # 备份日志
            if include_logs and self.logs_dir.exists():
                self._backup_directory(self.logs_dir, backup_path / 'logs')
                components.append('logs')
            
            # 备份数据库
            if include_database:
                db_backup = self._backup_database(backup_path)
                if db_backup:
                    components.append('database')
            
            # 保存元数据
            metadata = {
                'backup_id': backup_id,
                'created_at': datetime.now().isoformat(),
                'components': components
            }
            
            with open(backup_path / 'metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # 压缩备份
            if self.compress:
                archive_path = self._compress_backup(backup_path)
                shutil.rmtree(backup_path)
                final_path = archive_path
            else:
                final_path = backup_path
            
            # 清理旧备份
            self._cleanup_old_backups()
            
            # 计算大小
            if final_path.is_file():
                size = final_path.stat().st_size
            else:
                size = sum(f.stat().st_size for f in final_path.rglob('*') if f.is_file())
            
            backup_info = BackupInfo(
                backup_id=backup_id,
                backup_type='full',
                created_at=datetime.now().isoformat(),
                size_bytes=size,
                path=str(final_path),
                components=components
            )
            
            logger.info(f"备份创建成功: {backup_id}, 大小: {size / (1024*1024):.2f}MB")
            
            return backup_info
            
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            if backup_path.exists():
                shutil.rmtree(backup_path)
            return None
    
    def _backup_directory(self, src: Path, dest: Path) -> None:
        """备份目录"""
        if src.exists():
            shutil.copytree(src, dest, dirs_exist_ok=True)
    
    def _backup_database(self, backup_path: Path) -> bool:
        """
        备份数据库
        
        使用mysqldump备份MySQL数据库。
        """
        db_config = config.get('database', {})
        
        host = db_config.get('host', '127.0.0.1')
        port = db_config.get('port', 3306)
        user = db_config.get('user', 'root')
        password = db_config.get('password', '')
        database = db_config.get('database', 'bolt_preload')
        
        dump_file = backup_path / 'database.sql'
        
        try:
            cmd = [
                'mysqldump',
                f'-h{host}',
                f'-P{port}',
                f'-u{user}',
            ]
            
            if password:
                cmd.append(f'-p{password}')
            
            cmd.append(database)
            
            with open(dump_file, 'w') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    timeout=300
                )
            
            if result.returncode == 0:
                logger.debug("数据库备份成功")
                return True
            else:
                logger.warning(f"数据库备份失败: {result.stderr.decode()}")
                return False
                
        except FileNotFoundError:
            logger.warning("mysqldump未找到，跳过数据库备份")
            return False
        except Exception as e:
            logger.warning(f"数据库备份异常: {e}")
            return False
    
    def _compress_backup(self, backup_path: Path) -> Path:
        """压缩备份"""
        archive_path = backup_path.with_suffix('.tar.gz')
        
        shutil.make_archive(
            str(backup_path),
            'gztar',
            root_dir=backup_path.parent,
            base_dir=backup_path.name
        )
        
        return archive_path
    
    def _cleanup_old_backups(self) -> None:
        """清理旧备份"""
        # 获取所有备份
        backups = []
        
        for item in self.backup_dir.iterdir():
            if item.name.startswith('backup_'):
                backups.append(item)
        
        # 按修改时间排序
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # 删除超出数量的备份
        for backup in backups[self.max_backups:]:
            if backup.is_file():
                backup.unlink()
            else:
                shutil.rmtree(backup)
            logger.debug(f"删除旧备份: {backup.name}")
    
    def list_backups(self) -> List[BackupInfo]:
        """列出所有备份"""
        backups = []
        
        for item in sorted(
            self.backup_dir.iterdir(),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        ):
            if not item.name.startswith('backup_'):
                continue
            
            try:
                if item.is_file() and item.suffix == '.gz':
                    # 压缩备份
                    backups.append(BackupInfo(
                        backup_id=item.stem.replace('.tar', ''),
                        backup_type='compressed',
                        created_at=datetime.fromtimestamp(
                            item.stat().st_mtime
                        ).isoformat(),
                        size_bytes=item.stat().st_size,
                        path=str(item),
                        components=[]
                    ))
                elif item.is_dir():
                    # 目录备份
                    metadata_file = item / 'metadata.json'
                    if metadata_file.exists():
                        with open(metadata_file) as f:
                            metadata = json.load(f)
                        
                        backups.append(BackupInfo(
                            backup_id=metadata.get('backup_id', item.name),
                            backup_type='directory',
                            created_at=metadata.get('created_at', ''),
                            size_bytes=sum(
                                f.stat().st_size 
                                for f in item.rglob('*') if f.is_file()
                            ),
                            path=str(item),
                            components=metadata.get('components', [])
                        ))
            except Exception as e:
                logger.warning(f"读取备份信息失败 {item}: {e}")
        
        return backups
    
    def restore_backup(
        self,
        backup_id: Optional[str] = None,
        restore_models: bool = True,
        restore_config: bool = True,
        restore_database: bool = False
    ) -> bool:
        """
        恢复备份
        
        Args:
            backup_id: 备份ID，None则使用最新备份
            restore_models: 恢复模型
            restore_config: 恢复配置
            restore_database: 恢复数据库
            
        Returns:
            bool: 是否成功
        """
        # 查找备份
        backups = self.list_backups()
        
        if not backups:
            logger.error("没有可用的备份")
            return False
        
        if backup_id:
            backup = next((b for b in backups if b.backup_id == backup_id), None)
        else:
            backup = backups[0]  # 最新备份
        
        if not backup:
            logger.error(f"备份不存在: {backup_id}")
            return False
        
        backup_path = Path(backup.path)
        
        try:
            # 解压（如果需要）
            if backup_path.suffix == '.gz':
                temp_dir = self.backup_dir / 'temp_restore'
                shutil.unpack_archive(backup_path, temp_dir)
                backup_path = temp_dir / backup_path.stem.replace('.tar', '')
            
            # 恢复模型
            if restore_models:
                models_backup = backup_path / 'models'
                if models_backup.exists():
                    if self.models_dir.exists():
                        shutil.rmtree(self.models_dir)
                    shutil.copytree(models_backup, self.models_dir)
                    logger.info("模型已恢复")
            
            # 恢复配置
            if restore_config:
                config_backup = backup_path / 'config'
                if config_backup.exists():
                    if self.config_dir.exists():
                        shutil.rmtree(self.config_dir)
                    shutil.copytree(config_backup, self.config_dir)
                    logger.info("配置已恢复")
            
            # 恢复数据库
            if restore_database:
                db_file = backup_path / 'database.sql'
                if db_file.exists():
                    self._restore_database(db_file)
            
            # 清理临时目录
            temp_dir = self.backup_dir / 'temp_restore'
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            
            logger.info(f"备份恢复成功: {backup.backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            return False
    
    def _restore_database(self, dump_file: Path) -> bool:
        """恢复数据库"""
        db_config = config.get('database', {})
        
        host = db_config.get('host', '127.0.0.1')
        port = db_config.get('port', 3306)
        user = db_config.get('user', 'root')
        password = db_config.get('password', '')
        database = db_config.get('database', 'bolt_preload')
        
        try:
            cmd = [
                'mysql',
                f'-h{host}',
                f'-P{port}',
                f'-u{user}',
            ]
            
            if password:
                cmd.append(f'-p{password}')
            
            cmd.append(database)
            
            with open(dump_file, 'r') as f:
                result = subprocess.run(
                    cmd,
                    stdin=f,
                    stderr=subprocess.PIPE,
                    timeout=300
                )
            
            if result.returncode == 0:
                logger.info("数据库恢复成功")
                return True
            else:
                logger.error(f"数据库恢复失败: {result.stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"数据库恢复异常: {e}")
            return False
    
    def restore_latest(self) -> bool:
        """恢复最新备份"""
        return self.restore_backup(backup_id=None)


# 全局备份管理器
backup_manager = BackupManager()
