# Pipeline ETL y Análisis de Listas de Sanciones (ONU y OFAC)

Solución modular en Python y PostgreSQL para la ingesta, perfilado de calidad, estandarización, validación, almacenamiento idempotente y análisis SQL de las listas consolidadas de sanciones emitidas por el **Consejo de Seguridad de las Naciones Unidas (ONU)** y la **Oficina de Control de Activos Extranjeros de EE. UU. (OFAC)**.

---

## 1. Arquitectura y Flujo del Proceso

El pipeline sigue una arquitectura desacoplada en cinco capas orquestadas desde `src/Main.py`:

```text
[Fuentes XML Oficiales]
   ├── ONU:  https://scsanctions.un.org/resources/xml/en/consolidated.xml
   └── OFAC: https://www.treasury.gov/ofac/downloads/sdn.xml
          │
          ▼
  1. Source.py (GestorFuentes)
     • Verifica/crea el esquema DDL en PostgreSQL (Create.sql)
     • Descarga XML con reintentos y respaldo local controlado ante cortes de red
     • Registra trazabilidad de cada descarga en bitacora_ejecucion
          │
          ▼
  2. Extract.py (ExtractData)
     • Parsea estructuras XML heterogéneas (rutas XPath y namespaces {*})
     • Separa sujetos principales y sus múltiples alias (a.k.a., f.k.a., n.k.a.)
          │
          ▼
  3. Data_quality.py (Perfilado Crudo)
     • Genera diagnóstico inicial de nulos, duplicados y dominios (perfilado_calidad_cruda_*.csv)
          │
          ▼
  4. Transform.py (TransformData)
     • Construye llave primaria compuesta única: FUENTE_ID (ej. ONU_6907993, OFAC_36)
     • Normaliza espacios y unifica nombre_completo
     • Homologa categorías válidas al catálogo canónico (INDIVIDUO, ENTIDAD)
          │
          ▼
  5. Data_quality.py (Validación y Cuarentena)
     • Aísla registros inválidos o fuera de catálogo en rechazos_onu_*.csv y rechazos_ofac_*.csv
     • Elimina alias huérfanos o duplicados garantizando integridad referencial
     • Genera cuadre matemático en conciliacion_etl_*.csv y respaldos consolidados
          │
          ▼
  6. Database.py (Conexion) -> PostgreSQL
     • Carga idempotente mediante UPSERT (ON CONFLICT DO UPDATE) en sujetos_control
     • Refresco transaccional de alias en sujetos_alias
```

---

## 2. Requisitos Previos

* **Python:** 3.10 o superior (probado en Python 3.15).
* **Base de datos:** PostgreSQL 13 o superior en ejecución local o remota.
* **Librerías Python** (definidas en `requirements.txt`):
  * `pandas`
  * `requests`
  * `SQLAlchemy`
  * `psycopg2-binary`
  * `python-dotenv`
  * `pytest`

---

## 3. Estructura del Proyecto

```text
Prueba Tecnica/
├── data/
│   ├── raw/                        # Archivos XML descargados (data_onu.xml, data_ofac.xml)
│   └── output/                     # Evidencias CSV de perfilado, cuarentena, conciliación y consolidados
├── docs/
│   └── Documento_Resultados_ETL.md # Informe ejecutivo, indicadores, hallazgos y limitaciones
├── sql/
│   ├── Create.sql                  # DDL: tablas, llaves foráneas, restricciones CHECK e índices
│   └── Consultas.sql               # Las 5 consultas analíticas requeridas por el negocio
├── src/
│   ├── Database.py                 # Conexión PostgreSQL, bitácora y carga transaccional UPSERT
│   ├── Source.py                   # Descarga resiliente de XML y conteo crudo
│   ├── Extract.py                  # Extracción y parseo XML de ONU y OFAC
│   ├── Transform.py                # Estandarización de llaves, nombres y catálogos
│   ├── Data_quality.py             # Perfilado, reglas de calidad, cuarentena y conciliación
│   └── Main.py                     # Orquestador principal del pipeline ETL
├── tests/
│   └── test_etl.py                 # Suite de pruebas automatizadas con pytest
├── .env                            # Credenciales locales (excluido de Git)
├── .env.example                    # Plantilla de variables de entorno
├── .gitignore                      # Exclusión de archivos sensibles y temporales
├── DECLARATION_IA.md               # Declaración de uso de herramientas de IA
├── README.md                       # Documentación técnica del proyecto
└── requirements.txt                # Dependencias del entorno Python
```

---

## 4. Instalación y Configuración

1. **Clonar o descomprimir el repositorio** y ubicarse en la carpeta raíz del proyecto:
   ```bash
   cd "Prueba Tecnica"
   ```

2. **Instalar las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar la base de datos y variables de entorno:**
   * Crear una base de datos vacía en PostgreSQL (por ejemplo, `sanciones_db`).
   * Copiar `.env.example` a `.env` y completar las credenciales reales:
     ```env
     DB_USER=postgres
     DB_PASSWORD=tu_password
     DB_HOST=localhost
     DB_PORT=puerto_a_utilizar
     DB_NAME=nombre_base_de_datos
     ```

---

## 5. Pasos Exactos de Ejecución

### Paso 1: Ejecutar el pipeline ETL completo
Desde la raíz del proyecto, ejecutar:
```bash
python src/Main.py
```
**Qué ocurre automáticamente:**
* Se crean las tablas `bitacora_ejecucion`, `sujetos_control` y `sujetos_alias` ejecutando `sql/Create.sql`.
* Se descargan y almacenan `data_onu.xml` y `data_ofac.xml` en `data/raw/`.
* Se generan los 6 reportes CSV de auditoría en `data/output/`.
* Se cargan los **18,660** sujetos válidos y **27,125** alias en PostgreSQL.

*(Nota: Al ejecutar `python src/Main.py` por segunda vez, el proceso actualiza los registros existentes mediante `ON CONFLICT` sin generar duplicados).*

### Paso 2: Ejecutar las pruebas automatizadas
Con los archivos descargados en `data/raw/`, ejecutar la suite de pruebas unitarias e integración:
```bash
pytest -v
```
Valida 5 casos de prueba sobre extracción XML real, transformación de llaves/catálogos, cuadre matemático de calidad, manejo de credenciales `.env` y conversión de valores `NaN` a `NULL`.

### Paso 3: Ejecutar las consultas analíticas en PostgreSQL
Abrir `sql/Consultas.sql` en pgAdmin, DBeaver o mediante consola `psql` y ejecutarlo sobre la base de datos configurada:

Obtiene los conteos por país y tipo, sujetos con mayor número de alias (`a.k.a.`, `f.k.a.`, `n.k.a.`), sujetos sin alias, top de países y detección de nombres/alias duplicados.

---

## 6. Resumen de Resultados y Conciliación

| Fuente | Sujetos Extraídos | Sujetos Válidos | Sujetos Rechazados | Cuadre Exacto | Alias Válidos |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **ONU** | 1,007 | 1,007 | 0 | Sí | 2,744 |
| **OFAC** | 19,565 | 17,653 | 1,912 | Sí | 24,381 |
| **Total Consolidado** | **20,572** | **18,660** | **1,912** | **Sí** | **27,125** |

* Los **1,912** registros rechazados de OFAC corresponden a embarcaciones (`1,570 VESSEL`) y aeronaves (`342 AIRCRAFT`), aislados en `data/output/rechazos_ofac_*.csv` por encontrarse fuera del catálogo de negocio (`INDIVIDUO` / `ENTIDAD`).