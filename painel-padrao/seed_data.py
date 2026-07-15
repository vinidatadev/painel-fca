"""
seed_data.py — Popula o banco com dados realistas para testar o relatório BI.

Uso (dentro do container backend):
    DATABASE_URL=postgresql://admin:admin@db:5432/appdb python /tmp/seed_data.py

Cria:
  - 1 admin  (admin@fca.local / Admin@123)
  - 10 usuários distribuídos por empresa/setor  (senha: Senha@123)
  - 80 FCAs com datas nos últimos 60 dias + etapas com SLA variado
"""

import asyncio, os, uuid, random, hashlib
from datetime import datetime, timezone, timedelta

import asyncpg
import bcrypt

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin@db:5432/appdb")
# asyncpg não aceita o prefixo "postgresql+asyncpg"
DSN = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

# ─────────────────────────────────────────────────────────────────────────────
CAUSAS = [
    "Carro com problema mecânico",
    "Excesso de PBT",
    "Formatação da carga",
    "Material indisponível",
    "Material obstruído",
    "Material oxidado",
    "Pedido fora do padrão",
    "Peso fardo 1 tonelada",
    "Divergência de peso",
]
ACOES = [
    "Ajustar a carga",
    "Analisar e atuar junto com comercial",
    "Avaliar o material",
    "Bloquear os fardos",
    "Confere o estoque e programação",
    "Sinalizar o time comercial",
    "Desobstruir material",
    "Corrigir peso",
]
UFS = ["PB","PI","MT","PA","PR","AL","MS","PE","AP","AM","SP","RJ","MG","BA","GO","RS"]

TRIAGEM = {
    ("ACL",              "ACI_MATRIZ"):  ("ACL",              "ACI_MATRIZ"),
    ("ACL",              "ACI_FILIAL"):  ("ACL",              "ACI_FILIAL"),
    ("ACL",              "SINOBRAS"):    ("ACL",              "SINOBRAS"),
    ("PCP",              "ACI_MATRIZ"):  ("PCP",              "ACI_MATRIZ"),
    ("PCP",              "ACI_FILIAL"):  ("PCP",              "ACI_FILIAL"),
    ("Qualidade",        "ACI_MATRIZ"):  ("Qualidade",        "ACI_MATRIZ"),
    ("Qualidade",        "ACI_FILIAL"):  ("Qualidade",        "ACI_FILIAL"),
    ("MEP",              "ACI_MATRIZ"):  ("MEP",              "ACI_MATRIZ"),
    ("MEP",              "ACI_FILIAL"):  ("MEP",              "ACI_FILIAL"),
    ("Expedicao",        "ACI_MATRIZ"):  ("Expedicao",        "ACI_MATRIZ"),
    ("Expedicao",        "ACI_FILIAL"):  ("Expedicao",        "ACI_FILIAL"),
    ("Customer_Service", "ACC"):         ("Customer_Service", "ACC"),
    ("Comercial",        "ACC"):         ("Comercial",        "ACC"),
}

# Distribuição de áreas causadoras (par, peso)
AREA_POOL = (
    [("ACL",              "ACI_MATRIZ")] * 22 +
    [("ACL",              "ACI_FILIAL")] * 15 +
    [("PCP",              "ACI_MATRIZ")] *  8 +
    [("PCP",              "ACI_FILIAL")] *  5 +
    [("Qualidade",        "ACI_MATRIZ")] *  6 +
    [("Qualidade",        "ACI_FILIAL")] *  4 +
    [("MEP",              "ACI_MATRIZ")] *  4 +
    [("MEP",              "ACI_FILIAL")] *  3 +
    [("Expedicao",        "ACI_MATRIZ")] *  4 +
    [("Expedicao",        "ACI_FILIAL")] *  3 +
    [("Customer_Service", "ACC")]        *  8 +
    [("Comercial",        "ACC")]        *  6
)

