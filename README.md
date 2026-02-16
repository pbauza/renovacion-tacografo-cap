# Renovaciones Tacografo CAP

Aplicación web para gestión de renovaciones de documentación de clientes (conductores/empresas), con backend FastAPI, GUI web, importación masiva, alertas automáticas y generación de informes PDF.

## 1. Objetivo del proyecto
El sistema permite:
- Gestionar clientes.
- Gestionar documentos por cliente (DNI, Carnet, CAP, Tarjeta Tacógrafo, Power of Attorney, Other).
- Generar alertas automáticas por caducidad.
- Importar datos desde Excel/CSV.
- Generar informes PDF por cliente y en bloque.
- Operar desde GUI o vía API REST.

## 2. Stack técnico
- Python 3.11+
- FastAPI
- SQLAlchemy (async)
- SQLite por defecto (configurable)
- Jinja2 + Bootstrap 5 (GUI server-rendered)
- ReportLab + Pillow + pypdf (PDF)
- openpyxl / csv (importación)

## 3. Estructura del proyecto
```text
app/
  api/
    routers/
  core/
  db/
  models/
  pdf_generator/
  scheduler/
  schemas/
  services/
  ui/
config/
  app_config.json
static/
  admin.css
  admin.js
  img/
    logo.png
  config/forms/
  samples/
templates/
main.py
requirements.txt
pyproject.toml
```

## 4. Configuración

### 4.1 `.env`
Copia el archivo ejemplo:

```bash
cp .env.example .env
```

Variables principales:

```env
APP_NAME=Renovaciones Tacografo CAP
API_PREFIX=/api/v1
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000
UVICORN_RELOAD=false
DATABASE_URL=sqlite+aiosqlite:///./renovaciones.db
SCHEDULER_ENABLED=true
RESET_DB_ON_STARTUP=false
AUTO_RESET_SQLITE_ON_SCHEMA_MISMATCH=true
BACKUP_ON_STARTUP=true
BACKUP_KEEP_LAST=30
STORAGE_BACKUP_ON_STARTUP=true
STORAGE_BACKUP_KEEP_LAST=30
```

### 4.2 `config/app_config.json` (branding + PDF + GUI)
Todo lo visual/branding y contacto del PDF se configura aquí.

Ejemplo:

```json
{
  "app_name": "Renovaciones Tacografo CAP",
  "workspace_subtitle": "Tacograph + CAP management workspace",
  "ui": {
    "logo_path": "/static/img/logo.png",
    "favicon_path": "/static/img/logo.png",
    "dashboard_logo_path": "/static/img/logo.png"
  },
  "pdf": {
    "report_title": "Client Renewal Report",
    "organization_name": "Renovaciones Tacografo CAP",
    "contact_email": "contact@renovaciones.local",
    "contact_phone": "+34 000 000 000"
  }
}
```

Notas:
- El nombre de la app en GUI/API usa este JSON.
- El logo en cabecera PDF, favicon y dashboard usa este JSON.
- El contacto del footer PDF usa este JSON.

## 5. Instalación

### 5.1 Linux
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 5.2 Windows (PowerShell)
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

### 5.3 Build `.exe` para Windows (Makefile)
Con GNU Make disponible en Windows:

```powershell
make build-windows-exe
```

Salida esperada:
- Ejecutable: `dist\renovaciones_tacografo_cap\renovaciones_tacografo_cap.exe`
- Incluye carpetas: `templates`, `static`, `config`

## 6. Ejecución en desarrollo

```bash
python main.py
```

Accesos:
- GUI: `http://127.0.0.1:8000/`
- Swagger: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### 6.1 Ejecución en Windows con `.bat`
Script recomendado:

```powershell
.\run_app.bat
```

Qué hace:
- Instala dependencias desde `requirements.txt`.
- Arranca la app con `python main.py`.
- Si `DATABASE_URL` no está definida, usa SQLite local de Windows:
  - `C:\Users\<usuario>\AppData\Local\RenovacionesTacografoCap\renovaciones.db`

Este comportamiento evita bloqueos de SQLite al ejecutar desde rutas UNC/WSL (`\\wsl.localhost\...`).

## 7. GUI (panel de administración)
Secciones:
- Dashboard
- Clients
- Alerts
- Documents
- Tools
- Settings

