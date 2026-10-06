"""
Conversión de la geometría del lienzo a GeoJSON en coordenadas reales.

Los polígonos llegan en coordenadas de lienzo SVG. La proyección de
`config.PROYECCION` es lineal, así que se invierte exacto:

    lon = (x - bx) / ax
    lat = (y - by) / ay

El bounding box reconstruido cae dentro de 1 a 4 km del real de Antioquia,
suficiente para que los polígonos se asienten sobre un mapa base.

Los indicadores viajan como propiedades de cada polígono, de modo que el
mapa colorea sin tener que cruzar nada en el navegador.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import config as cfg

_PUNTO = re.compile(r"([-\d.]+),([-\d.]+)")


def _a_lonlat(x: float, y: float) -> list[float]:
    p = cfg.PROYECCION
    return [round((x - p["bx"]) / p["ax"], 6),
            round((y - p["by"]) / p["ay"], 6)]


def _anillo(path: str) -> list[list[float]]:
    puntos = [_a_lonlat(float(a), float(b)) for a, b in _PUNTO.findall(path)]
    if puntos and puntos[0] != puntos[-1]:
        puntos.append(puntos[0])
    return puntos


def municipios(datos: dict, geo: dict) -> dict:
    """FeatureCollection de los 125 municipios con todos los indicadores."""
    por_cod = {m["cod"]: m for m in datos["municipios"]}
    rasgos = []
    for cod, path in geo["paths"].items():
        m = por_cod.get(cod)
        if m is None:
            continue
        props = {
            "cod": cod,
            "nombre": m["nombre"],
            "subregion": m["subregion"],
            "eat": cfg.EAT_DISPLAY.get(m["eat"], m["eat"]),
            "inversion_total": m["inversion_total"],
        }
        for eje in cfg.IDS_EJES:
            e = m["ejes"][eje]
            props[eje + "_unidades"] = e["unidades"]
            props[eje + "_cobertura"] = (
                round(e["cobertura"] * 100, 1) if e["cobertura"] is not None else None
            )
            props[eje + "_inversion"] = m["inversion"][eje]
        rasgos.append({
            "type": "Feature",
            "id": int(cod),
            "properties": props,
            "geometry": {"type": "Polygon", "coordinates": [_anillo(path)]},
        })
    return {"type": "FeatureCollection", "features": rasgos}


def puntos(datos: dict) -> dict[str, dict]:
    """Una FeatureCollection por capa, en coordenadas reales."""
    por_cod = {m["cod"]: m["nombre"] for m in datos["municipios"]}
    salida = {}
    for capa in datos["capas"]:
        rasgos = [{
            "type": "Feature",
            "properties": {"cod": cod, "municipio": por_cod.get(cod, ""),
                           "capa": capa["id"], "eje": capa["eje"]},
            "geometry": {"type": "Point", "coordinates": _a_lonlat(x, y)},
        } for x, y, cod in capa["puntos"]]
        salida[capa["id"]] = {"type": "FeatureCollection", "features": rasgos}
    return salida


def escribir(datos: dict, geo: dict, carpeta: Path | None = None) -> list[Path]:
    """Escribe los GeoJSON sueltos, por si se quieren usar en QGIS o Power BI."""
    carpeta = carpeta or (cfg.DIR_SALIDA / "geojson")
    carpeta.mkdir(parents=True, exist_ok=True)
    escritos = []
    destino = carpeta / "municipios.geojson"
    destino.write_text(json.dumps(municipios(datos, geo), ensure_ascii=False),
                       encoding="utf-8")
    escritos.append(destino)
    for capa, coleccion in puntos(datos).items():
        destino = carpeta / f"puntos_{capa}.geojson"
        destino.write_text(json.dumps(coleccion, ensure_ascii=False),
                           encoding="utf-8")
        escritos.append(destino)
    return escritos
