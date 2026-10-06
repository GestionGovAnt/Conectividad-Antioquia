"""
Reporte interno de calidad del dato.

Los hallazgos NO se publican dentro del informe: son insumo de gestión de la
Dirección, no contenido para el municipio. Este módulo los escribe en un
Markdown aparte, con la magnitud medida contra el archivo y la acción
sugerida, para que se puedan repartir y hacerles seguimiento.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from . import config as cfg

ORDEN = {"alta": 0, "media": 1, "baja": 2, "informativa": 3}
TITULO = {
    "alta": "Prioridad alta",
    "media": "Prioridad media",
    "baja": "Prioridad baja",
    "informativa": "Informativo",
}


def escribir(hallazgos: list[dict], destino: Path | None = None) -> Path:
    destino = destino or (cfg.DIR_SALIDA / "puntos_a_gestionar.md")
    destino.parent.mkdir(parents=True, exist_ok=True)

    lineas = [
        "# Puntos a gestionar — sábana única del visor",
        "",
        f"Generado el {date.today().strftime('%d/%m/%Y')} a partir de "
        f"`{cfg.ARCHIVO_SABANA.name}`.",
        "",
        "Documento interno. No se publica dentro de la ficha municipal.",
        "Cada punto se recalcula en cada construcción: si la fuente se corrige,",
        "el punto desaparece solo de este reporte.",
        "",
    ]

    for severidad in sorted({h["severidad"] for h in hallazgos},
                            key=lambda s: ORDEN.get(s, 9)):
        grupo = [h for h in hallazgos if h["severidad"] == severidad]
        lineas += [f"## {TITULO.get(severidad, severidad)}", ""]
        for i, h in enumerate(grupo, 1):
            lineas += [
                f"### {i}. {h['titulo']}",
                "",
                f"- **Magnitud:** {h['magnitud']}",
                f"- **Qué pasa:** {h['detalle']}",
                f"- **Acción sugerida:** {h['accion']}",
                "- **Responsable:** _por asignar_",
                "- **Estado:** _pendiente_",
                "",
            ]

    lineas += [
        "---",
        "",
        "## Cómo hacerle seguimiento",
        "",
        "Complete responsable y estado en cada punto. Al volver a ejecutar",
        "`python build.py` el reporte se regenera desde cero, así que conviene",
        "guardar la versión trabajada con otro nombre antes de reconstruir.",
        "",
    ]

    destino.write_text("\n".join(lineas), encoding="utf-8")
    return destino
