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

# Mapeamento triagem: (area_causadora, empresa_causadora) -> (setor, empresa)
TRIAGEM: dict[tuple[str, str], tuple[str, str]] = {
    ("ACL", "ACI_MATRIZ"):         ("ACL", "ACI_MATRIZ"),
    ("ACL", "ACI_FILIAL"):         ("ACL", "ACI_FILIAL"),
    ("ACL", "SINOBRAS"):           ("ACL", "SINOBRAS"),
    ("Comercial", "ACC"):          ("Comercial", "ACC"),
    ("PCP", "ACI_MATRIZ"):         ("PCP", "ACI_MATRIZ"),
    ("PCP", "ACI_FILIAL"):         ("PCP", "ACI_FILIAL"),
    ("PCP", "SINOBRAS"):           ("PCP", "SINOBRAS"),
    ("Qualidade", "ACI_MATRIZ"):   ("Qualidade", "ACI_MATRIZ"),
    ("Qualidade", "ACI_FILIAL"):   ("Qualidade", "ACI_FILIAL"),
    ("Qualidade", "SINOBRAS"):     ("Qualidade", "SINOBRAS"),
    ("MEP", "ACI_MATRIZ"):         ("MEP", "ACI_MATRIZ"),
    ("MEP", "ACI_FILIAL"):         ("MEP", "ACI_FILIAL"),
    ("MEP", "SINOBRAS"):           ("MEP", "SINOBRAS"),
    ("Expedicao", "ACI_MATRIZ"):   ("Expedicao", "ACI_MATRIZ"),
    ("Expedicao", "ACI_FILIAL"):   ("Expedicao", "ACI_FILIAL"),
    ("Expedicao", "SINOBRAS"):     ("Expedicao", "SINOBRAS"),
    ("Customer_Service", "ACC"):   ("Customer_Service", "ACC"),
    ("Producao", "ACI_MATRIZ"):    ("Producao", "ACI_MATRIZ"),
    ("Producao", "ACI_FILIAL"):    ("Producao", "ACI_FILIAL"),
    ("Producao", "SINOBRAS"):      ("Producao", "SINOBRAS"),
}


def validate_company_sector(company: str, sector: str) -> bool:
    """Retorna True se a combinação empresa+setor é válida."""
    allowed = SECTORS_BY_COMPANY.get(company, [])
    return sector in allowed


def get_triagem(area_causadora: str, empresa_causadora: str) -> tuple[str, str] | None:
    """Retorna (setor, empresa) da primeira etapa ou None se combinação inválida."""
    return TRIAGEM.get((area_causadora, empresa_causadora))
