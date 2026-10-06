# Despliegue del Observatorio

## Lo primero: por qué el tablero no lee SharePoint directamente

Un sitio estático no puede abrir un archivo de SharePoint. La biblioteca está
detrás de la autenticación de la organización, y hacerlo desde el navegador
obligaría a que **cada visitante inicie sesión con su cuenta institucional**.
Eso descarta compartir el tablero con una alcaldía o publicarlo abierto.

La solución va al revés: **la descarga ocurre en la construcción, no en la
visita.** Un proceso programado baja el Excel, recalcula y publica un HTML ya
resuelto. El visitante solo abre una página.

```
SharePoint ──► GitHub Actions ──► build.py ──► sitio/ ──► GitHub Pages
  (Excel)        cada noche        recalcula     HTML       público
```

Consecuencia que conviene tener clara: **el tablero muestra el dato de la
última construcción**, no el de este segundo. Con una corrida diaria basta
para información que cambia por semanas.

---

## Paso 1 — Repositorio

Un repositorio con los dos proyectos al mismo nivel:

```
repo/
├── observatorio/        este proyecto
└── ficha/               el proyecto de la ficha municipal
```

El flujo de GitHub Actions vive en `observatorio/.github/workflows/`. Si deja
los proyectos en otra disposición, ajuste la ruta `--ficha` en el flujo.

## Paso 2 — Activar GitHub Pages

En el repositorio: **Settings → Pages → Source: GitHub Actions**.

Queda publicado en `https://<usuario>.github.io/<repo>/`.

**Advertencia:** GitHub Pages en un repositorio gratuito es **público**. Si la
Dirección considera que estos datos no deben ser abiertos, hay que resolverlo
antes de publicar. Alternativas gratuitas con control de acceso: Cloudflare
Pages con Cloudflare Access, o Netlify con autenticación. Dígalo y lo ajusto.

## Paso 3 — Conectar SharePoint

### Modo `enlace` (el más rápido)

Si pueden generar un enlace de descarga directa del archivo que no pida
iniciar sesión:

1. En SharePoint: **Compartir → Cualquier persona con el vínculo → Ver**.
2. Al final de la URL cambie `?web=1` por `?download=1`.
3. En el repositorio: **Settings → Secrets and variables → Actions**
   - Variable `SP_MODO` = `enlace`
   - Secreto `SP_ENLACE` = la URL

Sin registros ni permisos. **Pero muchas organizaciones bloquean los enlaces
anónimos por política**, y en ese caso hay que ir al otro modo.

### Modo `graph` (el correcto para producción)

Requiere que TI registre una aplicación. Pídales esto:

> Necesitamos registrar una aplicación en Entra ID, de solo lectura, para que
> un proceso automatizado descargue un archivo de una biblioteca de SharePoint
> una vez al día.
>
> - Permiso de aplicación: `Sites.Selected` (preferible) o `Files.Read.All`
> - Alcance: únicamente el sitio `<nombre del sitio>`
> - Necesitamos: Tenant ID, Client ID y un Client Secret

`Sites.Selected` es el permiso que conviene pedir: limita el acceso a un solo
sitio en lugar de a toda la organización. A TI le va a costar menos aprobarlo.

Configure en el repositorio:

| Dónde | Nombre | Ejemplo |
|---|---|---|
| Variable | `SP_MODO` | `graph` |
| Variable | `SP_HOST` | `antioquia.sharepoint.com` |
| Variable | `SP_SITIO` | `/sites/PlaneacionTIC` |
| Variable | `SP_RUTA` | `/Documentos compartidos/General/sabana.xlsx` |
| Secreto | `SP_TENANT_ID` | |
| Secreto | `SP_CLIENT_ID` | |
| Secreto | `SP_CLIENT_SECRET` | |

Los secretos van en **Secrets**, nunca en **Variables** ni en el código.

### Si falla la descarga

El build **no se detiene**: usa la copia del Excel que esté en el repositorio
y lo advierte en el log. Un tablero con el dato de ayer sirve; uno que no
compila, no.

---

## Paso 4 — Probar antes de publicar

```bash
cd observatorio
python publicar.py --ficha ../ficha
python -m http.server 8000 --directory sitio
```

Abra `http://localhost:8000`. Verifique que carga el mapa base, que el botón
«Ficha completa» abre la ficha, y que la ficha vuelve al mapa.

---

## Alternativas de hosting gratuito

| Opción | A favor | En contra |
|---|---|---|
| **GitHub Pages** | Ya trae el cron y el despliegue | Público en plan gratuito |
| **Cloudflare Pages** | Permite restringir acceso gratis | El cron se configura aparte |
| **Netlify** | Despliegue simple | 100 GB/mes de tráfico |

Los tres sirven el mismo `sitio/`. La recomendación es GitHub Pages porque la
construcción programada y el despliegue quedan en el mismo lugar.

---

## El componente de inversión

Está **apagado**: `config.MOSTRAR_INVERSION = False`. No aparece el selector de
inversión, ni el bloque del panel, ni las columnas en el CSV.

Se prefiere ocultarlo a mostrarlo en ceros, porque un tablero con ceros se lee
como «no se invirtió nada», que es distinto de «no tenemos el dato».

Cuando llegue la tabla: ponga el CSV en `datos/inversion.csv`, cambie la
bandera a `True` y vuelva a construir. No hay que tocar nada más.
