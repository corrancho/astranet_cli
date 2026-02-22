#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════
🚀 Astranet CLI - Gestión Completa del Sistema
═══════════════════════════════════════════════════════════════════════════
Sistema modular para gestión de Astranet, CockroachDB, Kubernetes y Docker

Uso:
  ./astranet.py              # Modo interactivo
"""

import sys
from pathlib import Path

# Agregar el directorio actual al path para imports
sys.path.insert(0, str(Path(__file__).parent))

from astranet_cli import __version__

# Verificar dependencias
try:
    from rich.console import Console
except ImportError:
    print("⚠️  Instalando dependencias necesarias...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "--user", "rich"], check=False)
    from rich.console import Console

console = Console()

def main():
    """Punto de entrada principal"""
    # Soporte para --version / -v
    if len(sys.argv) > 1 and sys.argv[1] in ('--version', '-v', '-V'):
        print(f"Astranet CLI v{__version__}")
        sys.exit(0)
    
    try:
        from astranet_cli.main import main as cli_main
        cli_main()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Proceso interrumpido por el usuario[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
