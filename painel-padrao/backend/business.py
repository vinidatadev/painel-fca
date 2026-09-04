# Regras de negócio: empresas, setores, validações e triagem automática

COMPANIES = ["ACI_MATRIZ", "ACI_FILIAL", "SINOBRAS", "ACC"]

SECTORS_BY_COMPANY: dict[str, list[str]] = {
    "ACI_MATRIZ": ["ACL", "PCP", "Qualidade", "MEP", "Expedicao", "Producao"],
    "ACI_FILIAL": ["ACL", "PCP", "Qualidade", "MEP", "Expedicao", "Producao"],
    "SINOBRAS":   ["ACL", "PCP", "Qualidade", "MEP", "Expedicao", "Producao"],
    "ACC":        ["Comercial", "Customer_Service"],
}

# Setores que podem ABRIR FCA (excluindo Producao)
SECTORS_CAN_OPEN = ["ACL", "PCP", "Qualidade", "MEP", "Expedicao", "Comercial", "Customer_Service"]

# Setores que recebem devolutiva
SECTORS_WITH_RETURN = ["ACL", "Qualidade", "MEP", "Expedicao", "Customer_Service"]

# Áreas (mesmo conceito de "setor") configuráveis — derivadas do mapeamento empresa→setores.
# Usadas no formulário de FCA ("Área Causadora"), no perfil do usuário e na triagem.
AREAS = sorted({s for setores in SECTORS_BY_COMPANY.values() for s in setores})

# Vínculos padrão Área ↔ Empresa, derivados do mapeamento empresa→setores.
# Servem apenas para semear a tabela areas_empresas — o admin gerencia depois
# em Configurações → "Empresas por Área".
DEFAULT_AREA_EMPRESAS: dict[str, list[str]] = {}
for _empresa, _setores in SECTORS_BY_COMPANY.items():
    for _setor in _setores:
        DEFAULT_AREA_EMPRESAS.setdefault(_setor, []).append(_empresa)

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
    "Atuar junto com comercial",
    "Avaliar o material",
    "Bloquear os fardos",
    "Confere o estoque e programação",
    "Sinalizar o time comercial",
    "Desobstruir material",
    "Corrigir peso",
]

UFS = [
    "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA",
    "MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN",
    "RO","RR","RS","SC","SE","SP","TO",
]

def validate_company_sector(company: str, sector: str) -> bool:
    """Retorna True se a combinação empresa+setor é válida."""
    allowed = SECTORS_BY_COMPANY.get(company, [])
    return sector in allowed
