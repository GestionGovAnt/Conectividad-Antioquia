"""
Lectura y normalización de la sábana única del visor.

Heredado del proyecto de la ficha municipal: mismo contrato de datos.

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
        columna_maestro = self._columna_codigo(maestro)
        if columna_maestro is None:
            raise ValueError(
                "La hoja Municipios no tiene columna COD_DANE ni COD_DANE_MPIO. "
                "Sin ella no hay forma de cruzar las demás hojas."
            )
        maestro["cod"] = (
            maestro[columna_maestro].astype(str)
            .str.replace(r"\.0$", "", regex=True).str.strip().str.zfill(5)
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

        self._codigos_validos = set(maestro["cod"])
        self.usa_llave_dane = {}
        self.hojas_faltantes: list[str] = []
        for clave, (hoja, col) in cfg.HOJAS.items():
            if clave == "municipios":
                continue
            if hoja not in self._libro.sheet_names:
                # El Excel puede ser un extracto con solo algunas hojas. Se
                # anota y sigue: quien necesite esa hoja decide si aborta.
                self.hojas_faltantes.append(hoja)
                continue
            df = _limpiar_columnas(self._libro.parse(hoja))

            # Si la sábana ya viene estandarizada, se cruza por el código DANE
            # y no por nombre. Ese es el objetivo: que la tabla de alias deje
            # de ser necesaria. Mientras tanto, se cae al cruce por nombre.
            columna_cod = self._columna_codigo(df)
            if columna_cod is not None:
                df["cod"] = self._codigos(df[columna_cod])
                self.usa_llave_dane[clave] = True
            else:
                df["cod"] = df[col].map(llave_municipio).map(self._llave_a_cod)
                self.usa_llave_dane[clave] = False
            self.hojas[clave] = df

        if "sedes" in self.hojas:
            self._preparar_sedes()
        if "peti" in self.hojas:
            self._preparar_peti()

    # ----------------------------------------------------------------------
    @staticmethod
    def _columna_codigo(df: pd.DataFrame) -> str | None:
        """La columna del código DANE, con cualquiera de los dos nombres.

        La sábana normalizada por el proyecto la llama COD_DANE_MPIO, la
        estandarizada a mano la llama COD_DANE y la hoja de SALUD la llama
        codigo_dane. Las tres son la misma llave.
        """
        nombres = {str(c).strip().upper(): c for c in df.columns}
        for candidato in ("COD_DANE_MPIO", "COD_DANE", "CODIGO_DANE"):
            if candidato in nombres:
                return nombres[candidato]
        return None

    def _codigos(self, serie: pd.Series) -> pd.Series:
        """Código a cinco dígitos como texto, descartando los que no existen."""
        cod = (serie.astype(str)
               .str.replace(r"\.0$", "", regex=True).str.strip().str.zfill(5))
        return cod.where(cod.isin(self._codigos_validos))

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
        # La etiqueta se homologa sin distinguir mayúsculas ni tildes. La
        # sábana ha traído el mismo estado como «Inicio proceso de
        # acompañamiento» y como «INICIO PROCESO DE ACOMPAÑAMIENTO»; con una
        # comparación exacta, la segunda forma se perdía del tablero sin
        # avisar y el reparto quedaba mostrando solo los «SI».
        etiquetas = {normalizar(k): v for k, v in cfg.ETIQUETA_ESTADO.items()}
        for origen, destino in [("ESTADO PETI", "estado_peti"),
                                ("ESTADO PAMUDA", "estado_pamuda")]:
            crudo = df[origen].astype(str).str.strip()
            df[destino] = [
                etiquetas.get(normalizar(v), titulo_es(v) if v else "Sin dato")
                for v in crudo
            ]
        df["madurez"] = (
            df["FICHA MADUREZ (NIVEL)"].astype(str).str.strip()
            .replace({"nan": "Sin ficha"})
            .str.replace("NIVEL ", "Nivel ", regex=False)
        )

    # ----------------------------------------------------------------------
    def hoja(self, clave: str) -> pd.DataFrame:
        return self.hojas[clave]

    def hoja_opcional(self, nombre: str) -> pd.DataFrame | None:
        """Hoja que puede no existir todavía, ya cruzada por COD_DANE_MPIO.

        Para hojas que se van sumando a la sábana sin que el tablero dependa
        de ellas: si no está, el build sigue igual en vez de romperse.
        """
        if nombre not in self._libro.sheet_names:
            return None
        df = _limpiar_columnas(self._libro.parse(nombre))
        columna = self._columna_codigo(df)
        if columna is None:
            return None
        df["cod"] = self._codigos(df[columna])
        return df

    def por_municipio(self, clave: str, cod: str) -> pd.DataFrame:
        df = self.hojas[clave]
        return df[df["cod"] == cod]

    def sin_cruce(self) -> dict[str, int]:
        """Filas que no quedaron asignadas a ningún municipio.

        Una fila sin COD_DANE_MPIO —o con un nombre que no cruza— queda fuera
        de TODOS los conteos, también del departamental. Es la forma más
        silenciosa de perder datos: el tablero compila bien y la cifra
        simplemente no sube.
        """
        return {clave: int(df["cod"].isna().sum())
                for clave, df in self.hojas.items()
                if int(df["cod"].isna().sum()) > 0}

    def resumen(self) -> dict:
        """Conteos de control para el log de la construcción."""
        return {
            "municipios": len(self.municipios),
            "hojas": len(self.hojas) + 1,
            "filas": {k: len(v) for k, v in self.hojas.items()},
            "hojas_con_dane": sum(1 for v in self.usa_llave_dane.values() if v),
            "hojas_por_nombre": sum(1 for v in self.usa_llave_dane.values() if not v),
        }
