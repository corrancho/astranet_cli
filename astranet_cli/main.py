"""
Astranet CLI - Menú Principal
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box

from pathlib import Path
from . import __version__
from .cockroach_manager import CockroachManager
from .astranet_manager import AstranetManager
from .k8s_manager import K8sManager
from .docker_manager import DockerManager

console = Console()


def show_cockroach_menu(crdb: CockroachManager):
    """Menú de gestión de CockroachDB"""
    while True:
        console.clear()
        console.print(Panel.fit("🪳 Gestión de CockroachDB", style="bold cyan"))
        console.print()
        
        # Estado
        installed = crdb.is_installed()
        running, pid = crdb.is_running()
        has_ca = (crdb.certs_dir / "ca.crt").exists()
        has_node_cert = (crdb.certs_dir / "node.crt").exists()
        config = crdb.load_config()
        
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_column("Campo", style="cyan")
        table.add_column("Valor")
        
        table.add_row("Estado", "[green]Instalado[/green]" if installed else "[red]No instalado[/red]")
        if installed:
            table.add_row("Versión", crdb.get_version())
        table.add_row("Corriendo", f"[green]Sí (PID: {pid})[/green]" if running else "[red]No[/red]")
        table.add_row("Configuración", f"[green]{config['domain']}:{config['sql_port']}[/green]")
        table.add_row("CA cert", "[green]Sí[/green]" if has_ca else "[red]No[/red]")
        table.add_row("Node cert", "[green]Sí[/green]" if has_node_cert else "[red]No[/red]")
        
        console.print(table)
        console.print()
        
        # Menú dinámico
        if not installed:
            console.print("  [green]1. Instalar CockroachDB[/green]")
            console.print("  [magenta]0. Volver[/magenta]")
            choice = Prompt.ask("Selecciona una opción", choices=["1", "0"])
            
            if choice == "1":
                crdb.install()
                input("\nPresiona Enter...")
            else:
                break
        else:
            console.print("  [cyan]1. Ver/Editar configuración cluster[/cyan]")
            console.print("  [green]2. Generar/Regenerar certificados[/green]")
            
            if running:
                console.print("  [red]3. Detener cluster[/red]")
                console.print("  [yellow]4. Ver logs[/yellow]")
                console.print("  [cyan]5. Crear/Inicializar base de datos[/cyan]")
                console.print("  [green]6. Crear usuario web[/green]")
                console.print("  [red]7. Eliminar base de datos[/red]")
            else:
                console.print("  [green]3. Iniciar cluster[/green]")
                console.print("  [red]4. Borrar TODOS los datos[/red]")
            
            console.print("  [magenta]0. Volver[/magenta]")
            
            valid_choices = ["1", "2", "3", "0"]
            if running:
                valid_choices.extend(["4", "5", "6", "7"])
            else:
                valid_choices.append("4")
            
            choice = Prompt.ask("Selecciona una opción", choices=valid_choices)
            
            if choice == "1":
                crdb.configure_cluster_interactive()
                input("\nPresiona Enter...")
            elif choice == "2":
                if not has_ca:
                    # Intentar descargar CA de otros nodos primero
                    console.print("🔍 Buscando CA existente en el cluster...")
                    ca_downloaded = crdb.download_ca_from_cluster()
                    
                    if not ca_downloaded:
                        # Si no se pudo descargar, crear nuevo CA
                        console.print("[yellow]No se encontró CA en otros nodos. Creando nuevo CA...[/yellow]")
                        if not crdb.create_ca_cert():
                            console.print("[red]✗ Error creando CA[/red]")
                            input("\nPresiona Enter...")
                            continue
                    
                    # Generar certificados del nodo
                    crdb.create_node_cert()
                    crdb.create_client_cert()
                else:
                    if Confirm.ask("¿Regenerar todos los certificados?"):
                        crdb.create_ca_cert()
                        crdb.create_node_cert()
                        crdb.create_client_cert()
                input("\nPresiona Enter...")
            elif choice == "3":
                if running:
                    crdb.stop()
                else:
                    if crdb.start():
                        import time
                        time.sleep(2)
                        crdb.init_cluster()
                input("\nPresiona Enter...")
            elif choice == "4" and running:
                import subprocess
                subprocess.run(f"tail -50 ~/.astranet/cockroach.log", shell=True)
                input("\nPresiona Enter...")
            elif choice == "5" and running:
                crdb.create_database()
                input("\nPresiona Enter...")
            elif choice == "6" and running:
                crdb.create_web_user()
                input("\nPresiona Enter...")
            elif choice == "7" and running:
                crdb.drop_database()
                input("\nPresiona Enter...")
            elif choice == "4" and not running:
                crdb.purge_all_data()
                input("\nPresiona Enter...")
            elif choice == "0":
                break


def show_astranet_menu(astranet: AstranetManager):
    """Menú de gestión de Astranet"""
    while True:
        console.clear()
        console.print(Panel.fit("🚀 Gestión del Servidor Astranet", style="bold cyan"))
        
        services = astranet.get_services_status()
        
        console.print("[bold]Estado de servicios:[/bold]")
        if services["backend"]["running"]:
            console.print(f"  [green]✓ Backend corriendo (PID: {services['backend']['pid']})[/green]")
        else:
            console.print("  [yellow]✗ Backend detenido[/yellow]")
        
        if services["dashboard"]["running"]:
            console.print(f"  [green]✓ Dashboard corriendo (PID: {services['dashboard']['pid']})[/green]")
        else:
            console.print("  [yellow]✗ Dashboard detenido[/yellow]")
        
        console.print()
        
        # Menú
        if not services["backend"]["running"]:
            console.print("  [green]1. Iniciar Backend[/green]")
        else:
            console.print("  [red]1. Detener Backend[/red]")
        
        if not services["dashboard"]["running"]:
            console.print("  [green]2. Iniciar Dashboard[/green]")
        else:
            console.print("  [red]2. Detener Dashboard[/red]")
        
        console.print("  [cyan]3. Compilar proyecto (cargo build --release)[/cyan]")
        console.print("  [magenta]0. Volver[/magenta]")
        
        choice = Prompt.ask("Selecciona una opción", choices=["1", "2", "3", "0"])
        
        if choice == "1":
            if services["backend"]["running"]:
                astranet.stop_backend()
            else:
                astranet.start_backend()
            input("\nPresiona Enter...")
        elif choice == "2":
            if services["dashboard"]["running"]:
                astranet.stop_dashboard()
            else:
                astranet.start_dashboard()
            input("\nPresiona Enter...")
        elif choice == "3":
            astranet.compile_backend()
            input("\nPresiona Enter...")
        elif choice == "0":
            break


def clean_all_astranet_data():
    """Elimina todos los datos y archivos de Astranet"""
    console.clear()
    console.print(Panel.fit(
        "🗑️  Limpieza Total de Datos de Astranet",
        style="bold red"
    ))
    console.print()
    
    # Lista de directorios/archivos a eliminar
    items_to_remove = [
        (Path.home() / ".astranet", "Directorio principal (~/.astranet)"),
        (Path.home() / ".astranet" / "certs", "  • Certificados SSL/TLS"),
        (Path.home() / ".astranet" / "cockroach-data", "  • Datos de CockroachDB"),
        (Path.home() / ".astranet" / "cockroach.log", "  • Logs de CockroachDB"),
    ]
    
    console.print("[yellow]⚠️  Se eliminarán los siguientes archivos y directorios:[/yellow]\n")
    
    existing_items = []
    for path, description in items_to_remove:
        if path.exists():
            size = ""
            if path.is_dir():
                # Contar archivos
                try:
                    file_count = sum(1 for _ in path.rglob('*') if _.is_file())
                    size = f" ({file_count} archivos)"
                except:
                    size = ""
            elif path.is_file():
                # Tamaño del archivo
                try:
                    size_bytes = path.stat().st_size
                    if size_bytes < 1024:
                        size = f" ({size_bytes}B)"
                    elif size_bytes < 1024*1024:
                        size = f" ({size_bytes/1024:.1f}KB)"
                    else:
                        size = f" ({size_bytes/(1024*1024):.1f}MB)"
                except:
                    size = ""
            
            console.print(f"  ✓ {description}{size}")
            existing_items.append(path)
    
    if not existing_items:
        console.print("[green]No hay datos de Astranet para eliminar.[/green]\n")
        input("Presiona Enter para continuar...")
        return
    
    console.print()
    console.print("[bold red]⚠️  ADVERTENCIA: Esta acción NO se puede deshacer[/bold red]")
    console.print("[yellow]Se eliminarán:[/yellow]")
    console.print("  • Todos los certificados SSL/TLS")
    console.print("  • Todos los datos de CockroachDB")
    console.print("  • Configuración de nodos")
    console.print("  • Logs del sistema")
    console.print()
    
    if not Confirm.ask("[bold red]¿Estás SEGURO de que quieres eliminar todos los datos?[/bold red]"):
        console.print("\n[yellow]Operación cancelada[/yellow]\n")
        input("Presiona Enter para continuar...")
        return
    
    console.print()
    console.print("[cyan]Eliminando datos...[/cyan]\n")
    
    import shutil
    errors = []
    
    # Eliminar el directorio principal (esto elimina todo dentro)
    main_dir = Path.home() / ".astranet"
    if main_dir.exists():
        try:
            shutil.rmtree(main_dir)
            console.print(f"[green]✓ Eliminado: {main_dir}[/green]")
        except Exception as e:
            console.print(f"[red]✗ Error eliminando {main_dir}: {e}[/red]")
            errors.append((main_dir, str(e)))
    
    console.print()
    
    if errors:
        console.print("[yellow]⚠️  Algunos elementos no pudieron eliminarse:[/yellow]")
        for path, error in errors:
            console.print(f"  • {path}: {error}")
    else:
        console.print("[bold green]✓ Todos los datos de Astranet han sido eliminados correctamente[/bold green]")
    
    console.print()
    input("Presiona Enter para continuar...")


def main():
    """Punto de entrada principal"""
    # Inicializar managers
    crdb = CockroachManager()
    astranet = AstranetManager()
    k8s = K8sManager()
    docker = DockerManager()
    
    while True:
        console.clear()
        console.print(Panel.fit(
            f"🚀 Astranet CLI - Gestión del Sistema\nv{__version__}",
            style="bold cyan"
        ))
        console.print()
        
        console.print("  [green]1. Gestionar CockroachDB[/green]")
        console.print("  [green]2. Gestionar Astranet (Backend/Dashboard)[/green]")
        console.print("  [green]3. Gestionar Kubernetes[/green]")
        console.print("  [green]4. Gestionar Docker[/green]")
        console.print("  [red]5. Limpiar todos los datos de Astranet[/red]")
        console.print("  [red]0. Salir[/red]")
        console.print()
        
        choice = Prompt.ask("Selecciona una opción", choices=["1", "2", "3", "4", "5", "0"])
        
        if choice == "1":
            show_cockroach_menu(crdb)
        elif choice == "2":
            show_astranet_menu(astranet)
        elif choice == "3":
            k8s.k8s_menu()
        elif choice == "4":
            docker.docker_menu()
        elif choice == "5":
            clean_all_astranet_data()
        elif choice == "0":
            console.print("\n[cyan]👋 ¡Hasta luego![/cyan]\n")
            break


if __name__ == "__main__":
    main()
