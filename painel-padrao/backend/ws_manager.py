"""Gerenciador de conexões WebSocket para broadcast de eventos em tempo real."""
import asyncio
import json
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.append(ws)
        logger.info(f"WS conectado. Total: {len(self._connections)}")

    def disconnect(self, ws: WebSocket):
        self._connections.remove(ws)
        logger.info(f"WS desconectado. Total: {len(self._connections)}")

    async def broadcast(self, event: str, destinatarios: list[dict] | None = None):
        """
        Envia evento para todos os clientes.
        destinatarios: lista de {"setor": str, "empresa": str} — quem deve receber notificação sonora.
                       None = todos recarregam a lista, mas ninguém toca som.
        """
        payload = json.dumps({"event": event, "destinatarios": destinatarios or []})
        logger.info(f"Broadcast '{event}' para {len(self._connections)} cliente(s), destinatários: {destinatarios}")
        dead = []
        for ws in self._connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.remove(ws)


manager = ConnectionManager()
