"""
Lectura y normalización de la sábana única del visor.

Única puerta de entrada al Excel. Devuelve DataFrames ya limpios y con la
columna `cod` (COD_DANE de 5 dígitos) como llave común, de modo que el resto
del proyecto nunca vuelve a cruzar por nombre de municipio.
"""
from __future__ import annotations

import unicodedata

import pandas as pd

from . import config as cfg


# --------------------------------------------------------------------------
# Normalización de texto
# --------------------------------------------------------------------------
def normalizar(texto) -> str | None:
    """Mayúsculas, sin tildes y sin espacios repetidos. None si viene vacío."""
    if pd.isna(texto):
        return None
    texto = str(texto).strip().upper()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(texto.split()) or None


def llave_municipio(nombre) -> str | None:
    """Nombre normalizado y homologado contra la tabla de alias."""
    base = normalizar(nombre)
    if base is None:
        return None
    return cfg.ALIAS_MUNICIPIOS.get(base, base)


def titulo_es(texto: str) -> str:
    """MAYÚSCULAS a nombre propio, dejando en minúscula las partículas."""
    palabras = str(texto).strip().lower().split()
    salida = []
    for i, palabra in enumerate(palabras):
        if i > 0 and palabra in cfg.MINUSCULAS_TITULO:
            salida.append(palabra)
        else:
            salida.append(palabra[:1].upper() + palabra[1:])
    return " ".join(salida)


def nombre_oficial(llave: str, crudo: str) -> str:
    """Nombre para mostrar: corrige el maestro donde está mal escrito."""
    if llave in cfg.NOMBRES_OFICIALES:
        return cfg.NOMBRES_OFICIALES[llave]
    return titulo_es(crudo)


def _limpiar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).strip() for c in df.columns]
    return df


class Sabana:
    """Sábana cargada, normalizada y lista para calcular indicadores."""

    def __init__(self, ruta=None):
        self.ruta = ruta or cfg.ARCHIVO_SABANA
        self._libro = pd.ExcelFile(self.ruta)
        self.hojas: dict[str, pd.DataFrame] = {}
        self._cargar()

    # ----------------------------------------------------------------------
    def _cargar(self) -> None:
        maestro = _limpiar_columnas(
            self._libro.parse(cfg.HOJAS["municipios"][0])
        )
        maestro["cod"] = (
            maestro["COD_DANE"].astype(str)
            .str.replace(r"\.0$", "", regex=True).str.zfill(5)
        )
        maestro["llave"] = maestro["MUNICIPIO"].map(llave_municipio)
        self._llave_a_cod = dict(zip(maestro["llave"], maestro["cod"]))

        maestro["nombre"] = [
            nombre_oficial(llave, crudo)
            for llave, crudo in zip(maestro["llave"], maestro["MUNICIPIO"])
        ]
        crudo_sub = maestro["SUBREGIÓN"].map(normalizar)
        corregida = [
            cfg.CORRECCIONES_SUBREGION.get(llave, valor)
            for llave, valor in zip(maestro["llave"], crudo_sub)
        ]
        maestro["subregion"] = (
            pd.Series(corregida, index=maestro.index).map(normalizar)
            .map(titulo_es).map(lambda s: cfg.SUBREGION_DISPLAY.get(s, s))
        )
        maestro["eat"] = maestro["EAT"].astype(str).str.strip()
        self.municipios = maestro[["cod", "nombre", "subregion", "eat"]].copy()
        self.municipios = self.municipios.sort_values("nombre").reset_index(drop=True)

        codigos_validos = set(maestro["cod"])
        self.usa_llave_dane = {}
        for clave, (hoja, col) in cfg.HOJAS.items():
            if clave == "municipios":
                continue
            df = _limpiar_columnas(self._libro.parse(hoja))

            # Si la sábana ya viene normalizada, se cruza por COD_DANE_MPIO y
            # no por nombre. Ese es el objetivo: que la tabla de alias deje de
            # ser necesaria. Mientras tanto, se cae al cruce por nombre.
            columna_cod = next(
                (c for c in df.columns if c.upper() == "COD_DANE_MPIO"), None
            )
            if columna_cod is not None:
                cod = (df[columna_cod].astype(str)
                       .str.replace(r"\.0$", "", regex=True).str.zfill(5))
                df["cod"] = cod.where(cod.isin(codigos_validos))
                self.usa_llave_dane[clave] = True
            else:
                df["cod"] = df[col].map(llave_municipio).map(self._llave_a_cod)
                self.usa_llave_dane[clave] = False
            self.hojas[clave] = df

        self._preparar_sedes()
        self._preparar_peti()

    # ----------------------------------------------------------------------
    def _preparar_sedes(self) -> None:
        """Agrega programa, subprograma y tecnología normalizados."""
        df = self.hojas["sedes"]
        df["tecnologia_raw"] = df["PROYECTO"].astype(str).str.strip().str.upper()
        df["tecnologia"] = df["tecnologia_raw"].map(cfg.TECNOLOGIAS)
        df["conectada"] = df["tecnologia_raw"] != cfg.SIN_TECNOLOGIA

        observacion = df["Observacion"].fillna("").astype(str).str.strip().str.upper()
        df["programa"] = observacion.map(self._clasificar_programa)
        df["subprograma"] = observacion.map(
            lambda o: cfg.SUBPROGRAMAS.get(o, cfg.SUBPROGRAMA_OTROS)
        )
        df["zona"] = observacion.map(
            lambda o: cfg.ZONA_SEDE.get(o, cfg.ZONA_SIN_DATO)
        )

    @staticmethod
    def _clasificar_programa(observacion: str) -> str:
        if observacion.startswith("GOBERNACI"):
            return "Gobernación"
        if observacion.startswith("MINTIC"):
            return "MinTIC"
        if observacion.startswith("POR EL MUNICIPIO"):
            return "Municipio"
        if observacion in ("NAN", "NONE", ""):
            return "Sin programa"
        return "Otros"

    # ----------------------------------------------------------------------
    def _preparar_peti(self) -> None:
        df = self.hojas["peti"]
        for origen, destino in [("ESTADO PETI", "estado_peti"),
                                ("ESTADO PAMUDA", "estado_pamuda")]:
            df[destino] = df[origen].astype(str).str.strip()
        df["madurez"] = (
            df["FICHA MADUREZ (NIVEL)"].astype(str).str.strip()
            .replace({"nan": "Sin ficha"})
            .str.replace("NIVEL ", "Nivel ", regex=False)
        )

    # ----------------------------------------------------------------------
    def hoja(self, clave: str) -> pd.DataFrame:
        return self.hojas[clave]

    def por_municipio(self, clave: str, cod: str) -> pd.DataFrame:
        df = self.hojas[clave]
        return df[df["cod"] == cod]

    def resumen(self) -> dict:
        """Conteos de control para el log de la construcción."""
        return {
            "municipios": len(self.municipios),
            "hojas": len(self.hojas) + 1,
            "filas": {k: len(v) for k, v in self.hojas.items()},
            "hojas_con_dane": sum(1 for v in self.usa_llave_dane.values() if v),
            "hojas_por_nombre": sum(1 for v in self.usa_llave_dane.values() if not v),
        }
