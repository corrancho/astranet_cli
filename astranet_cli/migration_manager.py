"""
Migration Manager - Gestión de migraciones de base de datos
"""

from pathlib import Path
from typing import List, Tuple
from rich.console import Console

console = Console()


class MigrationManager:
    """Gestor de migraciones SQL para CockroachDB"""
    
    def __init__(self, cockroach_manager):
        self.crdb = cockroach_manager
        self.migrations_dir = Path(__file__).parent / "migrations"
        
    def get_current_version(self) -> int:
        """Obtiene la versión actual del schema"""
        cockroach = self.crdb.get_cockroach_binary()
        certs_dir = Path.home() / ".astranet" / "certs"
        config = self.crdb.load_config()
        sql_port = config.get("sql_port", 26257)
        db_name = config.get("database_name", "astranetdb")
        
        sql = f"SELECT COALESCE(MAX(version), 0) FROM {db_name}.schema_migrations;"
        
        returncode, stdout, _ = self.crdb.run_command(
            f'{cockroach} sql --certs-dir={certs_dir} --host=localhost:{sql_port} -e "{sql}"',
            capture_output=True
        )
        
        if returncode == 0 and stdout:
            # Parsear salida
            lines = stdout.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.isdigit():
                    return int(line)
        
        return 0
    
    def get_pending_migrations(self) -> List[Tuple[int, Path]]:
        """Obtiene lista de migraciones pendientes"""
        current_version = self.get_current_version()
        console.print(f"[dim]Versión actual del schema: {current_version}[/dim]")
        
        if not self.migrations_dir.exists():
            console.print("[yellow]⚠️  Directorio de migraciones no existe[/yellow]")
            return []
        
        migrations = []
        for migration_file in sorted(self.migrations_dir.glob("*.sql")):
            # Extraer número de versión del nombre del archivo
            # Formato esperado: 001_descripcion.sql
            try:
                version = int(migration_file.stem.split('_')[0])
                if version > current_version:
                    migrations.append((version, migration_file))
            except (ValueError, IndexError):
                console.print(f"[yellow]⚠️  Archivo de migración ignorado: {migration_file.name}[/yellow]")
                continue
        
        return sorted(migrations, key=lambda x: x[0])
    
    def apply_migration(self, version: int, migration_file: Path) -> bool:
        """Aplica una migración específica"""
        cockroach = self.crdb.get_cockroach_binary()
        certs_dir = Path.home() / ".astranet" / "certs"
        config = self.crdb.load_config()
        sql_port = config.get("sql_port", 26257)
        db_name = config.get("database_name", "astranetdb")
        
        console.print(f"[cyan]📄 Aplicando migración {version}: {migration_file.name}[/cyan]")
        
        # Leer archivo SQL
        sql_content = migration_file.read_text()
        
        # Crear archivo temporal con el SQL
        temp_sql = Path.home() / ".astranet" / f"migration_{version}.sql"
        temp_sql.write_text(f"USE {db_name};\n{sql_content}")
        
        try:
            # Ejecutar migración
            returncode, stdout, stderr = self.crdb.run_command(
                f"{cockroach} sql --certs-dir={certs_dir} --host=localhost:{sql_port} < {temp_sql}",
                capture_output=True
            )
            
            if returncode == 0:
                console.print(f"[green]✓ Migración {version} aplicada correctamente[/green]")
                return True
            else:
                console.print(f"[red]✗ Error aplicando migración {version}[/red]")
                console.print(f"[red]{stderr}[/red]")
                return False
        finally:
            # Limpiar archivo temporal
            if temp_sql.exists():
                temp_sql.unlink()
    
    def migrate(self) -> bool:
        """Aplica todas las migraciones pendientes"""
        pending = self.get_pending_migrations()
        
        if not pending:
            console.print("[green]✓ Base de datos actualizada (no hay migraciones pendientes)[/green]")
            return True
        
        console.print(f"[yellow]📋 Encontradas {len(pending)} migraciones pendientes[/yellow]")
        
        success = True
        for version, migration_file in pending:
            if not self.apply_migration(version, migration_file):
                success = False
                console.print(f"[red]✗ Deteniendo migraciones en versión {version}[/red]")
                break
        
        if success:
            console.print("[green]✓ Todas las migraciones aplicadas correctamente[/green]")
        
        return success
    
    def create_migration(self, name: str) -> Path:
        """Crea un nuevo archivo de migración"""
        # Obtener siguiente versión
        current_version = self.get_current_version()
        next_version = current_version + 1
        
        # Encontrar el último archivo para determinar el siguiente número
        existing_files = list(self.migrations_dir.glob("*.sql"))
        if existing_files:
            last_number = max([
                int(f.stem.split('_')[0]) 
                for f in existing_files 
                if f.stem.split('_')[0].isdigit()
            ])
            next_version = max(next_version, last_number + 1)
        
        # Crear archivo
        filename = f"{next_version:03d}_{name}.sql"
        filepath = self.migrations_dir / filename
        
        template = f"""-- Migración {next_version:03d}: {name.replace('_', ' ').title()}
-- Descripción: TODO: Añadir descripción

-- TODO: Añadir CREATE TABLE, ALTER TABLE, etc.

-- Registrar esta migración
INSERT INTO schema_migrations (version, name) 
VALUES ({next_version}, '{next_version:03d}_{name}') 
ON CONFLICT (version) DO NOTHING;
"""
        
        filepath.write_text(template)
        console.print(f"[green]✓ Migración creada: {filepath}[/green]")
        
        return filepath
