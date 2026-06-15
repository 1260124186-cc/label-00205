import json
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any

from loguru import logger

from app.utils.database import get_db, StrategyConfig, StrategyAuditLog
from app.utils.config import config


_strategy_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = threading.Lock()
_cache_loaded = False


def _cache_key(scope: str, node_type: Optional[str], node_id: Optional[str]) -> str:
    if scope == 'global':
        return 'global'
    return f"{scope}:{node_type or ''}:{node_id or ''}"


def _ensure_default_global():
    with get_db() as db:
        if db is None:
            return
        exists = db.query(StrategyConfig).filter(
            StrategyConfig.scope == 'global',
            StrategyConfig.is_active == True,
        ).first()
        if not exists:
            row = StrategyConfig(
                scope='global',
                strategy_type=1,
                confidence_threshold=0.7,
                false_positive_threshold=0.05,
                false_negative_threshold=None,
                version=1,
                is_active=True,
                description='默认全局策略：应报尽报',
            )
            db.add(row)
            db.flush()


def load_cache():
    global _cache_loaded, _strategy_cache
    with _cache_lock:
        _ensure_default_global()
        with get_db() as db:
            if db is None:
                return
            rows = db.query(StrategyConfig).filter(
                StrategyConfig.is_active == True,
            ).all()
            new_cache = {}
            for r in rows:
                key = _cache_key(r.scope, r.node_type, r.node_id)
                new_cache[key] = {
                    'id': r.id,
                    'scope': r.scope,
                    'node_type': r.node_type,
                    'node_id': r.node_id,
                    'strategy_type': r.strategy_type,
                    'confidence_threshold': r.confidence_threshold,
                    'false_positive_threshold': r.false_positive_threshold,
                    'false_negative_threshold': r.false_negative_threshold,
                    'version': r.version,
                    'description': r.description,
                    'operator_id': r.operator_id,
                    'operator_name': r.operator_name,
                    'update_time': r.update_time.isoformat() if r.update_time else None,
                }
            _strategy_cache = new_cache
            _cache_loaded = True
            logger.info(f"策略缓存已加载, 共{len(_strategy_cache)}条")


def get_effective_strategy(
    node_type: Optional[str] = None,
    node_id: Optional[str] = None,
) -> Dict[str, Any]:
    global _cache_loaded
    if not _cache_loaded:
        load_cache()

    with _cache_lock:
        if node_type and node_id:
            key = _cache_key(node_type, node_type, node_id)
            if key in _strategy_cache:
                return _strategy_cache[key]

        global_cfg = _strategy_cache.get('global', {
            'scope': 'global',
            'strategy_type': 1,
            'confidence_threshold': 0.7,
            'false_positive_threshold': 0.05,
            'false_negative_threshold': None,
            'version': 1,
        })
        return global_cfg


