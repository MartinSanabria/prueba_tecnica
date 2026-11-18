# -*- coding: utf-8 -*-
import pandas as pd


class TransformData:
    def __init__(self):
        self._mapa_tipos = {
            "INDIVIDUAL": "INDIVIDUO",
            "INDIVIDUO": "INDIVIDUO",
            "ENTITY": "ENTIDAD",
            "ENTIDAD": "ENTIDAD"
        }

    def _limpiar_texto(self, serie):
        """Elimina espacios extremos y colapsa múltiples espacios internos en uno solo."""
        limpia = (
            serie.fillna("")
            .astype(str)
            .str.split()
            .str.join(" ")
        )
        return limpia.replace("", None)

    def transformar_sujetos(self, df_sujetos):
        """Estandariza llaves, nombres completos y catálogos de una fuente."""
        df = df_sujetos.copy()

        # 1. Generar llave primaria compuesta (ej. ONU_6907993, OFAC_36)
        id_limpio = df["id_origen"].fillna("").astype(str).str.strip()
        df["id_sujeto"] = df["fuente"] + "_" + id_limpio
        df.loc[id_limpio == "", "id_sujeto"] = None

        # 2. Construir nombre_completo unificando todas las partes del nombre
        cols_nombre = ["primer_nombre", "segundo_nombre", "tercer_nombre", "apellido"]
        df["nombre_completo"] = (
            df[cols_nombre]
            .fillna("")
            .agg(" ".join, axis=1)
            .str.split()
            .str.join(" ")
            .replace("", None)
        )

        # 3. Limpiar columnas individuales de texto
        df["primer_nombre"] = self._limpiar_texto(df["primer_nombre"])
        df["apellido"] = self._limpiar_texto(df["apellido"])
        df["pais"] = self._limpiar_texto(df["pais"])
        df["programa_sancion"] = self._limpiar_texto(df["programa_sancion"])

        # 4. Homologar tipo_sujeto a INDIVIDUO / ENTIDAD
        # Los valores fuera de catálogo (ej. Vessel, Aircraft) se conservan en mayúsculas
        # para que Data_quality.py los detecte y los envíe al archivo de rechazos.
        tipo_norm = df["tipo_sujeto"].fillna("").astype(str).str.strip().str.upper()
        df["tipo_sujeto"] = tipo_norm.map(self._mapa_tipos).fillna(tipo_norm)
        df.loc[df["tipo_sujeto"] == "", "tipo_sujeto"] = None

        # 5. Seleccionar y ordenar columnas exactas de la tabla sujetos_control
        columnas_sujetos = [
            "id_sujeto",
            "id_origen",
            "fuente",
            "tipo_sujeto",
            "nombre_completo",
            "primer_nombre",
            "apellido",
            "pais",
            "programa_sancion"
        ]
        return df[columnas_sujetos]

    def transformar_alias(self, df_alias):
        """Genera la llave foránea id_sujeto y limpia los nombres de alias."""
        if df_alias.empty:
            return pd.DataFrame(columns=["id_sujeto", "tipo_alias", "nombre_alias"])

        df = df_alias.copy()

        id_limpio = df["id_origen"].fillna("").astype(str).str.strip()
        df["id_sujeto"] = df["fuente"] + "_" + id_limpio
        df.loc[id_limpio == "", "id_sujeto"] = None

        df["tipo_alias"] = self._limpiar_texto(df["tipo_alias"])
        df["nombre_alias"] = self._limpiar_texto(df["nombre_alias"])

        return df[["id_sujeto", "tipo_alias", "nombre_alias"]]

    def ejecutar_transformacion(self, datos_crudos):
        """Transforma cada fuente por separado manteniendo la trazabilidad para calidad."""
        resultado = {}
        for fuente in ("onu", "ofac"):
            df_suj = self.transformar_sujetos(datos_crudos[fuente]["sujetos"])
            df_ali = self.transformar_alias(datos_crudos[fuente]["alias"])
            resultado[fuente] = {"sujetos": df_suj, "alias": df_ali}
        return resultado