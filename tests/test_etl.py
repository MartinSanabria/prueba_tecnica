import os
import sys
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

# Agregar la carpeta src/ al path para importar los módulos del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from Extract import ExtractData
from Transform import TransformData
from Data_quality import CalidadDatos
from Database import Conexion


# ============================================================================
# FIXTURES CON LAS FUENTES REALES DESCARGADAS EN data/raw/
# ============================================================================
@pytest.fixture(scope="module")
def rutas_xml_reales():
    """Localiza los XML reales de ONU y OFAC previamente descargados en data/raw/."""
    ruta_onu = os.path.join(RAW_DIR, "data_onu.xml")
    ruta_ofac = os.path.join(RAW_DIR, "data_ofac.xml")

    if not os.path.exists(ruta_onu) or not os.path.exists(ruta_ofac):
        pytest.skip(
            "No se encontraron data_onu.xml y/o data_ofac.xml en data/raw/. "
            "Ejecuta primero 'python src/Main.py' para descargar las fuentes."
        )

    return {"ONU": ruta_onu, "OFAC": ruta_ofac}


@pytest.fixture(scope="module")
def datos_crudos_reales(rutas_xml_reales):
    """Extrae una sola vez los DataFrames crudos desde los XML reales para toda la suite."""
    extractor = ExtractData()
    df_suj_onu, df_ali_onu = extractor.extraer_onu(rutas_xml_reales["ONU"])
    df_suj_ofac, df_ali_ofac = extractor.extraer_ofac(rutas_xml_reales["OFAC"])

    return {
        "onu": {"sujetos": df_suj_onu, "alias": df_ali_onu},
        "ofac": {"sujetos": df_suj_ofac, "alias": df_ali_ofac}
    }


@pytest.fixture(scope="module")
def datos_transformados_reales(datos_crudos_reales):
    """Aplica las reglas de transformación sobre los datos reales extraídos."""
    transformador = TransformData()
    return transformador.ejecutar_transformacion(datos_crudos_reales)


# ============================================================================
# 1. PRUEBAS DE EXTRACCIÓN SOBRE XML REALES (Extract.py)
# ============================================================================
def test_extraccion_fuentes_reales(datos_crudos_reales):
    """Verifica que la extracción desde data_onu.xml y data_ofac.xml devuelva datos y esquemas válidos."""
    columnas_sujetos = {
        "id_origen", "fuente", "tipo_sujeto", "primer_nombre",
        "segundo_nombre", "tercer_nombre", "apellido", "pais", "programa_sancion"
    }
    columnas_alias = {"id_origen", "fuente", "tipo_alias", "nombre_alias"}

    for clave, fuente_esperada in (("onu", "ONU"), ("ofac", "OFAC")):
        df_suj = datos_crudos_reales[clave]["sujetos"]
        df_ali = datos_crudos_reales[clave]["alias"]

        assert not df_suj.empty, f"El DataFrame de sujetos para {fuente_esperada} está vacío."
        assert not df_ali.empty, f"El DataFrame de alias para {fuente_esperada} está vacío."
        assert set(df_suj.columns) == columnas_sujetos
        assert set(df_ali.columns) == columnas_alias
        assert (df_suj["fuente"] == fuente_esperada).all()
        assert df_suj["id_origen"].notna().all()


# ============================================================================
# 2. PRUEBAS DE TRANSFORMACIÓN SOBRE DATOS REALES (Transform.py)
# ============================================================================
def test_transformacion_fuentes_reales(datos_transformados_reales):
    """Verifica generación de llaves compuestas, nombres limpios y mapeo de tipos en datos reales."""
    columnas_esperadas = [
        "id_sujeto", "id_origen", "fuente", "tipo_sujeto",
        "nombre_completo", "primer_nombre", "apellido", "pais", "programa_sancion"
    ]

    for clave, prefijo in (("onu", "ONU_"), ("ofac", "OFAC_")):
        df_suj = datos_transformados_reales[clave]["sujetos"]
        df_ali = datos_transformados_reales[clave]["alias"]

        assert list(df_suj.columns) == columnas_esperadas
        assert df_suj["id_sujeto"].str.startswith(prefijo).all()
        assert df_ali["id_sujeto"].str.startswith(prefijo).all()

        # Verificar que nombre_completo no tenga espacios dobles ni extremos
        nombres_validos = df_suj["nombre_completo"].dropna()
        assert not nombres_validos.str.contains(r"  +", regex=True).any()
        assert (nombres_validos == nombres_validos.str.strip()).all()

    # En ONU todos los tipos deben quedar homologados a INDIVIDUO o ENTIDAD
    tipos_onu = set(datos_transformados_reales["onu"]["sujetos"]["tipo_sujeto"].unique())
    assert tipos_onu.issubset({"INDIVIDUO", "ENTIDAD"})

    # En OFAC se homologan INDIVIDUO/ENTIDAD y se preservan categorías fuera de catálogo (ej. VESSEL/AIRCRAFT)
    tipos_ofac = set(datos_transformados_reales["ofac"]["sujetos"]["tipo_sujeto"].unique())
    assert "INDIVIDUO" in tipos_ofac and "ENTIDAD" in tipos_ofac


