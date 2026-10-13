"""
Estado de DataCenter por municipio: unión de las cuatro fuentes de la sábana.

Hay cuatro hojas que hablan de DataCenter y ninguna sola responde la pregunta
completa:

  1. D. GESTION TERRITORIAL TIC, filas con Punto = DATACENTER
     Quién tiene DataCenter y de quién es. Es la que hoy pinta el mapa.
  2. INVENTARIO GENERAL
     Qué equipos se entregaron, municipio por municipio. Es el único dato
     duro de AP: lo demás es lo que cada municipio dice tener.
  3. Diagnosticos DataCenters
     Cómo usan el DataCenter los municipios a los que la Gobernación se lo
     entregó. Universo: esos municipios, nadie más.
  4. ENCUESTA DATACENTER  (opcional, puede no existir todavía)
     Qué respondió el municipio sobre tener DataCenter propio. Universo:
     los municipios priorizados de la encuesta, no el departamento.

Este módulo las une por COD_DANE y devuelve UNA fila por municipio. La tabla
resultante es derivada: se regenera en cada construcción y no se digita. Si
se digitara a mano repetiríamos el problema de la hoja Consolidados, que hoy
tiene más de mil filas sin categoría justamente por eso.

Tres columnas sostienen la trazabilidad:
  FUENTE     de dónde salió la fila
  FECHA_DATO fecha del dato más reciente que la alimenta
  CONFLICTO  dónde las fuentes se contradicen, en vez de elegir en silencio
"""
from __future__ import annotations

import pandas as pd

HOJA_ENCUESTA = "ENCUESTA DATACENTER"

ORIGEN_GOBERNACION = "Gobernación"
ORIGEN_PROPIO = "Propio"

# Cómo se reconoce cada equipo en la columna DISPOSITIVO del inventario.
EQUIPOS = {
    "ap_internos": "MR44",
    "ap_externos": "MR76",
    "radioenlaces": "RADIOENLACE",
    "datacenter": "DATACENTER AUTO",
}

