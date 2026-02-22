-- Migración 001: Esquema inicial
-- Descripción: Crea las tablas básicas del sistema

-- Tabla de versión de schema (para tracking de migraciones)
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INT PRIMARY KEY,
    name STRING NOT NULL,
    applied_at TIMESTAMPTZ DEFAULT current_timestamp()
);

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username STRING UNIQUE NOT NULL,
    email STRING UNIQUE NOT NULL,
    password_hash STRING NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT current_timestamp(),
    updated_at TIMESTAMPTZ DEFAULT current_timestamp(),
    INDEX users_username_idx (username),
    INDEX users_email_idx (email)
);

-- Tabla de nodos P2P
CREATE TABLE IF NOT EXISTS nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    peer_id STRING UNIQUE NOT NULL,
    multiaddr STRING NOT NULL,
    public_key STRING,
    last_seen TIMESTAMPTZ DEFAULT current_timestamp(),
    status STRING DEFAULT 'active',
    reputation INT DEFAULT 100,
    created_at TIMESTAMPTZ DEFAULT current_timestamp(),
    INDEX nodes_peer_id_idx (peer_id),
    INDEX nodes_status_idx (status),
    INDEX nodes_last_seen_idx (last_seen)
);

-- Tabla de sesiones
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token STRING UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT current_timestamp(),
    INDEX sessions_token_idx (token),
    INDEX sessions_user_id_idx (user_id),
    INDEX sessions_expires_at_idx (expires_at)
);

-- Registrar esta migración
INSERT INTO schema_migrations (version, name) 
VALUES (1, '001_initial_schema') 
ON CONFLICT (version) DO NOTHING;
