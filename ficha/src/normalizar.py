"""
Normalización de la sábana única del visor.

Qué hace
--------
1. Agrega `COD_DANE_MPIO` como primera columna de todas las hojas. Es el
   código DANE del municipio en formato oficial de cinco dígitos con cero a
   la izquierda (05002), guardado como texto para que Excel no lo recorte.
2. Reescribe el nombre del municipio con el valor canónico de la hoja
   `Municipios`, que queda como única fuente de verdad.
3. Deriva `SUBREGION` y `EAT` desde el maestro en las hojas que ya tienen esas
   columnas, en vez de confiar en lo que cada hoja traía escrito.
4. Limpia los nombres de columna (espacios sobrantes al inicio y al final).
5. Deja constancia de todo en dos hojas nuevas de control.

Por qué COD_DANE_MPIO y no COD_DANE
-----------------------------------
`SEDES EDUCATIVAS` ya usa `CODIGO_DANE` para el código de la sede (doce
dígitos) y `SALUD` usa `codigo_dane` para el del municipio. Un nombre nuevo y
explícito evita que se confundan dos cosas distintas.

Qué NO hace
-----------
No borra ni modifica ninguna columna de datos, no elimina filas y no corrige
el contenido de los indicadores. Solo toca las llaves territoriales.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from . import config as cfg
from .loader import llave_municipio, nombre_oficial, normalizar

COL_COD = "COD_DANE_MPIO"
COL_SUB = "SUBREGION"
COL_EAT = "EAT"


class Normalizador:
    """Estandariza las llaves territoriales de la sábana."""

    def __init__(self, ruta_entrada: Path | None = None):
        self.ruta = ruta_entrada or cfg.ARCHIVO_SABANA
        self._libro = pd.ExcelFile(self.ruta)
        self.hojas: dict[str, pd.DataFrame] = {}
        self.cambios: list[dict] = []
        self.resumen: list[dict] = []
        self._cargar_maestro()

    # ------------------------------------------------------------------
    def _cargar_maestro(self) -> None:
        hoja_maestro = cfg.HOJAS["municipios"][0]
        maestro = self._libro.parse(hoja_maestro)
        maestro.columns = [str(c).strip() for c in maestro.columns]

        maestro[COL_COD] = (
            maestro["COD_DANE"].astype(str)
            .str.replace(r"\.0$", "", regex=True).str.zfill(5)
        )
        maestro["llave"] = maestro["MUNICIPIO"].map(llave_municipio)
        # El nombre que se escribe en toda la base es el oficial, no el que
        # traía el maestro: a tres municipios les faltaban tildes y a Santa Fe
        # de Antioquia le faltaba el "de".
        maestro["MUNICIPIO"] = [
            nombre_oficial(llave, crudo)
            for llave, crudo in zip(maestro["llave"], maestro["MUNICIPIO"])
        ]
        maestro["SUBREGIÓN"] = [
            cfg.CORRECCIONES_SUBREGION.get(llave, str(valor).strip())
            for llave, valor in zip(maestro["llave"], maestro["SUBREGIÓN"])
        ]
        maestro["EAT"] = maestro["EAT"].astype(str).str.strip()

        self.maestro = maestro
        self.por_llave = {
            fila["llave"]: {
                "cod": fila[COL_COD],
                "municipio": fila["MUNICIPIO"],
                "subregion": fila["SUBREGIÓN"],
                "eat": fila["EAT"],
            }
            for _, fila in maestro.iterrows()
        }

    # ------------------------------------------------------------------
    def _registrar(self, hoja: str, columna: str, antes, despues) -> None:
        """Acumula los cambios como pares distintos, no fila por fila."""
        antes = "" if pd.isna(antes) else str(antes).strip()
        despues = "" if despues is None else str(despues)
        if antes == despues:
            return
        for c in self.cambios:
            if (c["hoja"], c["columna"], c["antes"], c["despues"]) == \
               (hoja, columna, antes, despues):
                c["filas"] += 1
                return
        self.cambios.append({"hoja": hoja, "columna": columna, "antes": antes,
                             "despues": despues, "filas": 1})

    # ------------------------------------------------------------------
    def _normalizar_hoja(self, clave: str, nombre_hoja: str,
                         col_municipio: str) -> pd.DataFrame:
        df = self._libro.parse(nombre_hoja)
        originales = list(df.columns)
        df.columns = [str(c).strip() for c in df.columns]
        renombradas = sum(1 for a, b in zip(originales, df.columns)
                          if str(a) != str(b))

        col_mun = str(col_municipio).strip()
        llaves = df[col_mun].map(llave_municipio)
        datos = llaves.map(self.por_llave)
        sin_cruce = int(datos.isna().sum())

        # 1. COD_DANE_MPIO como primera columna
        df.insert(0, COL_COD, datos.map(
            lambda d: d["cod"] if isinstance(d, dict) else None))

        # 2. nombre canónico del municipio
        renombrados = 0
        nuevos = []
        for antes, d in zip(df[col_mun], datos):
            if isinstance(d, dict):
                nuevos.append(d["municipio"])
                if str(antes).strip() != d["municipio"]:
                    renombrados += 1
                    self._registrar(nombre_hoja, col_mun, antes, d["municipio"])
            else:
                nuevos.append(antes)
        df[col_mun] = nuevos

        # 3. subregión y EAT derivadas del maestro
        derivadas = 0
        for candidato, campo in ((COL_SUB, "subregion"), (COL_EAT, "eat")):
            existente = next(
                (c for c in df.columns if normalizar(c) == normalizar(candidato)),
                None,
            )
            if existente is None:
                continue
            nuevos = []
            for antes, d in zip(df[existente], datos):
                if isinstance(d, dict):
                    nuevos.append(d[campo])
                    if str(antes).strip() != d[campo]:
                        derivadas += 1
                        self._registrar(nombre_hoja, existente, antes, d[campo])
                else:
                    nuevos.append(antes)
            df[existente] = nuevos

        self.resumen.append({
            "Hoja": nombre_hoja,
            "Filas": len(df),
            "Con COD_DANE_MPIO": len(df) - sin_cruce,
            "Sin cruce": sin_cruce,
            "Municipios renombrados": renombrados,
            "Subregión / EAT corregidas": derivadas,
            "Encabezados limpiados": renombradas,
        })
        return df

    # ------------------------------------------------------------------
    def normalizar(self) -> dict[str, pd.DataFrame]:
        maestro = self.maestro.drop(columns=["llave"])
        maestro = maestro[[COL_COD] + [c for c in maestro.columns if c != COL_COD]]
        self.hojas[cfg.HOJAS["municipios"][0]] = maestro
        self.resumen.append({
            "Hoja": cfg.HOJAS["municipios"][0],
            "Filas": len(maestro),
            "Con COD_DANE_MPIO": len(maestro),
            "Sin cruce": 0,
            "Municipios renombrados": 0,
            "Subregión / EAT corregidas": 0,
            "Encabezados limpiados": 2,
        })

        for clave, (nombre_hoja, col) in cfg.HOJAS.items():
            if clave == "municipios":
                continue
            self.hojas[nombre_hoja] = self._normalizar_hoja(clave, nombre_hoja, col)
        return self.hojas

    # ------------------------------------------------------------------
    def _hoja_control(self) -> pd.DataFrame:
        return pd.DataFrame(self.resumen)

    def _hoja_cambios(self) -> pd.DataFrame:
        if not self.cambios:
            return pd.DataFrame([{"hoja": "—", "columna": "—", "antes": "—",
                                  "despues": "—", "filas": 0}])
        df = pd.DataFrame(self.cambios)
        df = df.rename(columns={"hoja": "Hoja", "columna": "Columna",
                                "antes": "Valor original",
                                "despues": "Valor estandarizado",
                                "filas": "Filas afectadas"})
        return df.sort_values(["Hoja", "Columna", "Filas afectadas"],
                              ascending=[True, True, False])

    def _hoja_diccionario(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"Campo": COL_COD,
             "Descripción": "Código DANE del municipio, cinco dígitos con cero "
                            "a la izquierda, guardado como texto.",
             "Origen": "Hoja Municipios",
             "Uso": "Llave de cruce entre todas las hojas. Úsela en lugar del "
                    "nombre del municipio."},
            {"Campo": "MUNICIPIO / nombre_municipio",
             "Descripción": "Nombre canónico tomado del maestro.",
             "Origen": "Hoja Municipios",
             "Uso": "Solo para mostrar. No cruzar por este campo."},
            {"Campo": "SUBREGION",
             "Descripción": "Subregión derivada del maestro.",
             "Origen": "Hoja Municipios",
             "Uso": "Reemplaza lo que cada hoja traía escrito."},
            {"Campo": "EAT",
             "Descripción": "Esquema asociativo territorial derivado del maestro.",
             "Origen": "Hoja Municipios",
             "Uso": "Antes venía vacío en casi todas las hojas."},
            {"Campo": "CODIGO_DANE (SEDES EDUCATIVAS)",
             "Descripción": "Código DANE de la sede, doce dígitos. No es el "
                            "código del municipio.",
             "Origen": "Fuente original",
             "Uso": "No confundir con COD_DANE_MPIO."},
        ])

    # ------------------------------------------------------------------
    def escribir(self, destino: Path | None = None) -> Path:
        destino = destino or (cfg.DIR_SALIDA / "sabana_normalizada.xlsx")
        destino.parent.mkdir(parents=True, exist_ok=True)
        if not self.hojas:
            self.normalizar()

        with pd.ExcelWriter(destino, engine="openpyxl") as writer:
            for nombre, df in self.hojas.items():
                df.to_excel(writer, sheet_name=nombre[:31], index=False)
            self._hoja_control().to_excel(
                writer, sheet_name="CONTROL DE CAMBIOS", index=False)
            self._hoja_cambios().to_excel(
                writer, sheet_name="CAMBIOS APLICADOS", index=False)
            self._hoja_diccionario().to_excel(
                writer, sheet_name="DICCIONARIO", index=False)

        self._dar_formato(destino)
        return destino

    # ------------------------------------------------------------------
    @staticmethod
    def _dar_formato(ruta: Path) -> None:
        """Encabezados legibles, columna de código como texto y filtros."""
        from openpyxl import load_workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        libro = load_workbook(ruta)
        verde = PatternFill("solid", fgColor="1B4D3E")
        for hoja in libro.worksheets:
            encabezados = [c.value for c in hoja[1]]
            for celda in hoja[1]:
                celda.font = Font(name="Arial", size=9, bold=True, color="FFFFFF")
                celda.fill = verde
                celda.alignment = Alignment(horizontal="center",
                                            vertical="center", wrap_text=True)
            hoja.row_dimensions[1].height = 30
            hoja.freeze_panes = "A2"
            if hoja.max_row > 1:
                hoja.auto_filter.ref = (
                    f"A1:{get_column_letter(hoja.max_column)}{hoja.max_row}"
                )
            for indice, nombre in enumerate(encabezados, start=1):
                letra = get_column_letter(indice)
                ancho = 16
                if nombre == COL_COD:
                    ancho = 15
                    for celda in hoja[letra][1:]:
                        celda.number_format = "@"
                        celda.alignment = Alignment(horizontal="center")
                elif nombre and len(str(nombre)) > 22:
                    ancho = 26
                hoja.column_dimensions[letra].width = ancho
        libro.save(ruta)


def normalizar_sabana(entrada: Path | None = None,
                      salida: Path | None = None) -> tuple[Path, Normalizador]:
    norm = Normalizador(entrada)
    norm.normalizar()
    destino = norm.escribir(salida)
    return destino, norm
