#!/usr/bin/env python3
"""
Observatorio de Conectividad — construcción del tablero.

Uso:
    python build.py
    python build.py --sabana otra.xlsx --inversion inversion_2026.csv

Produce un HTML autónomo en salida/. Ese archivo no necesita este proyecto,
ni Python, ni internet: se abre con doble clic.
"""
import argparse
import sys
from pathlib import Path

from src import (config as cfg, datos_tablero, geojson as gj, inversion,
                 render, sharepoint)
from src.loader import Sabana


def main() -> int:
    ap = argparse.ArgumentParser(description="Construye el observatorio.")
    ap.add_argument("--sabana", type=Path, default=cfg.ARCHIVO_SABANA)
    ap.add_argument("--inversion", type=Path, default=cfg.ARCHIVO_INVERSION)
    ap.add_argument("--kmz", type=Path, default=cfg.DIR_KMZ)
    ap.add_argument("--sharepoint", metavar="MODO", choices=("graph", "enlace"),
                    help="Descarga la sábana de SharePoint antes de construir. "
                         "También se activa con la variable SP_MODO.")
    ap.add_argument("--salida", type=Path, default=cfg.ARCHIVO_SALIDA)
    ap.add_argument("--salida-mapa", type=Path, default=cfg.ARCHIVO_SALIDA_MAPA)
    ap.add_argument("--sin-mapa", action="store_true",
                    help="No generar la versión con mapa base.")
    ap.add_argument("--geojson", action="store_true",
                    help="Además, escribir los GeoJSON sueltos en salida/geojson.")
    args = ap.parse_args()

    actualizado, detalle = sharepoint.sincronizar(args.sabana, args.sharepoint)
    print(f"Fuente: {detalle}" if (actualizado or args.sharepoint
                                   or __import__("os").environ.get("SP_MODO"))
          else "Fuente: copia local")

    if not args.sabana.exists():
        # Tolerancia al nombre: el archivo de SharePoint trae tildes.
        encontrado = None
        for patron in cfg.PATRONES_SABANA:
            candidatos = sorted(cfg.DIR_DATOS.glob(patron))
            candidatos = [c for c in candidatos if "inversion" not in c.name.lower()]
            if candidatos:
                encontrado = candidatos[0]
                break
        if encontrado is None:
            print(f"  No se encontró la sábana: {args.sabana}", file=sys.stderr)
            print(f"  Ni ningún Excel en {cfg.DIR_DATOS}", file=sys.stderr)
            return 1
        print(f"  Nombre distinto al esperado, se usa: {encontrado.name}")
        args.sabana = encontrado
    inversion.plantilla(args.inversion)

    print(f"Leyendo {args.sabana.name} ...")
    sabana = Sabana(args.sabana)
    print(f"  {len(sabana.municipios)} municipios")

    print("Calculando los cuatro ejes ...")
    datos = datos_tablero.construir(sabana, args.inversion, args.kmz)
    for eje in cfg.EJES:
        e = datos["departamento"]["ejes"][eje["id"]]
        cob = f" · cobertura {e['cobertura']:.1%}" if e["cobertura"] else ""
        print(f"  {eje['nombre']:<10} {e['unidades']:>6,} {eje['unidad'].lower()}{cob}")

    total_pts = sum(c["georreferenciados"] for c in datos["capas"])
    sin_pts = sum(c["sin_coordenada"] for c in datos["capas"])
    print(f"  capas del mapa: {total_pts:,} puntos · {sin_pts:,} sin coordenada")

    fib = datos["fibra"]
    print("Trazado de fibra ...")
    if fib["disponible"]:
        total = sum(fib["metros"].values())
        rep = sum(fib.get("metros_sabana", {}).values())
        print(f"  {fib['archivos']} archivos · {len(fib['metros'])} municipios "
              f"· {total:,.0f} m medidos")
        if rep:
            print(f"  sábana reporta {rep:,.0f} m · diferencia "
                  f"{total - rep:+,.0f} m")
        if args.kmz.exists() and any(args.kmz.rglob("*.km[zl]")):
            from src import kmz as _kmz
            destino = _kmz.guardar_cache(fib)
            print(f"  caché actualizado: {destino.name} "
                  f"({destino.stat().st_size/1024:.0f} KB)")
    else:
        print("  sin archivos en datos/kmz/")
    for aviso in fib["avisos"]:
        print(f"    · {aviso}")

    inv = datos["inversion"]
    if inv["disponible"]:
        print(f"Inversión ({inv['etiqueta_valor']}) ...")
        print(f"  {inv['registros']} registros · total {inv['total']:,.0f}")
        for f in inv["reparto_ejes"]:
            parte = f" ({f['part']:.1%})" if f["part"] else ""
            print(f"    {f['nombre']:<10} {f['total']:>15,.0f}{parte}")
    else:
        print("Inversión ...")
        print("  sin datos cargados — el tablero muestra el aviso correspondiente")
    for aviso in inv["avisos"]:
        print(f"    · {aviso}")

    import json as _json
    geo = _json.loads(cfg.ARCHIVO_GEO.read_text(encoding="utf-8"))

    print("\nGenerando tableros ...")
    if not args.sin_mapa:
        paquete = {"municipios": gj.municipios(datos, geo),
                   "puntos": gj.puntos(datos),
                   "fibra": {"type": "FeatureCollection",
                             "features": datos["fibra"]["rasgos"]}}
        mapa = render.generar_mapa(datos, paquete, args.salida_mapa)
        print(f"  principal  {mapa.name:<38} {mapa.stat().st_size/1024:>6.0f} KB")

    destino = render.generar(datos, args.salida)
    print(f"  respaldo   {destino.name:<38} {destino.stat().st_size/1024:>6.0f} KB")

    if args.geojson:
        for archivo in gj.escribir(datos, geo):
            print(f"  geojson       {archivo.name}")

    print("\n  El principal necesita internet: descarga el mapa base.")
    print("  El respaldo funciona sin conexión, con el mapa dibujado en SVG.")
    print("  Deje ficha_tic_antioquia.html en la misma carpeta para que el")
    print("  enlace entre los dos funcione.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
