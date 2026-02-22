"""
Astranet Manager - Gestión de Backend y Dashboard
"""

import time
from pathlib import Path
from typing import Dict
from rich.console import Console
from rich.panel import Panel

from .system_utils import SystemUtils

console = Console()


class AstranetManager(SystemUtils):
    """Manager para Backend Rust y Dashboard React"""
    
    def __init__(self):
        super().__init__()
        self.project_root = Path("/home/corrancho/Astranet")
        self.backend_binary = self.project_root / "target/release/astranet"
        self.dashboard_dir = self.project_root / "dashboard"
        self.logs_dir = self.project_root / "logs"
    
    def get_services_status(self) -> Dict:
        """Obtiene el estado de backend y dashboard"""
        backend_running, backend_pid = self.is_port_in_use(3000)
        dashboard_running, dashboard_pid = self.is_port_in_use(5173)
        
        return {
            "backend": {"running": backend_running, "pid": backend_pid or ""},
            "dashboard": {"running": dashboard_running, "pid": dashboard_pid or ""}
        }
    
    def start_backend(self) -> bool:
        """Inicia el backend de Astranet"""
        if not self.backend_binary.exists():
            console.print("[red]✗ Backend no compilado. Ejecuta opción 6 primero.[/red]")
            return False
        
        self.logs_dir.mkdir(exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_file = self.logs_dir / f"backend_{timestamp}.log"
        
        console.print("Iniciando backend de Astranet...")
        cmd = f"cd {self.project_root} && setsid nohup {self.backend_binary} --api-port 3000 > {log_file} 2>&1 &"
        
        self.run_command(cmd)
        
        console.print("Esperando a que el backend inicie...")
        time.sleep(2)
        
        running, pid = self.is_port_in_use(3000)
        if running:
            console.print(f"[green]✓ Backend iniciado correctamente[/green]")
            console.print(f"API: http://localhost:3000")
            console.print(f"Logs: tail -f {log_file}")
            return True
        else:
            console.print("[red]✗ Error al iniciar backend[/red]")
            return False
    
    def stop_backend(self) -> bool:
        """Detiene el backend"""
        console.print("Deteniendo backend...")
        running, pid = self.is_port_in_use(3000)
        
        if not running:
            console.print("[yellow]Backend ya está detenido[/yellow]")
            return True
        
        if self.kill_process(pid):
            console.print("[green]✓ Backend detenido correctamente[/green]")
            return True
        else:
            console.print("[red]✗ Error al detener backend[/red]")
            return False
    
    def start_dashboard(self) -> bool:
        """Inicia el dashboard de Astranet"""
        if not (self.dashboard_dir / "package.json").exists():
            console.print("[red]✗ Dashboard no encontrado[/red]")
            return False
        
        self.logs_dir.mkdir(exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_file = self.logs_dir / f"dashboard_{timestamp}.log"
        
        console.print("Iniciando dashboard de Astranet...")
        cmd = f"cd {self.dashboard_dir} && setsid nohup npm run dev -- --host > {log_file} 2>&1 &"
        
        self.run_command(cmd)
        
        console.print("Esperando a que el dashboard inicie...")
        time.sleep(3)
        
        running, pid = self.is_port_in_use(5173)
        if running:
            console.print(f"[green]✓ Dashboard iniciado correctamente[/green]")
            console.print(f"UI: http://localhost:5173")
            console.print(f"Logs: tail -f {log_file}")
            return True
        else:
            console.print("[red]✗ Error al iniciar dashboard[/red]")
            return False
    
    def stop_dashboard(self) -> bool:
        """Detiene el dashboard"""
        console.print("Deteniendo dashboard...")
        running, pid = self.is_port_in_use(5173)
        
        if not running:
            console.print("[yellow]Dashboard ya está detenido[/yellow]")
            return True
        
        if self.kill_process(pid):
            console.print("[green]✓ Dashboard detenido correctamente[/green]")
            return True
        else:
            console.print("[red]✗ Error al detener dashboard[/red]")
            return False
    
    def compile_backend(self) -> bool:
        """Compila el backend con cargo"""
        console.print(Panel.fit("🔨 Compilando Astranet", style="bold cyan"))
        
        # Verificar dependencias TPM
        console.print("Verificando dependencias del sistema...")
        returncode, _, _ = self.run_command("pkg-config --exists tss2-sys")
        
        if returncode != 0:
            console.print("[yellow]⚠️  Instalando dependencias TPM...[/yellow]")
            self.run_command("sudo apt-get update && sudo apt-get install -y libtss2-dev", sudo=False)
        
        console.print("[green]✓ Dependencias del sistema OK[/green]")
        console.print("\nEjecutando: cargo build --release --features tpm\n")
        
        returncode, _, _ = self.run_command(
            f"cd {self.project_root} && cargo build --release --features tpm",
            capture_output=False
        )
        
        if returncode == 0:
            console.print("\n[green]✓ Compilación exitosa[/green]")
            return True
        else:
            console.print("\n[red]✗ Error en la compilación[/red]")
            return False
