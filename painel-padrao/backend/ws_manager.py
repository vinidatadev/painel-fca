"""Gerenciador de conexões WebSocket para broadcast de eventos em tempo real."""
import asyncio
import json
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # {user_id: WebSocket}  — um socket por usuário (último vence)
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, ws: WebSocket, user_id: str):
        await ws.accept()
        self._connections[user_id] = ws
        logger.info(f"WS conectado user={user_id}. Total: {len(self._connections)}")

    def disconnect(self, ws: WebSocket, user_id: str):
        if self._connections.get(user_id) is ws:
            del self._connections[user_id]
        logger.info(f"WS desconectado user={user_id}. Total: {len(self._connections)}")

    async def broadcast(self, event: str, destinatarios: list[dict] | None = None):
        """
        Envia evento para todos os clientes conectados.
        destinatarios: lista de {"setor": str, "empresa": str} para filtro de som/badge.
                       None = todos recebem mas sem destaque sonoro.
        """
        payload = json.dumps({
            "event": event,
            "destinatarios": destinatarios or [],
        })
        await self._send_to_all(payload)

    async def send_to_users(self, event: str, user_ids: list[str], data: dict | None = None):
        """Envia evento apenas para user_ids específicos (notificações personalizadas)."""
        payload = json.dumps({
            "event": event,
            "user_ids": user_ids,
            **(data or {}),
        })
        dead = []
        for uid in user_ids:
            ws = self._connections.get(uid)
            if ws:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.append(uid)
        for uid in dead:
            self._connections.pop(uid, None)

    async def broadcast_notif(self, user_ids: list[str]):
        """Sinaliza para user_ids que há nova notificação pendente."""
        await self.send_to_users("nova_notificacao", user_ids)

    async def _send_to_all(self, payload: str):
        dead = []
        for uid, ws in list(self._connections.items()):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(uid)
        for uid in dead:
            self._connections.pop(uid, None)


manager = ConnectionManager()
