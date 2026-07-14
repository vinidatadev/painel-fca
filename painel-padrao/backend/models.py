import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Integer, BigInteger, Text, ForeignKey, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(20), nullable=False, default="local")
    company: Mapped[str] = mapped_column(String(20), nullable=False, default="ACC")
    sector: Mapped[str] = mapped_column(String(30), nullable=False, default="Customer_Service")
    role: Mapped[str] = mapped_column(String(10), nullable=False, default="user")
    matricula: Mapped[str | None] = mapped_column(String(20), nullable=True)
    turno: Mapped[str | None] = mapped_column(String(1), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notif_email: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notif_sms: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notif_push: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notif_som: Mapped[str] = mapped_column(String(10), default="som1", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    fcas_criados: Mapped[list["FCA"]] = relationship("FCA", back_populates="criado_por_user", foreign_keys="FCA.created_by")
    etapas_respondidas: Mapped[list["FCAEtapa"]] = relationship("FCAEtapa", back_populates="respondido_por_user")


class OpcaoLista(Base):
    """Tabela genérica para listas configuráveis: causas, acoes, ufs."""
    __tablename__ = "opcoes_lista"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # 'causa' | 'acao' | 'uf'
    valor: Mapped[str] = mapped_column(String(200), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class SlaRegra(Base):
    """Regras de SLA por escopo (global → empresa → setor+empresa)."""
    __tablename__ = "sla_regras"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa: Mapped[str | None] = mapped_column(String(20), nullable=True)   # None = global
    setor: Mapped[str | None] = mapped_column(String(30), nullable=True)     # None = toda a empresa
    valor: Mapped[int] = mapped_column(Integer, nullable=False)               # ex: 4
    unidade: Mapped[str] = mapped_column(String(10), nullable=False)          # minuto | hora | dia
    prazo_minutos: Mapped[int] = mapped_column(Integer, nullable=False)       # calculado na criação
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class FCA(Base):
    __tablename__ = "fcas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cod_fca: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    causa: Mapped[str] = mapped_column(String(100), nullable=False)
    acao: Mapped[str] = mapped_column(String(150), nullable=False)
    uf: Mapped[str] = mapped_column(String(2), nullable=False)
    numero_remessa: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # mantido por compatibilidade
    remessas: Mapped[list[int] | None] = mapped_column(ARRAY(BigInteger), nullable=True)
    detalhe: Mapped[str | None] = mapped_column(Text, nullable=True)
    anexo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    anexo_urls: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)  # múltiplos anexos
    setor_solicitante: Mapped[str] = mapped_column(String(30), nullable=False)
    empresa_solicitante: Mapped[str] = mapped_column(String(20), nullable=False)
    area_causadora: Mapped[str] = mapped_column(String(30), nullable=False)
    empresa_causadora: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(25), nullable=False, default="aberto")
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    criado_por_user: Mapped["User"] = relationship("User", back_populates="fcas_criados", foreign_keys=[created_by])
    etapas: Mapped[list["FCAEtapa"]] = relationship("FCAEtapa", back_populates="fca", order_by="FCAEtapa.order_index")


class FCAEtapa(Base):
    __tablename__ = "fca_etapas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fca_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("fcas.id"), nullable=False, index=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    setor: Mapped[str] = mapped_column(String(30), nullable=False)
    empresa: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="pendente")
    problema_solucionado: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    devolutiva: Mapped[str | None] = mapped_column(Text, nullable=True)
    respondido_por: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    entered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    concluded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    fca: Mapped["FCA"] = relationship("FCA", back_populates="etapas")
    respondido_por_user: Mapped["User | None"] = relationship("User", back_populates="etapas_respondidas")


# ── Help / Suporte ────────────────────────────────────────────────────────────

class HelpTicket(Base):
    __tablename__ = "help_tickets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    anexo_keys: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)  # múltiplos anexos
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="aberto")  # aberto | em_andamento | resolvido | fechado
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    criado_por: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    mensagens: Mapped[list["HelpMensagem"]] = relationship(
        "HelpMensagem", back_populates="ticket", order_by="HelpMensagem.created_at"
    )


class HelpMensagem(Base):
    """Respostas/comentários em um ticket de help."""
    __tablename__ = "help_mensagens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("help_tickets.id"), nullable=False, index=True)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    autor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    ticket: Mapped["HelpTicket"] = relationship("HelpTicket", back_populates="mensagens")
    autor: Mapped["User"] = relationship("User", foreign_keys=[autor_id])
