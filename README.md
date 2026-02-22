# 🚀 Astranet CLI

Herramienta de línea de comandos para la gestión completa del ecosistema Astranet, incluyendo CockroachDB, backend Rust, dashboard React, Kubernetes y Docker.

## 📋 Descripción

Astranet CLI es un sistema modular de gestión que proporciona una interfaz unificada e interactiva para administrar todos los componentes de la infraestructura Astranet:

- **🪳 CockroachDB**: Gestión de cluster de base de datos distribuida
- **⚙️ Backend Astranet**: Control del backend en Rust
- **🎨 Dashboard**: Gestión del dashboard React
- **☸️ Kubernetes**: Administración de cluster K8s (opcional)
- **🐳 Docker**: Gestión de contenedores (opcional)
- **🔄 Migraciones**: Sistema de migraciones de base de datos

## ✨ Características

### Gestión de CockroachDB
- ✅ Instalación automática de CockroachDB
- ✅ Configuración de cluster multi-nodo
- ✅ Generación y gestión de certificados SSL/TLS
- ✅ Sincronización de CA entre nodos
- ✅ Creación de bases de datos y usuarios
- ✅ Sistema de migraciones SQL
- ✅ Monitoreo de logs en tiempo real

### Gestión de Astranet
- ✅ Inicio/detención del backend Rust
- ✅ Inicio/detención del dashboard React
- ✅ Compilación del backend
- ✅ Instalación de dependencias del dashboard
- ✅ Gestión de logs

### Sistema de Migraciones
- ✅ Aplicación automática de migraciones
- ✅ Rollback de migraciones
- ✅ Verificación de estado de migraciones
- ✅ Migraciones versionadas

## 🔧 Requisitos

### Sistema Operativo
- Linux (recomendado: Ubuntu 20.04+)
- Python 3.8+

### Dependencias de Sistema
```bash
# Para CockroachDB
curl

# Para backend Astranet
rust (rustc, cargo)

# Para dashboard
node.js (v16+)
npm o yarn
```

### Dependencias de Python
- `rich` - Para la interfaz de terminal interactiva

La instalación se cubre en la sección de instalación con múltiples opciones según tu sistema.

## 📦 Instalación

### 1. Clonar el repositorio

**Opción A: HTTPS (recomendado para empezar)**
```bash
git clone https://github.com/corrancho/astranet_cli.git
cd astranet_cli
```

**Opción B: SSH (requiere configuración previa)**
```bash
git clone git@github.com:corrancho/astranet_cli.git
cd astranet_cli
```

<details>
<summary>📌 Configurar SSH para GitHub (si usas la Opción B)</summary>

Si obtienes el error `Permission denied (publickey)`, necesitas configurar tu clave SSH:

```bash
# 1. Generar clave SSH (si no tienes una)
ssh-keygen -t ed25519 -C "tu_email@example.com"
# Presiona Enter para aceptar la ubicación por defecto
# Opcionalmente agrega una contraseña

# 2. Iniciar el agente SSH
eval "$(ssh-agent -s)"

# 3. Agregar la clave al agente
ssh-add ~/.ssh/id_ed25519

# 4. Copiar la clave pública
cat ~/.ssh/id_ed25519.pub
# Copia todo el contenido que aparece

# 5. Agregar la clave a GitHub
# Ve a: https://github.com/settings/keys
# Click en "New SSH key"
# Pega la clave pública copiada

# 6. Verificar la conexión
ssh -T git@github.com
```

</details>

### 2. Instalar dependencias de Python

**Opción A: Usar el paquete del sistema (recomendado)**
```bash
# Debian/Ubuntu
sudo apt install python3-rich

# Fedora/RHEL
sudo dnf install python3-rich
```

**Opción B: Usar pipx (recomendado para herramientas CLI)**
```bash
# Instalar pipx si no lo tienes
sudo apt install pipx  # Debian/Ubuntu
# o
sudo dnf install pipx  # Fedora/RHEL

# Instalar astranet_cli con todas sus dependencias
pipx install .
```

**Opción C: Entorno virtual**
```bash
# Crear entorno virtual
python3 -m venv .venv

# Activar entorno virtual
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Nota: Deberás activar el entorno cada vez que uses la CLI
```

**Opción D: Instalación global (no recomendado)**
```bash
# Solo si las opciones anteriores no funcionan
pip install --user rich --break-system-packages
```

### 3. Dar permisos de ejecución
```bash
chmod +x astranet.py
```

## 🚀 Uso

### Modo Interactivo
Ejecuta la CLI en modo interactivo con menús visuales:

```bash
./astranet.py
```

También puedes ejecutarlo como módulo Python:

```bash
python -m astranet_cli
```

### Menú Principal

Al ejecutar la aplicación, verás un menú interactivo con las siguientes opciones:

1. **🪳 Gestión de CockroachDB**
   - Instalar/configurar CockroachDB
   - Gestionar certificados
   - Iniciar/detener cluster
   - Crear bases de datos y usuarios

2. **🚀 Gestión de Astranet**
   - Iniciar/detener backend
   - Iniciar/detener dashboard
   - Compilar backend
   - Instalar dependencias

3. **🔄 Migraciones de Base de Datos**
   - Aplicar migraciones pendientes
   - Rollback de migraciones
   - Ver estado de migraciones

