import os
import asyncio
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
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
from routes.admin import router as admin_router
from routes.notifications import router as notifications_router
from routes.bi import router as bi_router
from routes.onboarding import router as onboarding_router
import storage

load_dotenv()

logger = logging.getLogger(__name__)


async def _processar_timeouts():
    """Encerra FCAs em aguardando_devolutiva que ultrapassaram o prazo configurado."""
    from sqlalchemy import select
    from models import FCA, AuditLog
    from datetime import timedelta

    timeout_horas = int(os.getenv("FCA_TIMEOUT_HORAS", "72"))
    threshold = datetime.now(timezone.utc) - timedelta(hours=timeout_horas)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(FCA).where(
                FCA.status == "aguardando_devolutiva",
                FCA.updated_at < threshold,
            )
        )
        fcas = result.scalars().all()
        for fca in fcas:
            fca.status = "encerrado"
            db.add(AuditLog(
                fca_id=fca.id,
                usuario_id=None,
                acao="timeout_encerramento",
                detalhe=f"cod_fca={fca.cod_fca}",
            ))
            logger.info("Timeout_Job: encerrado %s em %s", fca.cod_fca, datetime.now(timezone.utc).isoformat())
        if fcas:
            await db.commit()


async def _limpar_anexos_orfaos():
    """Remove do MinIO arquivos sem referência no banco com mais de 2h."""
    from sqlalchemy import select
    from models import FCA, HelpTicket
    from datetime import timedelta

    try:
        # Coleta todas as keys referenciadas no banco
        async with AsyncSessionLocal() as db:
            fca_urls = (await db.execute(select(FCA.anexo_urls).where(FCA.anexo_urls.isnot(None)))).scalars().all()
            help_keys = (await db.execute(select(HelpTicket.anexo_keys).where(HelpTicket.anexo_keys.isnot(None)))).scalars().all()

        referenced: set[str] = set()
        for urls in fca_urls:
            if urls:
                referenced.update(urls)
        for keys in help_keys:
            if keys:
                referenced.update(keys)

        threshold = datetime.now(timezone.utc) - timedelta(hours=2)

        def _sync_cleanup():
            s3 = storage._client()
            paginator = s3.get_paginator("list_objects_v2")
            deleted = 0
            for page in paginator.paginate(Bucket=storage.BUCKET):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    last_modified = obj["LastModified"]
                    if key not in referenced and last_modified < threshold:
                        storage.delete_file(key)
                        deleted += 1
            return deleted

        loop = asyncio.get_event_loop()
        deleted = await loop.run_in_executor(None, _sync_cleanup)
        if deleted:
            logger.info("Storage_Job: removidos %d arquivos órfãos", deleted)
    except Exception as e:
        logger.warning("Storage_Job erro: %s", e)


async def _timeout_job():
    while True:
        try:
            await _processar_timeouts()
        except Exception as e:
            logger.error("Timeout_Job erro: %s", e)
        await asyncio.sleep(3600)


async def _storage_cleanup_job():
    await asyncio.sleep(3600)  # aguarda 1h antes da primeira execução
    while True:
        try:
            await _limpar_anexos_orfaos()
        except Exception as e:
            logger.error("Storage_Job loop erro: %s", e)
        await asyncio.sleep(3600)  # roda a cada 1h