class StrategyConfigService:

    def get_effective(
        self,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return get_effective_strategy(node_type, node_id)

    def list_configs(
        self,
        scope: Optional[str] = None,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        try:
            with get_db() as db:
                if db is None:
                    return []
                query = db.query(StrategyConfig)
                if scope:
                    query = query.filter(StrategyConfig.scope == scope)
                if node_type:
                    query = query.filter(StrategyConfig.node_type == node_type)
                if node_id:
                    query = query.filter(StrategyConfig.node_id == node_id)
                if is_active is not None:
                    query = query.filter(StrategyConfig.is_active == is_active)

                rows = query.order_by(
                    StrategyConfig.scope,
                    StrategyConfig.node_type,
                    StrategyConfig.node_id,
                    StrategyConfig.version.desc(),
                ).limit(limit).all()

                return [self._to_dict(r) for r in rows]
        except Exception as e:
            logger.error(f"查询策略配置失败: {e}")
            return []

    def get_config(self, config_id: int) -> Optional[Dict[str, Any]]:
        try:
            with get_db() as db:
                if db is None:
                    return None
                r = db.query(StrategyConfig).filter(
                    StrategyConfig.id == config_id,
                ).first()
                if r is None:
                    return None
                return self._to_dict(r)
        except Exception as e:
            logger.error(f"获取策略配置失败: {e}")
            return None

    def update_config(
        self,
        scope: str = 'global',
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
        strategy_type: Optional[int] = None,
        confidence_threshold: Optional[float] = None,
        false_positive_threshold: Optional[float] = None,
        false_negative_threshold: Optional[float] = None,
        description: Optional[str] = None,
        operator_id: Optional[str] = None,
        operator_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            with get_db() as db:
                if db is None:
                    return None

                active = db.query(StrategyConfig).filter(
                    StrategyConfig.scope == scope,
                    StrategyConfig.node_type == (node_type if scope != 'global' else None),
                    StrategyConfig.node_id == (node_id if scope != 'global' else None),
                    StrategyConfig.is_active == True,
                ).first()

                if active is None:
                    return self._create_config(
                        db, scope, node_type, node_id, strategy_type,
                        confidence_threshold, false_positive_threshold,
                        false_negative_threshold, description,
                        operator_id, operator_name,
                    )

                old_value = self._to_dict(active)
                old_version = active.version

                new_strategy_type = strategy_type if strategy_type is not None else active.strategy_type
                new_confidence = confidence_threshold if confidence_threshold is not None else active.confidence_threshold
                new_fp = false_positive_threshold if false_positive_threshold is not None else active.false_positive_threshold
                new_fn = false_negative_threshold if false_negative_threshold is not None else active.false_negative_threshold

                if new_strategy_type == 1:
                    new_fp = new_fp if new_fp is not None else 0.05
                    new_fn = None
                else:
                    new_fn = new_fn if new_fn is not None else 0.10
                    new_fp = None

                active.is_active = False
                db.flush()

                new_row = StrategyConfig(
                    scope=scope,
                    node_type=node_type if scope != 'global' else None,
                    node_id=node_id if scope != 'global' else None,
                    strategy_type=new_strategy_type,
                    confidence_threshold=new_confidence,
                    false_positive_threshold=new_fp,
                    false_negative_threshold=new_fn,
                    version=old_version + 1,
                    is_active=True,
                    description=description or f"更新策略: v{old_version} -> v{old_version + 1}",
                    operator_id=operator_id,
                    operator_name=operator_name,
                )
                db.add(new_row)
                db.flush()

                self._write_audit(
                    db, new_row.id, scope, node_type, node_id,
                    action='update',
                    old_value=old_value,
                    new_value=self._to_dict(new_row),
                    version_before=old_version,
                    version_after=new_row.version,
                    change_summary=description or f"策略更新 v{old_version} -> v{new_row.version}",
                    operator_id=operator_id,
                    operator_name=operator_name,
                )

                load_cache()
                return self._to_dict(new_row)

        except Exception as e:
            logger.error(f"更新策略配置失败: {e}")
            return None

    def _create_config(
        self, db, scope, node_type, node_id,
        strategy_type, confidence_threshold,
        false_positive_threshold, false_negative_threshold,
        description, operator_id, operator_name,
    ):
        st = strategy_type or 1
        ct = confidence_threshold or (0.7 if st == 1 else 0.95)
        fp = false_positive_threshold if st == 1 else None
        fn = false_negative_threshold if st == 2 else None
        if fp is None and st == 1:
            fp = 0.05
        if fn is None and st == 2:
            fn = 0.10

        row = StrategyConfig(
            scope=scope,
            node_type=node_type if scope != 'global' else None,
            node_id=node_id if scope != 'global' else None,
            strategy_type=st,
            confidence_threshold=ct,
            false_positive_threshold=fp,
            false_negative_threshold=fn,
            version=1,
            is_active=True,
            description=description or '新建策略配置',
            operator_id=operator_id,
            operator_name=operator_name,
        )
        db.add(row)
        db.flush()

        self._write_audit(
            db, row.id, scope, node_type, node_id,
            action='create',
            old_value=None,
            new_value=self._to_dict(row),
            version_before=None,
            version_after=1,
            change_summary=description or '新建策略配置',
            operator_id=operator_id,
            operator_name=operator_name,
        )

        load_cache()
        return self._to_dict(row)

    def rollback(
        self,
        target_version: int,
        scope: str = 'global',
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
        operator_id: Optional[str] = None,
        operator_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            with get_db() as db:
                if db is None:
                    return None

                target = db.query(StrategyConfig).filter(
                    StrategyConfig.scope == scope,
                    StrategyConfig.node_type == (node_type if scope != 'global' else None),
                    StrategyConfig.node_id == (node_id if scope != 'global' else None),
                    StrategyConfig.version == target_version,
                ).first()

                if target is None:
                    logger.error(f"回滚目标版本不存在: {scope}/{node_type}/{node_id} v{target_version}")
                    return None

                current = db.query(StrategyConfig).filter(
                    StrategyConfig.scope == scope,
                    StrategyConfig.node_type == (node_type if scope != 'global' else None),
                    StrategyConfig.node_id == (node_id if scope != 'global' else None),
                    StrategyConfig.is_active == True,
                ).first()

                if current and current.version == target_version:
                    logger.warning(f"目标版本已是当前版本: v{target_version}")
                    return self._to_dict(current)

                old_value = self._to_dict(current) if current else None
                old_version = current.version if current else None

                if current:
                    current.is_active = False
                    db.flush()

                new_row = StrategyConfig(
                    scope=target.scope,
                    node_type=target.node_type,
                    node_id=target.node_id,
                    strategy_type=target.strategy_type,
                    confidence_threshold=target.confidence_threshold,
                    false_positive_threshold=target.false_positive_threshold,
                    false_negative_threshold=target.false_negative_threshold,
                    version=(current.version if current else target.version) + 1,
                    is_active=True,
                    description=f"回滚到 v{target_version} 的配置",
                    operator_id=operator_id,
                    operator_name=operator_name,
                )
                db.add(new_row)
                db.flush()

                self._write_audit(
                    db, new_row.id, scope, node_type, node_id,
                    action='rollback',
                    old_value=old_value,
                    new_value=self._to_dict(new_row),
                    version_before=old_version,
                    version_after=new_row.version,
                    change_summary=f"回滚到 v{target_version} 的配置",
                    operator_id=operator_id,
                    operator_name=operator_name,
                )

                load_cache()
                logger.info(
                    f"策略回滚成功: {scope}/{node_type}/{node_id} "
                    f"v{old_version} -> v{new_row.version} (基于v{target_version})"
                )
                return self._to_dict(new_row)

        except Exception as e:
            logger.error(f"策略回滚失败: {e}")
            return None

    def get_audit_logs(
        self,
        scope: Optional[str] = None,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
        action: Optional[str] = None,
        operator_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        try:
            with get_db() as db:
                if db is None:
                    return []
                query = db.query(StrategyAuditLog)
                if scope:
                    query = query.filter(StrategyAuditLog.scope == scope)
                if node_type:
                    query = query.filter(StrategyAuditLog.node_type == node_type)
                if node_id:
                    query = query.filter(StrategyAuditLog.node_id == node_id)
                if action:
                    query = query.filter(StrategyAuditLog.action == action)
                if operator_id:
                    query = query.filter(StrategyAuditLog.operator_id == operator_id)

                rows = query.order_by(
                    StrategyAuditLog.create_time.desc(),
                ).offset(offset).limit(limit).all()

                return [
                    {
                        'id': r.id,
                        'config_id': r.config_id,
                        'scope': r.scope,
                        'node_type': r.node_type,
                        'node_id': r.node_id,
                        'action': r.action,
                        'old_value': json.loads(r.old_value) if r.old_value else None,
                        'new_value': json.loads(r.new_value) if r.new_value else None,
                        'version_before': r.version_before,
                        'version_after': r.version_after,
                        'change_summary': r.change_summary,
                        'operator_id': r.operator_id,
                        'operator_name': r.operator_name,
                        'create_time': r.create_time.isoformat() if r.create_time else None,
                    }
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"查询审计日志失败: {e}")
            return []

    def delete_node_override(
        self,
        node_type: str,
        node_id: str,
        operator_id: Optional[str] = None,
        operator_name: Optional[str] = None,
    ) -> bool:
        try:
            with get_db() as db:
                if db is None:
                    return False

                rows = db.query(StrategyConfig).filter(
                    StrategyConfig.scope != 'global',
                    StrategyConfig.node_type == node_type,
                    StrategyConfig.node_id == node_id,
                ).all()

                if not rows:
                    return False

                for r in rows:
                    self._write_audit(
                        db, r.id, r.scope, r.node_type, r.node_id,
                        action='delete',
                        old_value=self._to_dict(r),
                        new_value=None,
                        version_before=r.version,
                        version_after=None,
                        change_summary=f"删除节点级覆盖策略: {node_type}/{node_id}",
                        operator_id=operator_id,
                        operator_name=operator_name,
                    )

                for r in rows:
                    db.delete(r)

                load_cache()
                logger.info(f"已删除节点覆盖策略: {node_type}/{node_id}")
                return True

        except Exception as e:
            logger.error(f"删除节点覆盖策略失败: {e}")
            return False

    @staticmethod
    def _to_dict(r: StrategyConfig) -> Dict[str, Any]:
        return {
            'id': r.id,
            'scope': r.scope,
            'node_type': r.node_type,
            'node_id': r.node_id,
            'strategy_type': r.strategy_type,
            'confidence_threshold': r.confidence_threshold,
            'false_positive_threshold': r.false_positive_threshold,
            'false_negative_threshold': r.false_negative_threshold,
            'version': r.version,
            'is_active': r.is_active,
            'description': r.description,
            'operator_id': r.operator_id,
            'operator_name': r.operator_name,
            'create_time': r.create_time.isoformat() if r.create_time else None,
            'update_time': r.update_time.isoformat() if r.update_time else None,
        }

    @staticmethod
    def _write_audit(
        db, config_id, scope, node_type, node_id,
        action, old_value, new_value,
        version_before, version_after,
        change_summary, operator_id, operator_name,
    ):
        log = StrategyAuditLog(
            config_id=config_id,
            scope=scope,
            node_type=node_type,
            node_id=node_id,
            action=action,
            old_value=json.dumps(old_value, ensure_ascii=False, default=str) if old_value else None,
            new_value=json.dumps(new_value, ensure_ascii=False, default=str) if new_value else None,
            version_before=version_before,
            version_after=version_after,
            change_summary=change_summary,
            operator_id=operator_id,
            operator_name=operator_name,
        )
        db.add(log)


_strategy_config_service: Optional[StrategyConfigService] = None


def get_strategy_config_service() -> StrategyConfigService:
    global _strategy_config_service
    if _strategy_config_service is None:
        _strategy_config_service = StrategyConfigService()
    return _strategy_config_service
