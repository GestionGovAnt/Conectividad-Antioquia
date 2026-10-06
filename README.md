# Observatorio de Conectividad — Antioquia

Tablero público de conectividad de la Dirección de Gestión Territorial TIC.
Cuatro ejes sobre el mapa del departamento: educación, salud, seguridad y TIC.

```
.github/workflows/publicar.yml   construcción y publicación automáticas
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

## Actualizar los datos

El tablero se reconstruye **cada vez que cambia el Excel en el repositorio** y
además todas las madrugadas a las 6:00.

Para actualizar: descargue la sábana de SharePoint, vaya a
`observatorio/datos/` en GitHub, **Add file → Upload files**, arrastre el
Excel y confirme. En tres minutos el sitio está al día.

No tiene que renombrarlo. El nombre de SharePoint trae tildes
(`sábana_única_visor.xlsx`) y el build lo reconoce igual; avisa en el log cuál
archivo usó.

### Conexión automática con SharePoint

La Gobernación tiene deshabilitados los enlaces anónimos, así que la descarga
automática necesita una aplicación registrada en Entra ID. El código ya está
escrito y probado; falta que TI entregue las credenciales. Ver
[observatorio/DESPLIEGUE.md](observatorio/DESPLIEGUE.md), que incluye el texto
para solicitarlas.

Mientras tanto, subir el archivo a mano toma dos minutos y el resultado es el
mismo.

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
