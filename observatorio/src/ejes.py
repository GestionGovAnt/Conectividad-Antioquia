"""
Los cuatro ejes de conectividad y las capas de puntos del mapa.

Cada eje responde lo mismo en su sector: cuántos puntos hay, cuántos están
conectados y dónde quedan. La unidad de cada eje es además el repartidor de
la inversión departamental (ver inversion.py).
"""
from __future__ import annotations

import pandas as pd

from . import config as cfg
from .loader import Sabana


def _frac(parte, total):
    return float(parte) / float(total) if total else None


def _reparto(serie: pd.Series, orden=None) -> list[dict]:
    conteo = serie.value_counts()
    total = int(conteo.sum())
    claves = orden or list(conteo.index)
    return [
        {"nombre": k, "total": int(conteo.get(k, 0)),
         "part": _frac(conteo.get(k, 0), total)}
        for k in claves if int(conteo.get(k, 0)) > 0
    ]


# ==========================================================================
# Ejes
# ==========================================================================
def eje_educacion(sab: Sabana, codigos: set[str]) -> dict:
    sedes = sab.hoja("sedes")
    sedes = sedes[sedes["cod"].isin(codigos)]
    total = len(sedes)
    conectadas = int(sedes["conectada"].sum()) if total else 0
    # Una institución agrupa varias sedes: la principal y las rurales que
    # dependen de ella. Se reportan las dos cifras porque responden a
    # preguntas distintas.
    instituciones = (int(sedes["CODIGO ESTABLECIMIENTO"].nunique())
                     if total else 0)
    return {
        "unidades": conectadas,
        "universo": total,
        "cobertura": _frac(conectadas, total),
        "pendientes": total - conectadas,
        "detalle": {
            "Instituciones educativas": instituciones,
            "Sedes educativas": total,
            "Con tecnología": conectadas,
            "Sin dato de conexión": total - conectadas,
            "Sin georreferenciar": int(sedes["latitud"].isna().sum()) if total else 0,
        },
        "repartos": [
            {"titulo": "Zona de la sede", "filas": _reparto(
                sedes["zona"], ["Rural", "Urbana", cfg.ZONA_SIN_DATO]) if total else []},
            {"titulo": "Programa", "filas": _reparto(sedes["programa"]) if total else []},
            {"titulo": "Tecnología de conexión", "filas": _reparto(
                sedes["tecnologia"], list(cfg.TECNOLOGIAS.values())) if total else []},
        ],
    }


def eje_salud(sab: Sabana, codigos: set[str]) -> dict:
    salud = sab.hoja("salud")
    salud = salud[salud["cod"].isin(codigos)]
    total = len(salud)
    if not total:
        return {"unidades": 0, "universo": 0, "cobertura": None, "pendientes": 0,
                "detalle": {}, "repartos": []}
    tokens = salud["equipos"].fillna("").astype(str).apply(
        lambda v: {t.strip().upper() for t in v.split(",")})
    fijo = tokens.apply(lambda c: cfg.EQUIPOS_SALUD["kit_fijo"] in c)
    itin = tokens.apply(lambda c: cfg.EQUIPOS_SALUD["kit_itinerante"] in c)
    con_kit = int((fijo | itin).sum())
    tipos = salud["tipo_punto"].astype(str).str.strip().str.title()
    return {
        "unidades": total,
        "universo": total,
        "cobertura": _frac(con_kit, total),
        "pendientes": total - con_kit,
        "detalle": {
            "Puntos conectados": total,
            "Con kit satelital fijo": int(fijo.sum()),
            "Con unidad itinerante": int(itin.sum()),
            "Sin kit satelital": total - con_kit,
        },
        "repartos": [
            {"titulo": "Dotación entregada", "filas": [
                {"nombre": "Kit satelital fijo", "total": int(fijo.sum()),
                 "part": _frac(fijo.sum(), total)},
                {"nombre": "Unidad itinerante", "total": int(itin.sum()),
                 "part": _frac(itin.sum(), total)},
                {"nombre": "Sin kit satelital", "total": total - con_kit,
                 "part": _frac(total - con_kit, total)},
            ]},
            {"titulo": "Tipo de punto", "filas": _reparto(tipos)},
        ],
    }


def eje_seguridad(sab: Sabana, codigos: set[str]) -> dict:
    """Entornos educativos seguros y proyecto de fibra óptica.

    La fibra vive en este eje por decisión de la Dirección: el proyecto se
    formuló como infraestructura de seguridad territorial.
    """
    seg = sab.hoja("seguridad")
    tipo = seg["Punto"].astype(str).str.strip()
    entornos = seg[(tipo != "PROYECTO FIBRA ÓPTICA") & seg["cod"].isin(codigos)]
    fibra = seg[(tipo == "PROYECTO FIBRA ÓPTICA") & seg["cod"].isin(codigos)]

    metros_reportados = pd.to_numeric(fibra["observacion"], errors="coerce")
    total = len(entornos)
    kmz = getattr(sab, "fibra_kmz", None) or {}
    metros_kmz = int(sum(v for c, v in kmz.items() if c in codigos))

    detalle = {
        "Entornos intervenidos": total,
        "Municipios intervenidos": int(entornos["cod"].nunique()),
        "Municipios en proyecto de fibra": int(fibra["cod"].nunique()),
        "Metros de fibra reportados": int(metros_reportados.sum()),
    }
    if kmz:
        detalle["Metros medidos en el KMZ"] = metros_kmz
    detalle["Sin coordenadas"] = int(entornos["latitud"].isna().sum())

    return {
        "unidades": total + int(fibra["cod"].nunique()),
        "universo": total,
        "cobertura": None,
        "pendientes": int(metros_reportados.isna().sum()),
        "detalle": detalle,
        "repartos": [],
    }


