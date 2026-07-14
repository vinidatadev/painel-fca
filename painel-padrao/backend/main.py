import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from ws_manager import manager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from limiter import limiter
from dotenv import load_dotenv
from database import engine, Base
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal
from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.fcas import router as fcas_router
from routes.upload import router as upload_router
from routes.dashboard import router as dashboard_router
from routes.opcoes import router as opcoes_router, seed_opcoes
from routes.sla import router as sla_router
from routes.perfil import router as perfil_router
from routes.help import router as help_router
import storage

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migrações incrementais — seguras para re-execução
        await conn.execute(
            __import__('sqlalchemy').text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS notif_som VARCHAR(10) NOT NULL DEFAULT 'som1'"
            )
        )
        # Migração: garante coluna anexo_keys (text[]) em help_tickets
        await conn.execute(__import__('sqlalchemy').text(
            "ALTER TABLE help_tickets ADD COLUMN IF NOT EXISTS anexo_keys TEXT[]"
        ))
        # Migração: múltiplos anexos em fcas
        await conn.execute(__import__('sqlalchemy').text(
            "ALTER TABLE fcas ADD COLUMN IF NOT EXISTS anexo_urls TEXT[]"
        ))
        await conn.execute(__import__('sqlalchemy').text(
            "UPDATE fcas SET anexo_urls = ARRAY[anexo_url] WHERE anexo_url IS NOT NULL AND anexo_urls IS NULL"
        ))
        # Remove a coluna antiga só se ainda existir (instâncias legadas)
        await conn.execute(__import__('sqlalchemy').text("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'help_tickets' AND column_name = 'anexo_key'
                ) THEN
                    UPDATE help_tickets
                       SET anexo_keys = ARRAY[anexo_key]
                     WHERE anexo_key IS NOT NULL AND anexo_keys IS NULL;
                    ALTER TABLE help_tickets DROP COLUMN anexo_key;
                END IF;
            END$$;
        """))
    storage.ensure_bucket()
    # Semeia listas padrão se banco estiver vazio
    async with AsyncSessionLocal() as db:
        await seed_opcoes(db)
    yield


app = FastAPI(
    title="FCA API",
    version="2.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(fcas_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(opcoes_router, prefix="/api")
app.include_router(sla_router, prefix="/api")
app.include_router(perfil_router, prefix="/api")
app.include_router(help_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "version": app.version}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            # Mantém a conexão viva; clientes podem enviar "ping" se quiserem
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
