"""
Ingesta del trazado de fibra óptica desde archivos KMZ.

Un KMZ es un ZIP que contiene un doc.kml. Este módulo lo abre, extrae las
líneas (`LineString`), mide su longitud real sobre el elipsoide y las
convierte en una capa de líneas para el mapa.

Asignación municipal
--------------------
1. Por nombre de archivo, homologado con la misma tabla de alias del resto
   del proyecto. `Fibra_Santa Fe de Antioquia.kmz` -> 05042.
2. Si el nombre no cruza, por ubicación: el municipio cuyo polígono contiene
   el punto medio del trazado.
3. Si tampoco, queda sin asignar y se reporta.

No usa librerías de GIS: KMZ es ZIP y KML es XML, ambos de la biblioteca
estándar.
"""
from __future__ import annotations

import difflib
import math
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from . import config as cfg
from .loader import llave_municipio

RADIO_TIERRA = 6_371_008.8  # metros, radio medio


# --------------------------------------------------------------------------
# Lectura
# --------------------------------------------------------------------------
def _kml_de(ruta: Path) -> list[str]:
    """Devuelve el contenido XML de los KML que haya dentro del KMZ."""
    if ruta.suffix.lower() == ".kml":
        return [ruta.read_text(encoding="utf-8", errors="ignore")]
    with zipfile.ZipFile(ruta) as z:
        nombres = [n for n in z.namelist() if n.lower().endswith(".kml")]
        return [z.read(n).decode("utf-8", errors="ignore") for n in nombres]


def _coordenadas(texto: str) -> list[list[float]]:
    """Convierte el bloque <coordinates> de KML a [[lon, lat], ...]."""
    puntos = []
    for trozo in texto.replace("\n", " ").split():
        partes = trozo.split(",")
        if len(partes) >= 2:
            try:
                puntos.append([round(float(partes[0]), 6),
                               round(float(partes[1]), 6)])
            except ValueError:
                continue
    return puntos


def _lineas(xml: str) -> list[list[list[float]]]:
    """Todas las LineString del KML, sin importar el nivel de anidamiento."""
    try:
        raiz = ET.fromstring(xml)
    except ET.ParseError:
        return []
    salida = []
    for elemento in raiz.iter():
        etiqueta = elemento.tag.split("}")[-1]
        if etiqueta not in ("LineString", "LinearRing"):
            continue
        for hijo in elemento.iter():
            if hijo.tag.split("}")[-1] == "coordinates" and hijo.text:
                puntos = _coordenadas(hijo.text)
                if len(puntos) >= 2:
                    salida.append(puntos)
    return salida


# --------------------------------------------------------------------------
# Medición
# --------------------------------------------------------------------------
def longitud(linea: list[list[float]]) -> float:
    """Longitud en metros por haversine entre vértices consecutivos."""
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(linea, linea[1:]):
        f1, f2 = math.radians(lat1), math.radians(lat2)
        df = f2 - f1
        dl = math.radians(lon2 - lon1)
        a = (math.sin(df / 2) ** 2
             + math.cos(f1) * math.cos(f2) * math.sin(dl / 2) ** 2)
        total += 2 * RADIO_TIERRA * math.asin(min(1.0, math.sqrt(a)))
    return total


def _punto_medio(lineas: list[list[list[float]]]) -> tuple[float, float] | None:
    puntos = [p for linea in lineas for p in linea]
    if not puntos:
        return None
    return (sum(p[0] for p in puntos) / len(puntos),
            sum(p[1] for p in puntos) / len(puntos))


# --------------------------------------------------------------------------
# Asignación municipal
# --------------------------------------------------------------------------
def _limpiar_nombre(texto: str) -> str:
    """Deja solo palabras: quita guiones bajos, signos, fechas y versiones."""
    texto = unicodedata.normalize("NFC", str(texto))
    texto = re.sub(r"[^\w\sáéíóúñÁÉÍÓÚÑ]", " ", texto)
    texto = texto.replace("_", " ")
    texto = re.sub(r"\d+", " ", texto)
    return " ".join(texto.split())


