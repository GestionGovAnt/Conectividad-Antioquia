"""
Configuración central del proyecto.

Todo lo que puede cambiar cuando la Dirección ajuste criterios vive aquí:
rutas, homologación de nombres, agrupación de programas y las reglas con las
que se califica cada eje. El resto del código no tiene constantes de negocio.
"""
from pathlib import Path

# --------------------------------------------------------------------------
# Rutas
# --------------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parent.parent
DIR_DATOS = RAIZ / "datos"
DIR_ASSETS = RAIZ / "assets"
DIR_PLANTILLAS = RAIZ / "src" / "plantillas"
DIR_SALIDA = RAIZ / "salida"

ARCHIVO_SABANA = DIR_DATOS / "sabana_unica_visor.xlsx"
ARCHIVO_GEO = DIR_DATOS / "geo_antioquia.json"
ARCHIVO_SALIDA = DIR_SALIDA / "ficha_tic_antioquia.html"

ASSETS = {
    "logo": DIR_ASSETS / "logo_gobernacion.png",
    "plaza": DIR_ASSETS / "encabezado_parque.jpg",
    "fondo": DIR_ASSETS / "fondo_monumento.jpg",
}

# --------------------------------------------------------------------------
# Identidad del documento
# --------------------------------------------------------------------------
ENTIDAD = "Administrativo de Planeación"
DEPENDENCIA = (
    "Dirección de Gestión Territorial de las Tecnologías de la Información "
    "y las Comunicaciones (TIC)"
)

# --------------------------------------------------------------------------
# Hojas de la sábana y su columna de municipio
# --------------------------------------------------------------------------
HOJAS = {
    "municipios": ("Municipios", "MUNICIPIO"),
    "sedes": ("SEDES EDUCATIVAS", "MUNICIPIO"),
    "salud": ("SALUD", "nombre_municipio"),
    "seguridad": ("SEGURIDAD", "nombre_municipio"),
    "territorial": ("D. GESTION TERRITORIAL TIC", "nombre_municipio"),
    "consolidados": ("Consolidados", "nombre_municipio"),
    "inventario": ("INVENTARIO GENERAL", "MUNICIPIO"),
    "diagnosticos": ("Diagnosticos DataCenters", "Municipio"),
    "peti": ("PETI-PAMUDA", "Municipio"),
    "apropiacion": ("USO Y APROPIACION", "MUNICIPIO"),
    "capacitaciones": ("CAPACITACIONES", "Municipio"),
    "enlaces": ("Enlaces TIC", "MUNICIPIO"),
}

# --------------------------------------------------------------------------
# Homologación de nombres de municipio
#
# La sábana no trae COD_DANE en la mayoría de hojas, así que el cruce se hace
# por nombre. Estas equivalencias corrigen las variantes encontradas.
# Cuando la fuente incorpore COD_DANE en todas las hojas, esta tabla sobra.
# --------------------------------------------------------------------------
ALIAS_MUNICIPIOS = {
    "SANTA FE DE ANTIOQUIA": "SANTA FE ANTIOQUIA",
    "DON MATIAS": "DONMATIAS",
    "LA CEJA": "LA CEJA DEL TAMBO",
    "SAN VICENTE": "SAN VICENTE FERRER",
    "SAN VICENTE DE FERRER": "SAN VICENTE FERRER",
    "PENOL": "EL PENOL",
    "RETIRO": "EL RETIRO",
    "MARINILA": "MARINILLA",
    "CAROLINA": "CAROLINA DEL PRINCIPE",
    "SAN PEDRO DE MILAGROS": "SAN PEDRO DE LOS MILAGROS",
    "TURBO": ("DISTRITO PORTUARIO, LOGISTICO, INDUSTRIAL, "
              "TURISTICO Y COMERCIAL DE TURBO"),
}

# Nombres oficiales que el maestro trae mal escritos. El maestro es la fuente
# de verdad para la asignación territorial, pero no para la ortografía: le
# faltan tildes en tres municipios y a Santa Fe de Antioquia le falta el "de".
NOMBRES_OFICIALES = {
    "ALEJANDRIA": "Alejandría",
    "ENTRERRIOS": "Entrerríos",
    "PUERTO BERRIO": "Puerto Berrío",
    "SANTA FE ANTIOQUIA": "Santa Fe de Antioquia",
    "DISTRITO PORTUARIO, LOGISTICO, INDUSTRIAL, TURISTICO Y COMERCIAL DE TURBO":
        "Turbo",
}

# Partículas que no se capitalizan al pasar de MAYÚSCULAS a nombre propio.
MINUSCULAS_TITULO = {"de", "del", "la", "las", "los", "y", "el"}

# Correcciones a la asignación territorial del maestro.
# Caicedo: el maestro lo pone en Suroeste, pero las otras seis hojas de la
# sábana y el listado oficial de la Gobernación lo ubican en Occidente. Con la
# corrección las subregiones quedan en 19 y 23 municipios, como el oficial.
# Para revertirla, borre la entrada.
CORRECCIONES_SUBREGION = {
    "CAICEDO": "OCCIDENTE",
}

CAPITALES_SUBREGION = {
    "Valle de Aburrá": "Medellín",
    "Oriente": "Rionegro",
    "Suroeste": "Andes",
    "Occidente": "Santa Fe de Antioquia",
    "Norte": "Santa Rosa de Osos",
    "Nordeste": "Yolombó",
    "Bajo Cauca": "Caucasia",
    "Magdalena Medio": "Puerto Berrío",
    "Urabá": "Apartadó",
}

