-- Migración 002: Tablas de mensajería
-- Descripción: Añade tablas para el sistema de mensajería P2P

-- Tabla de mensajes
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_peer_id STRING NOT NULL,
    to_peer_id STRING NOT NULL,
    message_type STRING NOT NULL,
    content BYTES NOT NULL,
    encrypted BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT current_timestamp(),
    delivered_at TIMESTAMPTZ,
    INDEX messages_from_idx (from_peer_id),
    INDEX messages_to_idx (to_peer_id),
    INDEX messages_created_at_idx (created_at)
);

-- Tabla de archivos compartidos
CREATE TABLE IF NOT EXISTS shared_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_hash STRING UNIQUE NOT NULL,
    filename STRING NOT NULL,
    size_bytes INT8 NOT NULL,
    mime_type STRING,
    owner_peer_id STRING NOT NULL,
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT current_timestamp(),
    INDEX shared_files_hash_idx (file_hash),
    INDEX shared_files_owner_idx (owner_peer_id)
);

-- Registrar esta migración
INSERT INTO schema_migrations (version, name) 
VALUES (2, '002_messaging_tables') 
ON CONFLICT (version) DO NOTHING;
