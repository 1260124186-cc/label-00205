import json
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any

from loguru import logger

from app.utils.database import get_db, NodeThreshold, ThresholdAuditLog
from app.utils.config import config


_threshold_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = threading.Lock()
_cache_loaded = False


def _cache_key(node_type: str, node_id: str, threshold_type: str) -> str:
    return f"{node_type}:{node_id}:{threshold_type}"


def _ensure_default_global():
    """Ensure global default thresholds exist for bolt and flange"""
    with get_db() as db:
        if db is None:
            return
        for nt in ('bolt', 'flange'):
            for tt in ('preload', 'risk'):
                exists = db.query(NodeThreshold).filter(
                    NodeThreshold.node_type == nt,
                    NodeThreshold.node_id == 'global',
                    NodeThreshold.scope == 'global',
                    NodeThreshold.threshold_type == tt,
                    NodeThreshold.is_active == True,
                ).first()
                if not exists:
                    if tt == 'preload':
                        params = json.dumps({
                            "min_normal": 400, "max_normal": 800,
                            "warning_deviation": 0.1, "critical_deviation": 0.2
                        })
                    else:
                        params = json.dumps({"high": 3, "medium": 7})
                    row = NodeThreshold(
                        node_type=nt,
                        node_id='global',
                        scope='global',
                        source='design',
                        threshold_type=tt,
                        parameters=params,
                        version=1,
                        is_active=True,
                        description=f'Default global {nt} {tt} threshold',
                    )
                    db.add(row)
        db.flush()


def load_cache():
    """Load all active thresholds into memory cache"""
    global _cache_loaded, _threshold_cache
    with _cache_lock:
        _ensure_default_global()
        with get_db() as db:
            if db is None:
                return
            rows = db.query(NodeThreshold).filter(
                NodeThreshold.is_active == True,
            ).all()
            new_cache = {}
            for r in rows:
                key = _cache_key(r.node_type, r.node_id, r.threshold_type)
                new_cache[key] = {
                    'id': r.id,
                    'node_type': r.node_type,
                    'node_id': r.node_id,
                    'scope': r.scope,
                    'source': r.source,
                    'threshold_type': r.threshold_type,
                    'parameters': json.loads(r.parameters) if isinstance(r.parameters, str) else r.parameters,
                    'version': r.version,
                    'description': r.description,
                    'design_value': r.design_value,
                    'deviation_ratio': r.deviation_ratio,
                    'statistical_mean': r.statistical_mean,
                    'statistical_std': r.statistical_std,
                    'statistical_sample_count': r.statistical_sample_count,
                    'statistical_window_days': r.statistical_window_days,
                    'operator_id': r.operator_id,
                    'operator_name': r.operator_name,
                    'update_time': r.update_time.isoformat() if r.update_time else None,
                }
            _threshold_cache = new_cache
            _cache_loaded = True
            logger.info(f"Threshold cache loaded, {len(_threshold_cache)} entries")


