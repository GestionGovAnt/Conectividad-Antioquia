# Observatorio de Conectividad — Antioquia

Tablero de mapa con los cuatro ejes de conectividad del departamento y la
inversión asociada a cada uno.

El archivo que sale de aquí es **autónomo**: se abre con doble clic en
cualquier navegador, sin internet, sin servidor y sin instalar nada.

---

## Publicar en internet

Ver **[DESPLIEGUE.md](DESPLIEGUE.md)**: sitio estático gratuito en GitHub
Pages, con descarga automática del Excel desde SharePoint una vez al día.

```bash
python publicar.py --ficha ../ficha     # arma la carpeta sitio/
```

## Uso

```bash
pip install -r requirements.txt
python build.py
```

Deja **dos** tableros en `salida/`:

| Archivo | Necesita internet | Para qué |
|---|---|---|
| `observatorio_conectividad.html` | Sí | **El observatorio.** Mapa base real, zoom, relieve 3D |
| `observatorio_sin_internet.html` | No | Respaldo para redes cerradas |

**No son dos productos: son el mismo tablero con dos motores de mapa.** Las
cifras son idénticas. El respaldo existe solo por si la red institucional
bloquea los dominios del mapa base; si no es el caso, ignórelo.

Para que los enlaces funcionen, deje en la misma carpeta:

```
observatorio_conectividad.html
ficha_tic_antioquia.html
```

Si renombra alguno, ajuste `config.ENLACE_FICHA` en este proyecto y
`config.ENLACE_OBSERVATORIO` en el de la ficha.

```bash
python build.py --sin-mapa     # solo la versión sin internet
python build.py --geojson      # además, los GeoJSON sueltos
```

Los GeoJSON de `salida/geojson/` sirven para QGIS, ArcGIS o Power BI.

```bash
python build.py --sabana datos/otra.xlsx --inversion datos/inversion_2026.csv
```

---

## Los cuatro ejes

Todos miden conectividad; cambia el sector donde llega.

| Eje | Unidad | Fuente |
|---|---|---|
| Educación | Sedes educativas conectadas | SEDES EDUCATIVAS |
| Salud | Puntos de salud conectados | SALUD |
| Seguridad | Entornos seguros y fibra óptica | SEGURIDAD + KMZ |
| TIC | DataCenter y puntos de conectividad | Consolidados, Gestión Territorial |

La fibra óptica está en **Seguridad** por decisión de la Dirección: el
proyecto se formuló como infraestructura de seguridad territorial.

## Navegación

| Acción | Resultado |
|---|---|
| Clic en un municipio | Acerca la cámara y abre su detalle |
| Subregión / EAT / Municipio | Se encadenan; lo de fuera del ámbito se atenúa |
| Pestañas de eje o franja inferior | Cambian el eje activo |
| «Ver ficha completa» | Abre la ficha municipal en `?mun=<COD_DANE>` |
| Relieve 3D | Levanta cada municipio como columna: la altura es el indicador |
| Capa de fibra encendida + clic | Acerca al trazado del KMZ, no al contorno |

Para que el enlace a la ficha funcione, deje `ficha_tic_antioquia.html` en la
misma carpeta que el observatorio, o cambie `config.ENLACE_FICHA` por la URL
donde esté publicada.

## Trazado de fibra óptica (KMZ)

Copie los archivos en `datos/kmz/` y vuelva a construir. El proceso abre cada
KMZ, extrae las líneas, **mide su longitud real sobre el elipsoide** y las
dibuja como capa del mapa.

El municipio se asigna primero por el nombre del archivo —homologado con la
misma tabla de alias del resto del proyecto— y, si no cruza, por la ubicación
del trazado. Lo que no se pueda asignar se reporta en el log.

La medición permite contrastar contra los metros digitados en la sábana. La
diferencia no es un error: el KMZ mide el trazado real y la sábana trae lo que
alguien escribió. Sirve para saber cuál de las dos corregir.

---

## Inversión

**Hoy está apagada** (`config.MOSTRAR_INVERSION = False`) porque todavía no
hay datos. No se muestra en ceros a propósito: un cero se lee como «no se
invirtió», que no es lo mismo que «no lo tenemos».

Cuando llegue la tabla, complete `datos/inversion.csv`, ponga la bandera en
`True` y reconstruya.

Complete `datos/inversion.csv`. Mientras esté vacío el tablero funciona igual
y muestra el aviso de que falta la fuente. `datos/inversion_ejemplo.csv`
enseña el formato con cuatro filas de muestra.

Columnas:

