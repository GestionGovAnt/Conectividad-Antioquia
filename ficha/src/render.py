"""
Generación del informe HTML autónomo.

El resultado es un único archivo: estilos, código, datos, mapa e imágenes van
embebidos. La auditoría de calidad NO viaja dentro del informe: se entrega
aparte, como insumo interno de gestión (ver reporte_calidad.py). No requiere servidor, internet ni instalación para usarse; se abre
con doble clic. Eso permite enviarlo por correo o dejarlo en una carpeta
compartida sin que el proyecto viaje con él.
"""
from __future__ import annotations

import base64
import json
from datetime import date
from pathlib import Path

from . import config as cfg


def _leer(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


def _b64(ruta: Path) -> str:
    return base64.b64encode(ruta.read_bytes()).decode("ascii")


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
        "{{META}}": _json({
            "entidad": cfg.ENTIDAD,
            "dependencia": cfg.DEPENDENCIA,
            "fecha": date.today().isoformat(),
        }),
        "{{DATOS}}": _json(datos),
        "{{GEO}}": _leer(cfg.ARCHIVO_GEO).strip(),
        "{{IMG}}": _json({k: _b64(v) for k, v in cfg.ASSETS.items()}),
    }
    for marca, valor in reemplazos.items():
        plantilla = plantilla.replace(marca, valor)

    destino.write_text(plantilla, encoding="utf-8")
    return destino
