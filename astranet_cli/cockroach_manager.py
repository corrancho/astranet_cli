"""
CockroachDB Manager - Gestión completa de CockroachDB
"""

import json
import time
from pathlib import Path
from typing import Tuple
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from .system_utils import SystemUtils

console = Console()


class CockroachManager(SystemUtils):
    """Manager para CockroachDB con configuración por cluster"""
    
    def __init__(self):
        super().__init__()
        # Config en el directorio del código
        self.config_file = Path(__file__).parent / "config.json"
        # Datos y certificados siguen en ~/.astranet/
        self.certs_dir = Path.home() / ".astranet" / "certs"
        self.store_dir = Path.home() / ".astranet" / "cockroach-data"
    
    # ═══════════════════════════════════════════════════════════════════
    # Métodos extraídos de K8sInstaller
    # ═══════════════════════════════════════════════════════════════════
    
    def load_config(self) -> dict:
        """Carga configuración de CockroachDB desde config.json"""
        default_config = {
            "sql_port": 26257,
            "http_port": 8080,
            "domain": "astranet.local",
            "cluster_nodes": [],
            "database_name": "defaultdb",
            "admin_user": "admin",
            "admin_password": "astranet2026"
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    full_config = json.load(f)
                    # Retornar solo la sección de cockroachdb
                    return full_config.get("cockroachdb", default_config)
            except Exception as e:
                console.print(f"[yellow]⚠️  Error al leer config: {e}[/yellow]")
                return default_config
        return default_config
    
    def save_config(self, config: dict) -> bool:
        """Guarda configuración en config.json (hace merge con campos existentes)"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Leer config completo
            full_config = {}
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    full_config = json.load(f)
            
            # Hacer merge: actualizar solo los campos que vienen en config
            # preservando los que ya existen y no se están actualizando
            if "cockroachdb" not in full_config:
                full_config["cockroachdb"] = {}
            
            full_config["cockroachdb"].update(config)
            
            # Guardar config completo
            with open(self.config_file, 'w') as f:
                json.dump(full_config, f, indent=2)
            return True
        except Exception as e:
            console.print(f"[red]✗ Error al guardar config: {e}[/red]")
            return False
    
    def update_config(self, **kwargs) -> bool:
        """Actualiza campos específicos de la configuración"""
        config = self.load_config()
        config.update(kwargs)
        return self.save_config(config)
    
    def configure_cluster_interactive(self) -> bool:
        """Configuración interactiva del cluster CockroachDB"""
        console.print(Panel.fit(
            "⚙️  Configuración del Cluster CockroachDB",
            style="bold cyan"
        ))
        console.print()
        
        config = self.load_config()
        
        # Puerto SQL
        sql_port = Prompt.ask(
            "Puerto SQL",
            default=str(config.get("sql_port", 26257))
        )
        
        # Puerto HTTP
        http_port = Prompt.ask(
            "Puerto HTTP (Admin UI)",
            default=str(config.get("http_port", 8080))
        )
        
        # Dominio principal
        domain = Prompt.ask(
            "Dominio principal del nodo",
            default=config.get("domain", "astranet.local")
        )
        
        # Nodos del cluster
        console.print("\n[cyan]Nodos adicionales del cluster (deja vacío si es un solo nodo):[/cyan]")
        console.print("[dim]Formato: dominio1:puerto,dominio2:puerto[/dim]")
        current_nodes = ",".join(config.get("cluster_nodes", []))
        nodes_input = Prompt.ask(
            "Nodos",
            default=current_nodes if current_nodes else ""
        )
        
        cluster_nodes = [n.strip() for n in nodes_input.split(",") if n.strip()]
        
        # Guardar configuración
        new_config = {
            "sql_port": int(sql_port),
            "http_port": int(http_port),
            "domain": domain,
            "cluster_nodes": cluster_nodes
        }
        
        if self.save_config(new_config):
            console.print("\n[green]✓ Configuración guardada[/green]")
            
            # Mostrar resumen
            table = Table(title="Configuración del Cluster", box=box.ROUNDED)
            table.add_column("Campo", style="cyan")
            table.add_column("Valor", style="green")
            
            table.add_row("Puerto SQL", str(new_config["sql_port"]))
            table.add_row("Puerto HTTP", str(new_config["http_port"]))
            table.add_row("Dominio", new_config["domain"])
            table.add_row("Nodos Cluster", ", ".join(cluster_nodes) if cluster_nodes else "[dim]Nodo único[/dim]")
            
            console.print(table)
            return True
        else:
            return False
    
    def is_cockroach_installed(self) -> bool:
        """Verifica si CockroachDB está instalado"""
        # Verificar múltiples ubicaciones posibles
        cockroach_paths = [
            "/usr/local/bin/cockroach",
            "/usr/bin/cockroach",
            str(Path.home() / "bin/cockroach")
        ]
        
        for path in cockroach_paths:
            if Path(path).exists() and Path(path).is_file():
                return True
        
        # Fallback: intentar which
        returncode, _, _ = self.run_command("which cockroach")
        return returncode == 0
    
    def get_cockroach_binary(self) -> str:
        """Obtiene la ruta del binario de cockroach"""
        cockroach_paths = [
            "/usr/local/bin/cockroach",
            "/usr/bin/cockroach",
            str(Path.home() / "bin/cockroach")
        ]
        
        for path in cockroach_paths:
            if Path(path).exists() and Path(path).is_file():
                return path
        
        # Fallback: intentar which
        returncode, stdout, _ = self.run_command("which cockroach")
        if returncode == 0:
            return stdout.strip()
        
        return "cockroach"  # Último recurso
    
    def get_cockroach_version(self) -> str:
        """Obtiene la versión de CockroachDB"""
        if not self.is_cockroach_installed():
            return "No instalado"
        cockroach = self.get_cockroach_binary()
        returncode, stdout, _ = self.run_command(f"{cockroach} version | head -1")
        if returncode == 0:
            return stdout.strip()
        return "Desconocida"
    
    def is_cockroach_running(self) -> Tuple[bool, str]:
        """Verifica si CockroachDB está corriendo"""
        # Usar ps para evitar que pgrep se detecte a sí mismo
        returncode, stdout, _ = self.run_command("ps aux | grep 'cockroach start' | grep -v grep | awk '{print $2}' | head -1")
        if returncode == 0 and stdout.strip():
            pid = stdout.strip()
            # Verificar que el PID realmente existe
            check_returncode, _, _ = self.run_command(f"ps -p {pid} > /dev/null 2>&1")
            if check_returncode == 0:
                return True, pid
        return False, ""
    
    def install_cockroach(self) -> bool:
        """Instala CockroachDB"""
        console.print(Panel.fit("📥 Instalando CockroachDB", style="bold blue"))
        
        # Determinar directorio de instalación según permisos
        if self.is_root:
            install_dir = "/usr/local/bin"
        else:
            # Instalar en directorio del usuario
            install_dir = str(Path.home() / "bin")
            Path(install_dir).mkdir(parents=True, exist_ok=True)
            console.print(f"[yellow]Instalando en {install_dir} (sin permisos root)[/yellow]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Descargar binario
            task = progress.add_task("Descargando CockroachDB...", total=None)
            
            arch = self.os_info["machine"]
            if arch == "x86_64":
                url = "https://binaries.cockroachdb.com/cockroach-latest.linux-amd64.tgz"
            elif arch == "aarch64":
                url = "https://binaries.cockroachdb.com/cockroach-latest.linux-arm64.tgz"
            else:
                console.print(f"[red]Arquitectura {arch} no soportada[/red]")
                return False
            
            # Descargar
            returncode, stdout, stderr = self.run_command(f"wget -q {url} -O /tmp/cockroach.tgz", capture_output=True)
            if returncode != 0:
                console.print(f"[red]✗ Error al descargar: {stderr}[/red]")
                # Intentar con curl si wget falla
                console.print("[yellow]Intentando con curl...[/yellow]")
                returncode, stdout, stderr = self.run_command(f"curl -sL {url} -o /tmp/cockroach.tgz", capture_output=True)
                if returncode != 0:
                    console.print(f"[red]✗ Error con curl: {stderr}[/red]")
                    return False
            
            progress.update(task, description="Extrayendo...")
            returncode, _, stderr = self.run_command("tar xzf /tmp/cockroach.tgz -C /tmp", capture_output=True)
            if returncode != 0:
                console.print(f"[red]✗ Error al extraer: {stderr}[/red]")
                return False
            
            progress.update(task, description="Instalando...")
            if self.is_root:
                returncode, _, stderr = self.run_command("cp /tmp/cockroach-*/cockroach /usr/local/bin/", capture_output=True)
                if returncode == 0:
                    self.run_command("chmod +x /usr/local/bin/cockroach", capture_output=False)
            else:
                # Copiar al directorio del usuario
                returncode, _, stderr = self.run_command(f"cp /tmp/cockroach-*/cockroach {install_dir}/", capture_output=True)
                if returncode == 0:
                    self.run_command(f"chmod +x {install_dir}/cockroach", capture_output=False)
                    # Agregar al PATH si no está
                    shell_rc = Path.home() / ".bashrc"
                    if shell_rc.exists():
                        with open(shell_rc, 'r') as f:
                            content = f.read()
                        if install_dir not in content:
                            with open(shell_rc, 'a') as f:
                                f.write(f'\n# Agregado por Astranet\nexport PATH="{install_dir}:$PATH"\n')
                            console.print(f"[yellow]Agregado {install_dir} al PATH en .bashrc[/yellow]")
                            console.print(f"[yellow]Ejecuta: source ~/.bashrc[/yellow]")
            
            if returncode != 0:
                console.print(f"[red]✗ Error al instalar: {stderr}[/red]")
                return False
            
            progress.update(task, description="Limpiando...")
            self.run_command("rm -rf /tmp/cockroach*", capture_output=False)
            
            progress.update(task, description="✓ Completado", completed=True)
        
        console.print("[green]✓ CockroachDB instalado correctamente[/green]")
        if not self.is_root:
            console.print(f"[yellow]📍 Binario instalado en: {install_dir}/cockroach[/yellow]")
            console.print(f"[yellow]💡 Recarga tu shell: source ~/.bashrc[/yellow]")
        return True
    
    def create_ca_cert(self) -> bool:
        """Crea certificado CA (solo primer nodo)"""
        certs_dir = Path.home() / ".astranet" / "certs"
        certs_dir.mkdir(parents=True, exist_ok=True)
        
        console.print("🔐 Generando certificado CA...")
        cockroach = self.get_cockroach_binary()
        returncode, _, stderr = self.run_command(
            f"{cockroach} cert create-ca --certs-dir={certs_dir} --ca-key={certs_dir}/ca.key",
            capture_output=False
        )
        
        if returncode == 0:
            console.print(f"[green]✓ CA generada en {certs_dir}/ca.crt[/green]")
            return True
        else:
            console.print(f"[red]✗ Error: {stderr}[/red]")
            return False
    
    def download_ca_cert(self, url: str) -> bool:
        """Descarga certificado CA de otro nodo"""
        certs_dir = Path.home() / ".astranet" / "certs"
        certs_dir.mkdir(parents=True, exist_ok=True)
        
        console.print(f"📥 Descargando CA desde {url}...")
        returncode, _, _ = self.run_command(
            f"wget -q {url} -O {certs_dir}/ca.crt"
        )
        
        if returncode == 0 and (certs_dir / "ca.crt").exists():
            console.print("[green]✓ CA descargada correctamente[/green]")
            return True
        else:
            console.print("[red]✗ Error al descargar CA[/red]")
            return False
    
    def create_node_cert(self) -> bool:
        """Crea certificado para este nodo con múltiples DNS/IPs del config"""
        certs_dir = Path.home() / ".astranet" / "certs"
        config = self.load_config()
        
        # Obtener IP del nodo
        returncode, stdout, _ = self.run_command("hostname -I | awk '{print $1}'")
        if returncode != 0:
            console.print("[red]✗ No se pudo obtener IP del nodo[/red]")
            return False
        
        ip = stdout.strip()
        
        # Construir lista de Subject Alternative Names (SAN)
        # Solo incluye el dominio de ESTE nodo (no todos los cluster_nodes)
        # Esto permite escalabilidad: cada nodo tiene su propio certificado
        # firmado por el mismo CA, sin necesidad de regenerar certificados
        san_list = ["localhost", "127.0.0.1", ip, config.get("domain", "astranet.local")]
        
        san_string = " ".join(san_list)
        console.print(f"🔐 Generando certificado para este nodo...")
        console.print(f"[dim]SAN: {san_string}[/dim]")
        console.print(f"[dim]ℹ️  Cada nodo usa su propio certificado firmado por el mismo CA[/dim]")
        
        cockroach = self.get_cockroach_binary()
        returncode, _, stderr = self.run_command(
            f"{cockroach} cert create-node {san_string} --certs-dir={certs_dir} --ca-key={certs_dir}/ca.key",
            capture_output=False
        )
        
        if returncode == 0:
            console.print("[green]✓ Certificado de nodo generado[/green]")
            return True
        else:
            console.print(f"[red]✗ Error: {stderr}[/red]")
            return False
    
    def create_client_cert(self) -> bool:
        """Crea certificado de cliente root"""
        certs_dir = Path.home() / ".astranet" / "certs"
        
        console.print("🔐 Generando certificado de cliente...")
        cockroach = self.get_cockroach_binary()
        returncode, _, stderr = self.run_command(
            f"{cockroach} cert create-client root --certs-dir={certs_dir} --ca-key={certs_dir}/ca.key",
            capture_output=False
        )
        
        if returncode == 0:
            console.print("[green]✓ Certificado de cliente generado[/green]")
            
            # Convertir la clave a formato PKCS#8 para el backend Rust
            console.print("🔐 Convirtiendo clave a formato PKCS#8...")
            client_key = f"{certs_dir}/client.root.key"
            client_pk8_key = f"{certs_dir}/client.root.pk8.key"
            
            returncode_conv, _, stderr_conv = self.run_command(
                f"openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt -in {client_key} -out {client_pk8_key}"
            )
            
            if returncode_conv == 0:
                console.print("[green]✓ Clave convertida a PKCS#8[/green]")
                return True
            else:
                console.print(f"[yellow]⚠️  Error al convertir clave: {stderr_conv}[/yellow]")
                console.print("[yellow]El certificado se creó pero falta el formato PKCS#8[/yellow]")
                return False
        else:
            console.print(f"[red]✗ Error: {stderr}[/red]")
            return False
    
    def setup_letsencrypt(self) -> bool:
        """Instala certbot para obtener certificados Let's Encrypt"""
        console.print("📦 Configurando Let's Encrypt (certbot)...")
        
        # Verificar si certbot ya está instalado
        returncode, _, _ = self.run_command("which certbot")
        if returncode == 0:
            console.print("[green]✓ Certbot ya está instalado[/green]")
            return True
        
        # Instalar certbot según el sistema
        console.print("📥 Instalando certbot...")
        returncode, _, stderr = self.run_command("sudo apt update && sudo apt install -y certbot")
        
        if returncode == 0:
            console.print("[green]✓ Certbot instalado correctamente[/green]")
            return True
        else:
            console.print(f"[red]✗ Error instalando certbot: {stderr}[/red]")
            return False
    
    def get_letsencrypt_cert(self) -> bool:
        """Obtiene certificado Let's Encrypt para el dominio configurado"""
        config = self.load_config()
        domain = config.get("domain", "")
        email = config.get("ca_server_email", "")
        ca_port = config.get("ca_server_port", 8443)
        
        if not domain or domain == "astranet.local":
            console.print("[yellow]⚠️  Necesitas configurar un dominio válido primero[/yellow]")
            return False
        
        if not email:
            console.print("[yellow]⚠️  Necesitas configurar ca_server_email en config.json[/yellow]")
            return False
        
        letsencrypt_dir = Path.home() / ".astranet" / "letsencrypt"
        letsencrypt_dir.mkdir(parents=True, exist_ok=True)
        
        console.print(f"🔐 Solicitando certificado Let's Encrypt para {domain}...")
        console.print(f"[dim]Email: {email}[/dim]")
        console.print(f"[dim]Puerto: {ca_port}[/dim]")
        console.print()
        console.print("[yellow]⚠️  IMPORTANTE: Asegúrate de que:[/yellow]")
        console.print(f"  • El dominio {domain} apunta a esta IP")
        console.print(f"  • El puerto {ca_port} está abierto en el firewall")
        console.print()
        
        if not Confirm.ask("¿Continuar con la solicitud?"):
            return False
        
        # Usar standalone mode con el puerto configurado
        cmd = (
            f"sudo certbot certonly --standalone "
            f"--preferred-challenges http "
            f"--http-01-port {ca_port} "
            f"-d {domain} "
            f"--email {email} "
            f"--agree-tos "
            f"--non-interactive"
        )
        
        returncode, stdout, stderr = self.run_command(cmd, capture_output=False)
        
        if returncode == 0:
            console.print("[green]✓ Certificado Let's Encrypt obtenido[/green]")
            
            # Copiar certificados a ~/.astranet/letsencrypt/ para fácil acceso
            cert_path = f"/etc/letsencrypt/live/{domain}"
            self.run_command(f"sudo cp {cert_path}/fullchain.pem {letsencrypt_dir}/")
            self.run_command(f"sudo cp {cert_path}/privkey.pem {letsencrypt_dir}/")
            self.run_command(f"sudo chown $USER:$USER {letsencrypt_dir}/*.pem")
            
            console.print(f"[dim]Certificados copiados a {letsencrypt_dir}[/dim]")
            return True
        else:
            console.print(f"[red]✗ Error obteniendo certificado: {stderr}[/red]")
            return False
    
    def start_ca_server(self, background: bool = True) -> bool:
        """Inicia servidor HTTPS para servir ca.crt"""
        config = self.load_config()
        domain = config.get("domain", "")
        ca_port = config.get("ca_server_port", 8443)
        
        certs_dir = Path.home() / ".astranet" / "certs"
        letsencrypt_dir = Path.home() / ".astranet" / "letsencrypt"
        
        ca_cert = certs_dir / "ca.crt"
        if not ca_cert.exists():
            console.print("[red]✗ ca.crt no existe. Genera certificados primero.[/red]")
            return False
        
        # Verificar si los certificados Let's Encrypt existen
        ssl_cert = letsencrypt_dir / "fullchain.pem"
        ssl_key = letsencrypt_dir / "privkey.pem"
        
        if not ssl_cert.exists() or not ssl_key.exists():
            console.print("[yellow]⚠️  Certificados Let's Encrypt no encontrados[/yellow]")
            if Confirm.ask("¿Deseas obtenerlos ahora?"):
                if not self.get_letsencrypt_cert():
                    return False
            else:
                return False
        
        # Crear script Python para el servidor HTTPS
        server_script = Path.home() / ".astranet" / "ca_server.py"
        server_code = f'''#!/usr/bin/env python3
import http.server
import ssl
from pathlib import Path

class CAHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/ca.crt' or self.path == '/':
            ca_file = Path.home() / ".astranet" / "certs" / "ca.crt"
            if ca_file.exists():
                self.send_response(200)
                self.send_header('Content-type', 'application/x-x509-ca-cert')
                self.send_header('Content-Disposition', 'attachment; filename="ca.crt"')
                self.end_headers()
                with open(ca_file, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "CA certificate not found")
        else:
            self.send_error(404, "Not Found")

httpd = http.server.HTTPServer(('0.0.0.0', {ca_port}), CAHandler)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(
    certfile='{ssl_cert}',
    keyfile='{ssl_key}'
)
httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

print(f"🌐 Servidor CA HTTPS corriendo en https://{{httpd.server_name}}:{ca_port}/ca.crt")
httpd.serve_forever()
'''
        
        with open(server_script, 'w') as f:
            f.write(server_code)
        server_script.chmod(0o755)
        
        console.print(f"🌐 Iniciando servidor CA HTTPS en puerto {ca_port}...")
        console.print(f"[dim]URL: https://{domain}:{ca_port}/ca.crt[/dim]")
        
        if background:
            # Iniciar en background
            cmd = f"nohup python3 {server_script} > /tmp/ca_server.log 2>&1 & echo $!"
            returncode, pid, _ = self.run_command(cmd)
            if returncode == 0:
                pid = pid.strip()
                console.print(f"[green]✓ Servidor CA iniciado (PID: {pid})[/green]")
                # Guardar PID para poder detenerlo después
                (Path.home() / ".astranet" / "ca_server.pid").write_text(pid)
                return True
            else:
                console.print("[red]✗ Error iniciando servidor CA[/red]")
                return False
        else:
            # Iniciar en foreground (para debugging)
            self.run_command(f"python3 {server_script}", capture_output=False)
            return True
    
    def stop_ca_server(self) -> bool:
        """Detiene el servidor CA HTTPS"""
        pid_file = Path.home() / ".astranet" / "ca_server.pid"
        
        if not pid_file.exists():
            console.print("[yellow]⚠️  Servidor CA no está corriendo (no se encontró PID)[/yellow]")
            return False
        
        pid = pid_file.read_text().strip()
        console.print(f"🛑 Deteniendo servidor CA (PID: {pid})...")
        
        returncode, _, _ = self.run_command(f"kill {pid}")
        if returncode == 0:
            pid_file.unlink()
            console.print("[green]✓ Servidor CA detenido[/green]")
            return True
        else:
            console.print("[red]✗ Error deteniendo servidor CA[/red]")
            return False
    
    def download_ca_from_cluster(self) -> bool:
        """Descarga ca.crt desde otros nodos del cluster"""
        config = self.load_config()
        cluster_nodes = config.get("cluster_nodes", [])
        ca_port = config.get("ca_server_port", 8443)
        certs_dir = Path.home() / ".astranet" / "certs"
        certs_dir.mkdir(parents=True, exist_ok=True)
        
        if not cluster_nodes:
            console.print("[yellow]⚠️  No hay nodos configurados en cluster_nodes[/yellow]")
            return False
        
        console.print("🔍 Buscando CA en nodos del cluster...")
        
        for node in cluster_nodes:
            # Extraer dominio (sin puerto)
            domain = node.split(":")[0] if ":" in node else node
            url = f"https://{domain}:{ca_port}/ca.crt"
            
            console.print(f"[dim]Intentando: {url}[/dim]")
            
            # Intentar descargar
            returncode, _, _ = self.run_command(
                f"curl -f -s -o {certs_dir}/ca.crt {url}",
                capture_output=True
            )
            
            if returncode == 0:
                console.print(f"[green]✓ CA descargada desde {domain}[/green]")
                return True
        
        console.print("[red]✗ No se pudo descargar CA desde ningún nodo[/red]")
        return False
    
    def create_web_user(self, username: str = None, password: str = None) -> bool:
        """Crea usuario con contraseña para acceso al panel web"""
        config = self.load_config()
        
        # Usar valores del config si no se especifican
        if username is None:
            username = config.get("admin_user", "admin")
        if password is None:
            password = config.get("admin_password", "astranet2026")
        
        certs_dir = Path.home() / ".astranet" / "certs"
        cockroach = self.get_cockroach_binary()
        sql_port = config.get("sql_port", 26257)
        
        # Obtener IP del host
        returncode, stdout, _ = self.run_command("hostname -I | awk '{print $1}'")
        host_ip = stdout.strip() if returncode == 0 else "localhost"
        
        console.print(f"👤 Creando usuario '{username}' para panel web...")
        console.print(f"[dim]Usando credenciales de config.json[/dim]")
        
        # Primero intentar eliminar el usuario si existe
        drop_sql = f"DROP USER IF EXISTS {username};"
        self.run_command(
            f'{cockroach} sql --url="postgresql://root@{host_ip}:{sql_port}/defaultdb?sslmode=verify-full&sslrootcert={certs_dir}/ca.crt&sslcert={certs_dir}/client.root.crt&sslkey={certs_dir}/client.root.key" --execute="{drop_sql}"',
            capture_output=True
        )
        
        # Crear usuario con contraseña y otorgar privilegios de admin
        create_sql = f"CREATE USER {username} WITH PASSWORD '{password}'; GRANT admin TO {username};"
        
        returncode, stdout, stderr = self.run_command(
            f'{cockroach} sql --url="postgresql://root@{host_ip}:{sql_port}/defaultdb?sslmode=verify-full&sslrootcert={certs_dir}/ca.crt&sslcert={certs_dir}/client.root.crt&sslkey={certs_dir}/client.root.key" --execute="{create_sql}"',
            capture_output=True
        )
        
        if returncode == 0:
            console.print(f"[green]✓ Usuario '{username}' creado correctamente[/green]")
            console.print(f"[cyan]📝 Credenciales del panel web:[/cyan]")
            console.print(f"[white]   URL: https://{host_ip}:8080[/white]")
            console.print(f"[white]   Usuario: {username}[/white]")
            console.print(f"[white]   Contraseña: {password}[/white]")
            
            # Guardar credenciales en archivo
            creds_file = Path.home() / ".astranet" / "web_credentials.txt"
            with open(creds_file, 'w') as f:
                f.write(f"CockroachDB Web UI Credentials\n")
                f.write(f"================================\n")
                f.write(f"URL: https://{host_ip}:8080\n")
                f.write(f"Usuario: {username}\n")
                f.write(f"Contraseña: {password}\n")
            console.print(f"[yellow]📄 Credenciales guardadas en: {creds_file}[/yellow]")
            return True
        else:
            console.print(f"[yellow]⚠️  No se pudo crear usuario: {stderr}[/yellow]")
            return False
    
    def start_cockroach(self, join_addr: str = None, is_first_node: bool = False) -> bool:
        """Inicia CockroachDB usando configuración de config.json"""
        certs_dir = Path.home() / ".astranet" / "certs"
        store_dir = Path.home() / ".astranet" / "cockroach-data"
        store_dir.mkdir(parents=True, exist_ok=True)
        
        cockroach = self.get_cockroach_binary()
        config = self.load_config()
        
        # Obtener puertos de configuración
        sql_port = config.get("sql_port", 26257)
        http_port = config.get("http_port", 8080)
        domain = config.get("domain", "astranet.local")
        cluster_nodes = config.get("cluster_nodes", [])
        
        # Obtener IP del host para advertise
        returncode, stdout, _ = self.run_command("hostname -I | awk '{print $1}'")
        host_ip = stdout.strip() if returncode == 0 else "127.0.0.1"
        
        # Construir lista de join con el dominio local + nodos configurados
        join_list = [f"{domain}:{sql_port}"]
        join_list.extend(cluster_nodes)
        join_string = ",".join(join_list)
        
        # Construir comando con setsid para desasociar del proceso padre
        # Usar --advertise-addr para que coincida con el certificado
        cmd_parts = [
            f"setsid nohup {cockroach} start",
            f"--certs-dir={certs_dir}",
            f"--store={store_dir}",
            f"--listen-addr=0.0.0.0:{sql_port}",
            f"--advertise-addr={host_ip}:{sql_port}",
            f"--http-addr=0.0.0.0:{http_port}",
            f"--join={join_string}"
        ]
        
        cmd_parts.append("> ~/.astranet/cockroach.log 2>&1 &")
        cmd = " ".join(cmd_parts)
        
        console.print("🚀 Iniciando CockroachDB en modo cluster...")
        console.print(f"[dim]Advertise: {host_ip}:{sql_port}[/dim]")
        console.print(f"[dim]Join: {join_string}[/dim]")
        console.print(f"[dim]Log: ~/.astranet/cockroach.log[/dim]")
        
        try:
            returncode, stdout, stderr = self.run_command(cmd)
            
            if returncode != 0:
                console.print(f"[red]✗ Error al ejecutar comando: {stderr}[/red]")
                return False
            
            import time
            console.print("[green]✓ CockroachDB iniciado[/green]")
            
            # Esperar a que el servidor esté listo
            console.print("⏳ Esperando a que el servidor esté listo...")
            time.sleep(3)
            
            # Verificar si está corriendo
            running, pid = self.is_cockroach_running()
            if running:
                console.print(f"[green]✓ Servidor corriendo (PID: {pid})[/green]")
                console.print(f"[cyan]📊 UI disponible en: https://{host_ip}:{http_port}[/cyan]")
                console.print(f"[dim]   Logs en tiempo real: tail -f ~/.astranet/cockroach.log[/dim]")
                
                # Iniciar servidor CA HTTPS automáticamente
                console.print()
                console.print("🌐 Iniciando servidor CA HTTPS...")
                if self.start_ca_server(background=True):
                    ca_port = config.get("ca_server_port", 8443)
                    console.print(f"[green]✓ Servidor CA disponible en: https://{domain}:{ca_port}/ca.crt[/green]")
                else:
                    console.print("[yellow]⚠️  No se pudo iniciar servidor CA (no crítico)[/yellow]")
                
                return True
            else:
                console.print("[red]✗ El servidor no se inició correctamente[/red]")
                console.print("[yellow]📋 Ver logs: tail -50 ~/.astranet/cockroach.log[/yellow]")
                return False
                
        except Exception as e:
            console.print(f"[red]✗ Excepción al iniciar: {str(e)}[/red]")
            console.print(f"[yellow]📋 Ver logs: tail -50 ~/.astranet/cockroach.log[/yellow]")
            return False
    
    def stop_cockroach(self) -> bool:
        """Detiene CockroachDB"""
        console.print("🛑 Deteniendo CockroachDB...")
        
        try:
            running, pid = self.is_cockroach_running()
            if not running:
                console.print("[yellow]⚠️  CockroachDB no está corriendo[/yellow]")
                return True
            
            # Usar kill directamente (quit no existe en v25.4.3)
            console.print(f"[dim]Deteniendo proceso {pid} con SIGTERM...[/dim]")
            returncode, stdout, stderr = self.run_command(
                f"kill -TERM {pid}",
                capture_output=True
            )
            
            if returncode != 0:
                console.print(f"[yellow]⚠️  Error al enviar SIGTERM: {stderr.strip()}[/yellow]")
            
            # Esperar y verificar
            import time
            console.print("⏳ Esperando cierre graceful...")
            time.sleep(2)
            running, new_pid = self.is_cockroach_running()
            
            if not running:
                console.print("[green]✓ CockroachDB detenido correctamente[/green]")
                return True
            else:
                # Force kill todos los procesos cockroach
                console.print("[yellow]⚠️  Forzando detención...[/yellow]")
                self.run_command("pkill -9 -f 'cockroach start'")
                time.sleep(1)
                
                # Verificar una última vez
                running, _ = self.is_cockroach_running()
                if not running:
                    console.print("[green]✓ CockroachDB forzado a detenerse[/green]")
                    return True
                else:
                    console.print("[red]✗ No se pudo detener CockroachDB completamente[/red]")
                    console.print("[yellow]💡 Intenta: pkill -9 -f 'cockroach start'[/yellow]")
                    return False
                    
        except Exception as e:
            console.print(f"[red]✗ Excepción al detener: {str(e)}[/red]")
            return False
    
    def serve_ca_cert(self, port: int = 9000) -> None:
        """Inicia servidor HTTP para compartir CA"""
        certs_dir = Path.home() / ".astranet" / "certs"
        ca_file = certs_dir / "ca.crt"
        
        if not ca_file.exists():
            console.print("[red]✗ No existe ca.crt para compartir[/red]")
            return
        
        console.print(f"\n[cyan]📤 Servidor HTTP iniciado en puerto {port}[/cyan]")
        console.print(f"[yellow]Otros nodos pueden descargar CA con:[/yellow]")
        
        # Obtener IP
        returncode, stdout, _ = self.run_command("hostname -I | awk '{print $1}'")
        ip = stdout.strip() if returncode == 0 else "TU_IP"
        
        console.print(f"[green]wget http://{ip}:{port}/ca.crt[/green]")
        console.print("\n[yellow]Presiona Ctrl+C para detener el servidor[/yellow]\n")
        
        # Iniciar servidor simple
        try:
            self.run_command(
                f"cd {certs_dir} && python3 -m http.server {port}",
                capture_output=False
            )
        except KeyboardInterrupt:
            console.print("\n[yellow]Servidor detenido[/yellow]")
    
    def init_cluster(self) -> bool:
        """Inicializa el cluster CockroachDB (solo primera vez)"""
        certs_dir = Path.home() / ".astranet" / "certs"
        config = self.load_config()
        cockroach = self.get_cockroach_binary()
        
        console.print("🔧 Inicializando cluster...")
        
        # Siempre usar localhost para init (se ejecuta localmente)
        sql_port = config.get("sql_port", 26257)
        
        try:
            console.print(f"[dim]Ejecutando: cockroach init --host=localhost:{sql_port}[/dim]")
            returncode, stdout, stderr = self.run_command(
                f"{cockroach} init --certs-dir={certs_dir} --host=localhost:{sql_port}",
                capture_output=True
            )
            
            if returncode == 0:
                console.print("[green]✓ Cluster inicializado correctamente[/green]")
                if stdout:
                    console.print(f"[dim]{stdout.strip()}[/dim]")
                
                # Crear base de datos automáticamente
                console.print()
                console.print("📊 Creando base de datos automáticamente...")
                if self.create_database():
                    console.print("[green]✓ Base de datos creada[/green]")
                else:
                    console.print("[yellow]⚠️  Error creando base de datos (no crítico)[/yellow]")
                
                return True
            elif "cluster has already been initialized" in stderr:
                console.print("[yellow]⚠️  Cluster ya estaba inicializado[/yellow]")
                return True
            else:
                console.print(f"[red]✗ Error al inicializar cluster[/red]")
                console.print(f"[red]{stderr.strip()}[/red]")
                console.print(f"[yellow]📋 Ver logs: tail -50 ~/.astranet/cockroach.log[/yellow]")
                return False
                
        except Exception as e:
            console.print(f"[red]✗ Excepción al inicializar: {str(e)}[/red]")
            return False
    
    def create_database_and_tables(self) -> bool:
        """Crea la base de datos astranet y tablas básicas"""
        certs_dir = Path.home() / ".astranet" / "certs"
        config = self.load_config()
        cockroach = self.get_cockroach_binary()
        
        domain = config.get("domain", "localhost")
        sql_port = config.get("sql_port", 26257)
        
        console.print("📊 Creando base de datos astranet...")
        
        # SQL para crear database y tablas
        sql_commands = """
-- Crear base de datos
CREATE DATABASE IF NOT EXISTS astranet;

-- Usar la base de datos
USE astranet;

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username STRING UNIQUE NOT NULL,
    password_hash STRING NOT NULL,
    created_at TIMESTAMPTZ DEFAULT current_timestamp(),
    updated_at TIMESTAMPTZ DEFAULT current_timestamp()
);

-- Tabla de nodos
CREATE TABLE IF NOT EXISTS nodos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    peer_id STRING UNIQUE NOT NULL,
    address STRING NOT NULL,
    last_seen TIMESTAMPTZ DEFAULT current_timestamp(),
    status STRING DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT current_timestamp()
);

-- Tabla de versión de schema
CREATE TABLE IF NOT EXISTS schema_version (
    id INT PRIMARY KEY DEFAULT 1,
    version INT8 NOT NULL,
    applied_at TIMESTAMPTZ DEFAULT current_timestamp(),
    CONSTRAINT single_row CHECK (id = 1)
);

-- Insertar versión inicial
INSERT INTO schema_version (id, version) VALUES (1, 1)
ON CONFLICT (id) DO NOTHING;

-- Usuario administrador por defecto
INSERT INTO usuarios (username, password_hash) 
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYk3H.olu')
ON CONFLICT (username) DO NOTHING;
"""
        
        # Escribir SQL a archivo temporal
        sql_file = Path.home() / ".astranet" / "init_schema.sql"
        with open(sql_file, 'w') as f:
            f.write(sql_commands)
        
        # Ejecutar SQL
        returncode, stdout, stderr = self.run_command(
            f"{cockroach} sql --certs-dir={certs_dir} --host={domain}:{sql_port} < {sql_file}",
            capture_output=True
        )
        
        # Limpiar archivo temporal
        sql_file.unlink(missing_ok=True)
        
        if returncode == 0:
            console.print("[green]✓ Base de datos y tablas creadas[/green]")
            console.print("[dim]Usuario: admin | Password: astranet2026[/dim]")
            return True
        else:
            console.print(f"[red]✗ Error: {stderr}[/red]")
            return False
    
    def drop_database(self) -> bool:
        """Elimina la base de datos astranet"""
        config = self.load_config()
        database_name = config.get("database_name", "astranetdb")
        
        # Confirmar acción
        from rich.prompt import Confirm
        if not Confirm.ask(f"[red]⚠️  ¿Estás seguro de eliminar la base de datos '{database_name}'? Esta acción no se puede deshacer[/red]"):
            console.print("[yellow]Operación cancelada[/yellow]")
            return False
        
        certs_dir = Path.home() / ".astranet" / "certs"
        cockroach = self.get_cockroach_binary()
        domain = config.get("domain", "localhost")
        sql_port = config.get("sql_port", 26257)
        
        console.print(f"🗑️  Eliminando base de datos '{database_name}'...")
        
        # Ejecutar DROP DATABASE
        returncode, stdout, stderr = self.run_command(
            f"{cockroach} sql --certs-dir={certs_dir} --host=localhost:{sql_port} --execute=\"DROP DATABASE IF EXISTS {database_name} CASCADE;\"",
            capture_output=True
        )
        
        if returncode == 0:
            console.print(f"[green]✓ Base de datos '{database_name}' eliminada[/green]")
            return True
        else:
            console.print(f"[red]✗ Error al eliminar: {stderr}[/red]")
            return False
    
    def purge_all_data(self) -> bool:
        """Elimina TODOS los datos, certificados, logs y binario de CockroachDB"""
        # Triple confirmación para esta operación peligrosa
        from rich.prompt import Confirm
        import shutil
        
        console.print(Panel.fit(
            "[bold red]⚠️  ADVERTENCIA: OPERACIÓN DESTRUCTIVA COMPLETA ⚠️[/bold red]\n\n"
            "Esta acción eliminará PERMANENTEMENTE:\n"
            "• Todos los datos del cluster\n"
            "• Todas las bases de datos\n"
            "• Todos los certificados TLS\n"
            "• Todos los logs\n"
            "• El binario de CockroachDB\n"
            "• Credenciales guardadas\n\n"
            "[bold]El sistema quedará como si nunca se hubiera instalado[/bold]",
            style="red"
        ))
        
        if not Confirm.ask("[red]¿Continuar con la eliminación TOTAL?[/red]"):
            console.print("[yellow]Operación cancelada[/yellow]")
            return False
        
        if not Confirm.ask("[red]¿Estás COMPLETAMENTE seguro? (Segunda confirmación)[/red]"):
            console.print("[yellow]Operación cancelada[/yellow]")
            return False
        
        if not Confirm.ask("[red]¿ÚLTIMA OPORTUNIDAD? Esta acción NO se puede deshacer[/red]"):
            console.print("[yellow]Operación cancelada[/yellow]")
            return False
        
        # Verificar si está corriendo
        running, pid = self.is_cockroach_running()
        if running:
            console.print("[red]✗ CockroachDB está corriendo. Deténlo primero.[/red]")
            if Confirm.ask("¿Detener CockroachDB ahora?"):
                if not self.stop_cockroach():
                    console.print("[red]✗ No se pudo detener. Cancela manualmente los procesos.[/red]")
                    return False
            else:
                return False
        
        console.print("\n[bold red]🗑️  INICIANDO ELIMINACIÓN COMPLETA...[/bold red]\n")
        errors = []
        
        try:
            # 1. Eliminar directorio de datos
            store_dir = Path.home() / ".astranet" / "cockroach-data"
            console.print(f"[dim]Eliminando datos: {store_dir}[/dim]")
            if store_dir.exists():
                shutil.rmtree(store_dir)
                console.print("[green]✓ Datos eliminados[/green]")
            else:
                console.print("[yellow]⚠️  Directorio de datos no existía[/yellow]")
            
            # 2. Eliminar certificados
            certs_dir = Path.home() / ".astranet" / "certs"
            console.print(f"[dim]Eliminando certificados: {certs_dir}[/dim]")
            if certs_dir.exists():
                shutil.rmtree(certs_dir)
                console.print("[green]✓ Certificados eliminados[/green]")
            else:
                console.print("[yellow]⚠️  Directorio de certificados no existía[/yellow]")
            
            # 3. Eliminar logs
            log_file = Path.home() / ".astranet" / "cockroach.log"
            console.print(f"[dim]Eliminando log: {log_file}[/dim]")
            if log_file.exists():
                log_file.unlink()
                console.print("[green]✓ Log eliminado[/green]")
            
            # 4. Eliminar credenciales guardadas
            creds_file = Path.home() / ".astranet" / "web_credentials.txt"
            if creds_file.exists():
                creds_file.unlink()
                console.print("[green]✓ Credenciales eliminadas[/green]")
            
            # 5. Eliminar binario de CockroachDB
            console.print("\n[dim]Buscando y eliminando binario de CockroachDB...[/dim]")
            cockroach_paths = [
                Path.home() / "bin" / "cockroach",
                Path("/usr/local/bin/cockroach"),
                Path("/usr/bin/cockroach")
            ]
            
            binary_found = False
            for cockroach_path in cockroach_paths:
                if cockroach_path.exists():
                    try:
                        cockroach_path.unlink()
                        console.print(f"[green]✓ Binario eliminado: {cockroach_path}[/green]")
                        binary_found = True
                    except PermissionError:
                        console.print(f"[yellow]⚠️  Sin permisos para eliminar: {cockroach_path}[/yellow]")
                        console.print(f"[yellow]   Ejecuta: sudo rm {cockroach_path}[/yellow]")
                        errors.append(f"Binario no eliminado: {cockroach_path}")
            
            if not binary_found:
                console.print("[yellow]⚠️  No se encontró el binario de CockroachDB[/yellow]")
            
            # 6. Limpiar entrada del PATH en .bashrc (si se agregó)
            bashrc = Path.home() / ".bashrc"
            if bashrc.exists():
                with open(bashrc, 'r') as f:
                    lines = f.readlines()
                
                # Filtrar líneas relacionadas con Astranet
                new_lines = []
                skip_next = False
                for line in lines:
                    if "# Agregado por Astranet" in line:
                        skip_next = True
                        continue
                    if skip_next and "export PATH=" in line and "/bin/cockroach" in line:
                        skip_next = False
                        continue
                    new_lines.append(line)
                
                if len(new_lines) < len(lines):
                    with open(bashrc, 'w') as f:
                        f.writelines(new_lines)
                    console.print("[green]✓ Entrada de PATH limpiada en .bashrc[/green]")
            
            # 7. Eliminar directorio .astranet si está vacío
            astranet_dir = Path.home() / ".astranet"
            if astranet_dir.exists() and not list(astranet_dir.iterdir()):
                astranet_dir.rmdir()
                console.print("[green]✓ Directorio .astranet eliminado[/green]")
            
            # Resumen final
            console.print("\n" + "="*50)
            if errors:
                console.print("[yellow]✓ Eliminación completada con advertencias:[/yellow]")
                for error in errors:
                    console.print(f"[yellow]  • {error}[/yellow]")
            else:
                console.print("[green]✓ ELIMINACIÓN COMPLETA EXITOSA[/green]")
            console.print("[cyan]💡 CockroachDB ha sido completamente desinstalado[/cyan]")
            console.print("="*50)
            return True
            
        except Exception as e:
            console.print(f"\n[red]✗ Error durante la eliminación: {str(e)}[/red]")
            return False

    # ═══════════════════════════════════════════════════════════════════
    # Métodos de interfaz simplificada (wrappers)
    # ═══════════════════════════════════════════════════════════════════
    
    def is_installed(self) -> bool:
        """Alias para is_cockroach_installed"""
        return self.is_cockroach_installed()
    
    def get_binary(self) -> str:
        """Alias para get_cockroach_binary"""
        return self.get_cockroach_binary()
    
    def get_version(self) -> str:
        """Alias para get_cockroach_version"""
        return self.get_cockroach_version()
    
    def is_running(self) -> Tuple[bool, str]:
        """Alias para is_cockroach_running"""
        return self.is_cockroach_running()
    
    def install(self) -> bool:
        """Alias para install_cockroach"""
        return self.install_cockroach()
    
    def start(self) -> bool:
        """Inicia CockroachDB con configuración del cluster"""
        return self.start_cockroach()
    
    def stop(self) -> bool:
        """Detiene CockroachDB"""
        return self.stop_cockroach()
    
    def create_database(self) -> bool:
        """Crea la base de datos y aplica migraciones"""
        cockroach = self.get_cockroach_binary()
        certs_dir = Path.home() / ".astranet" / "certs"
        config = self.load_config()
        sql_port = config.get("sql_port", 26257)
        db_name = config.get("database_name", "astranetdb")
        
        console.print(f"📊 Creando base de datos '{db_name}'...")
        
        # Crear base de datos
        returncode, stdout, stderr = self.run_command(
            f'{cockroach} sql --certs-dir={certs_dir} --host=localhost:{sql_port} -e "CREATE DATABASE IF NOT EXISTS {db_name};"',
            capture_output=True
        )
        
        if returncode != 0:
            console.print(f"[red]✗ Error creando base de datos: {stderr}[/red]")
            return False
        
        console.print(f"[green]✓ Base de datos '{db_name}' lista[/green]")
        
        # Aplicar migraciones
        from .migration_manager import MigrationManager
        migrator = MigrationManager(self)
        return migrator.migrate()
    
    