def _ventanas(texto: str):
    """Todas las secuencias de palabras, de la más larga a la más corta.

    Los archivos vienen con el municipio en cualquier posición:
    `Amalfí FO CCTV EDS FINAL`, `DIAGNOSTICO CAROLINA V3.0`,
    `FINAL SAN ANDRES DE CUERQUIA`. Probar ventanas lo resuelve sin
    depender de dónde quedó el nombre.
    """
    palabras = _limpiar_nombre(texto).split()
    for largo in range(min(5, len(palabras)), 0, -1):
        for inicio in range(len(palabras) - largo + 1):
            yield " ".join(palabras[inicio:inicio + largo])


def _codigo_por_nombre(nombre_archivo: str, llave_a_cod: dict):
    """Devuelve (codigo, modo). El modo dice cómo se resolvió."""
    stem = Path(nombre_archivo).stem
    for ventana in _ventanas(stem):
        llave = llave_municipio(ventana)
        if not llave:
            continue
        if llave in llave_a_cod:
            return llave_a_cod[llave], "nombre"
        equivalente = cfg.ALIAS_ARCHIVO_KMZ.get(llave)
        if equivalente:
            llave2 = llave_municipio(equivalente)
            if llave2 in llave_a_cod:
                return llave_a_cod[llave2], "alias"

    # Última opción: coincidencia aproximada, para nombres con acentos
    # mal exportados o palabras pegadas.
    candidatos = [llave_municipio(v) for v in _ventanas(stem)]
    for candidato in [c for c in candidatos if c and len(c) > 4]:
        cerca = difflib.get_close_matches(
            candidato, list(llave_a_cod), n=1, cutoff=cfg.UMBRAL_APROXIMADO)
        if cerca:
            return llave_a_cod[cerca[0]], "aproximado:" + cerca[0]
    return None, None


def _dentro(punto: tuple[float, float], anillo: list[list[float]]) -> bool:
    """Point-in-polygon por cruce de rayos."""
    x, y = punto
    dentro = False
    for (x1, y1), (x2, y2) in zip(anillo, anillo[1:]):
        if (y1 > y) != (y2 > y):
            corte = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < corte:
                dentro = not dentro
    return dentro


def _codigo_por_ubicacion(punto, poligonos: dict) -> str | None:
    for cod, anillo in poligonos.items():
        if _dentro(punto, anillo):
            return cod
    return None


# --------------------------------------------------------------------------
# Proceso
# --------------------------------------------------------------------------
def _desde_cache() -> dict | None:
    """Lee el trazado ya procesado, si existe."""
    import json
    if not cfg.ARCHIVO_FIBRA.exists():
        return None
    datos = json.loads(cfg.ARCHIVO_FIBRA.read_text(encoding="utf-8"))
    rasgos = datos.get("features", [])
    metros = {}
    for r in rasgos:
        cod = r["properties"].get("cod")
        if cod:
            metros[cod] = metros.get(cod, 0) + r["properties"].get("metros", 0)
    return {
        "disponible": True, "rasgos": rasgos, "metros": metros,
        "archivos": datos.get("archivos", len(rasgos)),
        "sin_asignar": datos.get("sin_asignar", []), "repetidos": {},
        "avisos": [f"trazado leído de {cfg.ARCHIVO_FIBRA.name} "
                   f"(para reprocesar, deje los KMZ en datos/kmz/)"],
    }


def guardar_cache(resultado: dict) -> Path:
    """Escribe el resultado del procesamiento para no versionar los KMZ."""
    import json
    cfg.ARCHIVO_FIBRA.parent.mkdir(parents=True, exist_ok=True)
    cfg.ARCHIVO_FIBRA.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": resultado["rasgos"],
        "archivos": resultado["archivos"],
        "sin_asignar": resultado["sin_asignar"],
    }, ensure_ascii=False), encoding="utf-8")
    return cfg.ARCHIVO_FIBRA