| Columna | Contenido |
|---|---|
| `vigencia` | Año |
| `cod_dane_mpio` | 05002, o `DEPARTAMENTAL` si es transversal |
| `eje` | educacion, salud, seguridad, tic |
| `proyecto_bpin`, `contrato`, `objeto` | Identificación |
| `fuente` | departamento, sgp, regalias, mintic, municipio |
| `valor_comprometido`, `valor_obligado`, `valor_pagado` | Las tres, no una |
| `unidades` | Cuántos puntos entregó ese contrato |

Las tres columnas de valor no son capricho: dan cifras distintas del mismo
contrato. El tablero siempre rotula cuál está mostrando; se cambia en
`config.VALOR_POR_DEFECTO`.

### Cómo se imputa

Una fila con código DANE va directo a ese municipio.

Una fila `DEPARTAMENTAL` **se reparte en proporción a las unidades que cada
municipio recibió en ese eje**. Si un contrato cubrió 250 entornos educativos
seguros y Yarumal recibió 6, a Yarumal le corresponde el 2,4 %.

Un contrato transversal que no entrega puntos —una plataforma, una
consultoría— **no se reparte**: se reporta aparte como inversión transversal.
Repartirlo por población o en partes iguales sería inventar una cifra. Esa
decisión está en `config.REPARTIR_SIN_UNIDADES`.

---

## Estructura

```
build.py                   punto de entrada
datos/
  sabana_unica_visor.xlsx  fuente de conectividad (ya normalizada)
  geo_antioquia.json       125 polígonos municipales por COD_DANE
  inversion.csv            fuente de inversión (se crea vacía)
src/
  config.py                ejes, proyección, esquema de inversión
  loader.py                lectura y normalización del Excel
  ejes.py                  cálculo de los cuatro ejes y capas de puntos
  inversion.py             lectura, validación y reparto
  datos_tablero.py         ensamble por municipio, subregión, EAT y depto.
  render.py                armado del HTML autónomo
  plantillas/              base.html · estilos.css · app.js
```

---

## Las dos versiones del mapa

**Sin internet.** SVG dibujado a mano con los polígonos en coordenadas de
lienzo. No tiene mapa base ni zoom, pero funciona en cualquier parte.

### Qué significan las métricas

Cada eje mide cosas distintas, así que el selector de indicador y el glosario
del panel cambian con el eje:

| Eje | Unidad | Cobertura |
|---|---|---|
| Educación | Sedes conectadas | Conectadas / total de sedes |
| Salud | Puntos conectados | Con kit satelital / total de puntos |
| Seguridad | Entornos + municipios con fibra | No aplica |
| TIC | DataCenter + puntos de conectividad | Municipios con PETI / total |

«Conectada» significa que el dato de tecnología está registrado, no que el
servicio esté activo: la sábana no guarda estado operativo.

**Con mapa base.** MapLibre GL sobre CARTO, en **tema oscuro tipo sala de
monitoreo**: fondo negro, colores neón por eje, latido en los puntos del eje
activo y franja inferior con los cuatro contadores. Trae zoom, arrastre,
pantalla completa, relieve 3D, agrupación automática de las 3.939 sedes,
popup al hacer clic y resaltado al pasar el mouse. Descarga la librería de
`unpkg.com` y las teselas de `basemaps.cartocdn.com`: ninguna necesita llave
de API, pero **sí requieren que la red institucional permita esos dominios**.
Si no cargan, el tablero muestra un aviso y remite a la versión sin internet.

Para cambiar el estilo del mapa base, edite `config.ESTILO_MAPA`. Las
alternativas probadas son `dark-matter-gl-style` y `voyager-gl-style` en la
misma ruta de CARTO.

## La geometría

Los polígonos vienen en coordenadas de lienzo, no en lon/lat. Los puntos se
proyectan con un ajuste lineal calculado por mínimos cuadrados contra los
centroides (`config.PROYECCION`). El 91 % de las sedes cae dentro de su propio
municipio; las que no, son municipios de borde con polígono simplificado.

Para la versión con mapa base esa proyección **se invierte** y produce
GeoJSON en coordenadas reales (`src/geojson.py`). El bounding box
reconstruido cae entre 1 y 4 km del real de Antioquia: los polígonos se
asientan bien sobre el mapa base, pero **no son cartografía oficial**. Si el
producto va a publicarse, reemplace `datos/geo_antioquia.json` por el
shapefile del DANE o el IGAC.

**La asignación municipal siempre sale de COD_DANE, nunca de la geometría.**
La proyección solo sirve para dibujar.

---

## Lo que falta en la fuente

- **Proyecto de fibra óptica: 80 registros, ninguno con coordenada.** Esa capa
  hoy no se puede pintar. El KMZ del trazado la resolvería.
- **361 sedes educativas sin georreferenciar.** Aparecen en los conteos pero no
  en el mapa.
- 5 entornos educativos seguros y 2 puntos de conectividad sin coordenada.
