#!/usr/bin/env python3
"""
Organiza la base: agrega COD_DANE al municipio y estandariza los nombres
contra la hoja Municipios.

Uso:
    python normalizar.py
    python normalizar.py --entrada datos/otra.xlsx --salida salida/limpia.xlsx

Deja un Excel con las mismas hojas y filas de la fuente, más la llave
COD_DANE_MPIO, los nombres de municipio canónicos y tres hojas de control.
"""
import argparse
import sys
from pathlib import Path

from src import config as cfg
from src.normalizar import normalizar_sabana


def main() -> int:
    ap = argparse.ArgumentParser(description="Normaliza la sábana única del visor.")
    ap.add_argument("--entrada", type=Path, default=cfg.ARCHIVO_SABANA)
    ap.add_argument("--salida", type=Path,
                    default=cfg.DIR_SALIDA / "sabana_normalizada.xlsx")
    args = ap.parse_args()

    if not args.entrada.exists():
        print(f"  No se encontró: {args.entrada}", file=sys.stderr)
        return 1

    print(f"Normalizando {args.entrada.name} ...")
    destino, norm = normalizar_sabana(args.entrada, args.salida)

    print(f"\n{'Hoja':<30}{'Filas':>7}{'Con DANE':>10}{'Sin cruce':>11}"
          f"{'Renombrados':>13}{'Sub/EAT':>9}")
    print("-" * 80)
    for r in norm.resumen:
        print(f"{r['Hoja']:<30}{r['Filas']:>7}{r['Con COD_DANE_MPIO']:>10}"
              f"{r['Sin cruce']:>11}{r['Municipios renombrados']:>13}"
              f"{r['Subregión / EAT corregidas']:>9}")

    sin_cruce = sum(r["Sin cruce"] for r in norm.resumen)
    total = sum(r["Filas"] for r in norm.resumen)
    print("-" * 80)
    print(f"{'TOTAL':<30}{total:>7}{total - sin_cruce:>10}{sin_cruce:>11}")
    print(f"\n{len(norm.cambios)} tipos de corrección aplicados "
          f"(ver hoja CAMBIOS APLICADOS).")
    if sin_cruce:
        print(f"  ATENCIÓN: {sin_cruce} fila(s) sin cruce contra el maestro. "
              f"Revise la hoja CONTROL DE CAMBIOS.")
    print(f"\n  {destino}  ({destino.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
