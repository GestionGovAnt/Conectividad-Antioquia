# Ficha municipal de avance TIC — Antioquia

Genera un informe HTML **autónomo** con la ficha de avance TIC de los 125
municipios de Antioquia, calculado directamente desde la sábana única del
visor.

El archivo que sale de aquí no necesita este proyecto para funcionar: se abre
con doble clic en cualquier navegador, sin internet, sin servidor y sin
instalar nada. Se puede enviar por correo o dejar en una carpeta compartida.

---

## Uso rápido

```bash
pip install -r requirements.txt
python build.py
```

Deja tres archivos en `salida/`:

| Archivo | Para qué |
|---|---|
| `ficha_tic_antioquia.html` | El informe, autónomo y listo para compartir |
| `cifras_tic_antioquia.xlsx` | Las mismas cifras en tabla: por municipio, por EAT y por subregión |
| `puntos_a_gestionar.md` | Calidad del dato, uso interno |

Para actualizar el informe cuando cambie la fuente, reemplace
`datos/sabana_unica_visor.xlsx` y vuelva a ejecutar `python build.py`.
No hay que tocar código.

Opciones:

```bash
python build.py --sabana ruta/otra_sabana.xlsx
python build.py --salida salida/ficha_septiembre.html
```

---

## Qué contiene el informe

**Vista Ficha** — la principal. Una página por municipio, lista para
imprimir: mapa del EAT, los 7 ejes, sedes por programa y los indicadores
clave de infraestructura, gobierno digital y apropiación.

**Vista Componentes** — detrás de la ficha. Tres agrupaciones:

- **Ecosistemas digitales**: PETI, PAMUDA y ficha de madurez.
- **Infraestructura**: conectividad de sedes educativas (con reparto rural y
  urbano), DataCenter y puntos de conectividad, fibra óptica, entornos
  educativos seguros y salud conectada.
- **Uso y apropiación**: personas formadas y personas capacitadas, con
  desglose por tipo de formación, modalidad, curso, género y cargo.

**Vista Zona** — resumen de un EAT, de una subregión o del departamento. En
esta vista el filtro de municipio se ignora y se bloquea.

**Filtros encadenados** — Subregión → EAT → Municipio. El ámbito del informe
es siempre el más específico que esté seleccionado; el filtro de componente
solo se habilita en la vista Componentes. Los filtros que una vista no usa se
bloquean para que no confundan.

**Botón Exportar cifras** — descarga un CSV con los municipios del ámbito
seleccionado y sus 38 indicadores. Excel lo abre directo; el `.xlsx` con
formatos y hojas por EAT y subregión lo produce `build.py`. El selector de *ámbito* permite ver
el mismo componente para el municipio, su subregión, su EAT o todo el
departamento.

---

## Cómo se leen las cifras

**Participación.** Cada desglose muestra el total absoluto y qué porción del
ámbito representa. Si un municipio tiene 60 sedes y 20 son de la Gobernación,
esa fila marca 20 y una barra de 33 %. La barra reparte el universo; no mide
avance.

**Dotación de salud.** Un punto puede tener más de una dotación, así que las
filas no suman el total de puntos: cada una dice en cuántos puntos está
presente ese equipo. El kit fijo y la unidad itinerante son cosas distintas y
se cuentan por token exacto del campo `equipos`.

**Unidades entregadas.** Es una sumatoria de la columna CANTIDAD del
inventario y mezcla unidades de distinta naturaleza: un DataCenter completo
pesa igual que un inyector PoE. Por eso siempre se muestra junto a su
desglose y rotulada como suma.

**Personas formadas y personas capacitadas.** Son dos cosas distintas y no se
suman. *Formadas* son los asistentes a charlas, cursos y capacitaciones
grupales (hoja USO Y APROPIACIÓN, 1.639 en el departamento). *Capacitadas* son
las personas con acompañamiento individual registrado con nombre y cargo (hoja
CAPACITACIONES, 134 personas y 445 sesiones).

**Sedes.** Se cuentan las 4.300 sedes del departamento, sin separar por
institución: la conectividad se instala en el punto físico.

**Zona rural y urbana.** La sábana solo distingue zona en el programa de la
Gobernación (1.849 rurales y 415 urbanas). Las 2.036 sedes restantes quedan
como «sin clasificar»: no es que no tengan zona, es que la fuente no la
registra.

**Entornos educativos seguros.** Cada registro de la hoja SEGURIDAD es una placa
deportiva intervenida con cámaras e iluminación, **no una cámara individual**.
La fuente no dice cuántas cámaras hay por placa. Un municipio con 1 tiene una
placa intervenida.

**Puntos de conectividad.** Antes rotulados como zonas wifi. Son los puntos de
acceso público georreferenciados.

**Avance.** Las columnas *Con tecnología* y *Sin dato* sí miden avance dentro
de cada programa. Conviene saber que el 100 % de las sedes de la Gobernación
ya tienen tecnología registrada: el vacío de información está en MinTIC y en
las sedes sin programa asociado.

**Índice de avance.** Promedio simple de los 7 ejes aplicables, cada uno
entre 0 % y 100 %. Para cambiar la ponderación, edite `indicadores.indice()`:
es el único punto donde los ejes se combinan.

