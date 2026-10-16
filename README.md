# Observatorio de Conectividad — Antioquia

Tablero público de conectividad de la Dirección de Gestión Territorial TIC.
Cuatro ejes sobre el mapa del departamento: educación, salud, seguridad y TIC.

```
.github/workflows/publicar.yml   construcción y publicación en GitHub Pages
vercel.json                      construcción y publicación en Vercel
api/subir.py                     recibe la sábana desde la página de carga
observatorio/                    el tablero de mapa
ficha/                           la ficha municipal detallada
```

---

## Montarlo en GitHub

### 1. Descomprimir

Al descomprimir deben quedarle **estas carpetas sueltas**, no dentro de otra:

```
.github/
observatorio/
ficha/
README.md
.gitignore
```

Si le quedó todo dentro de una carpeta, entre a esa carpeta: lo que se sube es
su contenido, no ella.

### 2. Crear el repositorio

GitHub → **New repository**. Sin README ni .gitignore: este paquete los trae.

### 3. Subir

**Add file → Upload files** y arrastre las carpetas `observatorio` y `ficha`
más los archivos `README.md` y `.gitignore`. Son 53 archivos, entran en una
sola tanda.

La carpeta `.github` empieza por punto y Windows a veces la oculta. Si no
aparece para arrastrar, no insista: créela desde el navegador con **Add file →
Create new file**, escribiendo como nombre

```
.github/workflows/publicar.yml
```

y pegando el contenido de ese archivo. Al escribir cada `/` GitHub va creando
las carpetas.

### 4. Activar Pages

**Settings → Pages → Source: `GitHub Actions`**. No elija «Deploy from a
branch».

### 5. Publicar

**Actions → Publicar observatorio → Run workflow.** Unos tres minutos.

El sitio queda en `https://<usuario>.github.io/<repositorio>/`.

---

## Vercel

Publicado en **https://conectividad-antioquia.vercel.app**. El proyecto está
conectado al repositorio: **cada push a `main` lo reconstruye solo**. La
configuración del build vive en `vercel.json` (instala las dependencias en un
entorno virtual, corre `publicar.py` y publica `observatorio/sitio`).

**No active la variable `VERCEL_DEPLOY` en GitHub.** El paso de Vercel que
trae el workflow es de una configuración anterior; si se activa, el sitio se
publicaría dos veces por caminos distintos.

Vercel no corre la ejecución diaria de las 6:00, solo los push. Hoy da igual:
los datos cambian cuando cambia el Excel del repositorio. Cuando se active la
descarga desde SharePoint (modo `graph`), habrá que crear un *Deploy Hook* en
Vercel y llamarlo desde el workflow.

---

## Actualizar los datos

Abra **https://conectividad-antioquia.vercel.app/subir.html** (también está el
enlace «Actualizar datos» al pie del panel del tablero), arrastre la sábana tal
como la descarga de SharePoint, escriba su nombre y la clave de carga, y pulse
**Subir y actualizar**. La página avisa cuando el tablero ya muestra los datos
nuevos, normalmente en uno o dos minutos.

Qué pasa por dentro: `api/subir.py` revisa que el archivo sea un `.xlsx` sin
macros y que traiga las 12 hojas que lee el tablero; si falta alguna, lo
rechaza y no publica nada. Si está bien, lo guarda como
`observatorio/datos/sabana_unica_visor.xlsx` con un commit que lleva el nombre
de quien lo subió. Ese commit reconstruye Vercel y GitHub Pages. Si el archivo
es idéntico al publicado, no hace nada.

Si una carga sale mal, el historial del archivo en GitHub permite volver a la
versión anterior.

### Configurar la carga (una sola vez)

En Vercel → proyecto → **Settings → Environment Variables**, cree:

| Nombre | Valor |
|---|---|
| `GITHUB_TOKEN` | Token *fine-grained* de GitHub (ver abajo) |
| `SUBIDA_CLAVE` | La clave que se escribirá en el formulario, de 12 caracteres o más |

y vuelva a desplegar (**Deployments → … → Redeploy**) para que la función las
lea.

El token se crea en GitHub → **Settings → Developer settings → Personal access
tokens → Fine-grained tokens → Generate new token**:

- *Resource owner*: `GestionGovAnt`
- *Repository access*: **Only select repositories** → `Conectividad-Antioquia`
- *Permissions → Repository permissions → Contents*: **Read and write**
- Nada más. Póngale vencimiento y anote la fecha: cuando venza, la página de
  carga dirá que hay que renovar `GITHUB_TOKEN`.

Comparta la clave de carga solo con quien actualiza los datos. Cambiarla es
editar `SUBIDA_CLAVE` y volver a desplegar.

### A mano, desde GitHub

Sigue funcionando: en `observatorio/datos/` de GitHub, **Add file → Upload
files**. Pero súbalo con el nombre exacto **`sabana_unica_visor.xlsx`** para
que reemplace al actual. Si lo sube con el nombre de SharePoint
(`sábana_única_visor.xlsx`), queda como un segundo archivo y el build sigue
usando el de siempre.

### Conexión automática con SharePoint

La Gobernación tiene deshabilitados los enlaces anónimos, así que la descarga
automática necesita una aplicación registrada en Entra ID. El código ya está
escrito y probado; falta que TI entregue las credenciales. Ver
[observatorio/DESPLIEGUE.md](observatorio/DESPLIEGUE.md), que incluye el texto
para solicitarlas.

Mientras tanto, subir el archivo con la página de carga toma un minuto y el
resultado es el mismo.

---

## El trazado de fibra óptica

Los 76 KMZ pesan 29 MB y su lectura siempre da lo mismo, así que el
repositorio guarda solo el resultado: `observatorio/datos/fibra_trazado.geojson`
(338 KB, 73 municipios, 608.964 metros medidos).

Si llegan KMZ nuevos, póngalos en `observatorio/datos/kmz/` y el build los
reprocesa y actualiza ese archivo. Si la carpeta está vacía, usa el resultado
guardado.

---

## Lo que falta

**Inversión.** Apagada hasta que lleguen los datos
(`observatorio/src/config.py`, `MOSTRAR_INVERSION = False`). Está oculta por
completo, no en ceros: un cero se lee como «no se invirtió nada», que es
distinto de «no tenemos el dato». Cuando llegue la tabla, se pone el CSV en
`observatorio/datos/inversion.csv`, se cambia la bandera y se reconstruye.

---

## Advertencias

**El sitio es público.** GitHub Pages en un repositorio gratuito no tiene
control de acceso. Si la Dirección considera que estos datos no deben ser
abiertos, resuélvalo antes de divulgar el enlace. Alternativa gratuita con
control de acceso: Cloudflare Pages con Cloudflare Access.

**El tablero muestra el dato de la última construcción**, no el de este
segundo. Para información que cambia por semanas es suficiente.

**Desactive la traducción automática del navegador en GitHub.** Traduce los
nombres de archivos y carpetas, y si traduce el contenido de un YAML que esté
pegando, el flujo deja de funcionar.

---

## Probarlo en el computador

```bash
cd observatorio
pip install -r requirements.txt
python publicar.py --ficha ../ficha
python -m http.server 8000 --directory sitio
```

Abra `http://localhost:8000`.