# ============================================================================
# 3. PRUEBAS DE CALIDAD, CUARENTENA Y CONCILIACIÓN REAL (Data_quality.py)
# ============================================================================
def test_calidad_y_conciliacion_fuentes_reales(tmp_path, datos_crudos_reales, datos_transformados_reales):
    """Valida reglas de calidad, cuarentena, integridad referencial y cuadre matemático real."""
    calidad = CalidadDatos()

    # Redirigir la escritura de CSV hacia la carpeta temporal de pytest para no alterar data/output/
    calidad._carpeta_output = str(tmp_path)
    calidad._ruta_perfilado = str(tmp_path / f"perfilado_calidad_cruda_{calidad._timestamp}.csv")
    calidad._ruta_conciliacion = str(tmp_path / f"conciliacion_etl_{calidad._timestamp}.csv")

    sujetos_validos_lista = []
    alias_validos_lista = []

    for fuente, clave in (("ONU", "onu"), ("OFAC", "ofac")):
        # 1. Perfilado crudo
        calidad.perfilar_fuente(
            datos_crudos_reales[clave]["sujetos"],
            datos_crudos_reales[clave]["alias"],
            fuente
        )

        # 2. Validación y separación
        df_entrada = datos_transformados_reales[clave]["sujetos"]
        df_val, df_ali, df_rech = calidad.validar_y_separar(
            df_entrada,
            datos_transformados_reales[clave]["alias"],
            fuente
        )

        # Cuadre matemático exacto: Extraídos == Válidos + Rechazados
        assert len(df_entrada) == len(df_val) + len(df_rech)

        # Reglas estrictas sobre registros válidos
        assert df_val["id_sujeto"].notna().all()
        assert df_val["nombre_completo"].notna().all()
        assert not df_val["id_sujeto"].duplicated().any()
        assert set(df_val["tipo_sujeto"].unique()).issubset({"INDIVIDUO", "ENTIDAD"})

        # Integridad referencial y unicidad en alias válidos
        assert set(df_ali["id_sujeto"]).issubset(set(df_val["id_sujeto"]))
        assert not df_ali.duplicated(subset=["id_sujeto", "nombre_alias"]).any()

        # Si hubo rechazados (como VESSEL/AIRCRAFT en OFAC), deben tener motivo_rechazo
        if not df_rech.empty:
            assert (df_rech["motivo_rechazo"].str.strip() != "").all()

        sujetos_validos_lista.append(df_val)
        alias_validos_lista.append(df_ali)

    # Verificar archivo de conciliación generado
    df_conciliacion = pd.read_csv(calidad._ruta_conciliacion)
    assert len(df_conciliacion) == 2
    assert bool(df_conciliacion["cuadre_exacto"].all()) is True

    # Verificar generación de archivos consolidados finales
    df_suj_final = pd.concat(sujetos_validos_lista, ignore_index=True)
    df_ali_final = pd.concat(alias_validos_lista, ignore_index=True)
    calidad.exportar_consolidados(df_suj_final, df_ali_final)

    archivos_generados = [f.name for f in tmp_path.iterdir()]
    assert any(n.startswith("perfilado_calidad_cruda_") for n in archivos_generados)
    assert any(n.startswith("conciliacion_etl_") for n in archivos_generados)
    assert any(n.startswith("rechazos_onu_") for n in archivos_generados)
    assert any(n.startswith("rechazos_ofac_") for n in archivos_generados)
    assert any(n.startswith("sujetos_consolidados_") for n in archivos_generados)
    assert any(n.startswith("alias_consolidados_") for n in archivos_generados)


# ============================================================================
# 4. PRUEBAS DE PERSISTENCIA Y VARIABLES DE ENTORNO (Database.py)
# ============================================================================
def test_database_validacion_env_incompleto(monkeypatch):
    """Verifica que Database.py lance ValueError si falta alguna variable en .env."""
    db = Conexion()
    for var in ("DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME"):
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(ValueError, match="Faltan variables de conexión"):
        db.obtener_conexion()

def test_database_cargar_datos_con_muestra_real(datos_transformados_reales):
    """Verifica la carga transaccional usando una muestra real con valores nulos en pais."""
    db = Conexion()
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn

    # Tomar registros reales de ONU donde 'pais' viene nulo (NaN) para comprobar conversión a None
    df_onu = datos_transformados_reales["onu"]["sujetos"]
    muestra_sujetos = df_onu[df_onu["pais"].isna()].head(5).copy()
    ids_muestra = set(muestra_sujetos["id_sujeto"])
    df_ali_onu = datos_transformados_reales["onu"]["alias"]
    muestra_alias = df_ali_onu[df_ali_onu["id_sujeto"].isin(ids_muestra)].head(5).copy()

    with patch.object(db, "obtener_conexion", return_value=mock_engine):
        db.cargar_datos(muestra_sujetos, muestra_alias)

    # Verifica que se ejecute el UPSERT de sujetos
    assert mock_conn.execute.call_count >= 1
    params_insertados = mock_conn.execute.call_args_list[0][0][1]
    assert all(fila["pais"] is None for fila in params_insertados)