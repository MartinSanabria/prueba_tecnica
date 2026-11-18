-- 1. Tabla de Auditoría: Bitácora de Ejecución
CREATE TABLE IF NOT EXISTS bitacora_ejecucion (
    id_bitacora SERIAL PRIMARY KEY,
    fecha_proceso DATE NOT NULL DEFAULT CURRENT_DATE,
    nombre_archivo VARCHAR(150) NOT NULL,
    fuente VARCHAR(20) NOT NULL,
    cantidad_registros INTEGER NOT NULL DEFAULT 0,
    estatus VARCHAR(20) NOT NULL,
    ruta_archivo VARCHAR(500),
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    detalle_error TEXT
);

-- 2. Tabla Maestra: Sujetos de Control (ONU y OFAC unificados)
CREATE TABLE IF NOT EXISTS sujetos_control (
    id_sujeto VARCHAR(50) PRIMARY KEY,
    id_origen VARCHAR(50) NOT NULL,
    fuente VARCHAR(10) NOT NULL CHECK (fuente IN ('ONU', 'OFAC')),
    tipo_sujeto VARCHAR(20) NOT NULL CHECK (tipo_sujeto IN ('INDIVIDUO', 'ENTIDAD')),
    nombre_completo VARCHAR(1000) NOT NULL,
    primer_nombre VARCHAR(500),
    apellido VARCHAR(500),
    pais VARCHAR(150),
    programa_sancion VARCHAR(500),
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabla Detalle: Alias (Relación 1 a Muchos)
CREATE TABLE IF NOT EXISTS sujetos_alias (
    id_alias SERIAL PRIMARY KEY,
    id_sujeto VARCHAR(50) NOT NULL,
    tipo_alias VARCHAR(50) NOT NULL,
    nombre_alias VARCHAR(1000) NOT NULL,
    CONSTRAINT fk_sujeto_alias
        FOREIGN KEY (id_sujeto)
        REFERENCES sujetos_control(id_sujeto)
        ON DELETE CASCADE
);

-- 4. Índices para consultas analíticas y carga idempotente
CREATE INDEX IF NOT EXISTS idx_sujetos_fuente_tipo ON sujetos_control (fuente, tipo_sujeto);
CREATE INDEX IF NOT EXISTS idx_sujetos_pais ON sujetos_control (pais);
CREATE INDEX IF NOT EXISTS idx_alias_id_sujeto ON sujetos_alias (id_sujeto);