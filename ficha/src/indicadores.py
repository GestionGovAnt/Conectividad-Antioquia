"""
Cálculo de indicadores por municipio y por agregado territorial.

Convención de participación
---------------------------
Cada desglose (programas, tecnologías, tipos de punto) reporta el TOTAL
absoluto y su participación sobre el total del ámbito. Si un municipio tiene
60 sedes y 20 son de la Gobernación, la barra de esa fila marca 33 %.
Ese es el reparto del universo, no el avance interno del programa.

El avance interno se reporta aparte, en las columnas de conectadas y sin dato.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as cfg
from .loader import Sabana


def _fraccion(parte: float, total: float):
    return float(parte) / float(total) if total else None


def _desglose(serie: pd.Series, orden: list[str] | None = None,
              solo_con_datos: bool = True) -> list[dict]:
    """Conteo por categoría con participación sobre el total."""
    conteo = serie.value_counts()
    total = int(conteo.sum())
    claves = orden or list(conteo.index)
    filas = []
    for clave in claves:
        valor = int(conteo.get(clave, 0))
        if solo_con_datos and valor == 0:
            continue
        filas.append({"nombre": clave, "total": valor,
                      "part": _fraccion(valor, total)})
    return filas


# ==========================================================================
# Componentes
# ==========================================================================
def componente_educacion(sedes: pd.DataFrame) -> dict:
    total = len(sedes)
    conectadas = int(sedes["conectada"].sum()) if total else 0

    def bloque(columna: str, orden: list[str] | None) -> list[dict]:
        filas = []
        grupos = sedes.groupby(columna) if total else []
        vistos = {nombre: grupo for nombre, grupo in grupos}
        claves = orden or sorted(vistos)
        for clave in claves:
            grupo = vistos.get(clave)
            if grupo is None or not len(grupo):
                continue
            n = len(grupo)
            con = int(grupo["conectada"].sum())
            filas.append({
                "nombre": clave, "total": n, "part": _fraccion(n, total),
                "conectadas": con, "sin_dato": n - con,
                "avance": _fraccion(con, n),
            })
        return filas

    subprogramas = list(cfg.SUBPROGRAMAS.values()) + [cfg.SUBPROGRAMA_OTROS]
    return {
        "total": total,
        "conectadas": conectadas,
        "sin_dato": total - conectadas,
        "avance": _fraccion(conectadas, total),
        "sin_geo": int(sedes["latitud"].isna().sum()) if total else 0,
        "establecimientos": int(sedes["CODIGO ESTABLECIMIENTO"].nunique()) if total else 0,
        "programas": bloque("programa", cfg.PROGRAMAS),
        "subprogramas": bloque("subprograma", subprogramas),
        "zonas": bloque("zona", ["Rural", "Urbana", cfg.ZONA_SIN_DATO]),
        "tecnologias": _desglose(sedes["tecnologia"], cfg.ORDEN_TECNOLOGIAS) if total else [],
    }


def componente_infraestructura(sab: Sabana, codigos: set[str]) -> dict:
    consolidados = sab.hoja("consolidados")
    territorial = sab.hoja("territorial")
    diagnosticos = sab.hoja("diagnosticos")
    inventario = sab.hoja("inventario")

    dc = consolidados[(consolidados["Punto"] == "DATACENTER")
                      & consolidados["cod"].isin(codigos)]
    observacion = dc["observacion"].astype(str).str.strip()
    gobernacion = set(dc.loc[observacion == "GOBERNACIÓN", "cod"])
    propios = set(dc.loc[observacion == "PROPIO", "cod"])

    wifi = pd.concat([
        territorial[territorial["Punto"].astype(str).str.strip() == "ZONAS WIFI"],
        consolidados[consolidados["Punto"] == "ZONAS WIFI"],
    ]).drop_duplicates(subset=["cod", "latitud", "longitud"])
    wifi = wifi[wifi["cod"].isin(codigos)]

    diag = diagnosticos[diagnosticos["cod"].isin(codigos)]
    col = {c.lower(): c for c in diag.columns}

    def suma(fragmento: str) -> int:
        for texto, nombre in col.items():
            if fragmento in texto:
                return int(pd.to_numeric(diag[nombre], errors="coerce").sum())
        return 0

    inv = inventario[inventario["cod"].isin(codigos)]
    # El inventario reporta CANTIDAD por tipo de dispositivo. El total es una
    # SUMATORIA de unidades heterogéneas: un DataCenter completo pesa igual
    # que un inyector PoE. Por eso la ficha lo rotula como suma y siempre
    # muestra el desglose al lado.
    equipos = inv.groupby(inv["DISPOSITIVO"].astype(str).str.strip())["CANTIDAD"].sum()
    equipos = equipos[equipos > 0].sort_values(ascending=False)
    total_equipos = int(equipos.sum())

    return {
        "datacenter_gobernacion": len(gobernacion & codigos),
        "datacenter_propio": len(propios & codigos),
        "datacenter_total": len((gobernacion | propios) & codigos),
        "diagnosticados": int(diag["cod"].nunique()),
        "con_inventario": int(inv["cod"].nunique()),
        "zonas_wifi": int(len(wifi)),
        "municipios_wifi": int(wifi["cod"].nunique()),
        "ap_internos": suma("ap internos"),
        "ap_externos": suma("ap externos"),
        "ap_sin_funcionar": suma("sin funcionamiento"),
        "equipos_total": total_equipos,
        "equipos_tipos": int(len(equipos)),
        "equipos": [
            {"nombre": nombre, "total": int(valor),
             "part": _fraccion(valor, total_equipos)}
            for nombre, valor in equipos.items()
        ],
    }


def componente_fibra(sab: Sabana, codigos: set[str]) -> dict:
    seg = sab.hoja("seguridad")
    fibra = seg[(seg["Punto"].astype(str).str.strip() == "PROYECTO FIBRA ÓPTICA")
                & seg["cod"].isin(codigos)]
    metros = pd.to_numeric(fibra["observacion"], errors="coerce")
    return {
        "municipios": int(fibra["cod"].nunique()),
        "metros": int(metros.sum()),
        "sin_metros": int(metros.isna().sum()),
        "sin_coordenadas": int(fibra["latitud"].isna().sum()),
    }


def componente_seguridad(sab: Sabana, codigos: set[str]) -> dict:
    seg = sab.hoja("seguridad")
    camaras = seg[(seg["Punto"].astype(str).str.strip() != "PROYECTO FIBRA ÓPTICA")
                  & seg["cod"].isin(codigos)]
    return {
        "puntos": int(len(camaras)),
        "municipios": int(camaras["cod"].nunique()),
        "sin_coordenadas": int(camaras["latitud"].isna().sum()),
    }


def componente_salud(sab: Sabana, codigos: set[str]) -> dict:
    salud = sab.hoja("salud")
    salud = salud[salud["cod"].isin(codigos)]

    # El campo `equipos` es una lista separada por comas. Se compara token a
    # token: buscar la subcadena "STARLINK" mezclaba el kit fijo con la antena
    # Mini de la unidad itinerante y contaba dos dotaciones como una sola.
    if salud.empty:
        return {"puntos": 0, "municipios": 0, "kit_fijo": 0, "kit_itinerante": 0,
                "starlink_mini": 0, "ambos_kits": 0, "sin_kit": 0,
                "instituciones": 0, "tipos": [], "dotacion": []}

    tokens = salud["equipos"].fillna("").astype(str).apply(
        lambda v: {t.strip().upper() for t in v.split(",")}
    )

    def tiene(clave: str) -> pd.Series:
        marca = cfg.EQUIPOS_SALUD[clave]
        return tokens.apply(lambda conjunto: marca in conjunto).astype(bool)

    fijo = tiene("kit_fijo")
    itinerante = tiene("kit_itinerante")
    mini = tiene("starlink_mini")
    tipos = salud["tipo_punto"].astype(str).str.strip().str.title()

    return {
        "puntos": int(len(salud)),
        "municipios": int(salud["cod"].nunique()),
        "kit_fijo": int(fijo.sum()),
        "kit_itinerante": int(itinerante.sum()),
        "starlink_mini": int(mini.sum()),
        "ambos_kits": int((fijo & itinerante).sum()),
        "sin_kit": int((~fijo & ~itinerante).sum()),
        "instituciones": int(salud["hospital"].astype(str).str.strip().nunique()),
        "tipos": _desglose(tipos),
        "dotacion": [
            {"nombre": "Kit satelital fijo", "total": int(fijo.sum()),
             "part": _fraccion(int(fijo.sum()), len(salud))},
            {"nombre": "Unidad itinerante", "total": int(itinerante.sum()),
             "part": _fraccion(int(itinerante.sum()), len(salud))},
            {"nombre": "Antena Starlink Mini", "total": int(mini.sum()),
             "part": _fraccion(int(mini.sum()), len(salud))},
            {"nombre": "Sin kit satelital", "total": int((~fijo & ~itinerante).sum()),
             "part": _fraccion(int((~fijo & ~itinerante).sum()), len(salud))},
        ],
    }


def componente_gobierno(peti: pd.DataFrame) -> dict:
    if peti.empty:
        return {"estado_peti": "Sin dato", "estado_pamuda": "Sin dato",
                "madurez": "Sin ficha"}
    fila = peti.iloc[0]
    return {
        "estado_peti": fila["estado_peti"],
        "estado_pamuda": fila["estado_pamuda"],
        "madurez": fila["madurez"],
    }


def componente_gobierno_agregado(peti: pd.DataFrame) -> dict:
    return {
        "peti": _desglose(peti["estado_peti"], list(cfg.PUNTAJE_ESTADO)),
        "pamuda": _desglose(peti["estado_pamuda"], list(cfg.PUNTAJE_ESTADO)),
        "madurez": _desglose(peti["madurez"]),
    }


def componente_apropiacion(sab: Sabana, codigos: set[str]) -> dict:
    apro = sab.hoja("apropiacion")
    apro = apro[apro["cod"].isin(codigos)]
    cap = sab.hoja("capacitaciones")
    cap = cap[cap["cod"].isin(codigos)]

    comunidad = int(pd.to_numeric(apro["COMUNIDAD"], errors="coerce").sum())
    funcionarios = int(pd.to_numeric(apro["FUNCIONARIOS"], errors="coerce").sum())
    sesiones = int(pd.to_numeric(cap["Cantidad_Sesiones"], errors="coerce").sum())

    def texto(df: pd.DataFrame, columna: str) -> pd.Series:
        return df[columna].astype(str).str.strip().str.title()

    # Personas alcanzadas por curso: mide alcance, no número de actividades.
    cursos = []
    if not apro.empty:
        base = apro.assign(
            curso=texto(apro, "NOMBRE CURSO"),
            personas=pd.to_numeric(apro["COMUNIDAD"], errors="coerce").fillna(0)
            + pd.to_numeric(apro["FUNCIONARIOS"], errors="coerce").fillna(0),
        )
        agrupado = base.groupby("curso")["personas"].sum().sort_values(ascending=False)
        total_personas = float(agrupado.sum())
        cursos = [
            {"nombre": nombre, "total": int(valor),
             "part": _fraccion(valor, total_personas)}
            for nombre, valor in agrupado.items() if valor > 0
        ]

    return {
        "actividades": int(len(apro)),
        "comunidad": comunidad,
        "funcionarios": funcionarios,
        "personas": comunidad + funcionarios,
        "tipos": _desglose(texto(apro, "TIPO DE FORMACIÓN")) if len(apro) else [],
        "modalidades": _desglose(texto(apro, "MODALIDAD")) if len(apro) else [],
        "cursos": cursos,
        "acompanados": int(len(cap)),
        "sesiones": sesiones,
        "promedio_sesiones": _fraccion(sesiones, len(cap)),
        "generos": _desglose(texto(cap, "Genero")) if len(cap) else [],
        "tipos_acompanamiento": _desglose(texto(cap, "Tipo")) if len(cap) else [],
        "cargos": _desglose(texto(cap, "Cargo"))[:10] if len(cap) else [],
    }


# ==========================================================================
# Ejes e índice
# ==========================================================================
def calcular_ejes(datos: dict, certificado: bool) -> dict:
    edu = datos["educacion"]
    e1 = None if certificado or edu["total"] == 0 else edu["avance"]
    infra = datos["infraestructura"]
    e2 = (0.5 if infra["datacenter_total"] else 0.0) + \
         (0.5 if infra["zonas_wifi"] else 0.0)
    return {
        "E1": e1,
        "E2": e2,
        "E3": 1.0 if datos["fibra"]["municipios"] else 0.0,
        "E4": 1.0 if datos["seguridad"]["puntos"] else 0.0,
        "E5": 1.0 if datos["salud"]["puntos"] else 0.0,
        "E6": cfg.PUNTAJE_ESTADO.get(datos["gobierno"]["estado_peti"], 0.0),
        "E7": cfg.PUNTAJE_ESTADO.get(datos["gobierno"]["estado_pamuda"], 0.0),
    }


def indice(ejes: dict) -> float:
    """Promedio simple de los ejes aplicables.

    Para ponderar distinto, cambie esta función: es el único punto donde los
    ejes se combinan en una sola cifra.
    """
    valores = [v for v in ejes.values() if v is not None]
    return float(np.mean(valores)) if valores else 0.0


# ==========================================================================
# Construcción
# ==========================================================================
def _paquete(sab: Sabana, codigos: set[str]) -> dict:
    sedes = sab.hoja("sedes")
    return {
        "educacion": componente_educacion(sedes[sedes["cod"].isin(codigos)]),
        "infraestructura": componente_infraestructura(sab, codigos),
        "fibra": componente_fibra(sab, codigos),
        "seguridad": componente_seguridad(sab, codigos),
        "salud": componente_salud(sab, codigos),
        "apropiacion": componente_apropiacion(sab, codigos),
    }


def construir(sab: Sabana) -> dict:
    peti = sab.hoja("peti")
    municipios = []

    for _, fila in sab.municipios.iterrows():
        cod = fila["cod"]
        datos = _paquete(sab, {cod})
        datos["gobierno"] = componente_gobierno(peti[peti["cod"] == cod])
        # Municipios certificados en educación: no dependen de la Secretaría
        # departamental, por eso no tienen sedes en la base.
        certificado = fila["nombre"] in {
            "Medellín", "Bello", "Itagüí", "Envigado", "Sabaneta",
            "La Estrella", "Rionegro", "Apartadó", "Turbo",
        }
        datos["ejes"] = calcular_ejes(datos, certificado)
        datos["indice"] = indice(datos["ejes"])
        datos.update({
            "cod": cod, "nombre": fila["nombre"],
            "subregion": fila["subregion"], "eat": fila["eat"],
            "certificado": certificado,
        })
        municipios.append(datos)

    def agregado(seleccion: pd.DataFrame) -> dict:
        codigos = set(seleccion["cod"])
        datos = _paquete(sab, codigos)
        datos["gobierno"] = componente_gobierno_agregado(peti[peti["cod"].isin(codigos)])
        indices = [m["indice"] for m in municipios if m["cod"] in codigos]
        datos["indice"] = float(np.mean(indices)) if indices else 0.0
        datos["municipios"] = len(codigos)
        return datos

    subregiones = {
        nombre: agregado(grupo)
        for nombre, grupo in sab.municipios.groupby("subregion")
    }
    eats = {
        nombre: agregado(grupo)
        for nombre, grupo in sab.municipios.groupby("eat")
    }
    departamento = agregado(sab.municipios)

    for nombre, datos_eat in eats.items():
        datos_eat["nombre"] = cfg.EAT_DISPLAY.get(nombre, nombre)

    return {
        "municipios": municipios,
        "subregiones": subregiones,
        "eats": eats,
        "departamento": departamento,
        "ejes": [{"id": i, "nombre": n, "color": c, "icono": ic}
                 for i, n, c, ic in cfg.EJES],
        "etiquetas_estado": cfg.ETIQUETA_ESTADO,
        "eat_display": cfg.EAT_DISPLAY,
        "enlace_gobernacion": cfg.ENLACE_GOBERNACION,
    }
