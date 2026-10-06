"""Generación del tablero HTML autónomo."""
from __future__ import annotations

import base64
import json
from datetime import date
from pathlib import Path

from . import config as cfg


def _leer(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


def _json(objeto) -> str:
    return json.dumps(objeto, ensure_ascii=False, separators=(",", ":"))


def generar(datos: dict, destino: Path | None = None) -> Path:
    destino = destino or cfg.ARCHIVO_SALIDA
    destino.parent.mkdir(parents=True, exist_ok=True)
    plantilla = _leer(cfg.DIR_PLANTILLAS / "base.html")
    reemplazos = {
        "{{FECHA}}": date.today().strftime("%d/%m/%Y"),
        "{{ESTILOS}}": _leer(cfg.DIR_PLANTILLAS / "estilos.css"),
        "{{APP_JS}}": _leer(cfg.DIR_PLANTILLAS / "app.js"),
        "{{META}}": _json({"entidad": cfg.ENTIDAD,
                           "dependencia": cfg.DEPENDENCIA,
                           "titulo": cfg.TITULO,
                           "fecha": date.today().isoformat()}),
        "{{DATOS}}": _json(datos),
        "{{GEO}}": _leer(cfg.ARCHIVO_GEO).strip(),
        "{{IMG}}": _json({k: base64.b64encode(v.read_bytes()).decode("ascii")
                          for k, v in cfg.ASSETS.items()}),
    }
    for marca, valor in reemplazos.items():
        plantilla = plantilla.replace(marca, valor)
    destino.write_text(plantilla, encoding="utf-8")
    return destino


def generar_mapa(datos: dict, geojson: dict, destino: Path | None = None) -> Path:
    """Versión con mapa base. Requiere internet en el navegador del usuario:
    la librería MapLibre y las teselas se descargan de un CDN. Los datos
    siguen embebidos, así que el archivo tampoco necesita servidor."""
    destino = destino or cfg.ARCHIVO_SALIDA_MAPA
    destino.parent.mkdir(parents=True, exist_ok=True)
    plantilla = _leer(cfg.DIR_PLANTILLAS / "mapa.html")
    reemplazos = {
        "{{FECHA}}": date.today().strftime("%d/%m/%Y"),
        "{{ESTILOS}}": _leer(cfg.DIR_PLANTILLAS / "mapa.css"),
        "{{APP_JS}}": _leer(cfg.DIR_PLANTILLAS / "mapa.js"),
        "{{META}}": _json({"entidad": cfg.ENTIDAD,
                           "dependencia": cfg.DEPENDENCIA,
                           "titulo": cfg.TITULO,
                           "fecha": date.today().isoformat()}),
        "{{DATOS}}": _json(datos),
        "{{GEOJSON}}": _json(geojson),
        "{{IMG}}": _json({k: base64.b64encode(v.read_bytes()).decode("ascii")
                          for k, v in cfg.ASSETS.items()}),
    }
    for marca, valor in reemplazos.items():
        plantilla = plantilla.replace(marca, valor)
    destino.write_text(plantilla, encoding="utf-8")
    return destino