Funcionalidades clave:
- Búsqueda de clientes por nombre/NIF/empresa/teléfono.
- Alta/edición/borrado de clientes.
- Drag & drop de foto de cliente (imagen o PDF).
- Alta/edición/borrado de documentos.
- Alta automática de alerta al crear/editar documento con caducidad.
- Carga/reemplazo de PDF de documento.
- Importación masiva desde CSV/XLSX.
- Generación de PDF por cliente y en bloque.

## 8. Modelo de datos

### 8.1 Cliente (`clients`)
- `id`
- `full_name`
- `company` (opcional)
- `photo_path` (opcional)
- `nif` (único)
- `phone`
- `email` (opcional)
- `created_at`

### 8.2 Documento (`documents`)
Tipos (`doc_type`):
- `dni`
- `driving_license`
- `cap`
- `tachograph_card`
- `power_of_attorney`
- `other`

Campos persistidos:
- `id`, `client_id`, `doc_type`
- `expiry_date`, `issue_date`, `birth_date`
- `address`, `pdf_path`, `course_number`
- `flag_fran`, `flag_ciusaba`
- `expiry_fran`, `expiry_ciusaba`
- `created_at`

### 8.3 Alerta (`alerts`)
- `id`
- `client_id`
- `document_id`
- `expiry_date`
- `alert_date` (por defecto 50 días antes)
- `created_at`

## 9. Almacenamiento de archivos
- Fotos cliente: `storage/clientes/{nif}/{nif}_foto_cliente.{ext}`
- PDFs documento: `storage/documentos/{nif}/{tipo}/{nif}_{tipo}.pdf`
- Exportes PDF: `storage/exports/`
- Imports subidos: `storage/imports/`
- Logs: `storage/logs/app.log`

## 10. Configuración dinámica de formularios (JSON)
Campos de formulario leídos por frontend:
- `static/config/forms/client.json`
- `static/config/forms/alert.json`
- `static/config/forms/document_types.json`

Permite evolucionar formularios sin tocar lógica JS principal.

## 11. Importación de clientes
Plantillas disponibles:
- `static/samples/clients_import_example.csv`
- `static/samples/clients_import_example.xlsx`
- `static/samples/clients_import_50.csv`
- `static/samples/clients_import_50.xlsx`

Endpoint:
- `POST /api/v1/tools/import/clients`

Plantilla descargable vía API:
- `GET /api/v1/tools/import/template`

## 12. API REST (resumen)

### 12.1 Clients
- `POST /api/v1/clients`
- `GET /api/v1/clients`
- `GET /api/v1/clients/{client_id}`
- `PATCH /api/v1/clients/{client_id}`
- `DELETE /api/v1/clients/{client_id}`
- `POST /api/v1/clients/{client_id}/photo`

### 12.2 Documents
- `POST /api/v1/documents`
- `GET /api/v1/documents`
- `GET /api/v1/documents/{document_id}`
- `PATCH /api/v1/documents/{document_id}`
- `DELETE /api/v1/documents/{document_id}`
- `POST /api/v1/documents/{document_id}/file`

Filtros soportados en listado:
- `client_id`, `doc_type`
- `expiration_status` (`expired|expiring|ok`)
- `expires_within_days`
- `missing_pdf`
- `q`

### 12.3 Alerts
- `POST /api/v1/alerts`
- `GET /api/v1/alerts`
- `GET /api/v1/alerts/{alert_id}`
- `PATCH /api/v1/alerts/{alert_id}`
- `DELETE /api/v1/alerts/{alert_id}`

### 12.4 Reporting
- `GET /api/v1/reporting/dashboard`

### 12.5 Tools
- `GET /api/v1/tools/import/template`
- `POST /api/v1/tools/import/clients`
- `POST /api/v1/tools/pdf/client/{client_id}`
- `POST /api/v1/tools/pdf/bulk`
- `GET /api/v1/tools/logs`

## 13. PDF de cliente (informe oficial)
Incluye:
- Portada.
- Cabecera con logo y título.
- Footer con paginación y contacto.
- Datos de cliente.
- Resumen y detalle de documentos.
- Resumen de alertas.
- Foto de cliente incrustada (si imagen).
- Si la foto del cliente es PDF, se adjunta al final del informe.

Configuración desde `config/app_config.json`:
- `pdf.report_title`
- `pdf.organization_name`
- `pdf.contact_email`
- `pdf.contact_phone`
- `ui.logo_path`

## 14. Scheduler
Si `SCHEDULER_ENABLED=true`, se inicializa `DailyScheduler` al arrancar la app.
Está preparado para tareas periódicas de alertado diario.

