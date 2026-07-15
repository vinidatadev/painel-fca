import uuid
import csv
import io
from datetime import datetime, timezone
from uuid import UUID
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, cast, Text
from sqlalchemy.orm import selectinload
from database import get_db
from models import User, FCA, FCAEtapa
from auth import require_user
from business import (
    validate_company_sector, get_triagem,
    CAUSAS, ACOES, UFS, SECTORS_CAN_OPEN, SECTORS_WITH_RETURN, COMPANIES
)
import emails as email_svc
from sla import get_sla_deadline
from ws_manager import manager
import notif_helper

router = APIRouter(prefix="/fcas", tags=["fcas"])
any_user = require_user()


# ── helpers ──────────────────────────────────────────────────────────────────

async def _get_seq(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(FCA))
    return (result.scalar() or 0) + 1


def _etapa_ativa(etapas: list[FCAEtapa]) -> FCAEtapa | None:
    pendentes = [e for e in etapas if e.status in ("pendente", "em_andamento")]
    return min(pendentes, key=lambda e: e.order_index) if pendentes else None


def _can_view(fca: FCA, etapas: list[FCAEtapa], user: dict) -> bool:
    if user["role"] == "admin":
        return True
    # Cancelados são invisíveis para não-admins
    if fca.status == "cancelado":
        return False
    # Mesmo setor/empresa que abriu
    if fca.setor_solicitante == user["sector"] and fca.empresa_solicitante == user["company"]:
        return True
    # Tem ou teve etapa na fila
    return any(
        e.setor == user["sector"] and e.empresa == user["company"]
        for e in etapas
    )


# ── Schemas ───────────────────────────────────────────────────────────────────

class EtapaOut(BaseModel):
    id: str
    order_index: int
    setor: str
    empresa: str
    status: str
    problema_solucionado: bool | None
    devolutiva: str | None
    respondido_por: dict | None
    entered_at: str | None
    concluded_at: str | None
    sla_deadline: str | None

    @classmethod
    def from_orm(cls, e: FCAEtapa):
        return cls(
            id=str(e.id),
            order_index=e.order_index,
            setor=e.setor,
            empresa=e.empresa,
            status=e.status,
            problema_solucionado=e.problema_solucionado,
            devolutiva=e.devolutiva,
            respondido_por=(
                {"id": str(e.respondido_por_user.id), "name": e.respondido_por_user.name}
                if e.respondido_por_user else None
            ),
            entered_at=e.entered_at.isoformat() if e.entered_at else None,
            concluded_at=e.concluded_at.isoformat() if e.concluded_at else None,
            sla_deadline=e.sla_deadline.isoformat() if e.sla_deadline else None,
        )


class FCAListItem(BaseModel):
    id: str
    cod_fca: str
    causa: str
    area_causadora: str
    empresa_causadora: str
    setor_solicitante: str
    empresa_solicitante: str
    uf: str
    numero_remessa: int | None
    remessas: list[int]
    status: str
    etapa_atual: dict | None
    created_at: str

    @classmethod
    def from_orm(cls, fca: FCA, etapa: FCAEtapa | None):
        return cls(
            id=str(fca.id),
            cod_fca=fca.cod_fca,
            causa=fca.causa,
            area_causadora=fca.area_causadora,
            empresa_causadora=fca.empresa_causadora,
            setor_solicitante=fca.setor_solicitante,
            empresa_solicitante=fca.empresa_solicitante,
            uf=fca.uf,
            numero_remessa=fca.numero_remessa,
            remessas=fca.remessas or [],
            status=fca.status,
            etapa_atual=(
                {"setor": etapa.setor, "empresa": etapa.empresa, "order_index": etapa.order_index}
                if etapa else None
            ),
            created_at=fca.created_at.isoformat(),
        )


