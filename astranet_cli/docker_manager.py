"""
Docker Manager - Gestión de Docker Engine
"""

import os
import time
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import box

from .system_utils import SystemUtils

console = Console()


class DockerManager(SystemUtils):
    """Manager para Docker Engine"""
    
    def __init__(self):
        super().__init__()
        self.docker_version = "N/A"
    
    def is_docker_installed(self) -> bool:
        """Verifica si Docker está instalado"""
        return self.check_command_exists("docker")
    
    def get_docker_version(self) -> str:
        """Obtiene la versión de Docker"""
        if not self.is_docker_installed():
            return "N/A"
        
        returncode, stdout, _ = self.run_command("docker --version 2>/dev/null | awk '{print $3}' | tr -d ','")
        if returncode == 0 and stdout.strip():
            return stdout.strip()
        return "N/A"
    
    def is_docker_running(self) -> bool:
        """Verifica si Docker daemon está corriendo"""
        returncode, _, _ = self.run_command("systemctl is-active docker 2>/dev/null")
        return returncode == 0
    
    # ═══════════════════════════════════════════════════════════════════
    # Métodos extraídos de K8sInstaller
    # ═══════════════════════════════════════════════════════════════════
    
    def install_docker(self) -> bool:
        """Instala Docker CE"""
        console.print(Panel.fit(
            "🐳 Instalando Docker CE",
            style="bold blue"
        ))
        
        # Verificar si ya está instalado
        returncode, _, _ = self.run_command("docker --version 2>/dev/null")
        if returncode == 0:
            console.print("✓ [green]Docker ya está instalado[/green]\n")
            return True
        
        console.print("[cyan]Instalando Docker desde repositorio oficial...[/cyan]\n")
        
        # Detectar distribución usando /etc/os-release (como el script oficial)
        distro_result = subprocess.run(
            '. /etc/os-release && echo "$ID"',
            shell=True, capture_output=True, text=True
        )
        distro = distro_result.stdout.strip().lower()
        
        # Determinar qué repositorio usar
        if distro in ["ubuntu", "linuxmint", "pop"]:
            repo_distro = "ubuntu"
        elif distro in ["debian", "raspbian"]:
            repo_distro = "debian"
        else:
            console.print(f"[yellow]⚠ Distribución '{distro}' no reconocida, usando Debian[/yellow]")
            repo_distro = "debian"
        
        # Detectar arquitectura con dpkg
        arch_result = subprocess.run("dpkg --print-architecture", shell=True, capture_output=True, text=True)
        arch = arch_result.stdout.strip() if arch_result.returncode == 0 else "amd64"
        
        # Detectar codename
        codename_result = subprocess.run(
            "lsb_release -cs 2>/dev/null || (. /etc/os-release && echo $VERSION_CODENAME)",
            shell=True, capture_output=True, text=True
        )
        version_codename = codename_result.stdout.strip()
        
        # Prefijo sudo solo si NO somos root
        sudo_prefix = "" if self.is_root else "sudo "
        
        console.print(f"[cyan]Sistema: {distro} ({version_codename}) - {arch}[/cyan]")
        console.print(f"[cyan]Repositorio: docker.com/linux/{repo_distro}[/cyan]")
        console.print(f"[cyan]Root: {'Sí' if self.is_root else 'No (usando sudo)'}[/cyan]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            # 1. Instalar dependencias
            task = progress.add_task("[cyan]Instalando dependencias...", total=1)
            self.run_command("apt-get update -y", sudo=True)
            self.run_command("apt-get install -y ca-certificates curl gnupg lsb-release", sudo=True)
            progress.update(task, advance=1)
            
            # 2. Agregar clave GPG de Docker
            task = progress.add_task("[cyan]Agregando clave GPG Docker...", total=1)
            self.run_command("mkdir -p /etc/apt/keyrings", sudo=True)
            
            # Descargar y convertir clave GPG (sin sudo hardcoded en el pipe)
            gpg_cmd = (
                f"curl -fsSL https://download.docker.com/linux/{repo_distro}/gpg | "
                f"{sudo_prefix}gpg --dearmor -o /etc/apt/keyrings/docker.gpg"
            )
            self.run_command(gpg_cmd, sudo=False)
            self.run_command("chmod a+r /etc/apt/keyrings/docker.gpg", sudo=True)
            progress.update(task, advance=1)
            
            # 3. Configurar repositorio
            task = progress.add_task("[cyan]Configurando repositorio...", total=1)
            
            repo_line = (
                f"deb [arch={arch} signed-by=/etc/apt/keyrings/docker.gpg] "
                f"https://download.docker.com/linux/{repo_distro} "
                f"{version_codename} stable"
            )
            
            # Escribir repositorio (sin sudo hardcoded en el pipe)
            tee_cmd = f'echo "{repo_line}" | {sudo_prefix}tee /etc/apt/sources.list.d/docker.list > /dev/null'
            returncode, stdout, stderr = self.run_command(tee_cmd, sudo=False)
            
            if returncode != 0:
                console.print(f"\n[red]✗ Error al configurar repositorio[/red]")
                console.print(f"[red]{stderr}[/red]")
                return False
            
            # Actualizar repos
            self.run_command("apt-get update -y", sudo=True)
            progress.update(task, advance=1)
            
            # 4. Instalar Docker
            task = progress.add_task("[cyan]Instalando Docker Engine...", total=1)
            returncode, stdout, stderr = self.run_command(
                "apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
                sudo=True
            )
            progress.update(task, advance=1)
            
            if returncode != 0:
                console.print(f"\n[red]✗ Error al instalar Docker[/red]")
                if stderr:
                    console.print(f"[red]{stderr}[/red]")
                return False
            
            # 5. Configurar permisos
            task = progress.add_task("[cyan]Configurando permisos...", total=1)
            
            # Determinar usuario(s) a configurar para Docker sin sudo
            docker_users = set()
            
            # Si se ejecutó con sudo, agregar el usuario original
            if self.sudo_user and self.sudo_user != "root":
                docker_users.add(self.sudo_user)
            
            # Si USER no es root, agregarlo también
            current_user = os.environ.get('USER', 'root')
            if current_user != "root":
                docker_users.add(current_user)
            
            progress.update(task, advance=1)
        
        # Fuera del progress bar para poder interactuar con el usuario
        # Si estamos como root directo y no hay usuarios detectados, preguntar
        if not docker_users:
            console.print("\n[yellow]Ejecutando como root - Docker ya funciona sin restricciones.[/yellow]")
            try:
                add_user = Confirm.ask(
                    "[cyan]¿Deseas configurar un usuario para usar Docker sin sudo?[/cyan]",
                    default=True
                )
                if add_user:
                    docker_username = Prompt.ask(
                        "[cyan]Nombre del usuario[/cyan]",
                        default=""
                    ).strip()
                    if docker_username:
                        # Verificar que el usuario existe
                        ret, _, _ = self.run_command(f"id {docker_username}")
                        if ret == 0:
                            docker_users.add(docker_username)
                        else:
                            # Crear el usuario
                            create_user = Confirm.ask(
                                f"[yellow]El usuario '{docker_username}' no existe. ¿Deseas crearlo?[/yellow]",
                                default=True
                            )
                            if create_user:
                                self.run_command(f"useradd -m -s /bin/bash {docker_username}", sudo=True)
                                console.print(f"[green]✓ Usuario '{docker_username}' creado[/green]")
                                # Establecer contraseña
                                console.print(f"[cyan]Establece la contraseña para '{docker_username}':[/cyan]")
                                self.run_command(f"passwd {docker_username}", sudo=True, capture_output=False)
                                docker_users.add(docker_username)
            except (KeyboardInterrupt, EOFError):
                pass
        
        # Agregar usuarios al grupo docker
        for user in docker_users:
            self.run_command(f"usermod -aG docker {user}", sudo=True)
            console.print(f"[green]✓ Usuario '{user}' agregado al grupo docker[/green]")
        
        if docker_users:
            console.print(f"\n[yellow]ℹ Los usuarios deben cerrar sesión y volver a entrar para que el grupo docker surta efecto.[/yellow]")
            console.print(f"[yellow]  O ejecutar: newgrp docker[/yellow]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            # 6. Iniciar servicios
            task = progress.add_task("[cyan]Iniciando servicio Docker...", total=1)
            self.run_command("systemctl enable docker", sudo=True)
            self.run_command("systemctl start docker", sudo=True)
            progress.update(task, advance=1)
        
        # Verificar instalación
        console.print("\n[cyan]Verificando instalación...[/cyan]")
        time.sleep(2)
        
        # Verificar containerd primero
        returncode_containerd, stdout_containerd, _ = self.run_command("systemctl is-active containerd")
        if returncode_containerd != 0:
            console.print(f"\n[yellow]⚠ containerd no está activo: {stdout_containerd.strip()}[/yellow]")
            console.print("[cyan]Intentando reiniciar containerd...[/cyan]")
            self.run_command("systemctl restart containerd", sudo=True)
            time.sleep(2)
        
        # Verificar que el servicio esté corriendo
        returncode, stdout, stderr = self.run_command("systemctl is-active docker")
        if returncode != 0:
            console.print(f"\n[red]✗ El servicio Docker no está activo[/red]")
            console.print(f"[yellow]Estado: {stdout.strip() or stderr.strip()}[/yellow]\n")
            
            # Diagnóstico detallado
            console.print("[cyan]Diagnóstico del problema:[/cyan]\n")
            
            console.print("[cyan]1. Estado del servicio Docker:[/cyan]")
            self.run_command("systemctl status docker --no-pager -l", sudo=True, capture_output=False)
            
            console.print("\n[cyan]2. Estado de containerd:[/cyan]")
            self.run_command("systemctl status containerd --no-pager -l", sudo=True, capture_output=False)
            
            console.print("\n[cyan]3. Logs de Docker (últimas 30 líneas):[/cyan]")
            self.run_command("journalctl -u docker -n 30 --no-pager", sudo=True, capture_output=False)
            
            console.print("\n[cyan]4. Logs de containerd (últimas 30 líneas):[/cyan]")
            self.run_command("journalctl -u containerd -n 30 --no-pager", sudo=True, capture_output=False)
            
            console.print("\n[yellow]Intenta ejecutar manualmente:[/yellow]")
            console.print("  sudo systemctl restart containerd")
            console.print("  sudo systemctl restart docker")
            console.print("  sudo journalctl -u docker -f")
            
            return False
        
        # Verificar versión (con sudo por si el usuario no está en el grupo docker aún)
        returncode, stdout, stderr = self.run_command("docker --version", sudo=True)
        if returncode == 0:
            console.print(f"\n✓ [bold green]Docker instalado correctamente: {stdout.strip()}[/bold green]")
            
            # Verificar Docker Compose
            returncode_compose, stdout_compose, _ = self.run_command("docker compose version", sudo=True)
            if returncode_compose == 0:
                console.print(f"✓ [bold green]Docker Compose: {stdout_compose.strip()}[/bold green]")
            
            console.print(f"\n[yellow]Nota: Si quieres usar Docker sin sudo, cierra sesión y vuelve a entrar.[/yellow]")
            console.print(f"[yellow]O ejecuta: newgrp docker[/yellow]\n")
            return True
        else:
            console.print(f"\n✗ [red]Error al verificar Docker[/red]")
            if stderr:
                console.print(f"[red]Error: {stderr.strip()}[/red]")
            console.print("\n[yellow]Intentando diagnosticar el problema...[/yellow]")
            self.run_command("which docker", sudo=True, capture_output=False)
            self.run_command("systemctl status docker --no-pager", sudo=True, capture_output=False)
            return False
    
    def uninstall_docker(self) -> bool:
        """Desinstala Docker CE completamente"""
        console.print(Panel.fit(
            "🗑️  Desinstalando Docker CE",
            style="bold red"
        ))
        
        # Verificar si está instalado
        returncode, _, _ = self.run_command("docker --version 2>/dev/null")
        if returncode != 0:
            console.print("✓ [yellow]Docker no está instalado[/yellow]\n")
            return True
        
        console.print("[yellow]Se eliminarán los siguientes componentes:[/yellow]")
        console.print("  • Docker Engine (docker-ce)")
        console.print("  • Docker CLI (docker-ce-cli)")
        console.print("  • Docker Compose plugin")
        console.print("  • Imágenes y contenedores")
        console.print("  • Volúmenes")
        console.print("  • Configuraciones")
        console.print()
        
        if not Confirm.ask("⚠️  ¿Estás seguro de eliminar Docker?"):
            console.print("[yellow]Desinstalación cancelada[/yellow]\n")
            return False
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            # Detener servicio
            task = progress.add_task("[red]Deteniendo Docker...", total=1)
            self.run_command("systemctl stop docker", sudo=True)
            progress.update(task, advance=1)
            
            # Desinstalar paquetes
            task = progress.add_task("[red]Eliminando paquetes...", total=1)
            self.run_command(
                "apt-get purge -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin docker-ce-rootless-extras",
                sudo=True
            )
            progress.update(task, advance=1)
            
            # Limpiar datos
            task = progress.add_task("[red]Eliminando datos...", total=1)
            self.run_command("rm -rf /var/lib/docker", sudo=True)
            self.run_command("rm -rf /var/lib/containerd", sudo=True)
            self.run_command("rm -rf /etc/docker", sudo=True)
            progress.update(task, advance=1)
            
            # Autoremove
            task = progress.add_task("[red]Limpiando dependencias...", total=1)
            self.run_command("apt-get autoremove -y", sudo=True)
            progress.update(task, advance=1)
        
        console.print("\n✓ [bold green]Docker desinstalado completamente[/bold green]\n")
        return True
    
    def show_docker_info(self) -> None:
        """Muestra información de Docker"""
        console.print(Panel.fit(
            "🐳 Información de Docker",
            style="bold blue"
        ))
        
        # Verificar si está instalado
        returncode, stdout, _ = self.run_command("docker --version 2>/dev/null")
        if returncode != 0:
            console.print("[yellow]Docker no está instalado[/yellow]\n")
            return
        
        # Versión
        console.print(f"[bold]Versión:[/bold] {stdout.strip()}\n")
        
        # Estado del servicio
        returncode, _, _ = self.run_command("systemctl is-active docker", sudo=True)
        status = "✓ Activo" if returncode == 0 else "✗ Inactivo"
        style = "green" if returncode == 0 else "red"
        console.print(f"[bold]Estado:[/bold] [{style}]{status}[/{style}]\n")
        
        # Información del sistema
        console.print("[bold]Información del sistema:[/bold]")
        self.run_command("docker info 2>/dev/null | grep -E '(Server Version|Storage Driver|Cgroup Driver|Containers|Images)'", capture_output=False)
        console.print()
        
        # Contenedores en ejecución
        console.print("[bold]Contenedores en ejecución:[/bold]")
        returncode, stdout, _ = self.run_command("docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Image}}'")
        if returncode == 0:
            if stdout.strip():
                console.print(stdout)
            else:
                console.print("[dim]No hay contenedores en ejecución[/dim]")
        console.print()
        
        # Todos los contenedores
        console.print("[bold]Todos los contenedores:[/bold]")
        returncode, stdout, _ = self.run_command("docker ps -a --format 'table {{.Names}}\\t{{.Status}}\\t{{.Image}}'")
        if returncode == 0:
            if stdout.strip():
                console.print(stdout)
            else:
                console.print("[dim]No hay contenedores[/dim]")
        console.print()
        
        # Imágenes
        console.print("[bold]Imágenes descargadas:[/bold]")
        returncode, stdout, _ = self.run_command("docker images --format 'table {{.Repository}}:{{.Tag}}\\t{{.Size}}\\t{{.CreatedSince}}'")
        if returncode == 0:
            if stdout.strip():
                console.print(stdout)
            else:
                console.print("[dim]No hay imágenes[/dim]")
        console.print()
        
        # Volúmenes
        console.print("[bold]Volúmenes:[/bold]")
        returncode, stdout, _ = self.run_command("docker volume ls --format 'table {{.Name}}\\t{{.Driver}}'")
        if returncode == 0:
            if stdout.strip():
                console.print(stdout)
            else:
                console.print("[dim]No hay volúmenes[/dim]")
        console.print()
    
    def docker_menu(self) -> None:
        """Menú de gestión de Docker"""
        while True:
            console.clear()
            console.print(Panel.fit(
                "🐳 Gestión de Docker",
                style="bold cyan"
            ))
            
            # Detectar estado de Docker
            returncode, stdout, _ = self.run_command("docker --version 2>/dev/null")
            docker_installed = returncode == 0
            
            if docker_installed:
                version_str = stdout.strip().replace("Docker version ", "")
                parts = version_str.split(",")
                version = parts[0] if parts else version_str
                console.print(f"[green]Docker {version} instalado[/green]\n")
                
                returncode_active, _, _ = self.run_command("systemctl is-active docker", sudo=True)
                if returncode_active == 0:
                    console.print("[green]✓ Servicio activo[/green]\n")
                else:
                    console.print("[yellow]⚠️  Servicio inactivo[/yellow]\n")
            else:
                console.print("[yellow]Docker no está instalado[/yellow]\n")
            
            # Opciones del menú
            if docker_installed:
                options = [
                    ("1", "yellow", "Ver información completa y contenedores"),
                    ("2", "yellow", "Listar contenedores en ejecución"),
                    ("3", "yellow", "Listar todas las imágenes"),
                    ("4", "cyan", "Iniciar/Reiniciar servicio Docker"),
                    ("5", "cyan", "Detener servicio Docker"),
                    ("6", "red", "Desinstalar Docker"),
                    ("7", "magenta", "Volver al menú principal")
                ]
            else:
                options = [
                    ("1", "green", "Instalar Docker CE"),
                    ("2", "magenta", "Volver al menú principal")
                ]
            
            for key, color, value in options:
                console.print(f"  [{color}]{key}. {value}[/{color}]")
            
            console.print()
            valid_choices = [key for key, _, _ in options]
            choice = Prompt.ask("Selecciona una opción", choices=valid_choices)
            
            if docker_installed:
                if choice == "1":
                    self.show_docker_info()
                    Prompt.ask("\nPresiona Enter para continuar")
                    
                elif choice == "2":
                    console.print(Panel.fit("🐳 Contenedores en ejecución", style="bold blue"))
                    self.run_command("docker ps", capture_output=False)
                    Prompt.ask("\nPresiona Enter para continuar")
                    
                elif choice == "3":
                    console.print(Panel.fit("📦 Imágenes de Docker", style="bold blue"))
                    self.run_command("docker images", capture_output=False)
                    Prompt.ask("\nPresiona Enter para continuar")
                    
                elif choice == "4":
                    console.print("[cyan]Reiniciando servicio Docker...[/cyan]")
                    self.run_command("systemctl restart docker", sudo=True)
                    console.print("✓ [green]Servicio reiniciado[/green]")
                    Prompt.ask("\nPresiona Enter para continuar")
                    
                elif choice == "5":
                    console.print("[cyan]Deteniendo servicio Docker...[/cyan]")
                    self.run_command("systemctl stop docker", sudo=True)
                    console.print("✓ [green]Servicio detenido[/green]")
                    Prompt.ask("\nPresiona Enter para continuar")
                    
                elif choice == "6":
                    self.uninstall_docker()
                    Prompt.ask("\nPresiona Enter para continuar")
                    
                elif choice == "7":
                    break
            else:
                if choice == "1":
                    self.install_docker()
                    Prompt.ask("\nPresiona Enter para continuar")
                    
                elif choice == "2":
                    break
    
    def get_astranet_pid(self) -> tuple[bool, str]:
        """Obtiene el PID del servidor Astranet si está corriendo"""
        # Buscar proceso específico: debe ser el binario exacto, no shells ni otros
        returncode, stdout, _ = self.run_command("pgrep -f '^./target/release/server_p2p' || pgrep -x server_p2p")
