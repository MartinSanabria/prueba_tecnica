# -*- coding: utf-8 -*-
import os
from datetime import datetime
import pandas as pd


class CalidadDatos:
    def __init__(self):
        self._BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._carpeta_output = os.path.join(self._BASE_DIR, "data", "output")
        os.makedirs(self._carpeta_output, exist_ok=True)

        self._timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._ruta_perfilado = os.path.join(self._carpeta_output, f"perfilado_calidad_cruda_{self._timestamp}.csv")
        self._ruta_conciliacion = os.path.join(self._carpeta_output, f"conciliacion_etl_{self._timestamp}.csv")
        
        
    def perfilar_fuente(self, df_sujetos, df_alias, fuente):
        """Genera el documento de diagnóstico de datos crudos (nulos, duplicados y dominios)."""
        total_sujetos = len(df_sujetos)
        dup_sujetos = df_sujetos.duplicated(subset=["id_origen"]).sum()
        dup_alias = df_alias.duplicated(subset=["id_origen", "nombre_alias"]).sum() if not df_alias.empty else 0
        tipos_encontrados = df_sujetos["tipo_sujeto"].value_counts(dropna=False).to_dict()

        filas_perfilado = []
        for col, nulos in df_sujetos.isnull().sum().items():
            pct_nulos = round((nulos / total_sujetos * 100), 2) if total_sujetos > 0 else 0.0
            filas_perfilado.append({
                "fecha_analisis": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fuente": fuente,
                "total_sujetos_crudos": total_sujetos,
                "total_alias_crudos": len(df_alias),
                "columna": col,
                "valores_nulos": int(nulos),
                "porcentaje_nulos": pct_nulos,
                "duplicados_id_origen": int(dup_sujetos),
                "duplicados_alias": int(dup_alias),
                "distribucion_tipos_crudos": str(tipos_encontrados)
            })

        df_perfil = pd.DataFrame(filas_perfilado)
        escribir_encabezado = not os.path.exists(self._ruta_perfilado)
        df_perfil.to_csv(
            self._ruta_perfilado,
            mode="a",
            header=escribir_encabezado,
            index=False,
            encoding="utf-8-sig"
        )

    def validar_y_separar(self, df_sujetos, df_alias, fuente):
        """Valida reglas de negocio, exporta rechazos y registra la conciliación matemática."""
        total_entrada = len(df_sujetos)
        df = df_sujetos.copy()
        df["motivo_rechazo"] = ""

        # Regla 1: Campos críticos obligatorios
        cond_nulos = (
            df["id_sujeto"].isna() | (df["id_sujeto"].astype(str).str.strip() == "") |
            df["nombre_completo"].isna() | (df["nombre_completo"].astype(str).str.strip() == "")
        )
        df.loc[cond_nulos, "motivo_rechazo"] += "Campo crítico nulo o vacío; "

        # Regla 2: Dominio cerrado en tipo_sujeto
        cond_tipo = ~df["tipo_sujeto"].isin(["INDIVIDUO", "ENTIDAD"])
        df.loc[cond_tipo, "motivo_rechazo"] += "Tipo de sujeto fuera de catálogo; "

        # Regla 3: Unicidad de llave primaria
        cond_dup = df.duplicated(subset=["id_sujeto"], keep="first")
        df.loc[cond_dup, "motivo_rechazo"] += "ID de sujeto duplicado; "

        # Separar válidos y rechazados
        mascara_rechazo = df["motivo_rechazo"] != ""
        df_rechazados = df[mascara_rechazo].copy()
        df_validos = df[~mascara_rechazo].drop(columns=["motivo_rechazo"]).copy()

        # Generar documento de cuarentena/rechazos por fuente
        ruta_rechazos = os.path.join(self._carpeta_output, f"rechazos_{fuente.lower()}_{self._timestamp}.csv")
        df_rechazados.to_csv(ruta_rechazos, index=False, encoding="utf-8-sig")

        # Filtrar alias válidos manteniendo integridad referencial
        if not df_alias.empty:
            ids_validos = set(df_validos["id_sujeto"])
            df_alias_limpio = df_alias[
                df_alias["nombre_alias"].notna() &
                (df_alias["nombre_alias"].astype(str).str.strip() != "") &
                (df_alias["id_sujeto"].isin(ids_validos))
            ].drop_duplicates(subset=["id_sujeto", "nombre_alias"]).copy()
        else:
            df_alias_limpio = df_alias.copy()

        # Generar fila de conciliación matemática
        total_validos = len(df_validos)
        total_rechazados = len(df_rechazados)
        df_conciliacion = pd.DataFrame([{
            "fecha_ejecucion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fuente": fuente,
            "total_extraidos": total_entrada,
            "total_validos": total_validos,
            "total_rechazados": total_rechazados,
            "cuadre_exacto": (total_entrada == total_validos + total_rechazados),
            "alias_validos": len(df_alias_limpio)
        }])

        escribir_encabezado = not os.path.exists(self._ruta_conciliacion)
        df_conciliacion.to_csv(
            self._ruta_conciliacion,
            mode="a",
            header=escribir_encabezado,
            index=False,
            encoding="utf-8-sig"
        )

        return df_validos, df_alias_limpio, df_rechazados

    def exportar_consolidados(self, df_sujetos_final, df_alias_final):
        """Genera respaldo documental de los datos limpios finales cargados a PostgreSQL."""
        ruta_sujetos = os.path.join(self._carpeta_output, f"sujetos_consolidados_{self._timestamp}.csv")
        ruta_alias = os.path.join(self._carpeta_output, f"alias_consolidados_{self._timestamp}.csv")

        df_sujetos_final.to_csv(ruta_sujetos, index=False, encoding="utf-8-sig")
        df_alias_final.to_csv(ruta_alias, index=False, encoding="utf-8-sig")