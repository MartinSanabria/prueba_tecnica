# -*- coding: utf-8 -*-
import os
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from Database import Conexion


class GestorFuentes:
    def __init__(self):
        self._BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._carpeta_raw = os.path.join(self._BASE_DIR, "data", "raw")
        os.makedirs(self._carpeta_raw, exist_ok=True)
        self._db = Conexion()

    def contar_registros(self, ruta_xml, fuente):
        """Cuenta cuántos individuos y entidades trae el XML crudo."""
        arbol = ET.parse(ruta_xml)
        raiz = arbol.getroot()

        if fuente == "ONU":
            individuos = len(raiz.findall(".//INDIVIDUAL"))
            entidades = len(raiz.findall(".//ENTITY"))
            return individuos + entidades
        elif fuente == "OFAC":
            return len(raiz.findall(".//{*}sdnEntry"))
        return 0

    def descarga_xml(self, url, nombre_archivo, fuente):
        fecha_proceso = datetime.now().date()
        hora_inicio = datetime.now().time()
        ruta_destino = os.path.join(self._carpeta_raw, nombre_archivo)

        cantidad = 0
        estatus = "FALLIDO"
        error_detalle = None

        try:
            print(f"Descargando archivo desde {url}...")
            respuesta = None

            for intento in range(1, 4):
                try:
                    respuesta = requests.get(url, timeout=(20, 180))
                    respuesta.raise_for_status()
                    break
                except Exception as err_intento:
                    if intento == 3:
                        raise
                    print(f"Corte temporal en {fuente} (intento {intento}/3): {err_intento}. Reintentando...")
                    time.sleep(3)

            with open(ruta_destino, "wb") as archivo:
                archivo.write(respuesta.content)

            tamano_mb = len(respuesta.content) / (1024 * 1024)
            print(f"Descarga {fuente} completada ({tamano_mb:.2f} MB). Guardado en {ruta_destino}")

            cantidad = self.contar_registros(ruta_destino, fuente)
            estatus = "EXITOSO"
            return ruta_destino

        except BaseException as e:
            if os.path.exists(ruta_destino) and os.path.getsize(ruta_destino) > 1024 * 1024:
                print(f"Advertencia: descarga remota fallida ({e}). Usando respaldo local en {ruta_destino}")
                cantidad = self.contar_registros(ruta_destino, fuente)
                estatus = "EXITOSO_CACHE"
                error_detalle = f"Respaldo local usado por fallo de red: {e}"
                return ruta_destino

            error_detalle = str(e)
            print(f"Error en {fuente}: {error_detalle}")
            raise

        finally:
            hora_fin = datetime.now().time()
            registro = {
                "fecha_proceso": fecha_proceso,
                "nombre_archivo": nombre_archivo,
                "fuente": fuente,
                "cantidad_registros": cantidad,
                "estatus": estatus,
                "ruta_archivo": ruta_destino,
                "hora_inicio": hora_inicio.strftime("%H:%M:%S"),
                "hora_fin": hora_fin.strftime("%H:%M:%S"),
                "detalle_error": error_detalle
            }
            self._db.insertar_bitacora(registro)

    # ---> CAMBIO 2: Nuevo método al final de la clase GestorFuentes
    def obtener_fuentes(self):
        self._db.inicializar_tablas()
        fuentes = {
            "ONU": ("https://scsanctions.un.org/resources/xml/en/consolidated.xml", "data_onu.xml"),
            "OFAC": ("https://www.treasury.gov/ofac/downloads/sdn.xml", "data_ofac.xml")
        }
        
        rutas = {}
        for fuente, datos in fuentes.items():
            url = datos[0]
            archivo = datos[1]
            rutas[fuente] = self.descarga_xml(url, archivo, fuente)
            
        return rutas