def eje_tic(sab: Sabana, codigos: set[str]) -> dict:
    consolidados = sab.hoja("consolidados")
    territorial = sab.hoja("territorial")

    dc = consolidados[(consolidados["Punto"] == "DATACENTER")
                      & consolidados["cod"].isin(codigos)]
    obs = dc["observacion"].astype(str).str.strip()
    gob = set(dc.loc[obs == "GOBERNACIÓN", "cod"])
    propio = set(dc.loc[obs == "PROPIO", "cod"])

    wifi = pd.concat([
        territorial[territorial["Punto"].astype(str).str.strip() == "ZONAS WIFI"],
        consolidados[consolidados["Punto"] == "ZONAS WIFI"],
    ]).drop_duplicates(subset=["cod", "latitud", "longitud"])
    wifi = wifi[wifi["cod"].isin(codigos)]

    apro = sab.hoja("apropiacion")
    apro = apro[apro["cod"].isin(codigos)]
    personas = int(
        pd.to_numeric(apro["COMUNIDAD"], errors="coerce").fillna(0).sum()
        + pd.to_numeric(apro["FUNCIONARIOS"], errors="coerce").fillna(0).sum()
    )
    cap = sab.hoja("capacitaciones")
    cap = cap[cap["cod"].isin(codigos)]

    peti = sab.hoja("peti")
    peti = peti[peti["cod"].isin(codigos)]
    con_peti = int((peti["estado_peti"] == "SI").sum())

    datacenters = len((gob | propio) & codigos)
    unidades = datacenters + len(wifi)
    return {
        "unidades": unidades,
        "universo": len(codigos),
        "cobertura": _frac(con_peti, len(peti)) if len(peti) else None,
        "pendientes": len(peti) - con_peti,
        "detalle": {
            "DataCenter": datacenters,
            "Puntos de conectividad": int(len(wifi)),
            "Personas formadas": personas,
            "Personas capacitadas": int(len(cap)),
            "Municipios con PETI": con_peti,
        },
        "repartos": [
            {"titulo": "Estado del PETI", "filas": _reparto(
                peti["estado_peti"].map(cfg.ETIQUETA_ESTADO))} if len(peti) else
            {"titulo": "Estado del PETI", "filas": []},
            {"titulo": "Estado del PAMUDA", "filas": _reparto(
                peti["estado_pamuda"].map(cfg.ETIQUETA_ESTADO))} if len(peti) else
            {"titulo": "Estado del PAMUDA", "filas": []},
        ],
    }


CALCULO = {
    "educacion": eje_educacion,
    "salud": eje_salud,
    "seguridad": eje_seguridad,
    "tic": eje_tic,
}


def calcular(sab: Sabana, codigos: set[str]) -> dict:
    return {eje: CALCULO[eje](sab, codigos) for eje in cfg.IDS_EJES}


# ==========================================================================
# Capas de puntos
# ==========================================================================
def _proyectar(lat: pd.Series, lon: pd.Series) -> pd.DataFrame:
    p = cfg.PROYECCION
    return pd.DataFrame({
        "x": (lon * p["ax"] + p["bx"]).round(1),
        "y": (lat * p["ay"] + p["by"]).round(1),
    })


def _filtro_capa(capa: dict, df: pd.DataFrame) -> pd.DataFrame:
    if capa["id"] == "entornos":
        return df[df["Punto"].astype(str).str.strip() != "PROYECTO FIBRA ÓPTICA"]
    if capa["id"] == "wifi":
        return df[df["Punto"].astype(str).str.strip() == "ZONAS WIFI"]
    if capa["id"] == "datacenter":
        return df[df["Punto"].astype(str).str.strip() == "DATACENTER"]
    return df


def capas(sab: Sabana) -> list[dict]:
    """Puntos georreferenciados listos para dibujar sobre el lienzo SVG."""
    salida = []
    for capa in cfg.CAPAS:
        df = _filtro_capa(capa, sab.hoja(capa["hoja"]))
        lat = pd.to_numeric(df["latitud"], errors="coerce")
        lon = pd.to_numeric(df["longitud"], errors="coerce")
        valida = (lat.between(cfg.BBOX["lat_min"], cfg.BBOX["lat_max"])
                  & lon.between(cfg.BBOX["lon_min"], cfg.BBOX["lon_max"])
                  & df["cod"].notna())
        proy = _proyectar(lat[valida], lon[valida])
        puntos = [[fila.x, fila.y, cod] for fila, cod
                  in zip(proy.itertuples(), df.loc[valida, "cod"])]
        salida.append({
            "id": capa["id"], "eje": capa["eje"], "nombre": capa["nombre"],
            "radio": capa["radio"], "total": int(len(df)),
            "georreferenciados": int(valida.sum()),
            "sin_coordenada": int(len(df) - valida.sum()),
            "puntos": puntos,
        })
    return salida
