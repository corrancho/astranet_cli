"""
Utilidades del sistema - Funciones comunes para todos los managers
"""

import os
import subprocess
import platform
from pathlib import Path
from typing import Tuple, Optional
from rich.console import Console

console = Console()


class SystemUtils:
    """Utilidades compartidas para comandos del sistema"""
    
    def __init__(self):
        self.is_root = os.geteuid() == 0
        self.sudo_user = os.environ.get('SUDO_USER', os.environ.get('USER', 'root'))
        self.os_info = self._get_os_info()
        
    def _get_os_info(self) -> dict:
        """Obtiene información del sistema operativo"""
        info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "distro": "Unknown",
            "distro_version": "Unknown"
        }
        
        if Path("/etc/os-release").exists():
            with open("/etc/os-release") as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith("ID="):
                        info["distro"] = line.split("=")[1].strip().strip('"')
                    elif line.startswith("VERSION_ID="):
                        info["distro_version"] = line.split("=")[1].strip().strip('"')
        
        return info
    
    def run_command(
        self, 
        cmd: str, 
        sudo: bool = False, 
        capture_output: bool = True
    ) -> Tuple[int, str, str]:
        """Ejecuta un comando del sistema"""
        # Asegurar PATH completo para comandos
        env = os.environ.copy()
        env['PATH'] = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
        
        if sudo and not self.is_root:
            cmd = f"sudo {cmd}"
        
        try:
            if capture_output:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    env=env
                )
                return result.returncode, result.stdout, result.stderr
            else:
                result = subprocess.run(cmd, shell=True, env=env)
                return result.returncode, "", ""
        except Exception as e:
            return 1, "", str(e)
    
    def check_command_exists(self, command: str) -> bool:
        """Verifica si un comando existe en el sistema"""
        returncode, _, _ = self.run_command(f"which {command}")
        return returncode == 0
    
    def get_service_pid(self, pattern: str) -> Optional[str]:
        """Obtiene el PID de un proceso por patrón"""
        returncode, stdout, _ = self.run_command(f"pgrep -f '{pattern}'")
        if returncode == 0 and stdout.strip():
            return stdout.strip().split('\n')[0]
        return None
    
    def is_port_in_use(self, port: int) -> Tuple[bool, Optional[str]]:
        """Verifica si un puerto está en uso y retorna el PID"""
        returncode, stdout, _ = self.run_command(
            f"lsof -i :{port} -t 2>/dev/null | head -1"
        )
        if returncode == 0 and stdout.strip():
            return True, stdout.strip()
        return False, None
    
    def kill_process(self, pid: str, force: bool = False) -> bool:
        """Mata un proceso por PID"""
        signal = "-9" if force else "-15"
        returncode, _, _ = self.run_command(f"kill {signal} {pid}", sudo=True)
        return returncode == 0