def leer(carpeta: Path | None, municipios, poligonos: dict | None = None) -> dict:
    """Procesa los KMZ de la carpeta, o usa el trazado ya procesado.

    Devuelve la capa de líneas, los metros por municipio y los avisos.
    """
    carpeta = carpeta or cfg.DIR_KMZ
    vacio = {"disponible": False, "rasgos": [], "metros": {}, "archivos": 0,
             "sin_asignar": [], "repetidos": {}, "avisos": [
                 "Sin trazado de fibra. Copie los KMZ en datos/kmz/ "
                 "o deje datos/fibra_trazado.geojson."]}

    archivos = []
    if carpeta.exists():
        archivos = sorted([p for p in carpeta.rglob("*")
                           if p.suffix.lower() in (".kmz", ".kml")])
    if not archivos:
        return _desde_cache() or vacio

    llave_a_cod = {llave_municipio(n): c
                   for n, c in zip(municipios["nombre"], municipios["cod"])}
    rasgos, metros, sin_asignar, avisos = [], {}, [], []

    for archivo in archivos:
        try:
            lineas = []
            for xml in _kml_de(archivo):
                lineas.extend(_lineas(xml))
        except (zipfile.BadZipFile, OSError) as e:
            avisos.append(f"{archivo.name}: no se pudo abrir ({e})")
            continue
        if not lineas:
            avisos.append(f"{archivo.name}: no contiene trazados de línea")
            continue

        cod, modo = _codigo_por_nombre(archivo.name, llave_a_cod)
        if modo and modo != "nombre":
            avisos.append(f"{archivo.name}: asignado por {modo}")
        if cod is None and poligonos:
            centro = _punto_medio(lineas)
            if centro:
                cod = _codigo_por_ubicacion(centro, poligonos)
                if cod:
                    avisos.append(f"{archivo.name}: asignado por ubicación")
        if cod is None:
            sin_asignar.append(archivo.name)

        total = sum(longitud(linea) for linea in lineas)
        if cod:
            metros[cod] = metros.get(cod, 0.0) + total
        rasgos.append({
            "type": "Feature",
            "properties": {"cod": cod, "archivo": archivo.name,
                           "metros": round(total), "tramos": len(lineas)},
            "geometry": {"type": "MultiLineString", "coordinates": lineas},
        })

    # Varios archivos para un mismo municipio suelen ser versiones distintas
    # del mismo trazado: sumarlas duplicaría los metros.
    porcod = {}
    for r in rasgos:
        c = r["properties"]["cod"]
        if c:
            porcod.setdefault(c, []).append(r["properties"]["archivo"])
    repetidos = {c: v for c, v in porcod.items() if len(v) > 1}
    if repetidos:
        detalle = "; ".join(c + ": " + ", ".join(v) for c, v in repetidos.items())
        avisos.append(f"{len(repetidos)} municipio(s) con más de un archivo "
                      f"(revise si son versiones del mismo trazado) — {detalle}")

    if sin_asignar:
        avisos.append(f"{len(sin_asignar)} archivo(s) sin municipio asignado: "
                      + ", ".join(sin_asignar[:5]))
    return {
        "disponible": True,
        "rasgos": rasgos,
        "metros": {c: round(v) for c, v in metros.items()},
        "archivos": len(archivos),
        "sin_asignar": sin_asignar,
        "repetidos": repetidos,
        "avisos": avisos,
    }


def comparar(metros_kmz: dict, metros_sabana: dict) -> list[dict]:
    """Contrasta lo medido en el KMZ contra lo reportado en la sábana.

    La diferencia no es un error: el KMZ mide el trazado real y la sábana
    trae lo que alguien digitó. Sirve para saber cuál de las dos corregir.
    """
    filas = []
    for cod in sorted(set(metros_kmz) | set(metros_sabana)):
        kmz = metros_kmz.get(cod, 0)
        sab = metros_sabana.get(cod, 0)
        filas.append({
            "cod": cod, "kmz": kmz, "sabana": sab,
            "diferencia": kmz - sab,
            "razon": (kmz / sab) if sab else None,
        })
    return filas