ENLACE_GOBERNACION = "https://www.antioquia.gov.co/mapa-de-antioquia"

SUBREGION_DISPLAY = {"Uraba": "Urabá", "Valle de Aburra": "Valle de Aburrá"}

EAT_DISPLAY = {
    "A. Met Valle de Aburrá": "Área Metropolitana Valle de Aburrá",
    "A. Met Valle de San Nicolás": "Área Metropolitana Valle de San Nicolás",
    "A. Met Valle de San Nicolás PAP Agua, bosques y turismo":
        "Área Metropolitana Valle de San Nicolás + PAP Agua, bosques y turismo",
    "A. Met Valle de San Nicolás PAP de la Paz":
        "Área Metropolitana Valle de San Nicolás + PAP de la Paz",
    "PAP Agroindustrial Del Occidente": "PAP Agroindustrial del Occidente",
}

# --------------------------------------------------------------------------
# Sedes educativas: programas y tecnologías
# --------------------------------------------------------------------------
SIN_TECNOLOGIA = "SIN DATO"

PROGRAMAS = ["Gobernación", "MinTIC", "Municipio", "Otros", "Sin programa"]

# La sábana solo distingue zona rural y urbana en el programa de la
# Gobernación. Para las demás sedes no hay dato de zona.
ZONA_SEDE = {
    "GOBERNACIÓN - RURALES": "Rural",
    "GOBERNACIÓN - URBANAS": "Urbana",
}
ZONA_SIN_DATO = "Sin clasificar"

SUBPROGRAMAS = {
    "GOBERNACIÓN - RURALES": "Gobernación · rurales",
    "GOBERNACIÓN - URBANAS": "Gobernación · urbanas",
    "MINTIC - CENTROS DIGITALES": "MinTIC · Centros Digitales",
    "MINTIC - ZCP": "MinTIC · ZCP",
    "MINTIC - 5G": "MinTIC · 5G",
    "POR EL MUNICIPIO": "Por el municipio",
}
SUBPROGRAMA_OTROS = "Otros / sin programa"

TECNOLOGIAS = {
    "SATELITAL - STARLINK": "Satelital Starlink",
    "SATELITAL - TIGO": "Satelital Tigo",
    "SATELITAL KA": "Satelital KA",
    "FIBRA OPTICA DEDICADA": "Fibra óptica dedicada",
    "FIBRA OPTICA": "Fibra óptica",
    "RADIO": "Radio",
    "TVWS": "TVWS",
    "SIN DATO": "Sin dato",
}
ORDEN_TECNOLOGIAS = list(TECNOLOGIAS.values())

# --------------------------------------------------------------------------
# Estados de PETI y PAMUDA
#
# Se usan las columnas ESTADO PETI y ESTADO PAMUDA por decisión de la
# Dirección. Ver calidad.py: las columnas PETI y ESTADO PETI de la fuente
# se contradicen en varios municipios.
# --------------------------------------------------------------------------
PUNTAJE_ESTADO = {
    "SI": 1.0,
    "Inicio proceso de acompañamiento": 0.5,
    "No han iniciado proceso de acompañamiento": 0.0,
}
ETIQUETA_ESTADO = {
    "SI": "Sí",
    "Inicio proceso de acompañamiento": "En proceso",
    "No han iniciado proceso de acompañamiento": "Sin iniciar",
}

# --------------------------------------------------------------------------
# Ejes del índice de avance
#
# Cada eje se califica entre 0 y 1. El índice es el promedio simple de los
# ejes aplicables. Para cambiar la ponderación, modifique indicadores.py:
# la función indice() es el único punto donde se combinan.
# --------------------------------------------------------------------------
EJES = [
    ("E1", "Conectividad educativa", "teal", "conect"),
    ("E2", "Infraestructura tecnológica", "blue", "infra"),
    ("E3", "Proyecto de fibra", "teal", "fibra"),
    ("E4", "Entornos educativos seguros", "blue", "cam"),
    ("E5", "Contigo Antioquia Salud", "blue", "salud"),
    ("E6", "PETI", "amb", "gob"),
    ("E7", "PAMUDA", "amb", "gob"),
]

# Municipios certificados en educación: no dependen de la Secretaría
# departamental, por eso no tienen sedes en la base y el eje E1 no aplica.
CERTIFICADOS_EDUCACION = [
    "MEDELLIN", "BELLO", "ITAGUI", "ENVIGADO", "SABANETA",
    "LA ESTRELLA", "RIONEGRO", "APARTADO",
    "DISTRITO PORTUARIO, LOGISTICO, INDUSTRIAL, TURISTICO Y COMERCIAL DE TURBO",
]

# --------------------------------------------------------------------------
# Salud: el campo `equipos` es una lista separada por comas. Estos son los
# tokens que identifican cada dotación. Se buscan como token exacto, no como
# subcadena: "STARLINK" a secas casaba con KIT_SATELITAL_STARLINK y con
# STARLINK_MINI a la vez, y sumaba dos dotaciones distintas.
# --------------------------------------------------------------------------
EQUIPOS_SALUD = {
    "kit_fijo": "KIT_SATELITAL_STARLINK",
    "kit_itinerante": "KIT_SATELITAL_ITINERANTE",
    "starlink_mini": "STARLINK_MINI",
}

# Rango geográfico válido para validar coordenadas (bounding box Antioquia)
BBOX = {"lat_min": 5.4, "lat_max": 8.95, "lon_min": -77.3, "lon_max": -73.75}
