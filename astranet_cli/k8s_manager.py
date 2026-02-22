"""
Kubernetes Manager - Gestión de Kubernetes y containerd
"""

import subprocess
from pathlib import Path
from typing import Tuple
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import box

from .system_utils import SystemUtils

console = Console()

K8S_VERSION = "1.28"
K8S_FULL_VERSION = "1.28.0-1.1"


class K8sManager(SystemUtils):
    """Manager para Kubernetes y containerd"""
    
    def __init__(self):
        super().__init__()
        self.k8s_version = None
        self.cluster_initialized = False
    
    # ═══════════════════════════════════════════════════════════════════
    # Métodos extraídos de K8sInstaller
    # ═══════════════════════════════════════════════════════════════════
    
    def detect_k8s_state(self) -> None:
        """Detecta el estado actual de Kubernetes, Docker, CockroachDB y Astranet"""
        console.print(Panel.fit(
            "🔍 Detectando Instalación de Componentes",
            style="bold blue"
        ))
        
        # === KUBERNETES ===
        components_k8s = []
        
        kubectl_found = False
        kubeadm_found = False
        kubelet_found = False
        
        # Verificar kubectl
        returncode, stdout, _ = self.run_command("kubectl version --client -o json 2>/dev/null")
        if returncode == 0 and stdout:
            try:
                import json
                data = json.loads(stdout)
                version = data.get('clientVersion', {}).get('gitVersion', 'unknown')
                components_k8s.append(("kubectl", "✓", version, True))
                self.k8s_version = version
                kubectl_found = True
            except:
                components_k8s.append(("kubectl", "✓", "Instalado", True))
                kubectl_found = True
        else:
            components_k8s.append(("kubectl", "✗", "No instalado", False))
        
        # Verificar kubeadm
        returncode, stdout, _ = self.run_command("kubeadm version -o short 2>/dev/null")
        if returncode == 0 and stdout:
            components_k8s.append(("kubeadm", "✓", "Instalado", True))
            kubeadm_found = True
        else:
            components_k8s.append(("kubeadm", "✗", "No instalado", False))
        
        # Verificar kubelet
        returncode, stdout, _ = self.run_command("kubelet --version 2>/dev/null")
        if returncode == 0 and stdout:
            kubelet_found = True
            returncode, _, _ = self.run_command("systemctl is-active kubelet", sudo=True)
            if returncode == 0:
                components_k8s.append(("kubelet", "✓", "Activo", True))
            else:
                components_k8s.append(("kubelet", "⚠️", "Instalado pero inactivo", True))
        else:
            components_k8s.append(("kubelet", "✗", "No instalado", False))
        
        self.k8s_installed = kubectl_found and kubeadm_found and kubelet_found
        
        # Verificar containerd
        returncode, stdout, _ = self.run_command("containerd --version 2>/dev/null")
        if returncode == 0:
            version = stdout.strip().split()[2] if len(stdout.split()) > 2 else "instalado"
            returncode_active, _, _ = self.run_command("systemctl is-active containerd", sudo=True)
            if returncode_active == 0:
                components_k8s.append(("containerd", "✓", f"{version} (activo)", True))
            else:
                components_k8s.append(("containerd", "⚠️", f"{version} (inactivo)", True))
        else:
            components_k8s.append(("containerd", "✗", "No instalado", False))
        
        # Verificar cluster
        if Path("/etc/kubernetes/admin.conf").exists():
            returncode, _, _ = self.run_command("kubectl cluster-info", sudo=True)
            if returncode == 0:
                components_k8s.append(("Cluster", "✓", "Inicializado y accesible", True))
                self.cluster_initialized = True
            else:
                components_k8s.append(("Cluster", "⚠️", "Inicializado pero no accesible", True))
                self.cluster_initialized = True
        else:
            components_k8s.append(("Cluster", "✗", "No inicializado", False))
            self.cluster_initialized = False
        
        # === DOCKER ===
        components_docker = []
        docker_version = "N/A"
        returncode, stdout, _ = self.run_command("docker --version 2>/dev/null")
        if returncode == 0:
            version_str = stdout.strip().replace("Docker version ", "")
            parts = version_str.split(",")
            docker_version = parts[0] if parts else version_str
            returncode_active, _, _ = self.run_command("systemctl is-active docker", sudo=True)
            if returncode_active == 0:
                components_docker.append(("Docker Engine", "✓", f"{docker_version} (activo)", True))
            else:
                components_docker.append(("Docker Engine", "⚠️", f"{docker_version} (inactivo)", True))
        else:
            components_docker.append(("Docker Engine", "✗", "No instalado", False))
        
        # === COCKROACHDB ===
        components_cockroach = []
        cockroach_version = "N/A"
        if self.is_cockroach_installed():
            cockroach_version_raw = self.get_cockroach_version()
            # Limpiar la versión (quitar "Build Tag:" y espacios extra)
            if "Build Tag:" in cockroach_version_raw:
                cockroach_version = cockroach_version_raw.split("Build Tag:")[1].strip().split()[0]
            else:
                cockroach_version = cockroach_version_raw.strip()
            running, pid = self.is_cockroach_running()
            if running:
                components_cockroach.append(("CockroachDB", "✓", f"{cockroach_version_raw} (PID: {pid})", True))
            else:
                components_cockroach.append(("CockroachDB", "⚠️", f"{cockroach_version_raw} (detenido)", True))
        else:
            components_cockroach.append(("CockroachDB", "✗", "No instalado", False))
        
        # === ASTRANET ===
        astranet_version = "N/A"
        binary = Path.home() / "Astranet" / "target" / "release" / "astranet"
        if binary.exists():
            returncode, stdout, _ = self.run_command(f"{binary} --version 2>/dev/null")
            if returncode == 0:
                astranet_version = stdout.strip()
            else:
                # Intentar leer la versión de Cargo.toml
                cargo_toml = Path.home() / "Astranet" / "Cargo.toml"
                if cargo_toml.exists():
                    try:
                        with open(cargo_toml) as f:
                            for line in f:
                                if line.startswith("version"):
                                    version = line.split("=")[1].strip().strip('"')
                                    astranet_version = f"v{version}"
                                    break
                    except:
                        astranet_version = "Compilado"
                else:
                    astranet_version = "Compilado"
        
        # Mostrar tabla de Kubernetes
        console.print("[bold]Kubernetes:[/bold]")
        table_k8s = Table(box=box.ROUNDED)
        table_k8s.add_column("Componente", style="cyan")
        table_k8s.add_column("Estado", style="bold")
        table_k8s.add_column("Detalle", style="white")
        
        for component, status, detail, _ in components_k8s:
            style = "green" if status == "✓" else ("yellow" if status == "⚠️" else "red")
            table_k8s.add_row(component, status, detail, style=style)
        
        console.print(table_k8s)
        console.print()
        
        # Mostrar tabla de Docker
        console.print("[bold]Docker:[/bold]")
        table_docker = Table(box=box.ROUNDED)
        table_docker.add_column("Componente", style="cyan")
        table_docker.add_column("Estado", style="bold")
        table_docker.add_column("Detalle", style="white")
        
        for component, status, detail, _ in components_docker:
            style = "green" if status == "✓" else ("yellow" if status == "⚠️" else "red")
            table_docker.add_row(component, status, detail, style=style)
        
        console.print(table_docker)
        console.print()
        
        # Mostrar tabla de CockroachDB
        console.print("[bold]Base de Datos:[/bold]")
        table_db = Table(box=box.ROUNDED)
        table_db.add_column("Componente", style="cyan")
        table_db.add_column("Estado", style="bold")
        table_db.add_column("Detalle", style="white")
        
        for component, status, detail, _ in components_cockroach:
            style = "green" if status == "✓" else ("yellow" if status == "⚠️" else "red")
            table_db.add_row(component, status, detail, style=style)
        
        console.print(table_db)
        console.print()
        
        # Guardar versiones para el banner (ya limpiadas)
        self.docker_version = docker_version
        self.cockroach_version = cockroach_version
        self.astranet_version = astranet_version
    
    def install_kubernetes(self) -> bool:
        """Instala Kubernetes"""
        console.print(Panel.fit(
            f"📦 Instalando Kubernetes {K8S_VERSION}",
            style="bold green"
        ))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            # Deshabilitar swap
            task = progress.add_task("[cyan]Deshabilitando swap...", total=1)
            self.run_command("swapoff -a", sudo=True)
            self.run_command("sed -i '/ swap / s/^\\(.*\\)$/#\\1/g' /etc/fstab", sudo=True)
            progress.update(task, advance=1)
            
            # Configurar módulos del kernel
            task = progress.add_task("[cyan]Configurando módulos del kernel...", total=1)
            modules = "overlay\\nbr_netfilter"
            self.run_command(f"echo -e '{modules}' | sudo tee /etc/modules-load.d/k8s.conf", sudo=False)
            self.run_command("modprobe overlay", sudo=True)
            self.run_command("modprobe br_netfilter", sudo=True)
            progress.update(task, advance=1)
            
            # Configurar sysctl
            task = progress.add_task("[cyan]Configurando parámetros de red...", total=1)
            sysctl_conf = """net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1"""
            self.run_command(f"echo '{sysctl_conf}' | sudo tee /etc/sysctl.d/k8s.conf", sudo=False)
            self.run_command("sysctl --system", sudo=True, capture_output=False)
            progress.update(task, advance=1)
            
            # Instalar dependencias
            task = progress.add_task("[cyan]Instalando dependencias...", total=1)
            self.run_command("apt-get update", sudo=True, capture_output=False)
            self.run_command("apt-get install -y apt-transport-https ca-certificates curl gpg", sudo=True, capture_output=False)
            progress.update(task, advance=1)
            
            # Agregar repositorio
            task = progress.add_task("[cyan]Agregando repositorio de Kubernetes...", total=1)
            self.run_command("mkdir -p -m 755 /etc/apt/keyrings", sudo=True)
            self.run_command(
                f"curl -fsSL https://pkgs.k8s.io/core:/stable:/v{K8S_VERSION}/deb/Release.key | "
                "sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg",
                sudo=False
            )
            self.run_command(
                f"echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] "
                f"https://pkgs.k8s.io/core:/stable:/v{K8S_VERSION}/deb/ /' | "
                "sudo tee /etc/apt/sources.list.d/kubernetes.list",
                sudo=False
            )
            progress.update(task, advance=1)
            
            # Instalar paquetes
            task = progress.add_task("[cyan]Instalando kubelet, kubeadm, kubectl...", total=1)
            self.run_command("apt-get update", sudo=True, capture_output=False)
            self.run_command("apt-get install -y kubelet kubeadm kubectl", sudo=True, capture_output=False)
            self.run_command("apt-mark hold kubelet kubeadm kubectl", sudo=True)
            progress.update(task, advance=1)
            
            # Habilitar kubelet
            task = progress.add_task("[cyan]Habilitando kubelet...", total=1)
            self.run_command("systemctl enable --now kubelet", sudo=True)
            progress.update(task, advance=1)
        
        console.print("✓ [green]Kubernetes instalado correctamente[/green]\n")
        return True
    
    def install_containerd(self) -> bool:
        """Instala y configura containerd"""
        # Verificar si ya está instalado
        returncode, _, _ = self.run_command("which containerd")
        if returncode == 0:
            console.print("✓ [green]containerd ya está instalado[/green]\n")
            return True
        
        console.print(Panel.fit(
            "📦 Instalando containerd",
            style="bold green"
        ))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("[cyan]Instalando containerd...", total=1)
            self.run_command("apt-get install -y containerd", sudo=True, capture_output=False)
            progress.update(task, advance=1)
            
            task = progress.add_task("[cyan]Configurando containerd...", total=1)
            self.run_command("mkdir -p /etc/containerd", sudo=True)
            self.run_command("containerd config default | sudo tee /etc/containerd/config.toml", sudo=False, capture_output=False)
            self.run_command("sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml", sudo=True)
            progress.update(task, advance=1)
            
            task = progress.add_task("[cyan]Reiniciando containerd...", total=1)
            self.run_command("systemctl restart containerd", sudo=True)
            self.run_command("systemctl enable containerd", sudo=True)
            progress.update(task, advance=1)
        
        console.print("✓ [green]containerd instalado y configurado[/green]\n")
        return True
    
    def init_cluster(self) -> bool:
        """Inicializa el cluster de Kubernetes"""
        console.print(Panel.fit(
            "🚀 Inicializando Cluster de Kubernetes",
            style="bold green"
        ))
        
        # Obtener IP del nodo
        returncode, stdout, _ = self.run_command("hostname -I")
        if stdout and stdout.strip():
            parts = stdout.strip().split()
            node_ip = parts[0] if parts else "0.0.0.0"
        else:
            node_ip = "0.0.0.0"
        
        console.print(f"📍 IP del nodo: [cyan]{node_ip}[/cyan]\n")
        
        console.print("⏳ [yellow]Inicializando cluster (esto puede tardar varios minutos)...[/yellow]\n")
        
        returncode, _, stderr = self.run_command(
            f"kubeadm init --apiserver-advertise-address={node_ip} "
            f"--pod-network-cidr=10.244.0.0/16 --service-cidr=10.96.0.0/12",
            sudo=True,
            capture_output=False
        )
        
        if returncode != 0:
            console.print(f"✗ [red]Error al inicializar cluster:[/red] {stderr}\n")
            return False
        
        console.print("\n✓ [green]Cluster inicializado correctamente[/green]\n")
        return True
    
    def setup_kubectl(self) -> bool:
        """Configura kubectl para el usuario actual"""
        console.print(Panel.fit(
            "⚙️  Configurando kubectl",
            style="bold blue"
        ))
        
        home = Path.home()
        kube_dir = home / ".kube"
        kube_config = kube_dir / "config"
        
        # Crear directorio .kube
        kube_dir.mkdir(exist_ok=True)
        
        # Copiar configuración
        if Path("/etc/kubernetes/admin.conf").exists():
            self.run_command(f"cp -f /etc/kubernetes/admin.conf {kube_config}", sudo=True)
            self.run_command(f"chown {os.getuid()}:{os.getgid()} {kube_config}", sudo=True)
            console.print("✓ [green]kubectl configurado correctamente[/green]\n")
            return True
        else:
            console.print("✗ [red]No se encontró /etc/kubernetes/admin.conf[/red]\n")
            return False
    
    def install_cni(self) -> bool:
        """Instala Calico como plugin de red"""
        # Verificar si ya existe un CNI
        returncode, stdout, _ = self.run_command("kubectl get pods -n kube-system 2>/dev/null")
        if "calico" in stdout or "flannel" in stdout or "weave" in stdout:
            console.print("✓ [green]Plugin de red ya instalado[/green]\n")
            return True
        
        console.print(Panel.fit(
            "🌐 Instalando Plugin de Red (Calico)",
            style="bold green"
        ))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("[cyan]Descargando Calico...", total=1)
            returncode, _, _ = self.run_command(
                "kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.26.1/manifests/calico.yaml",
                capture_output=False
            )
            progress.update(task, advance=1)
            
            if returncode != 0:
                console.print("✗ [red]Error al instalar Calico[/red]\n")
                return False
            
            task = progress.add_task("[cyan]Esperando pods de Calico...", total=1)
            time.sleep(5)  # Dar tiempo para que se creen los pods
            self.run_command(
                "kubectl wait --for=condition=ready pod -l k8s-app=calico-node -n kube-system --timeout=300s",
                capture_output=False
            )
            progress.update(task, advance=1)
        
        console.print("✓ [green]Calico instalado correctamente[/green]\n")
        return True
    
    def allow_master_scheduling(self) -> bool:
        """Permite ejecutar pods en el nodo master"""
        console.print(Panel.fit(
            "⚙️  Configurando Nodo Master",
            style="bold blue"
        ))
        
        self.run_command("kubectl taint nodes --all node-role.kubernetes.io/control-plane- || true")
        self.run_command("kubectl taint nodes --all node-role.kubernetes.io/master- || true")
        
        console.print("✓ [green]Nodo master configurado para ejecutar pods[/green]\n")
        return True
    
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
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            # Instalar dependencias
            task = progress.add_task("[cyan]Instalando dependencias...", total=1)
            self.run_command("apt-get update", sudo=True)
            self.run_command("apt-get install -y ca-certificates curl gnupg", sudo=True)
            progress.update(task, advance=1)
            
            # Agregar clave GPG de Docker
            task = progress.add_task("[cyan]Agregando repositorio Docker...", total=1)
            self.run_command("install -m 0755 -d /etc/apt/keyrings", sudo=True)
            self.run_command(
                "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | "
                "sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg",
                sudo=False
            )
            self.run_command("chmod a+r /etc/apt/keyrings/docker.gpg", sudo=True)
            progress.update(task, advance=1)
            
            # Agregar repositorio
            task = progress.add_task("[cyan]Configurando repositorio...", total=1)
            arch = self.os_info["machine"]
            if arch == "x86_64":
                arch = "amd64"
            elif arch == "aarch64":
                arch = "arm64"
            
            distro = self.os_info["distro"]
            version_codename = subprocess.run(
                "grep VERSION_CODENAME /etc/os-release | cut -d= -f2",
                shell=True,
                capture_output=True,
                text=True
            ).stdout.strip()
            
            self.run_command(
                f'echo "deb [arch={arch} signed-by=/etc/apt/keyrings/docker.gpg] '
                f'https://download.docker.com/linux/ubuntu {version_codename} stable" | '
                'sudo tee /etc/apt/sources.list.d/docker.list',
                sudo=False
            )
            self.run_command("apt-get update", sudo=True)
            progress.update(task, advance=1)
            
            # Instalar Docker
            task = progress.add_task("[cyan]Instalando Docker Engine...", total=1)
            self.run_command(
                "apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
                sudo=True
            )
            progress.update(task, advance=1)
            
            # Agregar usuario al grupo docker
            task = progress.add_task("[cyan]Configurando permisos...", total=1)
            if self.sudo_user != "root":
                self.run_command(f"usermod -aG docker {self.sudo_user}", sudo=True)
                console.print(f"\n[yellow]Nota: Necesitarás cerrar sesión y volver a entrar para usar docker sin sudo[/yellow]")
            progress.update(task, advance=1)
            
            # Iniciar y habilitar Docker
            task = progress.add_task("[cyan]Iniciando servicio Docker...", total=1)
            self.run_command("systemctl start docker", sudo=True)
            self.run_command("systemctl enable docker", sudo=True)
            progress.update(task, advance=1)
        
        # Verificar instalación
        returncode, stdout, _ = self.run_command("docker --version")
        if returncode == 0:
            console.print(f"\n✓ [bold green]Docker instalado correctamente: {stdout.strip()}[/bold green]\n")
            return True
        else:
            console.print("\n✗ [red]Error al instalar Docker[/red]\n")
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
        if returncode == 0 and stdout.strip():
            pids = stdout.strip().split('\n')
            # Verificar que es realmente el proceso correcto
            for pid in pids:
                returncode2, stdout2, _ = self.run_command(f"ps -p {pid} -o cmd=")
                if returncode2 == 0 and 'server_p2p' in stdout2 and 'pgrep' not in stdout2:
                    return True, pid
        return False, ""
    
    def get_astranet_status(self) -> dict:
        """Obtiene el estado completo de Astranet"""
        running, pid = self.get_astranet_pid()
        status = {
            "running": running,
            "pid": pid,
            "uptime": "",
            "binary_exists": Path("/home/corrancho/astranet/target/release/server_p2p").exists()
        }
        
        if running and pid:
            # Obtener uptime del proceso
            returncode, stdout, _ = self.run_command(f"ps -p {pid} -o etime= 2>/dev/null")
            if returncode == 0 and stdout.strip():
                status["uptime"] = stdout.strip()
        
        return status
    
    def start_astranet(self) -> bool:
        """Inicia el servidor Astranet en background"""
        console.print("[cyan]Iniciando servidor Astranet...[/cyan]")
        
        # Verificar que el script de inicio existe
        start_script = Path("/home/corrancho/astranet/start_server.sh")
        if not start_script.exists():
            console.print("[red]✗ El script start_server.sh no existe.[/red]")
            return False
        
        # Verificar si ya está corriendo
        running, pid = self.get_astranet_pid()
        if running:
            console.print(f"[yellow]⚠️  Astranet ya está corriendo (PID: {pid})[/yellow]")
            return False
        
        # Crear directorio de logs si no existe
        log_dir = Path("/home/corrancho/astranet")
        log_file = log_dir / "astranet.log"
        
        # Iniciar en background con nohup usando start_server.sh (carga .env)
        cmd = f"cd /home/corrancho/astranet && nohup ./start_server.sh >> {log_file} 2>&1 &"
        console.print(f"[dim]Ejecutando: {cmd}[/dim]")
        returncode, stdout, stderr = self.run_command(cmd, sudo=False)
        
        if returncode == 0 or returncode == 1:  # nohup puede retornar 1 pero aún así funcionar
            import time
            time.sleep(5)  # Esperar más tiempo para que arranque completamente
            running, pid = self.get_astranet_pid()
            if running:
                console.print(f"✓ [green]Servidor iniciado correctamente (PID: {pid})[/green]")
                console.print(f"[cyan]Logs: tail -f {log_file}[/cyan]")
                return True
            else:
                console.print("[red]✗ El servidor no pudo iniciarse.[/red]")
                # Mostrar últimas líneas del log si existe
                if log_file.exists():
                    console.print("\n[yellow]Últimas líneas del log:[/yellow]")
                    self.run_command(f"tail -20 {log_file}", capture_output=False)
                return False
        else:
            console.print(f"[red]✗ Error al ejecutar el comando (código: {returncode})[/red]")
            if stderr:
                console.print(f"[red]{stderr}[/red]")
            return False
    
    def stop_astranet(self) -> bool:
        """Detiene el servidor Astranet"""
        console.print("[cyan]Deteniendo servidor Astranet...[/cyan]")
        
        running, pid = self.get_astranet_pid()
        if not running or not pid:
            console.print("[yellow]⚠️  Astranet no está corriendo[/yellow]")
            return False
        
        console.print(f"[yellow]Deteniendo PID: {pid}[/yellow]")
        
        # Intento graceful con SIGTERM
        self.run_command(f"kill -15 {pid} 2>/dev/null", sudo=False)
        
        import time
        time.sleep(2)
        
        # Verificar si se detuvo
        running, _ = self.get_astranet_pid()
        if not running:
            console.print("✓ [green]Servidor detenido correctamente[/green]")
            return True
        else:
            # Forzar con SIGKILL
            console.print("[yellow]Forzando detención con SIGKILL...[/yellow]")
            self.run_command(f"kill -9 {pid} 2>/dev/null", sudo=False)
            time.sleep(1)
            running, _ = self.get_astranet_pid()
            if not running:
                console.print("✓ [green]Servidor detenido (forzado)[/green]")
                return True
            else:
                # Último recurso: pkill
                console.print("[yellow]Usando pkill como último recurso...[/yellow]")
                self.run_command("pkill -9 -f 'target/release/server_p2p'", sudo=False)
                time.sleep(1)
                running, _ = self.get_astranet_pid()
                if not running:
                    console.print("✓ [green]Servidor detenido (pkill)[/green]")
                    return True
                else:
                    console.print("[red]✗ No se pudo detener el servidor[/red]")
                    console.print(f"[yellow]Intenta manualmente: kill -9 {pid}[/yellow]")
                    return False
    
    def restart_astranet(self) -> bool:
        """Reinicia el servidor Astranet"""
        console.print("[cyan]Reiniciando servidor Astranet...[/cyan]")
        self.stop_astranet()
        import time
        time.sleep(1)
        return self.start_astranet()
    
    def show_astranet_logs(self, lines: int = 50) -> None:
        """Muestra las últimas líneas del log de Astranet"""
        log_file = "/home/corrancho/astranet/astranet.log"
        if not Path(log_file).exists():
            console.print(f"[yellow]No existe el archivo de log: {log_file}[/yellow]")
            return
        
        console.print(Panel.fit(f"📄 Últimas {lines} líneas del log", style="bold cyan"))
        self.run_command(f"tail -n {lines} {log_file}", capture_output=False)
    
    def tail_astranet_logs(self) -> None:
        """Muestra logs en tiempo real (tail -f)"""
        log_file = "/home/corrancho/astranet/astranet.log"
        if not Path(log_file).exists():
            console.print(f"[yellow]No existe el archivo de log: {log_file}[/yellow]")
            console.print("[cyan]Inicia el servidor primero para generar logs[/cyan]")
            return
        
        console.print(Panel.fit("📡 Logs en tiempo real (Ctrl+C para salir)", style="bold cyan"))
        console.print()
        try:
            self.run_command(f"tail -f {log_file}", capture_output=False)
        except KeyboardInterrupt:
            console.print("\n[yellow]Detenido[/yellow]")
    
    def compile_astranet(self) -> bool:
        """Compila el proyecto Astranet"""
        console.print(Panel.fit("🔨 Compilando Astranet", style="bold cyan"))
        
        # Verificar e instalar dependencias TPM si es necesario
        console.print("[cyan]Verificando dependencias del sistema...[/cyan]")
        returncode, _, _ = self.run_command("pkg-config --exists tss2-sys")
        if returncode != 0:
            console.print("[yellow]⚠️  Librerías TPM no encontradas. Instalando...[/yellow]")
            returncode, _, _ = self.run_command("apt-get update && apt-get install -y libtss2-dev", sudo=True, capture_output=False)
            if returncode != 0:
                console.print("\n✗ [red]Error instalando dependencias TPM[/red]")
                return False
            console.print("[green]✓ Librerías TPM instaladas[/green]\n")
        else:
            console.print("[green]✓ Dependencias del sistema OK[/green]\n")
        
        console.print("[cyan]Ejecutando: cargo build --release --features tpm[/cyan]\n")
        
        # Usar Path.home() para el directorio correcto
        project_dir = Path.home() / "Astranet"
        cargo_bin = Path.home() / ".cargo" / "bin" / "cargo"
        
        # Si cargo no está en ~/.cargo/bin, intentar encontrarlo
        if not cargo_bin.exists():
            returncode, stdout, _ = self.run_command("which cargo")
            if returncode == 0:
                cargo_bin = stdout.strip()
            else:
                console.print("\n✗ [red]Cargo no encontrado. Instala Rust primero.[/red]")
                return False
        
        compile_cmd = f"cd {project_dir} && {cargo_bin} build --release --features tpm"
        
        returncode, _, _ = self.run_command(compile_cmd, sudo=False, capture_output=False)
        
        if returncode == 0:
            console.print("\n✓ [green]Compilación exitosa[/green]")
            return True
        else:
            console.print("\n✗ [red]Error en la compilación[/red]")
            return False
    
    def start_backend(self) -> bool:
        """Inicia el backend de Astranet (API + P2P)"""
        console.print("[cyan]Iniciando backend de Astranet...[/cyan]")
        
        # Verificar que el binario existe
        binary = Path.home() / "Astranet" / "target" / "release" / "astranet"
        if not binary.exists():
            console.print("[red]✗ Binario no encontrado. Ejecuta: cargo build --release[/red]")
            return False
        
        # Verificar si ya está corriendo
        returncode, _, _ = self.run_command("lsof -i :3000 > /dev/null 2>&1")
        if returncode == 0:
            console.print(f"[yellow]⚠️  Backend ya está corriendo en puerto 3000[/yellow]")
            return False
        
        # Iniciar en background con setsid para desasociar del proceso padre
        log_file = Path.home() / "Astranet" / "logs" / f"backend_{time.strftime('%Y%m%d_%H%M%S')}.log"
        log_file.parent.mkdir(exist_ok=True)
        
        cmd = f"cd {Path.home()}/Astranet && setsid nohup ./target/release/astranet --api-port 3000 > {log_file} 2>&1 &"
        console.print(f"[dim]Ejecutando: {cmd}[/dim]")
        returncode, _, _ = self.run_command(cmd, sudo=False)
        
        if returncode == 0:
            console.print("[yellow]Esperando a que el backend inicie...[/yellow]")
            # Esperar hasta 10 segundos a que el puerto esté escuchando
            for i in range(10):
                time.sleep(1)
                returncode, _, _ = self.run_command("lsof -i :3000 > /dev/null 2>&1")
                if returncode == 0:
                    console.print(f"✓ [green]Backend iniciado correctamente[/green]")
                    console.print(f"[cyan]API: http://localhost:3000[/cyan]")
                    console.print(f"[cyan]Logs: tail -f {log_file}[/cyan]")
                    return True
            
            console.print("[yellow]⚠️  Backend iniciado pero no responde en el puerto 3000[/yellow]")
            console.print(f"[yellow]Revisa los logs: tail -f {log_file}[/yellow]")
            return False
        
        console.print("[red]✗ Error al iniciar el backend[/red]")
        return False
    
    def stop_backend(self) -> bool:
        """Detiene el backend de Astranet"""
        console.print("[cyan]Deteniendo backend...[/cyan]")
        
        # Buscar PID por el puerto 3000
        returncode, stdout, _ = self.run_command("lsof -ti :3000 2>/dev/null")
        if returncode != 0 or not stdout.strip():
            console.print("[yellow]⚠️  Backend no está corriendo[/yellow]")
            return False
        
        pid = stdout.strip()
        self.run_command(f"kill {pid}", sudo=False)
        time.sleep(1)
        
        returncode, _, _ = self.run_command(f"ps -p {pid} > /dev/null 2>&1")
        if returncode != 0:
            console.print("✓ [green]Backend detenido correctamente[/green]")
            return True
        else:
            console.print("[red]✗ No se pudo detener el backend[/red]")
            return False
    
    def start_dashboard(self) -> bool:
        """Inicia el dashboard de React"""
        console.print("[cyan]Iniciando dashboard...[/cyan]")
        
        # Verificar que existe el directorio
        dashboard_dir = Path.home() / "Astranet" / "dashboard"
        if not dashboard_dir.exists():
            console.print("[red]✗ Directorio dashboard no encontrado[/red]")
            return False
        
        # Verificar si ya está corriendo
        returncode, _, _ = self.run_command("lsof -i :5173 > /dev/null 2>&1")
        if returncode == 0:
            console.print(f"[yellow]⚠️  Dashboard ya está corriendo en puerto 5173[/yellow]")
            return False
        
        # Iniciar en background con setsid para desasociar del proceso padre
        log_file = Path.home() / "Astranet" / "logs" / f"dashboard_{time.strftime('%Y%m%d_%H%M%S')}.log"
        log_file.parent.mkdir(exist_ok=True)
        
        cmd = f"cd {dashboard_dir} && setsid nohup npm run dev -- --host > {log_file} 2>&1 &"
        console.print(f"[dim]Ejecutando: {cmd}[/dim]")
        returncode, _, _ = self.run_command(cmd, sudo=False)
        
        if returncode == 0:
            console.print("[yellow]Esperando a que el dashboard inicie...[/yellow]")
            # Esperar hasta 15 segundos a que el puerto esté escuchando
            for i in range(15):
                time.sleep(1)
                returncode, _, _ = self.run_command("lsof -i :5173 > /dev/null 2>&1")
                if returncode == 0:
                    console.print(f"✓ [green]Dashboard iniciado correctamente[/green]")
                    console.print(f"[cyan]URL: http://localhost:5173[/cyan]")
                    console.print(f"[cyan]Logs: tail -f {log_file}[/cyan]")
                    return True
            
            console.print("[yellow]⚠️  Dashboard iniciado pero no responde en el puerto 5173[/yellow]")
            console.print(f"[yellow]Revisa los logs: tail -f {log_file}[/yellow]")
            return False
        
        console.print("[red]✗ Error al iniciar el dashboard[/red]")
        return False
    
    def stop_dashboard(self) -> bool:
        """Detiene el dashboard"""
        console.print("[cyan]Deteniendo dashboard...[/cyan]")
        
        # Buscar PID por el puerto 5173
        returncode, stdout, _ = self.run_command("lsof -ti :5173 2>/dev/null")
        if returncode != 0 or not stdout.strip():
            console.print("[yellow]⚠️  Dashboard no está corriendo[/yellow]")
            return False
        
        pid = stdout.strip()
        self.run_command(f"kill {pid}", sudo=False)
        time.sleep(1)
        
        returncode, _, _ = self.run_command(f"ps -p {pid} > /dev/null 2>&1")
        if returncode != 0:
            console.print("✓ [green]Dashboard detenido correctamente[/green]")
            return True
        else:
            console.print("[red]✗ No se pudo detener el dashboard[/red]")
            return False
    
    def get_services_status(self) -> dict:
        """Obtiene el estado de todos los servicios"""
        status = {}
        
        # Backend (puerto 3000)
        returncode, stdout, _ = self.run_command("lsof -ti :3000 2>/dev/null")
        status["backend"] = {
            "running": returncode == 0 and bool(stdout.strip()),
            "pid": stdout.strip() if returncode == 0 and stdout.strip() else None
        }
        
        # Dashboard (puerto 5173)
        returncode, stdout, _ = self.run_command("lsof -ti :5173 2>/dev/null")
        status["dashboard"] = {
            "running": returncode == 0 and bool(stdout.strip()),
            "pid": stdout.strip() if returncode == 0 and stdout.strip() else None
        }
        
        # CockroachDB
        running, pid = self.is_cockroach_running()
        status["cockroach"] = {
            "running": running,
            "pid": pid if pid else None
        }
        
        return status
        
        if returncode == 0:
            console.print("\n✓ [green]Compilación exitosa[/green]")
            # Verificar que el binario existe
            if Path("/home/corrancho/astranet/target/release/server_p2p").exists():
                console.print("[green]✓ Binario generado correctamente[/green]")
            return True
        else:
            console.print("\n[red]✗ Error en la compilación[/red]")
            console.print("[yellow]Verifica que Rust esté instalado: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh[/yellow]")
            return False
    
    # ═══════════════════════════════════════════════════════════════════
    # CockroachDB Management
    # ═══════════════════════════════════════════════════════════════════
    
    def k8s_menu(self) -> None:
        """Menú principal de gestión de Kubernetes"""
        while True:
            console.clear()
            console.print(Panel.fit(
                "☸️  Gestión de Kubernetes",
                style="bold cyan"
            ))
            console.print()
            
            console.print("  [green]1. Ver estado de componentes[/green]")
            console.print("  [yellow]2. Instalar Kubernetes (pendiente)[/yellow]")
            console.print("  [magenta]0. Volver[/magenta]")
            console.print()
            
            choice = Prompt.ask("Selecciona una opción", choices=["1", "2", "0"])
            
            if choice == "1":
                self.detect_k8s_state()
                input("\nPresiona Enter...")
            elif choice == "2":
                console.print("[yellow]Instalación de K8s pendiente de implementar[/yellow]")
                input("\nPresiona Enter...")
            elif choice == "0":
                break

