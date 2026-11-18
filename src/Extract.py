# -*- coding: utf-8 -*-
import os
import xml.etree.ElementTree as ET
import pandas as pd
import Source as sc


class ExtractData:
    def __init__(self):

        self._gestor = sc.GestorFuentes()

    def _obtener_texto(self, nodo, ruta):
        """Extrae el texto de una etiqueta XML de forma segura evitando errores por nulos."""
        elemento = nodo.find(ruta)
        if elemento is not None and elemento.text:
            return elemento.text.strip()
        return None

    def extraer_onu(self, ruta_xml):
        """Extrae individuos, entidades y sus alias desde el XML de la ONU."""
        raiz = ET.parse(ruta_xml).getroot()
        sujetos = []
        alias = []

        # 1. Extraer Individuos (<INDIVIDUAL>)
        for ind in raiz.findall(".//INDIVIDUAL"):
            id_origen = self._obtener_texto(ind, "DATAID")
            
            sujetos.append({
                "id_origen": id_origen,
                "fuente": "ONU",
                "tipo_sujeto": "INDIVIDUO",
                "primer_nombre": self._obtener_texto(ind, "FIRST_NAME"),
                "segundo_nombre": self._obtener_texto(ind, "SECOND_NAME"),
                "tercer_nombre": self._obtener_texto(ind, "THIRD_NAME"),
                "apellido": self._obtener_texto(ind, "FOURTH_NAME"),
                "pais": self._obtener_texto(ind, "NATIONALITY/VALUE") or self._obtener_texto(ind, "INDIVIDUAL_ADDRESS/COUNTRY"),
                "programa_sancion": self._obtener_texto(ind, "UN_LIST_TYPE")
            })

            # Extraer sus alias (<INDIVIDUAL_ALIAS>)
            for al in ind.findall("INDIVIDUAL_ALIAS"):
                nombre_alias = self._obtener_texto(al, "ALIAS_NAME")
                if nombre_alias:
                    alias.append({
                        "id_origen": id_origen,
                        "fuente": "ONU",
                        "tipo_alias": self._obtener_texto(al, "QUALITY") or "A.K.A.",
                        "nombre_alias": nombre_alias
                    })

        # 2. Extraer Entidades (<ENTITY>)
        for ent in raiz.findall(".//ENTITY"):
            id_origen = self._obtener_texto(ent, "DATAID")
            
            sujetos.append({
                "id_origen": id_origen,
                "fuente": "ONU",
                "tipo_sujeto": "ENTIDAD",
                "primer_nombre": self._obtener_texto(ent, "FIRST_NAME"),  # En ONU, el nombre de la entidad va aquí
                "segundo_nombre": None,
                "tercer_nombre": None,
                "apellido": None,
                "pais": self._obtener_texto(ent, "ENTITY_ADDRESS/COUNTRY"),
                "programa_sancion": self._obtener_texto(ent, "UN_LIST_TYPE")
            })

            # Extraer alias de la entidad (<ENTITY_ALIAS>)
            for al in ent.findall("ENTITY_ALIAS"):
                nombre_alias = self._obtener_texto(al, "ALIAS_NAME")
                if nombre_alias:
                    alias.append({
                        "id_origen": id_origen,
                        "fuente": "ONU",
                        "tipo_alias": self._obtener_texto(al, "QUALITY") or "A.K.A.",
                        "nombre_alias": nombre_alias
                    })

        return pd.DataFrame(sujetos), pd.DataFrame(alias)

    def extraer_ofac(self, ruta_xml):
        """Extrae sujetos y alias desde el XML de la OFAC manejando namespaces ({*})."""
        raiz = ET.parse(ruta_xml).getroot()
        sujetos = []
        alias = []

        for entry in raiz.findall(".//{*}sdnEntry"):
            id_origen = self._obtener_texto(entry, "{*}uid")
            tipo_raw = self._obtener_texto(entry, "{*}sdnType")

            # Unir todos los programas si el sujeto pertenece a más de uno
            programas = [
                p.text.strip() for p in entry.findall(".//{*}program") 
                if p.text and p.text.strip()
            ]
            programa_str = ", ".join(programas) if programas else None

            sujetos.append({
                "id_origen": id_origen,
                "fuente": "OFAC",
                "tipo_sujeto": tipo_raw,  
                "primer_nombre": self._obtener_texto(entry, "{*}firstName"),
                "segundo_nombre": None,
                "tercer_nombre": None,
                "apellido": self._obtener_texto(entry, "{*}lastName"),
                "pais": self._obtener_texto(entry, ".//{*}address/{*}country"),
                "programa_sancion": programa_str
            })

            # Extraer alias (<akaList>/<aka>)
            for aka in entry.findall(".//{*}aka"):
                aka_fn = self._obtener_texto(aka, "{*}firstName")
                aka_ln = self._obtener_texto(aka, "{*}lastName")
                nombre_alias = " ".join(filter(None, [aka_fn, aka_ln]))

                if nombre_alias:
                    alias.append({
                        "id_origen": id_origen,
                        "fuente": "OFAC",
                        "tipo_alias": self._obtener_texto(aka, "{*}type") or "a.k.a.",
                        "nombre_alias": nombre_alias
                    })

        return pd.DataFrame(sujetos), pd.DataFrame(alias)

    def ejecutar_extraccion(self):
            """Orquesta la descarga y devuelve los DataFrames crudos separados por fuente."""
            rutas = self._gestor.obtener_fuentes()

            df_sujetos_onu, df_alias_onu = self.extraer_onu(rutas["ONU"])
            df_sujetos_ofac, df_alias_ofac = self.extraer_ofac(rutas["OFAC"])

            return {
                "onu": {"sujetos": df_sujetos_onu, "alias": df_alias_onu},
                "ofac": {"sujetos": df_sujetos_ofac, "alias": df_alias_ofac}
            }

