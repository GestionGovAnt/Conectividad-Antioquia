"""
Configuración del Observatorio de Conectividad.

Cuatro ejes, una sola pregunta: dónde llegó la conectividad y cuánto costó.
Todo lo que la Dirección puede decidir vive aquí.
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

# El archivo suele venir de SharePoint con tildes y en otro orden
# ("sábana_única_visor.xlsx"). Si el nombre exacto no existe, se busca
# cualquier Excel de la carpeta que se le parezca, para que subirlo tal
# como viene no rompa la construcción.
PATRONES_SABANA = ["*abana*nica*visor*.xlsx", "*abana*.xlsx", "*.xlsx"]
ARCHIVO_GEO = DIR_DATOS / "geo_antioquia.json"
ARCHIVO_INVERSION = DIR_DATOS / "inversion.csv"
# El observatorio principal es el del mapa interactivo. La versión sin
# internet es un respaldo para redes cerradas, no un segundo producto.
ARCHIVO_SALIDA_MAPA = DIR_SALIDA / "observatorio_conectividad.html"
ARCHIVO_SALIDA = DIR_SALIDA / "observatorio_sin_internet.html"

# Estilo del mapa base para la versión con internet. CARTO Positron: vectorial,
# gratuito, sin llave de API. Alternativas probadas: "dark-matter-gl-style" y
# "voyager-gl-style" en la misma ruta.
ESTILO_MAPA = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"

ASSETS = {"logo": DIR_ASSETS / "logo_gobernacion.png"}

ENTIDAD = "Departamento Administrativo de Planeación"
DEPENDENCIA = ("Dirección de Gestión Territorial de las Tecnologías "
               "de la Información y las Comunicaciones")
TITULO = "Observatorio de Conectividad"
ENLACE_GOBERNACION = "https://www.antioquia.gov.co/mapa-de-antioquia"

# Ficha municipal detallada. Se abre con ?mun=<COD_DANE>. Debe quedar en la
# misma carpeta que el observatorio, o cambie esta ruta por la URL donde
# esté publicada.
ENLACE_FICHA = "ficha_tic_antioquia.html"

# --------------------------------------------------------------------------
# Proyección del mapa
#
# Ajuste lineal lon/lat -> coordenadas del lienzo SVG, calculado por mínimos
# cuadrados contra los centroides de los 125 polígonos. El 91 % de las sedes
# cae dentro de su propio municipio; las que no, son de municipios de borde
# cuyo polígono viene simplificado.
#
# La asignación municipal SIEMPRE sale de COD_DANE, nunca de la geometría.
# La proyección es solo para dibujar.
# --------------------------------------------------------------------------
PROYECCION = {
    "ax": 143.8287232410267, "bx": 11101.696966845308,
    "ay": -145.3511420659884, "by": 1296.76077487081,
}
BBOX = {"lat_min": 5.4, "lat_max": 8.95, "lon_min": -77.3, "lon_max": -73.75}

# --------------------------------------------------------------------------
# Los cuatro ejes
#
# `unidad` es el conteo físico del eje y también el repartidor de la inversión
# departamental: un contrato transversal se imputa a cada municipio en
# proporción a las unidades que recibió.
# --------------------------------------------------------------------------
EJES = [
    {"id": "educacion", "nombre": "Educación", "color": "#2BE5A0",
     "unidad": "Sedes educativas conectadas",
     "unidad_desc": "Sedes cuyo campo PROYECTO trae una tecnología de conexión. "
                    "Mide inventario documentado, no servicio activo.",
     "cobertura": "Sedes conectadas sobre el total de sedes del municipio",
     "icono": "escuela"},
    {"id": "salud", "nombre": "Salud", "color": "#FF4D7E",
     "unidad": "Puntos de salud conectados",
     "unidad_desc": "Hospitales, centros y puestos de salud con conectividad "
                    "registrada en la sábana.",
     "cobertura": "Puntos con kit satelital sobre el total de puntos conectados",
     "icono": "salud"},
    {"id": "seguridad", "nombre": "Seguridad", "color": "#38A3FF",
     "unidad": "Entornos seguros y fibra óptica",
     "unidad_desc": "Placas deportivas intervenidas con cámaras e iluminación, "
                    "más los municipios que hacen parte del proyecto de fibra.",
     "cobertura": None,
     "icono": "escudo"},
    {"id": "tic", "nombre": "TIC", "color": "#FFB020",
     "unidad": "DataCenter y puntos de conectividad",
     "unidad_desc": "DataCenter entregados más puntos de acceso público "
                    "georreferenciados.",
     "cobertura": "Municipios con PETI formulado sobre el total del ámbito",
     "icono": "antena"},
]

IDS_EJES = [e["id"] for e in EJES]

# Capas de puntos que se dibujan sobre el mapa, por eje.
CAPAS = [
    {"id": "sedes", "eje": "educacion", "nombre": "Sedes educativas",
     "hoja": "sedes", "radio": 1.6},
    {"id": "salud", "eje": "salud", "nombre": "Puntos de salud",
     "hoja": "salud", "radio": 2.6},
    {"id": "entornos", "eje": "seguridad", "nombre": "Entornos educativos seguros",
     "hoja": "seguridad", "radio": 2.6},
    {"id": "wifi", "eje": "tic", "nombre": "Puntos de conectividad",
     "hoja": "territorial", "radio": 2.6},
    {"id": "datacenter", "eje": "tic", "nombre": "DataCenter",
     "hoja": "consolidados", "radio": 3.4},
]

# Trazado de fibra óptica en KMZ, un archivo por municipio.
# Se leen de datos/kmz/ y se convierten a una capa de líneas.
DIR_KMZ = DIR_DATOS / "kmz"

# Resultado ya procesado de los KMZ. Los 76 archivos originales pesan 29 MB y
# su lectura siempre da lo mismo, así que el repositorio guarda solo el
# resultado. Si se dejan los KMZ en datos/kmz/ tienen prioridad y el caché se
# regenera; si no, se usa este archivo.
ARCHIVO_FIBRA = DIR_DATOS / "fibra_trazado.geojson"

# Equivalencias que aparecen solo en los nombres de archivo de los KMZ:
# nombres cortos, corregimientos y errores de digitación de quien exportó.
ALIAS_ARCHIVO_KMZ = {
    "SANTA FE": "SANTA FE ANTIOQUIA",
    "CARMEN VIBORAL": "EL CARMEN DE VIBORAL",
    "SANTUARIO": "EL SANTUARIO",
    "PENOL": "EL PENOL",
    "RETIRO": "EL RETIRO",
    "CEJA": "LA CEJA DEL TAMBO",
    "PUERTO NAREF": "PUERTO NARE",
    # Doradal es corregimiento de Puerto Triunfo.
    "DORADAL": "PUERTO TRIUNFO",
}
# Umbral de la coincidencia aproximada. Por encima se acepta y se reporta
# en el log para que alguien lo verifique; por debajo queda sin asignar.
UMBRAL_APROXIMADO = 0.86
CAPA_FIBRA = {"id": "fibra", "eje": "seguridad", "nombre": "Trazado de fibra óptica"}

# --------------------------------------------------------------------------
# Inversión
#
# Esquema de datos/inversion.csv. Mientras el archivo esté vacío el tablero
# muestra los ejes de conectividad y las tarjetas de inversión en cero, con
# el aviso de que falta cargar la fuente.
# --------------------------------------------------------------------------
COLUMNAS_INVERSION = [
    "vigencia",            # año: 2024, 2025, 2026
    "cod_dane_mpio",       # 05002 · o DEPARTAMENTAL si es transversal
    "eje",                 # educacion | salud | seguridad | tic
    "proyecto_bpin",
    "contrato",
    "objeto",
    "fuente",              # departamento | sgp | regalias | mintic | municipio
    "valor_comprometido",
    "valor_obligado",
    "valor_pagado",
    "unidades",            # cuántos puntos entregó ese contrato (opcional)
]

MARCA_DEPARTAMENTAL = "DEPARTAMENTAL"

# Qué valor se muestra por defecto. Comprometido, obligado y pagado dan
# cifras distintas del mismo contrato: el tablero siempre dice cuál usa.
VALOR_POR_DEFECTO = "valor_comprometido"
ETIQUETA_VALOR = {
    "valor_comprometido": "comprometido",
    "valor_obligado": "obligado",
    "valor_pagado": "pagado",
}

# Mientras la Dirección no entregue la tabla de inversión, el componente se
# oculta por completo en vez de mostrarse en ceros: un tablero con ceros se
# lee como "no se invirtió nada", que es distinto de "no tenemos el dato".
# Se enciende poniendo esto en True y cargando datos/inversion.csv.
MOSTRAR_INVERSION = False

# Un contrato transversal que no entrega puntos (una plataforma, una
# consultoría) no se reparte: se muestra aparte. Repartirlo sería inventar.
REPARTIR_SIN_UNIDADES = False

# --------------------------------------------------------------------------
# Homologación territorial (heredada del proyecto de la ficha)
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
NOMBRES_OFICIALES = {
    "ALEJANDRIA": "Alejandría",
    "ENTRERRIOS": "Entrerríos",
    "PUERTO BERRIO": "Puerto Berrío",
    "SANTA FE ANTIOQUIA": "Santa Fe de Antioquia",
    "DISTRITO PORTUARIO, LOGISTICO, INDUSTRIAL, TURISTICO Y COMERCIAL DE TURBO":
        "Turbo",
}
MINUSCULAS_TITULO = {"de", "del", "la", "las", "los", "y", "el"}
CORRECCIONES_SUBREGION = {"CAICEDO": "OCCIDENTE"}
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

SIN_TECNOLOGIA = "SIN DATO"
ZONA_SEDE = {"GOBERNACIÓN - RURALES": "Rural", "GOBERNACIÓN - URBANAS": "Urbana"}
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
EQUIPOS_SALUD = {
    "kit_fijo": "KIT_SATELITAL_STARLINK",
    "kit_itinerante": "KIT_SATELITAL_ITINERANTE",
}
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
