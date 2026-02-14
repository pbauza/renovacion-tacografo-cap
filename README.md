# Gestión de Renovaciones Tacógrafo y CAP

Aplicación web interna desarrollada en Python para centralizar,
automatizar y controlar las renovaciones de tarjetas de tacógrafo y CAP
de conductores y empresas.

------------------------------------------------------------------------

## 🎯 Objetivo

Eliminar la gestión manual basada en carpetas y Excel antiguos, creando
una herramienta profesional, automatizada y escalable.

------------------------------------------------------------------------

## 🚀 Funcionalidades Principales

### 👤 Gestión de Clientes

#### Conductores

-   Nombre y apellidos
-   DNI
-   Teléfono
-   Email
-   Fechas de caducidad (DNI, Carnet, Tacógrafo, CAP)
-   Estado de apoderamiento
-   Tipo de trámite
-   Documentación asociada

#### Empresas

-   Nombre empresa
-   CIF
-   Teléfono
-   Email
-   Fecha caducidad tarjeta empresa
-   Apoderamiento
-   Vehículos asociados
-   Conductores vinculados

------------------------------------------------------------------------

## 📂 Documentación gestionada

-   DNI (anverso/reverso)
-   Carnet conducir (anverso/reverso)
-   Tarjeta tacógrafo
-   Tarjeta CAP
-   Selfie fondo blanco
-   CIF y escrituras
-   Permisos circulación
-   Apoderamientos

------------------------------------------------------------------------

## 📊 Importación Masiva

-   Soporte .xlsx y .csv
-   Mapeo dinámico de columnas
-   Detección de duplicados (DNI/CIF)
-   Validación de fechas
-   Clasificación automática por urgencia

------------------------------------------------------------------------

## 🔔 Sistema de Alertas Automáticas

Proceso automático diario que:

-   Detecta vencimientos en 30 / 60 / 90 días
-   Comprueba documentación necesaria
-   Genera checklist automático
-   Clasifica por semáforo:
    -   🟢 Correcto
    -   🟡 Próximo vencimiento
    -   🔴 Urgente o incompleto

------------------------------------------------------------------------

## 📄 Generador Automático de PDF

-   Combina documentos en orden fijo
-   Mantiene calidad
-   Nombra automáticamente el archivo
-   Descarga directa

------------------------------------------------------------------------

## 💬 Generación de Mensajes

Texto dinámico listo para enviar por WhatsApp o email según
documentación faltante.

------------------------------------------------------------------------

## 🖥 Dashboard

-   Renovaciones en 30 / 60 / 90 días
-   Documentación incompleta
-   Clientes sin apoderamiento
-   Indicadores visuales tipo semáforo

------------------------------------------------------------------------

## 🧾 Historial y Trazabilidad

-   Registro de renovaciones
-   Fecha de cada trámite
-   Documentos utilizados
-   Observaciones internas

------------------------------------------------------------------------

## 🏗 Arquitectura del Proyecto (Python)

    renovaciones/
    │
    ├── app/
    │   ├── api/
    │   ├── models/
    │   ├── services/
    │   ├── repositories/
    │   ├── scheduler/
    │   ├── pdf_generator/
    │   ├── importer/
    │   ├── messaging/
    │   ├── dashboard/
    │   └── utils/
    │
    ├── tests/
    ├── migrations/
    ├── config/
    ├── static/
    ├── templates/
    │
    ├── main.py
    ├── requirements.txt
    ├── pyproject.toml
    ├── .env.example
    └── README.md

------------------------------------------------------------------------

## ⚙️ Requisitos

-   Python 3.11+
-   Compatible con Windows y Linux
-   Base de datos: PostgreSQL o SQLite (modo desarrollo)

------------------------------------------------------------------------

## ▶️ Ejecución

### Windows

    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    python main.py

### Linux

    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    python main.py

------------------------------------------------------------------------

## 📦 Empaquetado Ejecutable

Posibilidad de generar ejecutable con:

    pyinstaller --onefile main.py

------------------------------------------------------------------------

## 🔮 Roadmap

### Fase 1 (MVP)

-   Alta manual
-   Importación Excel
-   Alertas básicas
-   Dashboard simple
-   Subida documentos
-   Generador PDF

### Fase 2

-   Validación inteligente avanzada
-   Roles de usuario
-   Preparación SaaS

------------------------------------------------------------------------

## 🏁 Objetivo Final

Automatizar completamente la gestión de renovaciones y convertirlo
potencialmente en una solución SaaS para gestorías de transporte.

------------------------------------------------------------------------

Documento generado automáticamente el 14/02/2026