## 15. Testing
```bash
pytest -q
```

## 16. Despliegue

### 16.1 Linux (systemd + uvicorn)
Ejemplo de ejecución:
```bash
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

Recomendado para producción:
- Ejecutar detrás de Nginx/Caddy.
- Configurar HTTPS (TLS).
- Migrar de SQLite a PostgreSQL para carga real.

### 16.2 Variables recomendadas para producción
- `UVICORN_RELOAD=false`
- `DATABASE_URL` a PostgreSQL async (`postgresql+asyncpg://...`)
- Logs persistentes y backups de base de datos/`storage/`

## 17. Generación de ejecutable Windows (`.exe`)

### 17.1 Preparación
```powershell
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 17.2 Build con PyInstaller (incluyendo templates/static/config)
Desde PowerShell:

```powershell
pyinstaller --onedir --name renovaciones-app ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --add-data "config;config" ^
  --hidden-import=aiosqlite ^
  main.py
```

Salida:
- `dist\renovaciones-app.exe`

Importante:
- El ejecutable necesita acceso de escritura para `storage/` y base de datos.
- Si se ejecuta como servicio o en carpeta protegida, usar una ruta con permisos.

## 18. Troubleshooting rápido

### 18.1 `database is locked`
- Evitar ejecutar el proyecto simultáneamente desde Windows + WSL sobre la misma SQLite.
- Cerrar procesos duplicados y reiniciar.

### 18.2 Errores de esquema (`no such column ...`)
- Rehacer la base local (`renovaciones.db`) en entorno de desarrollo.
- O arrancar con `RESET_DB_ON_STARTUP=true` una vez.

### 18.3 Drag & drop no funciona
- Verificar que el navegador no abra el archivo fuera de la dropzone.
- Confirmar formato permitido según operación (imagen/PDF o PDF de documento).

## 19. Copias de seguridad y restauración

### 19.1 Copia automática al arrancar
En cada inicio, la app puede crear automáticamente:
- Backup de base de datos SQLite.
- Backup comprimido de `storage/`.

Variables de control en `.env`:
- `BACKUP_ON_STARTUP=true`
- `BACKUP_KEEP_LAST=30`
- `STORAGE_BACKUP_ON_STARTUP=true`
- `STORAGE_BACKUP_KEEP_LAST=30`

Rutas habituales:
- Backup BD (modo `run_app.bat`): `C:\Users\<usuario>\AppData\Local\RenovacionesTacografoCap\backups\`
- Backup de `storage/`: `storage/backups/`

### 19.2 Restaurar base de datos (Windows)
Restaurar el backup más reciente:

```powershell
.\restore_backup.bat
```

Restaurar uno concreto:

```powershell
.\restore_backup.bat renovaciones_YYYYMMDD_HHMMSS.db
```

### 19.3 Restaurar carpeta `storage/` (Windows)
Restaurar el backup ZIP más reciente:

```powershell
.\restore_storage_backup.bat
```

Restaurar uno concreto:

```powershell
.\restore_storage_backup.bat storage_YYYYMMDD_HHMMSS.zip
```

Antes de restaurar, el script genera rollback automáticamente:
- `storage/backups/storage_before_restore_YYYYMMDD_HHMMSS.zip`

### 19.4 Copia manual rápida (PowerShell)
Copiar BD local de Windows:

```powershell
Copy-Item "$env:LOCALAPPDATA\RenovacionesTacografoCap\renovaciones.db" "$env:LOCALAPPDATA\RenovacionesTacografoCap\backups\renovaciones_manual_$(Get-Date -Format yyyyMMdd_HHmmss).db"
```

Copiar carpeta `storage/` a ZIP:

```powershell
Compress-Archive -Path ".\storage\*" -DestinationPath ".\storage\backups\storage_manual_$(Get-Date -Format yyyyMMdd_HHmmss).zip" -Force
```

---

Si quieres, el siguiente paso puede ser añadir una guía de despliegue productivo completa (Nginx + systemd + PostgreSQL + backup/restore) también en español dentro de este README.

## 20. Licencia y uso
Este proyecto es propiedad de **Pedro Jose Bauza Ruiz** (`pjbauza@gmail.com`).

La licencia de este repositorio es **propietaria y de uso prohibido**.  
No se permite ningún uso del código (ni comercial ni no comercial) sin autorización
previa y por escrito del titular.

Ver archivo: `LICENSE`.
