# Declaración de Uso de Herramientas de Inteligencia Artificial

En cumplimiento con las disposiciones establecidas en la prueba técnica respecto a la transparencia en el desarrollo, se declara el uso de herramientas de Inteligencia Artificial generativa como soporte técnico durante la elaboración de esta solución.

---

## 1. Herramientas Utilizadas

* **Asistente de IA Generativa Copilot(LLM):** Empleado como herramienta de consulta técnica, revisión de arquitectura y apoyo en documentación.

---

## 2. Alcance y Propósito del Uso

La asistencia de IA se utilizó exclusivamente como apoyo en las siguientes actividades:

1. **Diseño de arquitectura modular y buenas prácticas:** Revisión de la separación de responsabilidades entre extracción (`Extract.py`), transformación (`Transform.py`), calidad de datos (`Data_quality.py`) y persistencia transaccional (`Database.py`).
2. **Optimización de expresiones XPath y SQL:** Consulta sobre manejo de espacios de nombres (`{*}`) en XML de la OFAC con `xml.etree.ElementTree`, sintaxis de carga idempotente (`ON CONFLICT DO UPDATE`) y cláusulas analíticas `FILTER (WHERE ...)` en PostgreSQL.
3. **Estructuración de pruebas automatizadas:** Apoyo en el diseño de casos de prueba con `pytest` para validar reglas de calidad y manejo de valores nulos sin alterar la base de datos productiva.
4. **Redacción y formato de documentación:** Estructuración del `README.md` y organización ejecutiva de hallazgos técnicos.

---

## 3. Supervisión, Validación y Autoría Humana

Todo el código fuente, los scripts SQL, los controles de calidad y los análisis presentados fueron **diseñados, implementados, depurados y validados directamente por el candidato**:

* **Resolución de incidencias reales de entorno:** Se diagnosticaron y resolvieron manualmente bloqueos de red y tiempos de espera (`ReadTimeoutError`) en el servidor AWS GovCloud de la OFAC (`~88 MB`), implementando mecanismos de reintento y respaldo local auditado (`EXITOSO_CACHE`) sin alterar las URLs oficiales exigidas.
* **Verificación empírica de cifras y reglas:** Cada regla de calidad, separación de cuarentena (`1,570 VESSEL` y `342 AIRCRAFT`) y resultado de conciliación matemática (`18,660` sujetos válidos y `27,125` alias) fue contrastado directamente contra los archivos XML oficiales y los registros persistidos en PostgreSQL.
* **Ejecución integral comprobada:** El flujo completo (`Main.py`), la suite de pruebas (`pytest -v`) y las consultas SQL (`Consultas.sql`) fueron ejecutados y verificados en entorno local.