def get_effective_threshold(
    node_type: str,
    node_id: str,
    threshold_type: str,
    flange_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Resolve effective threshold following priority chain:
    1. Node-level override (scope=node, node_type=X, node_id=specific_id)
    2. Flange-level default (scope=flange, node_type=X, node_id=flange_id)
    3. Global default (scope=global, node_type=X, node_id='global')
    """
    global _cache_loaded
    if not _cache_loaded:
        load_cache()

    with _cache_lock:
        # Priority 1: node-level override
        key = _cache_key(node_type, node_id, threshold_type)
        if key in _threshold_cache:
            entry = _threshold_cache[key]
            if entry['scope'] == 'node':
                return entry

        # Priority 2: flange-level default
        if flange_id:
            key = _cache_key(node_type, flange_id, threshold_type)
            if key in _threshold_cache:
                entry = _threshold_cache[key]
                if entry['scope'] == 'flange':
                    return entry

        # Priority 3: global default
        key = _cache_key(node_type, 'global', threshold_type)
        if key in _threshold_cache:
            return _threshold_cache[key]

        # Fallback: return config.yaml defaults
        if threshold_type == 'preload':
            thresholds = config.get('risk_assessment.preload_thresholds', {})
            return {
                'node_type': node_type,
                'node_id': 'config_yaml',
                'scope': 'config',
                'source': 'config',
                'threshold_type': 'preload',
                'parameters': thresholds or {
                    'min_normal': 400, 'max_normal': 800,
                    'warning_deviation': 0.1, 'critical_deviation': 0.2,
                },
                'version': 0,
            }
        elif threshold_type == 'risk':
            thresholds = config.get('risk_assessment', {})
            high = thresholds.get('high_risk_threshold', 3)
            medium = thresholds.get('medium_risk_threshold', 7)
            return {
                'node_type': node_type,
                'node_id': 'config_yaml',
                'scope': 'config',
                'source': 'config',
                'threshold_type': 'risk',
                'parameters': {'high': high, 'medium': medium},
                'version': 0,
            }
        else:
            return {
                'node_type': node_type,
                'node_id': 'unknown',
                'scope': 'fallback',
                'source': 'fallback',
                'threshold_type': threshold_type,
                'parameters': {},
                'version': 0,
            }


def get_resolution_chain(
    node_type: str,
    node_id: str,
    threshold_type: str,
    flange_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return the full resolution chain showing each level checked"""
    global _cache_loaded
    if not _cache_loaded:
        load_cache()

    chain = []
    with _cache_lock:
        # Level 1: node
        key = _cache_key(node_type, node_id, threshold_type)
        entry = _threshold_cache.get(key)
        chain.append({
            'scope': 'node', 'node_type': node_type,
            'node_id': node_id, 'version': entry['version'] if entry and entry['scope'] == 'node' else None,
            'matched': entry is not None and entry['scope'] == 'node',
        })

        # Level 2: flange
        if flange_id:
            key = _cache_key(node_type, flange_id, threshold_type)
            entry = _threshold_cache.get(key)
            chain.append({
                'scope': 'flange', 'node_type': node_type,
                'node_id': flange_id, 'version': entry['version'] if entry and entry['scope'] == 'flange' else None,
                'matched': entry is not None and entry['scope'] == 'flange',
            })

        # Level 3: global
        key = _cache_key(node_type, 'global', threshold_type)
        entry = _threshold_cache.get(key)
        chain.append({
            'scope': 'global', 'node_type': node_type,
            'node_id': 'global', 'version': entry['version'] if entry else None,
            'matched': entry is not None,
        })

    return chain


class ThresholdService:

    def get_effective(
        self,
        node_type: str,
        node_id: str,
        threshold_type: str,
        flange_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return get_effective_threshold(node_type, node_id, threshold_type, flange_id)

    def get_resolution_chain(
        self,
        node_type: str,
        node_id: str,
        threshold_type: str,
        flange_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return get_resolution_chain(node_type, node_id, threshold_type, flange_id)

    def get_threshold(
        self,
        node_type: str,
        node_id: str,
        threshold_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            with get_db() as db:
                if db is None:
                    return None
                query = db.query(NodeThreshold).filter(
                    NodeThreshold.node_type == node_type,
                    NodeThreshold.node_id == node_id,
                    NodeThreshold.is_active == True,
                )
                if threshold_type:
                    query = query.filter(NodeThreshold.threshold_type == threshold_type)
                r = query.first()
                if r is None:
                    return None
                return self._to_dict(r)
        except Exception as e:
            logger.error(f"Failed to get threshold: {e}")
            return None

    def list_thresholds(
        self,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
        scope: Optional[str] = None,
        source: Optional[str] = None,
        threshold_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        try:
            with get_db() as db:
                if db is None:
                    return []
                query = db.query(NodeThreshold)
                if node_type:
                    query = query.filter(NodeThreshold.node_type == node_type)
                if node_id:
                    query = query.filter(NodeThreshold.node_id == node_id)
                if scope:
                    query = query.filter(NodeThreshold.scope == scope)
                if source:
                    query = query.filter(NodeThreshold.source == source)
                if threshold_type:
                    query = query.filter(NodeThreshold.threshold_type == threshold_type)
                if is_active is not None:
                    query = query.filter(NodeThreshold.is_active == is_active)

                rows = query.order_by(
                    NodeThreshold.node_type,
                    NodeThreshold.node_id,
                    NodeThreshold.threshold_type,
                    NodeThreshold.version.desc(),
                ).limit(limit).all()
                return [self._to_dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to list thresholds: {e}")
            return []

    def upsert_threshold(
        self,
        node_type: str,
        node_id: str,
        scope: str,
        source: str,
        threshold_type: str,
        parameters: Dict[str, Any],
        description: Optional[str] = None,
        design_value: Optional[float] = None,
        deviation_ratio: Optional[float] = None,
        statistical_mean: Optional[float] = None,
        statistical_std: Optional[float] = None,
        statistical_sample_count: Optional[int] = None,
        statistical_window_days: Optional[int] = None,
        operator_id: Optional[str] = None,
        operator_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create or update a threshold. Update deactivates the old version and creates a new version."""
        try:
            with get_db() as db:
                if db is None:
                    return None

                active = db.query(NodeThreshold).filter(
                    NodeThreshold.node_type == node_type,
                    NodeThreshold.node_id == node_id,
                    NodeThreshold.threshold_type == threshold_type,
                    NodeThreshold.scope == scope,
                    NodeThreshold.is_active == True,
                ).first()

                if active is None:
                    return self._create_threshold(
                        db, node_type, node_id, scope, source,
                        threshold_type, parameters, description,
                        design_value, deviation_ratio,
                        statistical_mean, statistical_std,
                        statistical_sample_count, statistical_window_days,
                        operator_id, operator_name,
                    )

                old_value = self._to_dict(active)
                old_version = active.version

                active.is_active = False
                db.flush()

                new_row = NodeThreshold(
                    node_type=node_type,
                    node_id=node_id,
                    scope=scope,
                    source=source,
                    threshold_type=threshold_type,
                    parameters=json.dumps(parameters, ensure_ascii=False),
                    version=old_version + 1,
                    is_active=True,
                    description=description or f"Threshold update: v{old_version} -> v{old_version + 1}",
                    design_value=design_value,
                    deviation_ratio=deviation_ratio,
                    statistical_mean=statistical_mean,
                    statistical_std=statistical_std,
                    statistical_sample_count=statistical_sample_count,
                    statistical_window_days=statistical_window_days,
                    operator_id=operator_id,
                    operator_name=operator_name,
                )
                db.add(new_row)
                db.flush()

                self._write_audit(
                    db, new_row.id, node_type, node_id, scope,
                    threshold_type, source, action='update',
                    old_value=old_value,
                    new_value=self._to_dict(new_row),
                    version_before=old_version,
                    version_after=new_row.version,
                    change_summary=description or f"Threshold update v{old_version} -> v{new_row.version}",
                    operator_id=operator_id,
                    operator_name=operator_name,
                )

                load_cache()
                return self._to_dict(new_row)

        except Exception as e:
            logger.error(f"Failed to upsert threshold: {e}")
            return None

    def _create_threshold(self, db, node_type, node_id, scope, source,
                          threshold_type, parameters, description,
                          design_value, deviation_ratio,
                          statistical_mean, statistical_std,
                          statistical_sample_count, statistical_window_days,
                          operator_id, operator_name):
        row = NodeThreshold(
            node_type=node_type,
            node_id=node_id,
            scope=scope,
            source=source,
            threshold_type=threshold_type,
            parameters=json.dumps(parameters, ensure_ascii=False),
            version=1,
            is_active=True,
            description=description or 'New threshold config',
            design_value=design_value,
            deviation_ratio=deviation_ratio,
            statistical_mean=statistical_mean,
            statistical_std=statistical_std,
            statistical_sample_count=statistical_sample_count,
            statistical_window_days=statistical_window_days,
            operator_id=operator_id,
            operator_name=operator_name,
        )
        db.add(row)
        db.flush()

        self._write_audit(
            db, row.id, node_type, node_id, scope,
            threshold_type, source, action='create',
            old_value=None,
            new_value=self._to_dict(row),
            version_before=None,
            version_after=1,
            change_summary=description or 'New threshold config',
            operator_id=operator_id,
            operator_name=operator_name,
        )

        load_cache()
        return self._to_dict(row)

    def delete_threshold(
        self,
        node_type: str,
        node_id: str,
        threshold_type: str,
        scope: str = 'node',
        operator_id: Optional[str] = None,
        operator_name: Optional[str] = None,
    ) -> bool:
        try:
            with get_db() as db:
                if db is None:
                    return False

                rows = db.query(NodeThreshold).filter(
                    NodeThreshold.node_type == node_type,
                    NodeThreshold.node_id == node_id,
                    NodeThreshold.threshold_type == threshold_type,
                    NodeThreshold.scope == scope,
                ).all()

                if not rows:
                    return False

                for r in rows:
                    self._write_audit(
                        db, r.id, node_type, node_id, scope,
                        threshold_type, r.source, action='delete',
                        old_value=self._to_dict(r),
                        new_value=None,
                        version_before=r.version,
                        version_after=None,
                        change_summary=f"Delete threshold: {node_type}/{node_id}/{threshold_type}",
                        operator_id=operator_id,
                        operator_name=operator_name,
                    )

                for r in rows:
                    db.delete(r)

                load_cache()
                logger.info(f"Deleted threshold: {node_type}/{node_id}/{threshold_type}/{scope}")
                return True

        except Exception as e:
            logger.error(f"Failed to delete threshold: {e}")
            return False

    def batch_import(
        self,
        items: List[Dict[str, Any]],
        operator_id: Optional[str] = None,
        operator_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        result = {'total': len(items), 'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0, 'error_details': []}
        for item in items:
            try:
                r = self.upsert_threshold(
                    node_type=item['node_type'],
                    node_id=item['node_id'],
                    scope=item.get('scope', 'node'),
                    source=item.get('source', 'design'),
                    threshold_type=item['threshold_type'],
                    parameters=item['parameters'],
                    description=item.get('description'),
                    design_value=item.get('design_value'),
                    deviation_ratio=item.get('deviation_ratio'),
                    statistical_mean=item.get('statistical_mean'),
                    statistical_std=item.get('statistical_std'),
                    statistical_sample_count=item.get('statistical_sample_count'),
                    statistical_window_days=item.get('statistical_window_days'),
                    operator_id=operator_id,
                    operator_name=operator_name,
                )
                if r:
                    if r.get('version', 1) == 1:
                        result['created'] += 1
                    else:
                        result['updated'] += 1
                else:
                    result['errors'] += 1
                    result['error_details'].append({
                        'node_type': item.get('node_type'),
                        'node_id': item.get('node_id'),
                        'threshold_type': item.get('threshold_type'),
                        'error': 'upsert_failed',
                    })
            except Exception as e:
                result['errors'] += 1
                result['error_details'].append({
                    'node_type': item.get('node_type'),
                    'node_id': item.get('node_id'),
                    'threshold_type': item.get('threshold_type'),
                    'error': str(e),
                })
        return result

    def get_audit_logs(
        self,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
        threshold_type: Optional[str] = None,
        action: Optional[str] = None,
        operator_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        try:
            with get_db() as db:
                if db is None:
                    return []
                query = db.query(ThresholdAuditLog)
                if node_type:
                    query = query.filter(ThresholdAuditLog.node_type == node_type)
                if node_id:
                    query = query.filter(ThresholdAuditLog.node_id == node_id)
                if threshold_type:
                    query = query.filter(ThresholdAuditLog.threshold_type == threshold_type)
                if action:
                    query = query.filter(ThresholdAuditLog.action == action)
                if operator_id:
                    query = query.filter(ThresholdAuditLog.operator_id == operator_id)

                rows = query.order_by(
                    ThresholdAuditLog.create_time.desc(),
                ).offset(offset).limit(limit).all()

                return [
                    {
                        'id': r.id,
                        'threshold_id': r.threshold_id,
                        'node_type': r.node_type,
                        'node_id': r.node_id,
                        'scope': r.scope,
                        'threshold_type': r.threshold_type,
                        'source': r.source,
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
            logger.error(f"Failed to query threshold audit logs: {e}")
            return []

    @staticmethod
    def _to_dict(r: NodeThreshold) -> Dict[str, Any]:
        params = r.parameters
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except Exception:
                params = {}
        return {
            'id': r.id,
            'node_type': r.node_type,
            'node_id': r.node_id,
            'scope': r.scope,
            'source': r.source,
            'threshold_type': r.threshold_type,
            'parameters': params,
            'version': r.version,
            'is_active': r.is_active,
            'description': r.description,
            'design_value': r.design_value,
            'deviation_ratio': r.deviation_ratio,
            'statistical_mean': r.statistical_mean,
            'statistical_std': r.statistical_std,
            'statistical_sample_count': r.statistical_sample_count,
            'statistical_window_days': r.statistical_window_days,
            'operator_id': r.operator_id,
            'operator_name': r.operator_name,
            'create_time': r.create_time.isoformat() if r.create_time else None,
            'update_time': r.update_time.isoformat() if r.update_time else None,
        }

    @staticmethod
    def _write_audit(
        db, threshold_id, node_type, node_id, scope,
        threshold_type, source, action,
        old_value, new_value,
        version_before, version_after,
        change_summary, operator_id, operator_name,
    ):
        log = ThresholdAuditLog(
            threshold_id=threshold_id,
            node_type=node_type,
            node_id=node_id,
            scope=scope,
            threshold_type=threshold_type,
            source=source,
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


_threshold_service: Optional[ThresholdService] = None


def get_threshold_service() -> ThresholdService:
    global _threshold_service
    if _threshold_service is None:
        _threshold_service = ThresholdService()
    return _threshold_service
