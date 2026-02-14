# Gestion de Renovaciones Tacografo y CAP

Aplicacion FastAPI con GUI web para gestionar clientes, documentos y alertas de caducidad.

## Novedades implementadas

### GUI
- Busqueda de clientes por `Nombre`, `NIF`, `Empresa`, `Telefono`.
- Seleccion de cliente desde tabla (click en fila).
- Dashboard con datos reales desde BD (clientes, documentos y alertas).
- Crear y editar clientes/documentos/alertas con llamadas frontend->backend.
- Drag and drop de foto de cliente:
  - crear cliente: preview + subida al crear cliente
  - editar cliente: sustituye foto actual
- Drag and drop de PDF de documento:
  - crear documento: subida de PDF del documento recien creado
  - editar documento: sustituye PDF actual
- Importador Excel/CSV funcional y generacion de PDF por cliente o en bloque.

### Almacenamiento de ficheros
- Foto cliente:
  - `storage/clientes/{nif}/{nif}_foto_cliente.{ext}`
- Documento PDF:
  - `storage/documentos/{nif}/{tipo_documento}/{nif}_{tipo_documento}.{ext}`

### Alertas automaticas
- Al crear/editar documento con `expiry_date`, se crea o actualiza alerta automaticamente:
  - `alert_date = expiry_date - 50 dias`

## Modelo de datos actual

### Client
- `id` (autoincrement)
- `full_name`
- `company` (opcional)
- `photo_path`
- `nif` (unico)
- `phone`
- `email` (opcional)

### Document
Tipos:
- `dni`
- `driving_license`
- `cap`
- `tachograph_card`
- `power_of_attorney`
- `other`

Campos comunes en tabla:
- `id` (autoincrement)
- `client_id`
- `doc_type`
- `expiry_date`
- `issue_date`
- `birth_date`
- `address`
- `pdf_path`
- `course_number`
- `flag_fran`
- `flag_ciusaba`
- `expiry_fran`
- `expiry_ciusaba`

### Alert
- `id` (autoincrement)
- `client_id`
- `document_id`
- `expiry_date`
- `alert_date` (50 dias antes)

## Requisitos
- Python 3.11+
- Windows o Linux

## Instalacion

### Windows
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

### Linux
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Configuracion
Archivo `.env`:

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
```

## Cambio de esquema (importante)
Como se ha cambiado el modelo de base de datos, para aplicar limpio en desarrollo:

1. borrar `renovaciones.db`, o
2. arrancar una vez con `RESET_DB_ON_STARTUP=true`.

Si `AUTO_RESET_SQLITE_ON_SCHEMA_MISMATCH=true`, la app detecta tablas antiguas y rehace el schema automaticamente en SQLite.

## Ejecutar
```bash
python main.py
```

## Uso GUI
- URL: `http://127.0.0.1:8000/`
- API docs: `http://127.0.0.1:8000/docs`

## Endpoints nuevos clave
- `GET /api/v1/clients` (con filtros `full_name`, `nif`, `company`, `phone`, `q`)
- `POST /api/v1/clients/{client_id}/photo`
- `POST /api/v1/documents/{document_id}/file`
- `GET /api/v1/tools/import/template` (descarga plantilla)
- `POST /api/v1/tools/import/clients` (importa Excel/CSV)
- `POST /api/v1/tools/pdf/client/{client_id}` (genera PDF cliente)
- `POST /api/v1/tools/pdf/bulk` (genera PDF bloque)
- `GET /api/v1/tools/logs`

## Plantilla de importacion
- Excel ejemplo: `static/samples/clients_import_example.xlsx`
- CSV ejemplo: `static/samples/clients_import_example.csv`

## Configuracion dinamica de formularios (JSON)
Los campos de formularios se cargan por AJAX desde:
- `static/config/forms/client.json`
- `static/config/forms/alert.json`
- `static/config/forms/document_types.json`

Para cambiar o agregar campos, edita estos JSON sin tocar la logica JS principal.

## Ejecutable Windows
```powershell
.\.venv\Scripts\activate
pip install -r requirements.txt
pyinstaller --onefile --name renovaciones-api main.py
```
Salida: `dist\renovaciones-api.exe`