class FCADetail(BaseModel):
    id: str
    cod_fca: str
    causa: str
    acao: str
    uf: str
    numero_remessa: int | None
    remessas: list[int]
    detalhe: str | None
    anexo_url: str | None
    anexo_urls: list[str]
    setor_solicitante: str
    empresa_solicitante: str
    area_causadora: str
    empresa_causadora: str
    status: str
    created_by: dict
    created_at: str
    etapas: list[EtapaOut]

    @classmethod
    def from_orm(cls, fca: FCA):
        return cls(
            id=str(fca.id),
            cod_fca=fca.cod_fca,
            causa=fca.causa,
            acao=fca.acao,
            uf=fca.uf,
            numero_remessa=fca.numero_remessa,
            remessas=fca.remessas or [],
            detalhe=fca.detalhe,
            anexo_url=fca.anexo_url,
            anexo_urls=fca.anexo_urls or ([fca.anexo_url] if fca.anexo_url else []),
            setor_solicitante=fca.setor_solicitante,
            empresa_solicitante=fca.empresa_solicitante,
            area_causadora=fca.area_causadora,
            empresa_causadora=fca.empresa_causadora,
            status=fca.status,
            created_by={"id": str(fca.criado_por_user.id), "name": fca.criado_por_user.name},
            created_at=fca.created_at.isoformat(),
            etapas=[EtapaOut.from_orm(e) for e in fca.etapas],
        )


class FCACreate(BaseModel):
    causa: str
    area_causadora: str
    empresa_causadora: str
    acao: str
    uf: str
    numero_remessa: int | None = None
    remessas: list[int] = []
    detalhe: str | None = None
    anexo_url: str | None = None          # legado, mantido por compatibilidade
    anexo_urls: list[str] = []            # nova forma: múltiplos anexos


class EncaminharItem(BaseModel):
    setor: str
    empresa: str


class ResponderBody(BaseModel):
    problema_solucionado: bool
    devolutiva: str = Field(..., min_length=1)
    encaminhar: list[EncaminharItem] = []


# ── Rotas ─────────────────────────────────────────────────────────────────────

@router.get("/")
async def list_fcas(
    status_filter: str | None = None,
    company: str | None = None,
    sector: str | None = None,
    area_causadora: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current: dict = Depends(any_user),
):
    stmt = (
        select(FCA)
        .options(selectinload(FCA.etapas), selectinload(FCA.criado_por_user))
        .order_by(FCA.created_at.desc())
    )

    if current["role"] != "admin":
        stmt = stmt.join(FCAEtapa, FCAEtapa.fca_id == FCA.id, isouter=True).where(
            or_(
                # FCAs abertos pelo setor/empresa do usuário (qualquer pessoa do setor)
                and_(
                    FCA.setor_solicitante == current["sector"],
                    FCA.empresa_solicitante == current["company"],
                ),
                # FCAs onde o setor/empresa do usuário tem ou teve etapa na fila
                and_(
                    FCAEtapa.setor == current["sector"],
                    FCAEtapa.empresa == current["company"],
                )
            )
        ).distinct()
    else:
        # Admin vê tudo EXCETO cancelados (cancelados ficam só no filtro explícito)
        if not status_filter or status_filter != "cancelado":
            stmt = stmt.where(FCA.status != "cancelado")

    if status_filter:
        stmt = stmt.where(FCA.status == status_filter)
    if company:
        stmt = stmt.where(FCA.empresa_solicitante == company)
    if sector:
        stmt = stmt.where(FCA.setor_solicitante == sector)
    if area_causadora:
        stmt = stmt.where(FCA.area_causadora == area_causadora)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                FCA.cod_fca.ilike(pattern),
                FCA.causa.ilike(pattern),
                FCA.detalhe.ilike(pattern),
                cast(FCA.remessas, Text).ilike(pattern),
            )
        )

    count_q = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    fcas = result.scalars().unique().all()

    items = []
    for fca in fcas:
        etapa = _etapa_ativa(fca.etapas)
        items.append(FCAListItem.from_orm(fca, etapa))

    return {"total": total, "page": page, "items": [i.model_dump() for i in items]}


