#!/usr/bin/env python3
"""
Arma la carpeta `sitio/` lista para publicar.

Uso:
    python publicar.py
    python publicar.py --ficha ../proyecto     # también construye la ficha

Qué hace:
  1. Construye el observatorio (y la sábana se descarga de SharePoint si hay
     credenciales configuradas).
  2. Construye la ficha municipal, si se indica dónde está ese proyecto.
  3. Copia todo a `sitio/` con los nombres que esperan los enlaces internos.

El resultado es un sitio estático: archivos sueltos que cualquier hosting
sirve sin servidor de aplicación, sin base de datos y sin backend.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SITIO = RAIZ / "sitio"


def correr(comando: list[str], cwd: Path) -> None:
    print("  $", " ".join(str(c) for c in comando))
    resultado = subprocess.run(comando, cwd=cwd)
    if resultado.returncode != 0:
        raise SystemExit(f"Falló: {' '.join(str(c) for c in comando)}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Arma el sitio publicable.")
    ap.add_argument("--ficha", type=Path,
                    help="Carpeta del proyecto de la ficha municipal.")
    ap.add_argument("--sharepoint", choices=("graph", "enlace"),
                    help="Descargar la sábana de SharePoint antes de construir.")
    args = ap.parse_args()

    print("Construyendo el observatorio ...")
    comando = [sys.executable, "build.py"]
    if args.sharepoint:
        comando += ["--sharepoint", args.sharepoint]
    correr(comando, RAIZ)

    if SITIO.exists():
        shutil.rmtree(SITIO)
    SITIO.mkdir(parents=True)

    observatorio = RAIZ / "salida" / "observatorio_conectividad.html"
    respaldo = RAIZ / "salida" / "observatorio_sin_internet.html"

    # index.html y el nombre propio apuntan al mismo contenido: así funcionan
    # tanto la raíz del sitio como los enlaces que vienen de la ficha.
    shutil.copy(observatorio, SITIO / "index.html")
    shutil.copy(observatorio, SITIO / "observatorio_conectividad.html")
    if respaldo.exists():
        shutil.copy(respaldo, SITIO / "observatorio_sin_internet.html")

    if args.ficha:
        carpeta = args.ficha.resolve()
        # La ficha se construye con la MISMA sábana del observatorio, que es
        # la normalizada. Así las dos publicaciones no pueden divergir.
        sabana = RAIZ / "datos" / "sabana_unica_visor.xlsx"
        print("Construyendo la ficha municipal ...")
        comando = [sys.executable, "build.py"]
        if sabana.exists():
            comando += ["--sabana", str(sabana)]
        correr(comando, carpeta)
        ficha = carpeta / "salida" / "ficha_tic_antioquia.html"
        if ficha.exists():
            shutil.copy(ficha, SITIO / "ficha_tic_antioquia.html")
        else:
            print("  aviso: no se encontró la ficha generada")

    # GitHub Pages ignora las carpetas que empiezan por guion bajo si no se
    # desactiva Jekyll. Este archivo vacío lo desactiva.
    (SITIO / ".nojekyll").write_text("", encoding="utf-8")

    print("\nSitio listo en", SITIO)
    for archivo in sorted(SITIO.iterdir()):
        if archivo.name.startswith("."):
            continue
        print(f"  {archivo.name:<36} {archivo.stat().st_size/1024:>7.0f} KB")
    print("\nPara probarlo sin publicar:")
    print("  python -m http.server 8000 --directory sitio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
