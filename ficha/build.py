#!/usr/bin/env python3
"""
Punto de entrada del proyecto.

Uso:
    python build.py                      # usa datos/sabana_unica_visor.xlsx
    python build.py --sabana otra.xlsx   # usa otro archivo
    python build.py --salida ficha.html  # cambia el destino

Produce un HTML autónomo en salida/. Ese archivo se puede enviar o abrir solo:
no necesita este proyecto, ni Python, ni internet.
"""
import argparse
import sys
from pathlib import Path

from src import (calidad, config as cfg, exportar, indicadores, render,
                 reporte_calidad)
from src.loader import Sabana


def main() -> int:
    ap = argparse.ArgumentParser(description="Construye la ficha municipal de avance TIC.")
    ap.add_argument("--sabana", type=Path, default=cfg.ARCHIVO_SABANA,
                    help="Excel de la sábana única del visor.")
    ap.add_argument("--salida", type=Path, default=cfg.ARCHIVO_SALIDA,
                    help="Ruta del HTML a generar.")
    args = ap.parse_args()

    if not args.sabana.exists():
        print(f"  No se encontró la sábana: {args.sabana}", file=sys.stderr)
        return 1

    print(f"Leyendo {args.sabana.name} ...")
    sabana = Sabana(args.sabana)
    resumen = sabana.resumen()
    print(f"  {resumen['hojas']} hojas · {resumen['municipios']} municipios")
    if resumen["hojas_con_dane"]:
        print(f"  cruce por COD_DANE_MPIO en {resumen['hojas_con_dane']} hoja(s)"
              f" · por nombre en {resumen['hojas_por_nombre']}")
    else:
        print("  cruce por nombre de municipio (sábana sin normalizar)")

    print("Calculando indicadores ...")
    datos = indicadores.construir(sabana)
    dep = datos["departamento"]
    print(f"  sedes educativas: {dep['educacion']['total']:,}"
          f" · con tecnología: {dep['educacion']['conectadas']:,}"
          f" ({dep['educacion']['avance']:.1%})")
    print(f"  índice departamental: {dep['indice']:.1%}")

    print("Generando informe ...")
    destino = render.generar(datos, args.salida)
    print(f"  {destino}  ({destino.stat().st_size/1024:.0f} KB)")

    print("Exportando cifras a Excel ...")
    libro = exportar.exportar(datos)
    print(f"  {libro}  ({libro.stat().st_size/1024:.0f} KB)")

    print("Auditando calidad del dato ...")
    hallazgos = calidad.auditar(sabana)
    reporte = reporte_calidad.escribir(hallazgos)
    altas = sum(1 for h in hallazgos if h["severidad"] == "alta")
    print(f"  {len(hallazgos)} puntos a gestionar ({altas} de prioridad alta)")
    for h in hallazgos:
        print(f"    [{h['severidad'][:4]}] {h['titulo']} — {h['magnitud']}")
    print(f"  {reporte}")

    print("\nListo.")
    print("  · El HTML es autónomo: ábralo con doble clic o envíelo tal cual.")
    print("  · Las cifras por municipio, EAT y subregión quedan en Excel.")
    print("  · Los puntos a gestionar quedan aparte y NO viajan dentro del informe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