**Nombres y conformación territorial.** El maestro es la fuente de verdad para
la asignación territorial, pero no para la ortografía: `NOMBRES_OFICIALES`
corrige Alejandría, Entrerríos, Puerto Berrío y Santa Fe de Antioquia, y
`CORRECCIONES_SUBREGION` reubica a Caicedo en Occidente. Con esa corrección
las subregiones quedan en 19 y 23 municipios, como en el listado oficial de la
Gobernación. Para revertir cualquiera de las dos, borre la entrada en
`config.py`.

**Municipios certificados en educación.** No dependen de la Secretaría
departamental y por eso no tienen sedes en la base. En ellos el eje de
conectividad educativa no aplica y el índice promedia sobre 6 ejes.

---

## Estructura

```
├── build.py                  punto de entrada
├── requirements.txt
├── datos/
│   ├── sabana_unica_visor.xlsx    fuente (reemplazable)
│   └── geo_antioquia.json         polígonos municipales por COD_DANE
├── assets/                   logo y fotografías institucionales
├── src/
│   ├── config.py             rutas, homologaciones y reglas de los ejes
│   ├── loader.py             lectura y normalización del Excel
│   ├── indicadores.py        cálculo de indicadores, ejes e índice
│   ├── calidad.py            auditoría de calidad de la fuente
│   ├── reporte_calidad.py    exporta los puntos a gestionar (interno)
│   ├── render.py             armado del HTML autónomo
│   └── plantillas/
│       ├── base.html
│       ├── estilos.css
│       └── app.js
└── salida/
    ├── ficha_tic_antioquia.html   informe autónomo (se comparte)
    └── puntos_a_gestionar.md      calidad del dato (interno)
```

Todo lo que puede cambiar por decisión de la Dirección vive en `config.py`:
homologación de nombres, agrupación de programas, puntajes de PETI y PAMUDA,
y la definición de los ejes. El resto del código no tiene constantes de
negocio.

---

## Normalizar la base

```bash
python normalizar.py
```

Produce `salida/sabana_normalizada.xlsx`: las mismas hojas y las mismas filas
de la fuente, más

- `COD_DANE_MPIO` como primera columna de cada hoja, en formato de cinco
  dígitos con cero a la izquierda y guardado como texto;
- el nombre del municipio reescrito con el valor canónico del maestro;
- `SUBREGION` y `EAT` derivadas del maestro en vez de lo que traía cada hoja;
- tres hojas de control: `CONTROL DE CAMBIOS`, `CAMBIOS APLICADOS` y
  `DICCIONARIO`.

No borra columnas, no elimina filas y no toca los indicadores. Solo arregla
las llaves territoriales.

Con la base ya normalizada, el informe se construye cruzando por código:

```bash
python build.py --sabana salida/sabana_normalizada.xlsx
```

El cargador detecta `COD_DANE_MPIO` y deja de usar la tabla de alias. Las
cifras del informe son idénticas con una fuente o con la otra: lo que cambia
es de qué depende el cruce.

**Advertencia.** La normalización convierte el maestro en la única fuente de
verdad, así que sus errores se propagan. Hoy el maestro ubica a Caicedo en
Suroeste mientras las demás hojas lo ubican en Occidente. Corrija el maestro
antes de dar la base por buena.

## Sobre la homologación de nombres

La sábana solo trae `COD_DANE` en dos de sus doce hojas, así que el cruce
entre hojas se hace por nombre de municipio. Como los nombres no están
escritos igual en todas partes, `config.ALIAS_MUNICIPIOS` corrige las
variantes encontradas (SANTAFÉ / SANTA FE, MARINILA / MARINILLA, TURBO y el
nombre largo del distrito, entre otras).

**Esto es un parche, no una solución.** Cuando la fuente incorpore `COD_DANE`
en todas las hojas, esa tabla se puede borrar. Mientras tanto, cada hoja nueva
puede reintroducir el problema; por eso el componente *Calidad del dato*
reporta los registros que no logran cruzar.

---

## Calidad del dato

`calidad.py` audita el archivo en cada construcción, pero **el resultado no
viaja dentro del informe**: es insumo de gestión de la Dirección, no contenido
para el municipio. `reporte_calidad.py` lo escribe aparte en
`salida/puntos_a_gestionar.md`, con magnitud, acción sugerida y campos de
responsable y estado para hacerle seguimiento.

Los hallazgos no están escritos a mano: se recalculan contra el Excel, así que
si la fuente se corrige desaparecen solos.

Revisa, entre otras cosas, nombres que no cruzan, columnas que se contradicen,
coordenadas fuera del departamento, indicadores que aparecen en cero cuando en
realidad no se han levantado, y sedes sin ninguna información de conectividad.

---

## Impresión

La vista Ficha está diseñada para caber en una página A4 vertical. En Chrome
hay que activar **«Gráficos de fondo»** en el diálogo de impresión para que
salgan los colores y las imágenes. Si el botón no abre el diálogo, `Ctrl+P`
(`Cmd+P` en Mac) siempre funciona.