@router.get("/export")
async def export_fcas(
    format: str = "xlsx",
    status_filter: str | None = None,
    area_causadora: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
    current: dict = Depends(any_user),
):
    """Exporta FCAs filtrados em xlsx ou csv."""
    if format not in ("xlsx", "csv"):
        raise HTTPException(status_code=422, detail="Formato inválido. Use xlsx ou csv")

    stmt = (
        select(FCA)
        .options(selectinload(FCA.etapas), selectinload(FCA.criado_por_user))
        .order_by(FCA.created_at.desc())
    )

    if current["role"] != "admin":
        stmt = stmt.join(FCAEtapa, FCAEtapa.fca_id == FCA.id, isouter=True).where(
            or_(
                and_(
                    FCA.setor_solicitante == current["sector"],
                    FCA.empresa_solicitante == current["company"],
                ),
                and_(
                    FCAEtapa.setor == current["sector"],
                    FCAEtapa.empresa == current["company"],
                )
            )
        ).distinct()
    else:
        if not status_filter or status_filter != "cancelado":
            stmt = stmt.where(FCA.status != "cancelado")

    if status_filter:
        stmt = stmt.where(FCA.status == status_filter)
    if area_causadora:
        stmt = stmt.where(FCA.area_causadora == area_causadora)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                FCA.cod_fca.ilike(pattern),
                FCA.causa.ilike(pattern),
                FCA.detalhe.ilike(pattern),
                cast(FCA.remessas, Text).ilike(pattern),
            )
        )

    result = await db.execute(stmt)
    fcas = result.scalars().unique().all()

    headers_cols = [
        "cod_fca", "causa", "acao", "uf", "remessas",
        "setor_solicitante", "empresa_solicitante",
        "area_causadora", "empresa_causadora",
        "status", "created_at", "etapa_atual_setor", "etapa_atual_empresa",
    ]

    def _row(fca: FCA) -> list:
        etapa = _etapa_ativa(fca.etapas)
        return [
            fca.cod_fca,
            fca.causa,
            fca.acao,
            fca.uf,
            ",".join(str(r) for r in (fca.remessas or [])),
            fca.setor_solicitante,
            fca.empresa_solicitante,
            fca.area_causadora,
            fca.empresa_causadora,
            fca.status,
            fca.created_at.isoformat(),
            etapa.setor if etapa else "",
            etapa.empresa if etapa else "",
        ]

    try:
        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(headers_cols)
            for fca in fcas:
                writer.writerow(_row(fca))
            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=fcas.csv"},
            )
        else:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "FCAs"
            ws.append(headers_cols)
            for fca in fcas:
                ws.append(_row(fca))
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            return StreamingResponse(
                iter([buf.read()]),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=fcas.xlsx"},
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao gerar exportação")


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_fca(
    body: FCACreate,
    db: AsyncSession = Depends(get_db),
    current: dict = Depends(any_user),
):
    if current["sector"] == "Producao":
        raise HTTPException(status_code=403, detail="Setor Produção não pode abrir FCAs")
    if current["sector"] not in SECTORS_CAN_OPEN:
        raise HTTPException(status_code=403, detail="Seu setor não tem permissão para abrir FCAs")

    if body.causa not in CAUSAS:
        raise HTTPException(status_code=422, detail="Causa inválida")
    if body.acao not in ACOES:
        raise HTTPException(status_code=422, detail="Ação inválida")
    if body.uf not in UFS:
        raise HTTPException(status_code=422, detail="UF inválida")
    if body.empresa_causadora not in COMPANIES:
        raise HTTPException(status_code=422, detail="Empresa causadora inválida")

    triagem = get_triagem(body.area_causadora, body.empresa_causadora)
    if not triagem:
        raise HTTPException(status_code=422, detail="Combinação área causadora + empresa inválida")

    # Não pode abrir FCA para o próprio setor/empresa
    setor_destino, empresa_destino = triagem
    if setor_destino == current["sector"] and empresa_destino == current["company"]:
        raise HTTPException(status_code=422, detail="Você não pode abrir um FCA direcionado ao seu próprio setor")

    seq = await _get_seq(db)
    year = datetime.now(timezone.utc).year
    cod_fca = f"FCA-{year}-{seq:04d}"

    fca = FCA(
        cod_fca=cod_fca,
        causa=body.causa,
        acao=body.acao,
        uf=body.uf,
        numero_remessa=body.remessas[0] if body.remessas else body.numero_remessa,
        remessas=body.remessas if body.remessas else ([body.numero_remessa] if body.numero_remessa else []),
        detalhe=body.detalhe,
        anexo_url=body.anexo_urls[0] if body.anexo_urls else body.anexo_url,
        anexo_urls=body.anexo_urls if body.anexo_urls else ([body.anexo_url] if body.anexo_url else None),
        setor_solicitante=current["sector"],
        empresa_solicitante=current["company"],
        area_causadora=body.area_causadora,
        empresa_causadora=body.empresa_causadora,
        status="aberto",
        created_by=uuid.UUID(current["user_id"]),
    )
    db.add(fca)
    await db.flush()

    setor_etapa, empresa_etapa = triagem
    now_etapa = datetime.now(timezone.utc)
    deadline = await get_sla_deadline(db, setor_etapa, empresa_etapa, now_etapa)
    etapa = FCAEtapa(
        fca_id=fca.id,
        order_index=1,
        setor=setor_etapa,
        empresa=empresa_etapa,
        status="pendente",
        entered_at=now_etapa,
        sla_deadline=deadline,
    )
    db.add(etapa)
    await db.commit()
    await db.refresh(fca)

    # AuditLog: criacao
    from models import AuditLog
    db.add(AuditLog(
        fca_id=fca.id,
        usuario_id=uuid.UUID(current["user_id"]),
        acao="criacao",
    ))
    await db.commit()

    # Recarrega com relacionamentos para email
    result = await db.execute(
        select(FCA).options(selectinload(FCA.etapas)).where(FCA.id == fca.id)
    )
    fca_loaded = result.scalar_one()
    try:
        email_svc.notify_abertura(fca_loaded, fca_loaded.etapas[0])
    except Exception:
        pass

    await manager.broadcast("fca_updated", destinatarios=[{"setor": setor_etapa, "empresa": empresa_etapa}])
    await notif_helper.notif_fca_criado(db, fca_loaded)
    await db.commit()
    return {
        "id": str(fca.id),
        "cod_fca": fca.cod_fca,
        "status": fca.status,
        "etapas": [{"id": str(etapa.id), "order_index": 1, "setor": setor_etapa, "empresa": empresa_etapa, "status": "pendente"}]
    }


@router.get("/{fca_id}")
async def get_fca(
    fca_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: dict = Depends(any_user),
):
    result = await db.execute(
        select(FCA)
        .options(
            selectinload(FCA.etapas).selectinload(FCAEtapa.respondido_por_user),
            selectinload(FCA.criado_por_user)
        )
        .where(FCA.id == fca_id)
    )
    fca = result.scalar_one_or_none()
    if not fca:
        raise HTTPException(status_code=404, detail="FCA não encontrado")
    if not _can_view(fca, fca.etapas, current):
        raise HTTPException(status_code=403, detail="Acesso negado a este FCA")
    return FCADetail.from_orm(fca).model_dump()


@router.post("/{fca_id}/responder")
async def responder_fca(
    fca_id: UUID,
    body: ResponderBody,
    db: AsyncSession = Depends(get_db),
    current: dict = Depends(any_user),
):
    result = await db.execute(
        select(FCA)
        .options(
            selectinload(FCA.etapas).selectinload(FCAEtapa.respondido_por_user),
            selectinload(FCA.criado_por_user)
        )
        .where(FCA.id == fca_id)
    )
    fca = result.scalar_one_or_none()
    if not fca:
        raise HTTPException(status_code=404, detail="FCA não encontrado")

    etapa_atual = _etapa_ativa(fca.etapas)
    if not etapa_atual:
        raise HTTPException(status_code=409, detail="Não há etapa ativa neste FCA")

    if etapa_atual.setor != current["sector"] or etapa_atual.empresa != current["company"]:
        raise HTTPException(status_code=403, detail="Não é a vez do seu setor responder este FCA")

    if etapa_atual.status == "concluido":
        raise HTTPException(status_code=409, detail="Esta etapa já foi concluída")

    # Valida encaminhamentos
    for enc in body.encaminhar:
        if not validate_company_sector(enc.empresa, enc.setor):
            raise HTTPException(status_code=422, detail=f"Encaminhamento inválido: {enc.setor} + {enc.empresa}")

    now = datetime.now(timezone.utc)

    # Conclui etapa atual
    etapa_atual.status = "concluido"
    etapa_atual.problema_solucionado = body.problema_solucionado
    etapa_atual.devolutiva = body.devolutiva
    etapa_atual.respondido_por = uuid.UUID(current["user_id"])
    etapa_atual.concluded_at = now

    # Adiciona encaminhamentos ao final da fila
    max_index = max(e.order_index for e in fca.etapas)
    novas_etapas = []
    for i, enc in enumerate(body.encaminhar, start=1):
        enc_deadline = await get_sla_deadline(db, enc.setor, enc.empresa, now)
        nova = FCAEtapa(
            fca_id=fca.id,
            order_index=max_index + i,
            setor=enc.setor,
            empresa=enc.empresa,
            status="pendente",
            entered_at=now,
            sla_deadline=enc_deadline,
        )
        db.add(nova)
        novas_etapas.append(nova)

    # Atualiza status do FCA
    todas_etapas = fca.etapas + novas_etapas
    pendentes = [e for e in todas_etapas if e.status in ("pendente", "em_andamento") and e.id != etapa_atual.id]

    if pendentes or novas_etapas:
        fca.status = "em_andamento"
        proxima = min(pendentes + novas_etapas, key=lambda e: e.order_index) if (pendentes or novas_etapas) else None
    else:
        fca.status = "aguardando_devolutiva"
        proxima = None

    await db.commit()

    # AuditLog: resposta_etapa
    from models import AuditLog
    db.add(AuditLog(
        fca_id=fca.id,
        usuario_id=uuid.UUID(current["user_id"]),
        acao="resposta_etapa",
        detalhe=f"setor={etapa_atual.setor} order_index={etapa_atual.order_index}",
    ))
    await db.commit()

    # Recarrega para emails
    await db.refresh(fca)
    result2 = await db.execute(
        select(FCA).options(selectinload(FCA.etapas)).where(FCA.id == fca.id)
    )
    fca_reloaded = result2.scalar_one()

    try:
        if proxima:
            # Notifica próximo setor
            etapa_prox = next((e for e in fca_reloaded.etapas if e.order_index == proxima.order_index), None)
            if etapa_prox:
                email_svc.notify_abertura(fca_reloaded, etapa_prox)
        else:
            # Devolutiva ao solicitante
            concluidas = [e for e in fca_reloaded.etapas if e.status == "concluido"]
            email_svc.notify_devolutiva(fca_reloaded, concluidas)
    except Exception:
        pass

    await manager.broadcast(
        "fca_updated",
        destinatarios=[{"setor": e.setor, "empresa": e.empresa} for e in (pendentes + novas_etapas)] if (pendentes or novas_etapas) else []
    )
    await notif_helper.notif_fca_atualizado(db, fca, "Etapa respondida", current["name"], uuid.UUID(current["user_id"]))
    await db.commit()
    return {
        "fca_status": fca.status,
        "etapa_concluida": {"order_index": etapa_atual.order_index, "setor": etapa_atual.setor},
        "proxima_etapa": (
            {"order_index": proxima.order_index, "setor": proxima.setor, "empresa": proxima.empresa}
            if proxima else None
        ),
    }


@router.post("/{fca_id}/encerrar")
async def encerrar_fca(
    fca_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: dict = Depends(any_user),
):
    """Solicitante confirma ciência e encerra o FCA."""
    result = await db.execute(
        select(FCA)
        .options(selectinload(FCA.etapas))
        .where(FCA.id == fca_id)
    )
    fca = result.scalar_one_or_none()
    if not fca:
        raise HTTPException(status_code=404, detail="FCA não encontrado")

    if fca.status != "aguardando_devolutiva":
        raise HTTPException(status_code=409, detail="FCA não está aguardando devolutiva")

    # Só o setor solicitante pode encerrar
    if current["role"] != "admin":
        if fca.setor_solicitante != current["sector"] or fca.empresa_solicitante != current["company"]:
            raise HTTPException(status_code=403, detail="Apenas o setor solicitante pode encerrar o FCA")

    fca.status = "encerrado"
    await db.commit()

    # AuditLog: encerramento
    from models import AuditLog
    db.add(AuditLog(
        fca_id=fca.id,
        usuario_id=uuid.UUID(current["user_id"]),
        acao="encerramento",
    ))
    await db.commit()

    await manager.broadcast("fca_updated", destinatarios=[])
    await notif_helper.notif_fca_atualizado(db, fca, "FCA encerrado", current["name"], uuid.UUID(current["user_id"]))
    await db.commit()
    return {"fca_status": "encerrado"}


# ── Schemas para novos endpoints ──────────────────────────────────────────────

class ComentarioCreate(BaseModel):
    texto: str = Field(..., min_length=1)


class ReabrirBody(BaseModel):
    setor: str
    empresa: str


class ReatribuirBody(BaseModel):
    setor: str
    empresa: str
    justificativa: str = Field(..., min_length=1)


# ── helper: lista todos os destinatários do FCA (para WS broadcast) ───────────

def _destinatarios_fca(fca: FCA) -> list[dict]:
    dest = [{"setor": fca.setor_solicitante, "empresa": fca.empresa_solicitante}]
    for e in fca.etapas:
        entry = {"setor": e.setor, "empresa": e.empresa}
        if entry not in dest:
            dest.append(entry)
    return dest


# ── Comentários internos ──────────────────────────────────────────────────────

@router.get("/{fca_id}/comentarios")
async def list_comentarios(
    fca_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: dict = Depends(any_user),
):
    from models import ComentarioInterno
    result = await db.execute(
        select(FCA).options(selectinload(FCA.etapas)).where(FCA.id == fca_id)
    )
    fca = result.scalar_one_or_none()
    if not fca:
        raise HTTPException(status_code=404, detail="FCA não encontrado")
    if not _can_view(fca, fca.etapas, current):
        raise HTTPException(status_code=403, detail="Acesso negado a este FCA")

    from sqlalchemy.orm import selectinload as sil
    from models import User as UserModel
    coms = await db.execute(
        select(ComentarioInterno)
        .options(selectinload(ComentarioInterno.autor))
        .where(ComentarioInterno.fca_id == fca_id)
        .order_by(ComentarioInterno.created_at.asc())
    )
    items = coms.scalars().all()
    return [
        {
            "id": str(c.id),
            "fca_id": str(c.fca_id),
            "autor": {"id": str(c.autor.id), "name": c.autor.name},
            "texto": c.texto,
            "created_at": c.created_at.isoformat(),
        }
        for c in items
    ]


@router.post("/{fca_id}/comentarios", status_code=status.HTTP_201_CREATED)
async def create_comentario(
    fca_id: UUID,
    body: ComentarioCreate,
    db: AsyncSession = Depends(get_db),
    current: dict = Depends(any_user),
):
    from models import ComentarioInterno
    if not body.texto.strip():
        raise HTTPException(status_code=422, detail="Texto do comentário não pode ser vazio")

    result = await db.execute(
        select(FCA).options(selectinload(FCA.etapas)).where(FCA.id == fca_id)
    )
    fca = result.scalar_one_or_none()
    if not fca:
        raise HTTPException(status_code=404, detail="FCA não encontrado")
    if not _can_view(fca, fca.etapas, current):
        raise HTTPException(status_code=403, detail="Acesso negado a este FCA")

    comentario = ComentarioInterno(
        fca_id=fca_id,
        autor_id=uuid.UUID(current["user_id"]),
        texto=body.texto.strip(),
    )
    db.add(comentario)
    await db.commit()
    await db.refresh(comentario)

    # Carrega autor para resposta
    from models import User as UserModel
    autor_result = await db.execute(select(UserModel).where(UserModel.id == comentario.autor_id))
    autor = autor_result.scalar_one()

    await manager.broadcast("fca_updated", destinatarios=_destinatarios_fca(fca))
    await notif_helper.notif_fca_comentario(db, fca, current["name"], uuid.UUID(current["user_id"]))
    await db.commit()
    return {
        "id": str(comentario.id),
        "fca_id": str(comentario.fca_id),
        "autor": {"id": str(autor.id), "name": autor.name},
        "texto": comentario.texto,
        "created_at": comentario.created_at.isoformat(),
    }


# ── Auditoria ─────────────────────────────────────────────────────────────────

admin_user = require_user(required_role="admin")


@router.get("/{fca_id}/audit")
async def get_audit(
    fca_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: dict = Depends(admin_user),
):
    from models import AuditLog, User as UserModel
    result = await db.execute(
        select(AuditLog)
        .options(selectinload(AuditLog.usuario))
        .where(AuditLog.fca_id == fca_id)
        .order_by(AuditLog.created_at.asc())
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "fca_id": str(log.fca_id) if log.fca_id else None,
            "usuario": {"id": str(log.usuario.id), "name": log.usuario.name} if log.usuario else None,
            "acao": log.acao,
            "detalhe": log.detalhe,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


# ── Reabrir FCA ───────────────────────────────────────────────────────────────

@router.post("/{fca_id}/reabrir")
async def reabrir_fca(
    fca_id: UUID,
    body: ReabrirBody,
    db: AsyncSession = Depends(get_db),
    current: dict = Depends(admin_user),
):
    from models import AuditLog
    result = await db.execute(
        select(FCA).options(selectinload(FCA.etapas)).where(FCA.id == fca_id)
    )
    fca = result.scalar_one_or_none()
    if not fca:
        raise HTTPException(status_code=404, detail="FCA não encontrado")
    if fca.status != "encerrado":
        raise HTTPException(status_code=409, detail="FCA não está encerrado")

    now = datetime.now(timezone.utc)
    max_index = max((e.order_index for e in fca.etapas), default=0)
    deadline = await get_sla_deadline(db, body.setor, body.empresa, now)
    nova_etapa = FCAEtapa(
        fca_id=fca.id,
        order_index=max_index + 1,
        setor=body.setor,
        empresa=body.empresa,
        status="pendente",
        entered_at=now,
        sla_deadline=deadline,
    )
    db.add(nova_etapa)
    fca.status = "em_andamento"
    db.add(AuditLog(
        fca_id=fca.id,
        usuario_id=uuid.UUID(current["user_id"]),
        acao="reabertura",
        detalhe=f"setor={body.setor} empresa={body.empresa}",
    ))
    await db.commit()

    await manager.broadcast("fca_updated", destinatarios=[{"setor": body.setor, "empresa": body.empresa}])
    return {"fca_status": fca.status, "nova_etapa": {"setor": body.setor, "empresa": body.empresa, "order_index": max_index + 1}}


# ── Reatribuir etapa ──────────────────────────────────────────────────────────

@router.post("/{fca_id}/reatribuir")
async def reatribuir_fca(
    fca_id: UUID,
    body: ReatribuirBody,
    db: AsyncSession = Depends(get_db),
    current: dict = Depends(admin_user),
):
    from models import AuditLog
    result = await db.execute(
        select(FCA).options(selectinload(FCA.etapas)).where(FCA.id == fca_id)
    )
    fca = result.scalar_one_or_none()
    if not fca:
        raise HTTPException(status_code=404, detail="FCA não encontrado")

    etapa_ativa = _etapa_ativa(fca.etapas)
    if not etapa_ativa:
        raise HTTPException(status_code=409, detail="FCA não possui etapa ativa para reatribuição")

    now = datetime.now(timezone.utc)
    setor_origem = etapa_ativa.setor
    empresa_origem = etapa_ativa.empresa

    # Encerra etapa ativa com a justificativa
    etapa_ativa.status = "concluido"
    etapa_ativa.concluded_at = now
    etapa_ativa.devolutiva = body.justificativa

    # Cria nova etapa para o destino
    max_index = max(e.order_index for e in fca.etapas)
    deadline = await get_sla_deadline(db, body.setor, body.empresa, now)
    nova_etapa = FCAEtapa(
        fca_id=fca.id,
        order_index=max_index + 1,
        setor=body.setor,
        empresa=body.empresa,
        status="pendente",
        entered_at=now,
        sla_deadline=deadline,
    )
    db.add(nova_etapa)
    db.add(AuditLog(
        fca_id=fca.id,
        usuario_id=uuid.UUID(current["user_id"]),
        acao="reatribuicao",
        detalhe=f"origem={setor_origem}/{empresa_origem} destino={body.setor}/{body.empresa}",
    ))
    await db.commit()

    await manager.broadcast("fca_updated", destinatarios=[{"setor": body.setor, "empresa": body.empresa}])
    return {"fca_status": fca.status, "nova_etapa": {"setor": body.setor, "empresa": body.empresa, "order_index": max_index + 1}}


# ── Cancelar FCA ──────────────────────────────────────────────────────────────

class CancelarBody(BaseModel):
    motivo: str = Field(..., min_length=1)


@router.post("/{fca_id}/cancelar")
async def cancelar_fca(
    fca_id: UUID,
    body: CancelarBody,
    db: AsyncSession = Depends(get_db),
    current: dict = Depends(admin_user),
):
    """Admin cancela um FCA. FCA cancelado fica invisível para não-admins."""
    from models import AuditLog
    result = await db.execute(
        select(FCA).options(selectinload(FCA.etapas)).where(FCA.id == fca_id)
    )
    fca = result.scalar_one_or_none()
    if not fca:
        raise HTTPException(status_code=404, detail="FCA não encontrado")
    if fca.status == "cancelado":
        raise HTTPException(status_code=409, detail="FCA já está cancelado")

    # Encerra qualquer etapa ativa
    now = datetime.now(timezone.utc)
    for etapa in fca.etapas:
        if etapa.status in ("pendente", "em_andamento"):
            etapa.status = "concluido"
            etapa.concluded_at = now
            etapa.devolutiva = f"Cancelado: {body.motivo}"

    fca.status = "cancelado"
    db.add(AuditLog(
        fca_id=fca.id,
        usuario_id=uuid.UUID(current["user_id"]),
        acao="cancelamento",
        detalhe=body.motivo,
    ))
    await db.commit()

    await manager.broadcast("fca_updated", destinatarios=[])
    return {"fca_status": "cancelado"}
