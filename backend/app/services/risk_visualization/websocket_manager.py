"""
WebSocket 管理器

管理风险热力图的 WebSocket 连接，支持增量推送。
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from loguru import logger


class RiskHeatmapWebSocketManager:
    """
    风险热力图 WebSocket 连接管理器

    支持：
    1. 多客户端连接管理
    2. 按租户/组织隔离
    3. 增量数据推送（只推送变化的节点）
    3. 全量数据推送（首次连接或重连）
    4. 心跳保活
    5. 订阅/取消订阅特定节点或区域
    """

    def __init__(self):
        self._connections: Dict[str, Any] = {}
        self._subscriptions: Dict[str, Set[str]] = {}
        self._client_info: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

        logger.info("WebSocket管理器初始化完成")

    async def connect(
        self,
        websocket,
        tenant_id: str,
        client_id: Optional[str] = None,
    ) -> str:
        """
        客户端连接

        Args:
            websocket: WebSocket 连接对象
            tenant_id: 租户ID
            client_id: 客户端ID，不提供则自动生成

        Returns:
            客户端ID
        """
        if client_id is None:
            client_id = str(uuid.uuid4())

        async with self._lock:
            self._connections[client_id] = websocket
            self._subscriptions[client_id] = set()
            self._client_info[client_id] = {
                'tenant_id': tenant_id,
                'connected_at': datetime.now().isoformat(),
                'last_heartbeat': datetime.now().isoformat(),
                'message_count': 0,
            }

        logger.info(f"WebSocket客户端连接: client_id={client_id}, tenant={tenant_id}")

        await self._send_message(
            client_id,
            {
                'type': 'connected',
                'client_id': client_id,
                'timestamp': datetime.now().isoformat(),
            }
        )

        return client_id

    async def disconnect(self, client_id: str) -> None:
        """
        客户端断开连接

        Args:
            client_id: 客户端ID
        """
        async with self._lock:
            if client_id in self._connections:
                del self._connections[client_id]
            if client_id in self._subscriptions:
                del self._subscriptions[client_id]
            if client_id in self._client_info:
                del self._client_info[client_id]

        logger.info(f"WebSocket客户端断开: client_id={client_id}")

    async def subscribe(self, client_id: str, node_ids: List[str]) -> bool:
        """
        订阅节点

        Args:
            client_id: 客户端ID
            node_ids: 节点ID列表

        Returns:
            是否成功
        """
        async with self._lock:
            if client_id not in self._subscriptions:
                return False
            self._subscriptions[client_id].update(node_ids)

        logger.debug(
            f"客户端订阅节点: client_id={client_id}, "
            f"count={len(node_ids)}"
        )
        return True

    async def unsubscribe(self, client_id: str, node_ids: List[str]) -> bool:
        """
        取消订阅节点

        Args:
            client_id: 客户端ID
            node_ids: 节点ID列表

        Returns:
            是否成功
        """
        async with self._lock:
            if client_id not in self._subscriptions:
                return False
            for node_id in node_ids:
                self._subscriptions[client_id].discard(node_id)

        logger.debug(
            f"客户端取消订阅: client_id={client_id}, "
            f"count={len(node_ids)}"
        )
        return True

    async def broadcast_full_graph(
        self,
        graph_data: Dict[str, Any],
        tenant_id: Optional[str] = None,
    ) -> int:
        """
        广播全量图数据

        Args:
            graph_data: 图数据
            tenant_id: 租户ID，None 则广播给所有

        Returns:
            发送的客户端数量
        """
        count = 0

        async with self._lock:
            clients_to_send = []
            for client_id, info in self._client_info.items():
                if tenant_id is None or info['tenant_id'] == tenant_id:
                    clients_to_send.append(client_id)

        message = {
            'type': 'full_graph',
            'data': graph_data,
            'timestamp': datetime.now().isoformat(),
        }

        for client_id in clients_to_send:
            if await self._send_message(client_id, message):
                count += 1

        logger.info(
            f"广播全量图数据: count={count}, "
            f"tenant={tenant_id or 'all'}"
        )
        return count

    async def broadcast_incremental(
        self,
        updates: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
    ) -> int:
        """
        广播增量更新

        Args:
            updates: 更新数据列表
            tenant_id: 租户ID

        Returns:
            发送的客户端数量
        """
        count = 0

        async with self._lock:
            clients_to_send = []
            for client_id, info in self._client_info.items():
                if tenant_id is None or info['tenant_id'] == tenant_id:
                    clients_to_send.append(client_id)

        message = {
            'type': 'incremental_update',
            'updates': updates,
            'timestamp': datetime.now().isoformat(),
        }

        for client_id in clients_to_send:
            filtered_updates = self._filter_subscribed(
                client_id, updates
            )
            if filtered_updates:
                filtered_message = {
                    **message,
                    'updates': filtered_updates,
                }
                if await self._send_message(client_id, filtered_message):
                    count += 1

        logger.info(
            f"广播增量更新: count={count}, "
            f"updates={len(updates)}, "
            f"tenant={tenant_id or 'all'}"
        )
        return count

    async def broadcast_time_slice(
        self,
        slice_data: Dict[str, Any],
        slice_index: int,
        tenant_id: Optional[str] = None,
    ) -> int:
        """
        广播时间切片（用于动画回放）

        Args:
            slice_data: 切片数据
            slice_index: 切片索引
            tenant_id: 租户ID

        Returns:
            发送的客户端数量
        """
        count = 0

        async with self._lock:
            clients_to_send = []
            for client_id, info in self._client_info.items():
                if tenant_id is None or info['tenant_id'] == tenant_id:
                    clients_to_send.append(client_id)

        message = {
            'type': 'time_slice',
            'slice_index': slice_index,
            'data': slice_data,
            'timestamp': datetime.now().isoformat(),
        }

        for client_id in clients_to_send:
            if await self._send_message(client_id, message):
                count += 1

        return count

    async def send_alert(
        self,
        alert_data: Dict[str, Any],
        tenant_id: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> int:
        """
        发送告警

        Args:
            alert_data: 告警数据
            tenant_id: 租户ID
            node_id: 节点ID

        Returns:
            发送的客户端数量
        """
        count = 0

        async with self._lock:
            clients_to_send = []
            for client_id, info in self._client_info.items():
                if tenant_id is not None and info['tenant_id'] != tenant_id:
                    continue
                if node_id is not None:
                    subs = self._subscriptions.get(client_id, set())
                    if node_id not in subs and len(subs) > 0:
                        continue
                clients_to_send.append(client_id)

        message = {
            'type': 'alert',
            'data': alert_data,
            'timestamp': datetime.now().isoformat(),
        }

        for client_id in clients_to_send:
            if await self._send_message(client_id, message):
                count += 1

        logger.info(
            f"发送告警: count={count}, "
            f"node={node_id}, "
            f"tenant={tenant_id}"
        )
        return count

    async def handle_message(self, client_id: str, message: str) -> None:
        """
        处理客户端消息

        Args:
            client_id: 客户端ID
            message: 消息内容
        """
        try:
            data = json.loads(message)
            msg_type = data.get('type', '')

            if msg_type == 'heartbeat':
                await self._handle_heartbeat(client_id, data)
            elif msg_type == 'subscribe':
                node_ids = data.get('node_ids', [])
                await self.subscribe(client_id, node_ids)
            elif msg_type == 'unsubscribe':
                node_ids = data.get('node_ids', [])
                await self.unsubscribe(client_id, node_ids)
            elif msg_type == 'ping':
                await self._send_message(
                    client_id,
                    {'type': 'pong', 'timestamp': datetime.now().isoformat()}
                )
            else:
                logger.warning(
                    f"未知消息类型: client_id={client_id}, "
                    f"type={msg_type}"
                )

        except json.JSONDecodeError:
            logger.error(
                f"消息解析失败: client_id={client_id}, "
                f"message={message[:100]}"
            )
        except Exception as e:
            logger.error(f"处理消息异常: {e}")

    async def _handle_heartbeat(
        self, client_id: str, data: Dict[str, Any]
    ) -> None:
        """处理心跳"""
        async with self._lock:
            if client_id in self._client_info:
                self._client_info[client_id]['last_heartbeat'] = (
                    datetime.now().isoformat()
                )

    def _filter_subscribed(
        self,
        client_id: str,
        updates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """过滤订阅的节点更新"""
        subs = self._subscriptions.get(client_id, set())
        if not subs:
            return updates

        filtered = []
        for update in updates:
            node_id = update.get('id') or update.get('node_id')
            if node_id and node_id in subs:
                filtered.append(update)

        return filtered

    async def _send_message(
        self,
        client_id: str,
        message: Dict[str, Any],
    ) -> bool:
        """
        发送消息

        Args:
            client_id: 客户端ID
            message: 消息内容

        Returns:
            是否成功
        """
        try:
            websocket = self._connections.get(client_id)
            if websocket is None:
                return False

            await websocket.send_text(json.dumps(message, ensure_ascii=False))

            async with self._lock:
                if client_id in self._client_info:
                    self._client_info[client_id]['message_count'] += 1

            return True
        except Exception as e:
            logger.warning(
                f"发送消息失败: client_id={client_id}, error={e}"
            )
            return False

    def get_connected_clients(self, tenant_id: Optional[str] = None) -> List[str]:
        """
        获取已连接的客户端列表

        Args:
            tenant_id: 租户ID，None 表示全部

        Returns:
            客户端ID列表
        """
        if tenant_id is None:
            return list(self._connections.keys())

        return [
            cid for cid, info in self._client_info.items()
            if info['tenant_id'] == tenant_id
        ]

    def get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        获取客户端信息

        Args:
            client_id: 客户端ID

        Returns:
            客户端信息
        """
        info = self._client_info.get(client_id)
        if info is None:
            return None
        return {
            **info,
            'subscription_count': len(
                self._subscriptions.get(client_id, set())
            ),
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计数据
        """
        tenant_counts: Dict[str, int] = {}
        total_messages = 0

        for info in self._client_info.values():
            tenant_id = info['tenant_id']
            tenant_counts[tenant_id] = tenant_counts.get(tenant_id, 0) + 1
            total_messages += info.get('message_count', 0)

        return {
            'total_connections': len(self._connections),
            'tenant_counts': tenant_counts,
            'total_messages_sent': total_messages,
        }


_ws_manager: Optional[RiskHeatmapWebSocketManager] = None


def get_websocket_manager() -> RiskHeatmapWebSocketManager:
    """
    获取 WebSocket 管理器单例

    Returns:
        RiskHeatmapWebSocketManager
    """
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = RiskHeatmapWebSocketManager()
    return _ws_manager
