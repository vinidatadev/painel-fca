-- Migração: adiciona campo acesso_relatorio na tabela users
-- Flag booleano que permite conceder acesso à BI_View para usuários não-admin.
-- Padrão: false — apenas admins têm acesso por padrão.
ALTER TABLE users ADD COLUMN IF NOT EXISTS acesso_relatorio BOOLEAN NOT NULL DEFAULT FALSE;
