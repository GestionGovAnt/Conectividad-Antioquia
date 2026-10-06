"""
Ensamble del paquete de datos que consume el tablero.

Cruza los cuatro ejes de conectividad con la inversión y arma la estructura
por municipio, por subregión, por EAT y departamental.
"""
from __future__ import annotations

import json

from . import config as cfg, ejes as ejes_mod, inversion as inv_mod, kmz as kmz_mod
from .loader import Sabana


def _unidades_por_eje(municipios: list[dict]) -> dict[str, dict[str, int]]:
    """Repartidor de la inversión departamental: unidades de cada eje."""
    salida = {eje: {} for eje in cfg.IDS_EJES}
    for m in municipios:
        for eje in cfg.IDS_EJES:
            salida[eje][m["cod"]] = m["ejes"][eje]["unidades"]
    return salida


def _poligonos_lonlat() -> dict:
    """Anillos en lon/lat para asignar los KMZ que no cruzan por nombre."""
    from . import geojson as gj
    geo = json.loads(cfg.ARCHIVO_GEO.read_text(encoding="utf-8"))
    return {cod: gj._anillo(path) for cod, path in geo["paths"].items()}


def construir(sab: Sabana, ruta_inversion=None, ruta_kmz=None) -> dict:
    # El trazado de fibra se lee antes que los ejes: el eje de seguridad
    # reporta los metros medidos si están disponibles.
    fibra = kmz_mod.leer(ruta_kmz, sab.municipios, _poligonos_lonlat())
    sab.fibra_kmz = fibra["metros"]

    municipios = []
    for _, fila in sab.municipios.iterrows():
        cod = fila["cod"]
        municipios.append({
            "cod": cod, "nombre": fila["nombre"],
            "subregion": fila["subregion"], "eat": fila["eat"],
            "ejes": ejes_mod.calcular(sab, {cod}),
        })

    unidades = _unidades_por_eje(municipios)
    try:
        crudo = inv_mod.leer(ruta_inversion)
        inversion = inv_mod.procesar(
            crudo, unidades, set(sab.municipios["cod"]))
    except inv_mod.SinInversion as e:
        inversion = inv_mod.vacio()
        inversion["avisos"] = [str(e)] + inversion["avisos"]

    for m in municipios:
        m["inversion"] = inversion["por_municipio"].get(
            m["cod"], {e: 0.0 for e in cfg.IDS_EJES})
        m["inversion_total"] = round(sum(m["inversion"].values()), 2)

    def agregado(seleccion) -> dict:
        codigos = set(seleccion["cod"])
        datos = {"ejes": ejes_mod.calcular(sab, codigos),
                 "municipios": len(codigos)}
        datos["inversion"] = {
            e: round(sum(inversion["por_municipio"].get(c, {}).get(e, 0.0)
                         for c in codigos), 2)
            for e in cfg.IDS_EJES
        }
        datos["inversion_total"] = round(sum(datos["inversion"].values()), 2)
        return datos

    subregiones = {n: agregado(g) for n, g in sab.municipios.groupby("subregion")}
    eats = {n: agregado(g) for n, g in sab.municipios.groupby("eat")}
    departamento = agregado(sab.municipios)
    departamento["inversion"] = inversion["totales"]
    departamento["inversion_total"] = inversion["total"]

    metros_sabana = {}
    seg = sab.hoja("seguridad")
    solo_fibra = seg[seg["Punto"].astype(str).str.strip() == "PROYECTO FIBRA ÓPTICA"]
    import pandas as pd
    for cod, grupo in solo_fibra.groupby("cod"):
        metros_sabana[cod] = int(
            pd.to_numeric(grupo["observacion"], errors="coerce").fillna(0).sum())
    fibra["comparacion"] = kmz_mod.comparar(fibra["metros"], metros_sabana)
    fibra["metros_sabana"] = metros_sabana

    return {
        "municipios": municipios,
        "fibra": fibra,
        "subregiones": subregiones,
        "eats": eats,
        "departamento": departamento,
        "inversion": inversion,
        "ejes": cfg.EJES,
        "capas": ejes_mod.capas(sab),
        "eat_display": cfg.EAT_DISPLAY,
        "estilo_mapa": cfg.ESTILO_MAPA,
        "enlace_gobernacion": cfg.ENLACE_GOBERNACION,
        "enlace_ficha": cfg.ENLACE_FICHA,
        "mostrar_inversion": cfg.MOSTRAR_INVERSION,
    }