COLUMNAS = [
    "COD_DANE", "MUNICIPIO", "SUBREGION", "EAT",
    "TIENE_DATACENTER", "ORIGEN", "FUENTE", "FECHA_DATO",
    "AP_INT_ENTREGADOS", "AP_EXT_ENTREGADOS",
    "AP_INT_REPORTADOS", "AP_EXT_REPORTADOS", "AP_SIN_FUNCIONAR",
    "CIBERSEGURIDAD", "CAPACIDAD_MEGAS", "SERVICIOS",
    "FECHA_ENTREGA", "VIGENCIA_LICENCIAS", "CONFLICTO",
]


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def _texto(valor) -> str:
    """Celda a texto limpio. Vacío si no hay dato."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    texto = str(valor).strip()
    return "" if texto.lower() in ("nan", "nat", "none") else texto


def _entero(valor):
    """Celda a entero. None si no hay dato: un vacío no es un cero."""
    numero = pd.to_numeric(valor, errors="coerce")
    return None if pd.isna(numero) else int(numero)


def _fecha(valor) -> str:
    """Fecha a ISO.

    La sábana trae el mismo campo de tres formas: fecha real, texto
    dd/mm/aaaa y texto en palabras. Las dos primeras se resuelven aquí; la
    tercera queda vacía y sale como aviso, que es lo correcto: adivinar una
    fecha escrita a mano es peor que no tenerla.
    """
    texto = _texto(valor)
    if not texto:
        return ""
    # Un texto que ya viene en ISO no se interpreta con el día primero.
    iso = len(texto) >= 10 and texto[4] == "-" and texto[7] == "-"
    marca = pd.to_datetime(texto, dayfirst=not iso, errors="coerce")
    return "" if pd.isna(marca) else marca.date().isoformat()


def _columna(df: pd.DataFrame, prefijo: str) -> str | None:
    """Columna por el prefijo de la pregunta: los enunciados son largos."""
    clave = prefijo.replace(" ", "").upper()
    for nombre in df.columns:
        if str(nombre).replace(" ", "").upper().startswith(clave):
            return nombre
    return None


# --------------------------------------------------------------------------
# Lectura de cada fuente
# --------------------------------------------------------------------------
def _del_registro(sabana) -> dict[str, dict]:
    """Municipios con DataCenter registrado, y de quién es."""
    df = sabana.hoja("territorial")
    filas = df[df["Punto"].map(_texto).str.upper() == "DATACENTER"]
    salida: dict[str, dict] = {}
    for _, fila in filas.iterrows():
        cod = fila.get("cod")
        if not isinstance(cod, str):
            continue
        marca = _texto(fila.get("observacion")).upper()
        salida[cod] = {
            "origen": ORIGEN_GOBERNACION if marca.startswith("GOBERNACI")
            else ORIGEN_PROPIO,
        }
    return salida


def _del_inventario(sabana) -> dict[str, dict]:
    """Equipos efectivamente entregados por municipio.

    Es el único conteo duro de AP que existe en la sábana. El diagnóstico
    recoge lo que el municipio dice tener, que no es lo mismo.
    """
    df = sabana.hoja("inventario")
    salida: dict[str, dict] = {}
    for _, fila in df.iterrows():
        cod = fila.get("cod")
        if not isinstance(cod, str):
            continue
        dispositivo = _texto(fila.get("DISPOSITIVO")).upper()
        cantidad = _entero(fila.get("CANTIDAD")) or 0
        registro = salida.setdefault(cod, {k: 0 for k in EQUIPOS})
        for clave, patron in EQUIPOS.items():
            if patron in dispositivo:
                registro[clave] += cantidad
                break
    return salida


def _del_diagnostico(sabana) -> dict[str, dict]:
    """Uso del DataCenter entregado por la Gobernación."""
    df = sabana.hoja("diagnosticos")
    col_fecha = _columna(df, "Fecha Reunion")
    col_int = _columna(df, "P3.1")
    col_ext = _columna(df, "P.3.2")
    col_malos = _columna(df, "P3.4")
    col_ciber = _columna(df, "P.4")
    col_serv = _columna(df, "P2.1")
    col_entrega = _columna(df, "Fecha de entrega")
    col_licencias = _columna(df, "Fecha de Vigencia")

    salida: dict[str, dict] = {}
    for _, fila in df.iterrows():
        cod = fila.get("cod")
        if not isinstance(cod, str):
            continue
        fecha = _fecha(fila.get(col_fecha)) if col_fecha else ""
        ap_int = _entero(fila.get(col_int)) if col_int else None
        ap_ext = _entero(fila.get(col_ext)) if col_ext else None
        ciber = _texto(fila.get(col_ciber)) if col_ciber else ""
        salida[cod] = {
            "fecha": fecha,
            # Respondió algo, aunque la fila no traiga fecha de reunión.
            "respondido": bool(fecha) or ap_int is not None or bool(ciber),
            # Un único valor suelto en AP externos, sin AP internos y sin
            # fecha, casi nunca es un conteo de AP: es otra cosa que se
            # corrió de columna al llenar la fila.
            "valor_suelto": (not fecha and ap_int is None
                             and ap_ext is not None),
            "ap_internos": ap_int,
            "ap_externos": ap_ext,
            "ap_malos": _entero(fila.get(col_malos)) if col_malos else None,
            "ciberseguridad": ciber,
            "servicios": _texto(fila.get(col_serv)) if col_serv else "",
            "entrega": _fecha(fila.get(col_entrega)) if col_entrega else "",
            "licencias": _fecha(fila.get(col_licencias)) if col_licencias else "",
        }
    return salida


def _de_la_encuesta(sabana) -> dict[str, dict]:
    """Respuesta del municipio. Vacío si la hoja todavía no está en la sábana."""
    df = sabana.hoja_opcional(HOJA_ENCUESTA)
    if df is None:
        return {}
    salida: dict[str, dict] = {}
    for _, fila in df.iterrows():
        cod = fila.get("cod")
        if not isinstance(cod, str):
            continue
        respondio = _texto(fila.get("RESPONDIO")).upper().startswith("S")
        tiene = _texto(fila.get("TIENE_DATACENTER")).upper()
        salida[cod] = {
            "respondio": respondio,
            # None = no respondió. Distinto de False, que es "respondió que no".
            "tiene": None if not tiene else tiene.startswith("S"),
            "fecha": _fecha(fila.get("FECHA_CORTE")),
            "tipo": _texto(fila.get("TIPO")),
            "capacidad": _texto(fila.get("CAPACIDAD_MEGAS")),
            "servicios": _texto(fila.get("SERVICIOS")),
            "ap_externos": _entero(fila.get("AP_EXTERIORES")),
        }
    return salida


# --------------------------------------------------------------------------
# Unión
# --------------------------------------------------------------------------
def estado(sabana) -> pd.DataFrame:
    """Una fila por municipio del departamento, con las fuentes unidas."""
    registro = _del_registro(sabana)
    inventario = _del_inventario(sabana)
    diagnostico = _del_diagnostico(sabana)
    encuesta = _de_la_encuesta(sabana)

    filas = []
    for _, mpio in sabana.municipios.iterrows():
        cod = mpio["cod"]
        reg = registro.get(cod)
        equipos = inventario.get(cod)
        dia = diagnostico.get(cod)
        enc = encuesta.get(cod)

        fuentes = [nombre for nombre, fuente in
                   (("Registro", reg), ("Inventario", equipos),
                    ("Diagnóstico", dia), ("Encuesta", enc)) if fuente]

        # Regla 1: tiene DataCenter si cualquier fuente lo registra.
        tiene = bool(reg) or bool(enc and enc["tiene"])
        if not fuentes:
            valor_tiene = ""            # sin información, que no es "no tiene"
        elif tiene:
            valor_tiene = "SI"
        elif enc and enc["tiene"] is False:
            valor_tiene = "NO"
        else:
            valor_tiene = ""

        # Regla 2: el origen lo define el registro. Si solo lo reporta el
        # municipio, es propio: la Gobernación sabe cuáles entregó.
        if reg:
            origen = reg["origen"]
        elif enc and enc["tiene"]:
            origen = ORIGEN_PROPIO
        else:
            origen = ""

        # Regla 3: entre diagnóstico y encuesta gana el dato más reciente.
        fecha_dia = dia["fecha"] if dia else ""
        fecha_enc = enc["fecha"] if enc else ""
        manda_encuesta = bool(fecha_enc) and fecha_enc > (fecha_dia or "")

        ap_ext_rep = dia["ap_externos"] if dia else None
        if enc and enc["ap_externos"] is not None and (manda_encuesta
                                                       or ap_ext_rep is None):
            ap_ext_rep = enc["ap_externos"]

        servicios = (dia["servicios"] if dia else "") or (enc["servicios"] if enc else "")
        if enc and enc["servicios"] and manda_encuesta:
            servicios = enc["servicios"]

        filas.append({
            "COD_DANE": cod,
            "MUNICIPIO": mpio["nombre"],
            "SUBREGION": mpio["subregion"],
            "EAT": mpio["eat"],
            "TIENE_DATACENTER": valor_tiene,
            "ORIGEN": origen,
            "FUENTE": " + ".join(fuentes),
            "FECHA_DATO": max(filter(None, [fecha_dia, fecha_enc]), default=""),
            "AP_INT_ENTREGADOS": equipos["ap_internos"] if equipos else None,
            "AP_EXT_ENTREGADOS": equipos["ap_externos"] if equipos else None,
            "AP_INT_REPORTADOS": dia["ap_internos"] if dia else None,
            "AP_EXT_REPORTADOS": ap_ext_rep,
            "AP_SIN_FUNCIONAR": dia["ap_malos"] if dia else None,
            "CIBERSEGURIDAD": dia["ciberseguridad"] if dia else "",
            "CAPACIDAD_MEGAS": enc["capacidad"] if enc else "",
            "SERVICIOS": servicios,
            "FECHA_ENTREGA": dia["entrega"] if dia else "",
            "VIGENCIA_LICENCIAS": dia["licencias"] if dia else "",
            "CONFLICTO": "; ".join(_conflictos(reg, equipos, dia, enc)),
        })

    return pd.DataFrame(filas, columns=COLUMNAS)


def _conflictos(reg, equipos, dia, enc) -> list[str]:
    """Dónde las fuentes se contradicen. Se marcan, no se resuelven solas."""
    avisos = []

    if reg and enc and enc["tiene"] is False:
        avisos.append(
            f"el registro lo marca como {reg['origen'].lower()} "
            "y el municipio respondió que no tiene"
        )
    if enc and enc["tiene"] and not reg:
        avisos.append("reportado en la encuesta, falta en el registro del mapa")
    if reg and reg["origen"] == ORIGEN_GOBERNACION and enc and enc["tiene"]:
        avisos.append(
            "respondió por el DataCenter que entregó la Gobernación; "
            "no es uno propio"
        )
    if reg and reg["origen"] == ORIGEN_GOBERNACION and not equipos:
        avisos.append("marcado como de la Gobernación pero sin inventario de equipos")

    if dia and not dia["respondido"]:
        avisos.append("DataCenter entregado y diagnóstico sin diligenciar")
    elif dia and not dia["fecha"]:
        avisos.append("diagnóstico diligenciado pero sin fecha de reunión")
    if dia and dia["valor_suelto"]:
        avisos.append(
            f"el único valor del diagnóstico es un {dia['ap_externos']} "
            "en AP externos; verificar si se corrió de columna"
        )

    if equipos and dia and dia["ap_externos"] is not None and not dia["valor_suelto"]:
        entregados = equipos["ap_externos"]
        if dia["ap_externos"] != entregados:
            avisos.append(
                f"AP externos: recibió {entregados}, reporta {dia['ap_externos']}"
            )
    if equipos and dia and dia["ap_internos"] is not None:
        if dia["ap_internos"] != equipos["ap_internos"]:
            avisos.append(
                f"AP internos: recibió {equipos['ap_internos']}, "
                f"reporta {dia['ap_internos']}"
            )
    if (dia and enc
            and dia["ap_externos"] is not None
            and enc["ap_externos"] is not None
            and dia["ap_externos"] != enc["ap_externos"]):
        avisos.append(
            f"AP externos: diagnóstico {dia['ap_externos']}, "
            f"encuesta {enc['ap_externos']}"
        )
    return avisos


def agregar_hoja(origen, destino, nombre: str, df: pd.DataFrame) -> list[str]:
    """Copia un Excel con una hoja más, sin tocar las que ya tiene.

    Devuelve la lista de hojas originales que resultaron alteradas, que debe
    venir vacía: el objetivo es agregar, y una copia que recorta algo no
    sirve aunque se vea bien. Quien llama decide qué hacer si no lo está.
    """
    import openpyxl

    libro = openpyxl.load_workbook(origen)
    antes = {h: (libro[h].max_row, libro[h].max_column) for h in libro.sheetnames}

    if nombre in libro.sheetnames:
        del libro[nombre]
    hoja = libro.create_sheet(nombre)
    hoja.append(list(df.columns))
    for fila in df.itertuples(index=False):
        hoja.append(["" if v is None else v for v in fila])
    for celda in hoja["A"][1:]:
        celda.number_format = "@"      # el código DANE va como texto
    hoja.freeze_panes = "B2"

    destino.parent.mkdir(parents=True, exist_ok=True)
    libro.save(destino)

    revisado = openpyxl.load_workbook(destino, read_only=True)
    return [
        h for h, medida in antes.items()
        if h not in revisado.sheetnames
        or (revisado[h].max_row, revisado[h].max_column) != medida
    ]


def tabla(sabana) -> pd.DataFrame:
    """Estado por municipio, calculado una sola vez por sábana.

    Los ejes se recalculan para cada ámbito —departamento, 9 subregiones,
    18 EAT y 125 municipios—, así que la unión se hace una vez y se reusa.
    """
    if not hasattr(sabana, "_estado_datacenter"):
        sabana._estado_datacenter = estado(sabana)
    return sabana._estado_datacenter


def resumen(tabla: pd.DataFrame) -> dict:
    """Conteos de control para el log de la construcción."""
    con_info = tabla["FUENTE"] != ""
    return {
        "municipios": len(tabla),
        "con_informacion": int(con_info.sum()),
        "sin_informacion": int((~con_info).sum()),
        "con_datacenter": int((tabla["TIENE_DATACENTER"] == "SI").sum()),
        "de_la_gobernacion": int((tabla["ORIGEN"] == ORIGEN_GOBERNACION).sum()),
        "propios": int((tabla["ORIGEN"] == ORIGEN_PROPIO).sum()),
        "sin_datacenter_confirmado": int((tabla["TIENE_DATACENTER"] == "NO").sum()),
        "ap_ext_entregados": int(pd.to_numeric(
            tabla["AP_EXT_ENTREGADOS"], errors="coerce").sum()),
        "ap_ext_reportados": int(pd.to_numeric(
            tabla["AP_EXT_REPORTADOS"], errors="coerce").sum()),
        "con_conflicto": int((tabla["CONFLICTO"] != "").sum()),
    }
