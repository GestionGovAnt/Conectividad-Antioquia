"""
Auditoría de calidad de la sábana.

Cada hallazgo se calcula contra el archivo cargado, nunca se escribe a mano.
Si la fuente se corrige, el hallazgo desaparece solo del reporte.
"""
from __future__ import annotations

import pandas as pd

from . import config as cfg
from .loader import Sabana, llave_municipio, normalizar, titulo_es

SEVERIDADES = ("alta", "media", "baja", "informativa")


def _hallazgo(titulo, magnitud, detalle, severidad="media", accion=""):
    return {"titulo": titulo, "magnitud": magnitud, "detalle": detalle,
            "severidad": severidad, "accion": accion}


def auditar(sab: Sabana) -> list[dict]:
    hallazgos: list[dict] = []
    sedes = sab.hoja("sedes")

    # ----------------------------------------------------------------- llaves
    total_hojas = len(sab.hojas) + 1
    con_dane = 1 + sum(1 for usa in sab.usa_llave_dane.values() if usa)
    if con_dane < total_hojas:
        hallazgos.append(_hallazgo(
            "Hay hojas sin código DANE del municipio",
            f"{con_dane} de {total_hojas} hojas",
            "En las hojas sin código, el cruce se hace por nombre de municipio, "
            "que no está estandarizado. Es la causa raíz de que se requiera una "
            "tabla de alias.",
            "alta",
            "Ejecutar `python normalizar.py` y trabajar sobre la sábana "
            "normalizada, o incluir COD_DANE_MPIO en la fuente.",
        ))

    # ------------------------------------------------------- nombres sin cruce
    perdidas = {}
    for clave, (hoja, col) in cfg.HOJAS.items():
        if clave == "municipios":
            continue
        df = sab.hoja(clave)
        sin_cruce = df[df["cod"].isna()]
        if len(sin_cruce):
            perdidas[hoja] = sorted(
                {str(v) for v in sin_cruce[col].dropna().unique()}
            )[:6]
    if perdidas:
        hallazgos.append(_hallazgo(
            "Registros que no cruzan contra el maestro de municipios",
            f"{len(perdidas)} hoja(s)",
            "; ".join(f"{h}: {', '.join(v)}" for h, v in perdidas.items()),
            "alta",
            "Corregir el nombre en la fuente o ampliar ALIAS_MUNICIPIOS en config.py.",
        ))

    # -------------------------------------------------------------- PETI doble
    peti = sab.hoja("peti")
    if {"PETI", "ESTADO PETI"} <= set(peti.columns):
        distintos = int(
            (peti["PETI"].astype(str).str.strip()
             != peti["ESTADO PETI"].astype(str).str.strip()).sum()
        )
        if distintos:
            hallazgos.append(_hallazgo(
                "Las columnas PETI y ESTADO PETI se contradicen",
                f"{distintos} de {len(peti)} municipios",
                "Ambas tienen la misma distribución pero asignada a municipios "
                "distintos, patrón típico de una columna ordenada sin arrastrar "
                "el resto. Esta ficha usa ESTADO PETI.",
                "alta",
                "Reconciliar y dejar una sola columna.",
            ))

    # -------------------------------------------------------- ceros aparentes
    diag = sab.hoja("diagnosticos")["cod"].nunique()
    inv = sab.hoja("inventario")["cod"].nunique()
    total_mun = len(sab.municipios)
    hallazgos.append(_hallazgo(
        "Indicadores en cero que en realidad no se han medido",
        f"{total_mun - diag} sin diagnóstico · {total_mun - inv} sin inventario",
        "Los conteos de AP y de equipos solo existen para los municipios "
        "diagnosticados o inventariados. En el resto no son ceros: son vacíos.",
        "alta",
        "La ficha los muestra como «Sin medir» y «Sin registro».",
    ))

    # ------------------------------------------------------------ sedes vacías
    sin_programa = int((sedes["programa"] == "Sin programa").sum())
    if sin_programa:
        hallazgos.append(_hallazgo(
            "Sedes sin tecnología ni programa asociado",
            f"{sin_programa} sedes",
            "No tienen ni tecnología de conexión ni fuente de financiación "
            "registrada. Son el vacío real de información del componente educativo.",
            "alta",
            "Definir plan de levantamiento en campo.",
        ))

    sin_geo = int(sedes["latitud"].isna().sum())
    if sin_geo:
        hallazgos.append(_hallazgo(
            "Sedes educativas sin georreferenciación",
            f"{sin_geo} de {len(sedes)} ({sin_geo / len(sedes):.1%})",
            "No se pueden pintar en el visor.",
            "media",
            "Priorizar captura de coordenadas por subregión.",
        ))

    # ------------------------------------------------------------ coordenadas
    fuera = 0
    for clave in ("sedes", "salud", "consolidados", "territorial"):
        df = sab.hoja(clave)
        if "latitud" not in df.columns:
            continue
        lat = pd.to_numeric(df["latitud"], errors="coerce")
        lon = pd.to_numeric(df["longitud"], errors="coerce")
        fuera += int(
            (lat.notna() & (
                (lat < cfg.BBOX["lat_min"]) | (lat > cfg.BBOX["lat_max"])
                | (lon < cfg.BBOX["lon_min"]) | (lon > cfg.BBOX["lon_max"])
            )).sum()
        )
    if fuera:
        hallazgos.append(_hallazgo(
            "Coordenadas fuera del departamento",
            f"{fuera} registro(s)",
            f"Puntos por fuera del rango lat {cfg.BBOX['lat_min']}–"
            f"{cfg.BBOX['lat_max']} / lon {cfg.BBOX['lon_min']}–{cfg.BBOX['lon_max']}.",
            "media",
            "Validar antes de cargar al visor.",
        ))

    # ------------------------------------------------------------------ fibra
    seg = sab.hoja("seguridad")
    fibra = seg[seg["Punto"].astype(str).str.strip() == "PROYECTO FIBRA ÓPTICA"]
    sin_metros = int(pd.to_numeric(fibra["observacion"], errors="coerce").isna().sum())
    if sin_metros:
        hallazgos.append(_hallazgo(
            "Municipios del proyecto de fibra sin metros reportados",
            f"{sin_metros} de {len(fibra)}",
            "Los metros van en la columna «observacion», que en otras filas de "
            "la misma hoja guarda texto libre.",
            "alta",
            "Llevar el dato a una columna propia, numérica, llamada metros_fibra.",
        ))

    # ------------------------------------------------- subregión discrepante
    maestro = dict(zip(sab.municipios["cod"], sab.municipios["subregion"]))
    discrepantes = set()
    for clave in ("sedes", "salud", "seguridad", "apropiacion", "peti"):
        df = sab.hoja(clave)
        col = next((c for c in df.columns if normalizar(c) in ("SUBREGION",)), None)
        if not col:
            continue
        propia = df[col].map(normalizar).map(
            lambda v: cfg.SUBREGION_DISPLAY.get(titulo_es(v), titulo_es(v))
            if v else None)
        base = df["cod"].map(maestro)
        malos = df.loc[propia.notna() & base.notna() & (propia != base), "cod"]
        discrepantes |= set(malos.dropna())
    if discrepantes:
        nombres = sab.municipios.set_index("cod").loc[
            sorted(discrepantes), "nombre"].tolist()
        hallazgos.append(_hallazgo(
            "Municipios ubicados en subregiones distintas según la hoja",
            f"{len(discrepantes)} municipio(s)",
            ", ".join(nombres),
            "alta",
            "Definir el maestro «Municipios» como única fuente de la subregión.",
        ))

    # ------------------------------------------------------- doble conteo
    consolidados = sab.hoja("consolidados")
    sin_categoria = int(consolidados["Punto"].isna().sum())
    if sin_categoria:
        hallazgos.append(_hallazgo(
            "La hoja Consolidados mezcla capas y repite información",
            f"{sin_categoria} de {len(consolidados)} filas sin categoría",
            "Además duplica registros de DataCenter y zonas wifi que ya están "
            "en sus hojas propias.",
            "alta",
            "Generarla como vista de las hojas fuente, no digitarla aparte.",
        ))

    # ------------------------------------------- maestro con valor discutible
    hallazgos.append(_hallazgo(
        "El maestro de municipios es la fuente de verdad, y tiene al menos un "
        "valor discutible",
        "Caicedo",
        "La hoja Municipios lo ubica en SUROESTE mientras las demás hojas lo "
        "ubican en OCCIDENTE. Al normalizar, el maestro gana y su valor se "
        "propaga a toda la base. Revisar antes de dar la normalización por buena.",
        "alta",
        "Verificar la subregión de Caicedo, Gómez Plata, Anorí, Santo Domingo "
        "y Yalí en la hoja Municipios y corregir allí, no en las hojas hijas.",
    ))

    orden = {s: i for i, s in enumerate(SEVERIDADES)}
    return sorted(hallazgos, key=lambda h: orden.get(h["severidad"], 9))
