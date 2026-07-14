-- Migração: adiciona coluna notif_som na tabela users
-- Execute via psql ou pelo painel do banco antes de subir o backend atualizado

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS notif_som VARCHAR(10) NOT NULL DEFAULT 'som1';
