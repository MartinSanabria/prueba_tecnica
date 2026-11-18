# -*- coding: utf-8 -*-
import pandas as pd
from Extract import ExtractData
from Transform import TransformData
from Data_quality import CalidadDatos
from Database import Conexion


def ejecutar_pipeline():
    extractor = ExtractData()
    transformador = TransformData()
    calidad = CalidadDatos()
    db = Conexion()

    # 1. Descarga XML (registra bitácora) y extracción cruda por fuente
    datos_crudos = extractor.ejecutar_extraccion()

    # 2. Perfilado diagnóstico de calidad sobre datos crudos -> perfilado_calidad_cruda_*.csv
    for fuente, clave in (("ONU", "onu"), ("OFAC", "ofac")):
        calidad.perfilar_fuente(
            datos_crudos[clave]["sujetos"],
            datos_crudos[clave]["alias"],
            fuente
        )

    # 3. Estandarización de llaves, nombres y catálogos
    datos_transformados = transformador.ejecutar_transformacion(datos_crudos)

    # 4. Validación de reglas, exportación de rechazos y conciliación -> rechazos_*.csv y conciliacion_etl_*.csv
    sujetos_validos = []
    alias_validos = []

    for fuente, clave in (("ONU", "onu"), ("OFAC", "ofac")):
        df_suj_val, df_ali_val, _ = calidad.validar_y_separar(
            datos_transformados[clave]["sujetos"],
            datos_transformados[clave]["alias"],
            fuente
        )
        sujetos_validos.append(df_suj_val)
        alias_validos.append(df_ali_val)

    # 5. Consolidación final de ambas fuentes
    df_sujetos_final = pd.concat(sujetos_validos, ignore_index=True)
    df_alias_final = pd.concat(alias_validos, ignore_index=True)

    # 6. Exportar respaldo plano de consolidados -> sujetos_consolidados_*.csv y alias_consolidados_*.csv
    calidad.exportar_consolidados(df_sujetos_final, df_alias_final)

    # 7. Carga final en PostgreSQL
    db.cargar_datos(df_sujetos_final, df_alias_final)


if __name__ == "__main__":
    ejecutar_pipeline()