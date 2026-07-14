"""Envio de e-mails via SMTP (configuração via .env). Se não configurado, apenas loga."""
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@fca.local")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost")

# E-mails dos setores: em produção seria uma tabela; aqui usamos env vars ou dict configurável
SECTOR_EMAILS: dict[str, str] = {}
for key, val in os.environ.items():
    if key.startswith("EMAIL_SECTOR_"):
        sector = key.replace("EMAIL_SECTOR_", "").replace("_", " ")
        SECTOR_EMAILS[sector] = val


def _send(to: list[str], subject: str, body: str):
    if not SMTP_HOST or not to:
        logger.info("[EMAIL SIMULADO] Para: %s | Assunto: %s", to, subject)
        logger.debug("[EMAIL BODY]\n%s", body)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(to)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(EMAIL_FROM, to, msg.as_string())
        logger.info("[EMAIL ENVIADO] Para: %s | Assunto: %s", to, subject)
    except Exception as e:
        logger.error("[EMAIL ERRO] %s", e)


def notify_abertura(fca, etapa):
    """E-mail de abertura para o setor responsável da etapa atual."""
    setor = etapa.setor
    uf_suffix = f" - {fca.uf}" if setor == "ACL" else ""
    subject = f"Novo FCA Registrado - {fca.area_causadora}{uf_suffix}"

    body = f"""Prezados,

Informamos que foi registrado um novo FCA. Seguem os detalhes:

CodFCA: {fca.cod_fca}
________________________________________
Causa do FCA:         {fca.causa}
Setor Responsável:    {fca.setor_solicitante}
Área Causadora:       {fca.area_causadora}
Ação:                 {fca.acao}
UF:                   {fca.uf}
Empresa:              {fca.empresa_causadora}
Número da Remessa:    {fca.numero_remessa or '-'}
Detalhe / Observação: {fca.detalhe or '-'}
________________________________________

Para acessar e tratar o FCA, acesse:
{FRONTEND_URL}/fca/{fca.id}

Atenciosamente,
Customer Service
"""
    recipients = _get_sector_recipients(setor, etapa.empresa)
    _send(recipients, subject, body)


def notify_devolutiva(fca, etapas_concluidas):
    """E-mail de devolutiva ao solicitante quando fila esgota."""
    subject = f"FCA Respondido - {fca.area_causadora} - {fca.cod_fca}"

    historico = ""
    for e in etapas_concluidas:
        sol = "Sim" if e.problema_solucionado else "Não"
        historico += f"\n[{e.setor} / {e.empresa}]\n  Problema Solucionado: {sol}\n  Devolutiva: {e.devolutiva or '-'}\n"

    body = f"""Prezados,

Informamos que foi respondido/solucionado o FCA registrado para a área: {fca.setor_solicitante}

Resultado consolidado das tratativas:
{historico}
Dados de Registro:
CodFCA: {fca.cod_fca}
________________________________________
Causa do FCA:         {fca.causa}
Setor Responsável:    {fca.setor_solicitante}
Área Causadora:       {fca.area_causadora}
Ação:                 {fca.acao}
UF:                   {fca.uf}
Empresa:              {fca.empresa_solicitante}
Número da Remessa:    {fca.numero_remessa or '-'}
Detalhe / Observação: {fca.detalhe or '-'}
________________________________________

Atenciosamente,
Customer Service
"""
    recipients = _get_sector_recipients(fca.setor_solicitante, fca.empresa_solicitante)
    _send(recipients, subject, body)


def _get_sector_recipients(setor: str, empresa: str) -> list[str]:
    key = f"{setor}_{empresa}"
    email = SECTOR_EMAILS.get(key) or SECTOR_EMAILS.get(setor, "")
    return [email] if email else []