def _sql(s: str):
    return __import__('sqlalchemy').text(s)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migrações incrementais — seguras para re-execução
        await conn.execute(_sql(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS company VARCHAR(20) NOT NULL DEFAULT 'ACC'"
        ))
        await conn.execute(_sql(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS sector VARCHAR(30) NOT NULL DEFAULT 'Customer_Service'"
        ))
        await conn.execute(_sql(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS matricula VARCHAR(20)"
        ))
        await conn.execute(_sql(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS turno VARCHAR(1)"
        ))
        await conn.execute(_sql(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS telefone VARCHAR(20)"
        ))
        await conn.execute(_sql(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT"
        ))
        await conn.execute(_sql(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS notif_email BOOLEAN NOT NULL DEFAULT TRUE"
        ))
        await conn.execute(_sql(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS notif_sms BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        await conn.execute(_sql(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS notif_push BOOLEAN NOT NULL DEFAULT TRUE"
        ))
        await conn.execute(_sql(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS notif_som VARCHAR(10) NOT NULL DEFAULT 'som1'"
        ))
        await conn.execute(_sql(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS acesso_relatorio BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        await conn.execute(_sql(
            "ALTER TABLE help_tickets ADD COLUMN IF NOT EXISTS anexo_keys TEXT[]"
        ))
        await conn.execute(_sql(
            "ALTER TABLE fcas ADD COLUMN IF NOT EXISTS anexo_urls TEXT[]"
        ))
        await conn.execute(_sql(
            "UPDATE fcas SET anexo_urls = ARRAY[anexo_url] WHERE anexo_url IS NOT NULL AND anexo_urls IS NULL"
        ))
        await conn.execute(_sql(
            "CREATE INDEX IF NOT EXISTS ix_audit_logs_fca_id ON audit_logs(fca_id)"
        ))
        await conn.execute(_sql(
            "CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at)"
        ))
        await conn.execute(_sql(
            "CREATE INDEX IF NOT EXISTS ix_comentarios_internos_fca_id ON comentarios_internos(fca_id)"
        ))
        # Migração: tabela de notificacoes
        await conn.execute(_sql(
            "CREATE TABLE IF NOT EXISTS notificacoes ("
            "    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
            "    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,"
            "    tipo VARCHAR(20) NOT NULL,"
            "    titulo VARCHAR(200) NOT NULL,"
            "    mensagem TEXT,"
            "    imagem_url TEXT,"
            "    link_rota VARCHAR(300),"
            "    lida BOOLEAN NOT NULL DEFAULT FALSE,"
            "    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            ")"
        ))
        await conn.execute(_sql(
            "CREATE INDEX IF NOT EXISTS ix_notificacoes_user_id ON notificacoes(user_id)"
        ))
        await conn.execute(_sql(
            "CREATE INDEX IF NOT EXISTS ix_notificacoes_lida ON notificacoes(lida)"
        ))
        await conn.execute(_sql(
            "CREATE INDEX IF NOT EXISTS ix_notificacoes_created_at ON notificacoes(created_at)"
        ))
        # Migrações: onboarding e primeiro acesso
        await conn.execute(_sql(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT TRUE"
        ))
        await conn.execute(_sql(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        # Usuários já existentes não precisam trocar senha nem refazer onboarding
        await conn.execute(_sql(
            "UPDATE users SET must_change_password = FALSE "
            "WHERE must_change_password = TRUE AND password_hash IS NOT NULL"
        ))
        await conn.execute(_sql(
            "UPDATE users SET onboarding_completed = TRUE WHERE onboarding_completed = FALSE"
        ))
        await conn.execute(_sql(
            "CREATE TABLE IF NOT EXISTS onboarding_videos ("
            "    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
            "    titulo VARCHAR(200) NOT NULL,"
            "    descricao TEXT,"
            "    video_key TEXT NOT NULL,"
            "    ordem INTEGER NOT NULL DEFAULT 0,"
            "    ativo BOOLEAN NOT NULL DEFAULT TRUE,"
            "    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            ")"
        ))
        await conn.execute(_sql(
            "CREATE TABLE IF NOT EXISTS onboarding_progressos ("
            "    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
            "    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,"
            "    video_id UUID NOT NULL REFERENCES onboarding_videos(id) ON DELETE CASCADE,"
            "    assistido_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
            "    UNIQUE(user_id, video_id)"
            ")"
        ))
        await conn.execute(_sql(
            "CREATE INDEX IF NOT EXISTS ix_onboarding_progressos_user_id ON onboarding_progressos(user_id)"
        ))
        # Remove coluna legada anexo_key se existir
        await conn.execute(_sql("""
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
    try:
        storage.ensure_bucket()
    except Exception as e:
        logger.warning("MinIO indisponível no startup (não crítico): %s", e)
    # Garante bucket de onboarding
    try:
        import onboarding_storage
        onboarding_storage.ensure_onboarding_bucket()
    except Exception as e:
        logger.warning("MinIO onboarding bucket indisponível no startup: %s", e)
    async with AsyncSessionLocal() as db:
        await seed_opcoes(db)
    asyncio.create_task(_timeout_job())
    asyncio.create_task(_storage_cleanup_job())
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
app.include_router(admin_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(bi_router, prefix="/api")
app.include_router(onboarding_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "version": app.version}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, user_id: str = Query(...)):
    """
    Endpoint WebSocket. Requer user_id como query param:
      ws://host/ws?user_id=<uuid>
    """
    await manager.connect(ws, user_id)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws, user_id)
