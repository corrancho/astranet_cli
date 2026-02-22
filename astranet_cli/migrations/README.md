# Sistema de Migraciones de Base de Datos

## Descripción

El sistema de migraciones permite gestionar el esquema de la base de datos de forma versionada y reproducible.

## Estructura

```
astranet_cli/
├── migration_manager.py        # Gestor de migraciones
└── migrations/                 # Directorio de migraciones
    ├── 001_initial_schema.sql
    ├── 002_messaging_tables.sql
    └── ...
```

## Cómo Funciona

1. **Creación automática**: Al inicializar el cluster, se crea automáticamente la base de datos y se aplican todas las migraciones pendientes.

2. **Versionado**: Cada migración tiene un número de versión (001, 002, etc.)

3. **Tracking**: La tabla `schema_migrations` registra qué migraciones se han aplicado.

## Uso

### Aplicar migraciones pendientes

```bash
python3 astranet.py
# → Opción 1: Gestionar CockroachDB
# → Opción 5: Crear/Inicializar base de datos
```

O desde Python:
```python
from astranet_cli.cockroach_manager import CockroachManager
from astranet_cli.migration_manager import MigrationManager

crdb = CockroachManager()
migrator = MigrationManager(crdb)
migrator.migrate()
```

### Crear nueva migración

Desde Python:
```python
from astranet_cli.cockroach_manager import CockroachManager
from astranet_cli.migration_manager import MigrationManager

crdb = CockroachManager()
migrator = MigrationManager(crdb)

# Crea archivo migrations/003_nombre_descripcion.sql
migrator.create_migration("add_comments_table")
```

Luego edita el archivo y añade tu SQL.

### Ver versionactual

```python
migrator = MigrationManager(crdb)
version = migrator.get_current_version()
print(f"Versión actual: {version}")
```

## Formato de Archivos de Migración

```sql
-- Migración XXX: Título descriptivo
-- Descripción: Explicación de qué hace esta migración

-- Tu SQL aquí
CREATE TABLE IF NOT EXISTS mi_tabla (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre STRING NOT NULL,
    created_at TIMESTAMPTZ DEFAULT current_timestamp()
);

-- IMPORTANTE: Registrar la migración al final
INSERT INTO schema_migrations (version, name) 
VALUES (XXX, 'XXX_nombre_archivo') 
ON CONFLICT (version) DO NOTHING;
```

## Convenciones

- **Nombres de archivo**: `NNN_descripcion_corta.sql` (ej: `003_add_comments.sql`)
- **Versionado**: Números secuenciales de 3 dígitos (001, 002, 003...)
- **Idempotencia**: Usa `IF NOT EXISTS`, `IF EXISTS` para que las migraciones sean seguras de ejecutar múltiples veces
- **Un cambio por migración**: Cada migración debe ser atómica y enfocada

## Migraciones Incluidas

### 001_initial_schema.sql
- Tabla `schema_migrations` (tracking)
- Tabla `users` (usuarios)
- Tabla `nodes` (nodos P2P)
- Tabla `sessions` (sesiones)

### 002_messaging_tables.sql
- Tabla `messages` (mensajes)
- Tabla `shared_files` (archivos compartidos)

## Añadir Nuevas Tablas

1. Crear nueva migración:
   ```python
   migrator.create_migration("add_my_feature")
   ```

2. Editar `migrations/00X_add_my_feature.sql`:
   ```sql
   CREATE TABLE IF NOT EXISTS my_table (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       -- columnas...
   );
   
   INSERT INTO schema_migrations (version, name) 
   VALUES (X, '00X_add_my_feature') 
   ON CONFLICT (version) DO NOTHING;
   ```

3. Aplicar:
   ```bash
   python3 astranet.py # Opción 5
   ```

## Rollback

El sistema actualmente no soporta rollback automático. Para revertir:

1. Crear una nueva migración que deshaga los cambios
2. O eliminar manualmente las tablas/datos y re-aplicar migraciones desde cero

## Buenas Prácticas

✅ **Hacer**:
- Usa `IF NOT EXISTS` / `IF EXISTS`
- Mantén migraciones pequeñas y enfocadas
- Prueba en desarrollo antes de producción
- Documenta cambios complejos

❌ **Evitar**:
- Modificar migraciones ya aplicadas
- Hacer cambios destructivos sin backup
- Migraciones muy grandes (divide en varias)