# Causa dominante = "Carro com problema mecânico"
CAUSA_POOL = (
    [CAUSAS[0]] * 35 + [CAUSAS[1]] * 14 + [CAUSAS[2]] * 4 +
    [CAUSAS[3]] * 3  + [CAUSAS[4]] * 3  + [CAUSAS[5]] * 3 +
    [CAUSAS[6]] * 2  + [CAUSAS[7]] * 2  + [CAUSAS[8]] * 2
)

STATUSES = (
    ["aberto"] * 35 + ["em_andamento"] * 5 +
    ["aguardando_devolutiva"] * 5 + ["encerrado"] * 50 + ["cancelado"] * 5
)

NOW = datetime.now(timezone.utc)

def uid() -> str:
    return str(uuid.uuid4())

def rnd_date(max_days=60, min_days=1):
    delta = random.randint(min_days * 1440, max_days * 1440)
    return NOW - timedelta(minutes=delta)

def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=10)).decode()

# ─────────────────────────────────────────────────────────────────────────────
async def main():
    print(f"Conectando em: {DSN.split('@')[-1]}")
    conn = await asyncpg.connect(DSN)

    # ── 1. Admin ──────────────────────────────────────────────────────────────
    print("Criando admin...")
    admin_id = uid()
    row = await conn.fetchrow("""
        INSERT INTO users (id, email, name, password_hash, auth_provider,
                           company, sector, role, acesso_relatorio, is_active,
                           notif_email, notif_sms, notif_push, notif_som, created_at)
        VALUES ($1,$2,$3,$4,'local','ACI_MATRIZ','ACL','admin',true,true,true,false,true,'som1',$5)
        ON CONFLICT (email) DO UPDATE
            SET role='admin', acesso_relatorio=true, password_hash=$4
        RETURNING id
    """, admin_id, "admin@fca.local", "Administrador", hash_pw("Admin@123"), NOW)
    admin_id = str(row["id"])

    # ── 2. Usuários ───────────────────────────────────────────────────────────
    print("Criando usuários...")
    USER_DEFS = [
        ("joao.acl@fca.local",        "João Silva",       "ACI_MATRIZ", "ACL"),
        ("maria.qualidade@fca.local",  "Maria Souza",      "ACI_MATRIZ", "Qualidade"),
        ("pedro.pcp@fca.local",        "Pedro Lima",       "ACI_FILIAL", "PCP"),
        ("ana.mep@fca.local",          "Ana Costa",        "ACI_FILIAL", "MEP"),
        ("carlos.expedicao@fca.local", "Carlos Mendes",    "SINOBRAS",   "Expedicao"),
        ("julia.acl@fca.local",        "Julia Ferreira",   "SINOBRAS",   "ACL"),
        ("roberto.cs@fca.local",       "Roberto Alves",    "ACC",        "Customer_Service"),
        ("fernanda.com@fca.local",     "Fernanda Gomes",   "ACC",        "Comercial"),
        ("lucas.producao@fca.local",   "Lucas Rocha",      "ACI_MATRIZ", "Producao"),
        ("camila.acl2@fca.local",      "Camila Nunes",     "ACI_FILIAL", "ACL"),
    ]
    all_creators = [{"id": admin_id, "company": "ACI_MATRIZ", "sector": "ACL"}]
    for email, name, company, sector in USER_DEFS:
        row = await conn.fetchrow("""
            INSERT INTO users (id, email, name, password_hash, auth_provider,
                               company, sector, role, acesso_relatorio, is_active,
                               notif_email, notif_sms, notif_push, notif_som, created_at)
            VALUES ($1,$2,$3,$4,'local',$5,$6,'user',false,true,true,false,true,'som1',$7)
            ON CONFLICT (email) DO UPDATE SET company=$5, sector=$6, password_hash=$4
            RETURNING id
        """, uid(), email, name, hash_pw("Senha@123"), company, sector, NOW)
        all_creators.append({"id": str(row["id"]), "company": company, "sector": sector})

    # ── 3. Opções (seed se vazio) ─────────────────────────────────────────────
    count = await conn.fetchval("SELECT COUNT(*) FROM opcoes_lista")
    if count == 0:
        print("Inserindo opções padrão...")
        for i, c in enumerate(CAUSAS):
            await conn.execute(
                "INSERT INTO opcoes_lista (id,tipo,valor,ativo,ordem) VALUES ($1,'causa',$2,true,$3)",
                uid(), c, i)
        for i, a in enumerate(ACOES):
            await conn.execute(
                "INSERT INTO opcoes_lista (id,tipo,valor,ativo,ordem) VALUES ($1,'acao',$2,true,$3)",
                uid(), a, i)
        for i, u in enumerate(UFS):
            await conn.execute(
                "INSERT INTO opcoes_lista (id,tipo,valor,ativo,ordem) VALUES ($1,'uf',$2,true,$3)",
                uid(), u, i)

    # ── 4. FCAs + Etapas ──────────────────────────────────────────────────────
    print("Criando 80 FCAs...")
    SLA_HORAS = 12

    import time
    seed_ts = int(time.time()) % 100000  # sufixo único por execução

    for i in range(1, 81):
        fca_id  = uid()
        cod_fca = f"FCA-{seed_ts}{i:03d}"
        causa   = random.choice(CAUSA_POOL)
        acao    = random.choice(ACOES)
        uf      = random.choice(UFS)
        area_causadora, empresa_causadora = random.choice(AREA_POOL)
        creator = random.choice(all_creators)
        status  = random.choice(STATUSES)
        created = rnd_date(max_days=60, min_days=1)
        updated = min(created + timedelta(hours=random.randint(1, 72)), NOW)

        await conn.execute("""
            INSERT INTO fcas (id, cod_fca, causa, acao, uf, remessas, detalhe,
                              setor_solicitante, empresa_solicitante,
                              area_causadora, empresa_causadora,
                              status, created_by, created_at, updated_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
        """, fca_id, cod_fca, causa, acao, uf,
             [random.randint(80000000, 99999999)],
             f"Ocorrência registrada — {causa.lower()}.",
             creator["sector"], creator["company"],
             area_causadora, empresa_causadora,
             status, creator["id"], created, updated)

        # Etapa
        triagem = TRIAGEM.get((area_causadora, empresa_causadora))
        if not triagem:
            continue

        etapa_setor, etapa_empresa = triagem
        entered  = created + timedelta(minutes=random.randint(1, 30))
        deadline = entered + timedelta(hours=SLA_HORAS)

        if status in ("encerrado", "cancelado"):
            dentro_sla  = random.random() < 0.70
            offset_h    = random.uniform(1, SLA_HORAS - 1) if dentro_sla else random.uniform(SLA_HORAS + 1, SLA_HORAS * 3)
            concluded   = min(entered + timedelta(hours=offset_h), NOW)
            solucionado = random.random() < 0.78
            await conn.execute("""
                INSERT INTO fca_etapas (id, fca_id, order_index, setor, empresa, status,
                                        problema_solucionado, devolutiva, respondido_por,
                                        entered_at, concluded_at, sla_deadline)
                VALUES ($1,$2,1,$3,$4,'concluido',$5,$6,$7,$8,$9,$10)
            """, uid(), fca_id, etapa_setor, etapa_empresa,
                 solucionado,
                 "Análise concluída." if solucionado else "Não foi possível solucionar.",
                 admin_id, entered, concluded, deadline)
        else:
            etapa_status = {
                "aguardando_devolutiva": "ag_devolutiva",
                "em_andamento": "pendente",
                "aberto": "pendente",
            }.get(status, "pendente")
            await conn.execute("""
                INSERT INTO fca_etapas (id, fca_id, order_index, setor, empresa,
                                        status, entered_at, sla_deadline)
                VALUES ($1,$2,1,$3,$4,$5,$6,$7)
            """, uid(), fca_id, etapa_setor, etapa_empresa,
                 etapa_status, entered, deadline)

    await conn.close()
    print("""
✅ Seed concluído!
   admin@fca.local   →  Admin@123
   demais usuários   →  Senha@123
   FCAs criados: 80
""")

asyncio.run(main())