4. **☸️ Gestión de Kubernetes** (opcional)
   - Configuración de cluster K8s

5. **🐳 Gestión de Docker** (opcional)
   - Gestión de contenedores

## ⚙️ Configuración

La configuración se encuentra en `astranet_cli/config.json`:

```json
{
  "cockroachdb": {
    "sql_port": 26257,
    "http_port": 8090,
    "domain": "cockroachdb.astranet.dev",
    "cluster_nodes": [
      "cockroachdb.astranet.dev:26257",
      "cockroachdb1.astranet.dev:26258",
      "cockroachdb2.astranet.dev:26259",
      "cockroachdb3.astranet.dev:26260"
    ],
    "database_name": "astranetdb",
    "admin_user": "webadmin",
    "certs_dir": "~/.astranet/certs",
    "data_dir": "~/.astranet/cockroach-data"
  }
}
```

### Estructura de Directorios

```
~/.astranet/
├── certs/              # Certificados SSL/TLS
│   ├── ca.crt
│   ├── ca.key
│   ├── node.crt
│   └── node.key
├── cockroach-data/     # Datos de CockroachDB
└── cockroach.log       # Logs de CockroachDB
```

## 🗄️ Migraciones

Las migraciones SQL se encuentran en `astranet_cli/migrations/`:

```
astranet_cli/migrations/
├── 001_initial_schema.sql
├── 002_messaging_tables.sql
└── README.md
```

### Crear una Nueva Migración

1. Crea un archivo SQL en `astranet_cli/migrations/`
2. Nómbralo con el siguiente formato: `XXX_descripcion.sql`
   - Ejemplo: `003_add_users_table.sql`
3. La migración se aplicará automáticamente en orden numérico

## 🏗️ Estructura del Proyecto

```
astranet_cli/
├── astranet.py                 # Punto de entrada principal
├── astranet_cli/
│   ├── __init__.py
│   ├── __main__.py            # Entry point como módulo
│   ├── main.py                # Menú principal y lógica
│   ├── config.json            # Configuración
│   ├── cockroach_manager.py   # Gestión de CockroachDB
│   ├── astranet_manager.py    # Gestión de Backend/Dashboard
│   ├── migration_manager.py   # Sistema de migraciones
│   ├── k8s_manager.py         # Gestión de Kubernetes
│   ├── docker_manager.py      # Gestión de Docker
│   ├── system_utils.py        # Utilidades del sistema
│   └── migrations/            # Migraciones SQL
│       ├── 001_initial_schema.sql
│       ├── 002_messaging_tables.sql
│       └── README.md
└── README.md
```

## 🔒 Certificados SSL/TLS

La CLI gestiona automáticamente los certificados para CockroachDB:

### Generación de Certificados
1. Crea una CA (Certificate Authority) raíz
2. Genera certificados para cada nodo del cluster
3. Los almacena en `~/.astranet/certs/`

### Sincronización de CA
Si te unes a un cluster existente:
1. La CLI intentará descargar el CA del cluster
2. Si no está disponible, creará uno nuevo
3. Puedes servir tu CA para otros nodos mediante un servidor temporal

## 📊 Gestión de Cluster CockroachDB

### Primer Nodo (Inicializador)
```bash
./astranet.py
# Selecciona: Gestión de CockroachDB
# Instalar CockroachDB
# Generar certificados
# Iniciar cluster
# Inicializar base de datos
```

### Nodos Adicionales
```bash
./astranet.py
# Selecciona: Gestión de CockroachDB
# Instalar CockroachDB
# Configurar cluster (añade la IP del primer nodo)
# Generar certificados (descargará CA automáticamente)
# Iniciar cluster
```

## 🐛 Troubleshooting

### Error: externally-managed-environment
Si recibes este error al instalar con pip:
```
error: externally-managed-environment
```

**Solución**: Tu sistema usa PEP 668 para proteger los paquetes de Python del sistema. Usa una de estas alternativas:
1. **Recomendado**: `sudo apt install python3-rich`
2. Usar entorno virtual (ver sección de instalación)
3. Usar pipx para instalar la CLI completa

### CockroachDB no se inicia
```bash
# Verifica los logs
tail -f ~/.astranet/cockroach.log

# Verifica los certificados
ls -la ~/.astranet/certs/

# Verifica que el puerto no esté en uso
netstat -tulpn | grep 26257
```

### Errores de certificados
```bash
# Regenera los certificados desde la CLI
./astranet.py
# Gestión de CockroachDB > Generar/Regenerar certificados
```

### No se puede conectar al cluster
1. Verifica que todos los nodos estén en la misma red
2. Verifica que los dominios en `config.json` sean correctos
3. Verifica que los puertos estén abiertos en el firewall

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto es parte del ecosistema Astranet.

## 👤 Autor

**corrancho**
- GitHub: [@corrancho](https://github.com/corrancho)

## 🙏 Agradecimientos

- CockroachDB por su excelente base de datos distribuida
- Rich por la hermosa interfaz de terminal
- La comunidad de Astranet

---

**Nota**: Este proyecto está en desarrollo activo. Algunas características pueden estar incompletas o cambiar en futuras versiones.
