-- Initialize manual SQL migrations history for the auth schema
-- Idempotent: safe to run multiple times

BEGIN;

CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE IF NOT EXISTS auth.migration_history (
    id           bigserial PRIMARY KEY,
    schema_name  text        NOT NULL,
    file_seq     int         NOT NULL,
    name         text        NOT NULL, -- full filename e.g. 0001_auth_bootstrap.sql
    checksum     text        NULL,     -- optional md5 of file contents
    applied_by   text        NOT NULL DEFAULT current_user,
    applied_at   timestamptz NOT NULL DEFAULT now(),
    notes        text        NULL,
    CONSTRAINT uq_migration_history_schema_seq UNIQUE (schema_name, file_seq),
    CONSTRAINT uq_migration_history_schema_name UNIQUE (schema_name, name)
);

COMMIT;
