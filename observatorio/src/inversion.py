"""
Inversión por eje y por municipio.

Regla de imputación
-------------------
Una fila con `cod_dane_mpio` = 05002 se imputa directo a ese municipio.

Una fila marcada DEPARTAMENTAL se reparte entre los municipios en proporción
a las unidades que cada uno recibió en ese eje. Si un contrato de entornos
educativos seguros cubrió 250 placas y Yarumal recibió 6, a Yarumal le
corresponde el 2,4 % de ese contrato.

Un contrato transversal que no entrega puntos —una plataforma, una
consultoría— no se reparte: se reporta aparte como inversión transversal.
Repartirlo por población o en partes iguales sería inventar una cifra.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config as cfg


class SinInversion(Exception):
    """El archivo de inversión no existe o no tiene filas."""


def plantilla(destino: Path | None = None) -> Path:
    """Crea datos/inversion.csv vacío, solo con los encabezados."""
    destino = destino or cfg.ARCHIVO_INVERSION
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(columns=cfg.COLUMNAS_INVERSION).to_csv(
            destino, index=False, encoding="utf-8-sig")
    return destino


def leer(ruta: Path | None = None) -> pd.DataFrame:
    ruta = ruta or cfg.ARCHIVO_INVERSION
    if not ruta.exists():
        raise SinInversion(f"No existe {ruta}")
    df = pd.read_csv(ruta, dtype=str, encoding="utf-8-sig",
                     sep=None, engine="python")
    df.columns = [str(c).strip().lower() for c in df.columns]
    faltan = [c for c in cfg.COLUMNAS_INVERSION if c not in df.columns]
    if faltan:
        raise SinInversion("Faltan columnas: " + ", ".join(faltan))
    if df.empty:
        raise SinInversion("El archivo no tiene filas")

    for columna in ("valor_comprometido", "valor_obligado", "valor_pagado",
                    "unidades"):
        df[columna] = pd.to_numeric(
            df[columna].astype(str).str.replace(r"[^\d.\-]", "", regex=True),
            errors="coerce").fillna(0)
    df["vigencia"] = pd.to_numeric(df["vigencia"], errors="coerce").astype("Int64")
    df["eje"] = df["eje"].astype(str).str.strip().str.lower()
    df["cod_dane_mpio"] = df["cod_dane_mpio"].astype(str).str.strip().str.upper()
    es_codigo = df["cod_dane_mpio"] != cfg.MARCA_DEPARTAMENTAL
    df.loc[es_codigo, "cod_dane_mpio"] = (
        df.loc[es_codigo, "cod_dane_mpio"].str.zfill(5))
    df["fuente"] = df["fuente"].astype(str).str.strip().str.lower()
    return df


def _validar(df: pd.DataFrame, municipios: set[str]) -> list[str]:
    avisos = []
    ejes_malos = sorted(set(df["eje"]) - set(cfg.IDS_EJES))
    if ejes_malos:
        avisos.append("Ejes no reconocidos: " + ", ".join(ejes_malos))
    codigos = set(df["cod_dane_mpio"]) - {cfg.MARCA_DEPARTAMENTAL}
    perdidos = sorted(codigos - municipios)
    if perdidos:
        avisos.append("Códigos DANE que no cruzan: " + ", ".join(perdidos[:8]))
    return avisos


def procesar(df: pd.DataFrame, unidades: dict[str, dict[str, int]],
             municipios: set[str], valor: str | None = None) -> dict:
    """Reparte la inversión y devuelve los agregados listos para el tablero.

    unidades: {eje: {cod_dane: unidades}} — el repartidor.
    """
    valor = valor or cfg.VALOR_POR_DEFECTO
    avisos = _validar(df, municipios)

    por_municipio: dict[str, dict[str, float]] = {
        cod: {eje: 0.0 for eje in cfg.IDS_EJES} for cod in municipios
    }
    transversal: dict[str, float] = {eje: 0.0 for eje in cfg.IDS_EJES}
    sin_repartir = 0.0

    for _, fila in df.iterrows():
        eje = fila["eje"]
        monto = float(fila[valor])
        if eje not in cfg.IDS_EJES or monto == 0:
            continue

        if fila["cod_dane_mpio"] != cfg.MARCA_DEPARTAMENTAL:
            cod = fila["cod_dane_mpio"]
            if cod in por_municipio:
                por_municipio[cod][eje] += monto
            continue

        # Departamental: reparto proporcional a unidades del eje.
        base = unidades.get(eje, {})
        total_unidades = sum(base.values())
        if not total_unidades:
            transversal[eje] += monto
            sin_repartir += monto
            continue
        for cod, u in base.items():
            if u and cod in por_municipio:
                por_municipio[cod][eje] += monto * (u / total_unidades)

    totales = {eje: round(sum(m[eje] for m in por_municipio.values()) + transversal[eje], 2)
               for eje in cfg.IDS_EJES}
    total_general = round(sum(totales.values()), 2)

    def agrupar(columna: str) -> list[dict]:
        if columna not in df.columns:
            return []
        base = df.groupby(df[columna].astype(str))[valor].sum().sort_values(
            ascending=False)
        suma = float(base.sum())
        return [{"nombre": str(k), "total": round(float(v), 2),
                 "part": (float(v) / suma if suma else None)}
                for k, v in base.items() if float(v) > 0]

    return {
        "disponible": True,
        "valor_usado": valor,
        "etiqueta_valor": cfg.ETIQUETA_VALOR.get(valor, valor),
        "por_municipio": {cod: {e: round(v, 2) for e, v in ejes.items()}
                          for cod, ejes in por_municipio.items()},
        "transversal": {e: round(v, 2) for e, v in transversal.items()},
        "totales": totales,
        "total": total_general,
        "reparto_ejes": [
            {"nombre": next(x["nombre"] for x in cfg.EJES if x["id"] == e),
             "id": e, "total": totales[e],
             "part": (totales[e] / total_general if total_general else None)}
            for e in cfg.IDS_EJES
        ],
        "por_vigencia": agrupar("vigencia"),
        "por_fuente": agrupar("fuente"),
        "registros": int(len(df)),
        "sin_repartir": round(sin_repartir, 2),
        "avisos": avisos,
    }


def vacio() -> dict:
    """Estructura en ceros para cuando todavía no hay datos cargados."""
    return {
        "disponible": False,
        "valor_usado": cfg.VALOR_POR_DEFECTO,
        "etiqueta_valor": cfg.ETIQUETA_VALOR[cfg.VALOR_POR_DEFECTO],
        "por_municipio": {},
        "transversal": {e: 0.0 for e in cfg.IDS_EJES},
        "totales": {e: 0.0 for e in cfg.IDS_EJES},
        "total": 0.0,
        "reparto_ejes": [
            {"nombre": x["nombre"], "id": x["id"], "total": 0.0, "part": None}
            for x in cfg.EJES
        ],
        "por_vigencia": [], "por_fuente": [], "registros": 0,
        "sin_repartir": 0.0,
        "avisos": ["Sin datos de inversión cargados. "
                   "Complete datos/inversion.csv y vuelva a construir."],
    }
