# -*- coding: utf-8 -*-
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import pandas as pd


class Conexion():
    def __init__(self):
            self._BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self._ruta_env = os.path.join(self._BASE_DIR, ".env")
            load_dotenv(self._ruta_env)
    
    
    
    # 2. Construir el motor de conexión a PostgreSQL
    def obtener_conexion(self):
        usuario = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        host = os.getenv("DB_HOST")
        puerto = os.getenv("DB_PORT")
        bd = os.getenv("DB_NAME")
    
        # Validación rápida para detectar si falta configurar el archivo .env
        if not all([usuario, password, host, puerto, bd]):
            raise ValueError("Faltan variables de conexión en el archivo .env")
    
       
        try:

            cadena_conexion = f"postgresql+psycopg2://{usuario}:{password}@{host}:{puerto}/{bd}"
            motor = create_engine(cadena_conexion)
    
            # Probamos la conexión real ejecutando la consulta
            with motor.connect() as conexion:
                resultado = conexion.execute(text("SELECT version();")).fetchone()
    
                # Validamos con un if que fetchone() haya devuelto datos
                if resultado and resultado[0]:
                    return motor
                else:
                    raise ConnectionError("PostgreSQL respondió vacío a la consulta de verificación.")
    
        except Exception as error:
            print(f"Error al conectar con PostgreSQL: {error}")
            raise
    
    
    
    def inicializar_tablas(self):
        """Lee el archivo sql/Create.sql y crea las tablas en PostgreSQL."""
        ruta_sql = os.path.join(self._BASE_DIR, "sql", "Create.sql")
        
        if not os.path.exists(ruta_sql):
            raise FileNotFoundError(f"No se encontró el archivo SQL en: {ruta_sql}")
    
        # Leer el contenido completo de Create.sql
        with open(ruta_sql, "r", encoding="utf-8") as archivo:
            script_sql = archivo.read()
    
        motor = self.obtener_conexion()
        
        # Ejecutar el script en una transacción segura
        with motor.begin() as conexion:
            conexion.execute(text(script_sql))
            print("Tablas verificadas/creadas correctamente desde Create.sql")
        
        
    def insertar_bitacora(self,datos):
        engine = self.obtener_conexion()
        query = text("""
            INSERT INTO bitacora_ejecucion 
            (fecha_proceso, nombre_archivo, fuente, cantidad_registros, estatus, ruta_archivo, hora_inicio, hora_fin, detalle_error)
            VALUES 
            (:fecha_proceso, :nombre_archivo, :fuente, :cantidad_registros, :estatus, :ruta_archivo, :hora_inicio, :hora_fin, :detalle_error)
        """)
        with engine.begin() as conn:
            conn.execute(query, datos)    
            
            
    def cargar_datos(self, df_sujetos, df_alias):
        """Inserta o actualiza sujetos y refresca sus alias en PostgreSQL de forma transaccional."""
        engine = self.obtener_conexion()

        # Convertir NaN de Pandas a None de Python para compatibilidad con PostgreSQL
        registros_sujetos = [
            {k: (None if pd.isna(v) else v) for k, v in fila.items()}
            for fila in df_sujetos.to_dict(orient="records")
        ]
        registros_alias = [
            {k: (None if pd.isna(v) else v) for k, v in fila.items()}
            for fila in df_alias.to_dict(orient="records")
        ]

        upsert_sujetos = text("""
            INSERT INTO sujetos_control (
                id_sujeto, id_origen, fuente, tipo_sujeto, nombre_completo,
                primer_nombre, apellido, pais, programa_sancion, fecha_actualizacion
            ) VALUES (
                :id_sujeto, :id_origen, :fuente, :tipo_sujeto, :nombre_completo,
                :primer_nombre, :apellido, :pais, :programa_sancion, CURRENT_TIMESTAMP
            )
            ON CONFLICT (id_sujeto) DO UPDATE SET
                tipo_sujeto = EXCLUDED.tipo_sujeto,
                nombre_completo = EXCLUDED.nombre_completo,
                primer_nombre = EXCLUDED.primer_nombre,
                apellido = EXCLUDED.apellido,
                pais = EXCLUDED.pais,
                programa_sancion = EXCLUDED.programa_sancion,
                fecha_actualizacion = CURRENT_TIMESTAMP;
        """)

        insert_alias = text("""
            INSERT INTO sujetos_alias (id_sujeto, tipo_alias, nombre_alias)
            VALUES (:id_sujeto, :tipo_alias, :nombre_alias);
        """)

        with engine.begin() as conn:
            if registros_sujetos:
                conn.execute(upsert_sujetos, registros_sujetos)

            if registros_alias:
                ids_procesados = list(df_sujetos["id_sujeto"].unique())
                conn.execute(
                    text("DELETE FROM sujetos_alias WHERE id_sujeto = ANY(:ids);"),
                    {"ids": ids_procesados}
                )
                conn.execute(insert_alias, registros_alias)
    
        
              
        
        