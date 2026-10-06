"""
Descarga de la sábana desde SharePoint.

Por qué no se lee desde el navegador
------------------------------------
Un sitio estático no puede abrir un archivo de SharePoint: la biblioteca está
detrás de la autenticación de la organización. Hacerlo desde el navegador
obligaría a que cada visitante inicie sesión con su cuenta institucional, lo
que descarta compartir el tablero con un alcalde o publicarlo abierto.

La solución es al revés: **la descarga ocurre en la construcción**, no en la
visita. Un proceso programado baja el Excel, recalcula y publica un HTML ya
resuelto. El visitante no necesita cuenta ni permisos.

Dos modos
---------
1. `graph`  — aplicación registrada en Entra ID con permiso de solo lectura.
   Es el modo correcto para producción. Requiere TENANT_ID, CLIENT_ID y
   CLIENT_SECRET, y que TI apruebe el registro.

2. `enlace` — enlace de descarga directa de SharePoint o OneDrive. No requiere
   registro ni secretos, pero el enlace debe permitir acceso anónimo, cosa que
   muchas organizaciones bloquean por política.

Las credenciales se leen de variables de entorno. Nunca van en el código ni
en el repositorio.
"""
from __future__ import annotations

import os
import urllib.parse
import urllib.request
from pathlib import Path

GRAPH = "https://graph.microsoft.com/v1.0"
LOGIN = "https://login.microsoftonline.com"


class ErrorSharePoint(Exception):
    """Falló la descarga. El build sigue con la copia local."""


def _pedir(url: str, datos: bytes | None = None,
           cabeceras: dict | None = None) -> bytes:
    peticion = urllib.request.Request(url, data=datos, headers=cabeceras or {})
    try:
        with urllib.request.urlopen(peticion, timeout=120) as respuesta:
            return respuesta.read()
    except Exception as e:                      # noqa: BLE001
        raise ErrorSharePoint(f"{url.split('?')[0]} -> {e}") from e


def _token(tenant: str, cliente: str, secreto: str) -> str:
    import json
    cuerpo = urllib.parse.urlencode({
        "client_id": cliente,
        "client_secret": secreto,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }).encode()
    bruto = _pedir(f"{LOGIN}/{tenant}/oauth2/v2.0/token", cuerpo,
                   {"Content-Type": "application/x-www-form-urlencoded"})
    datos = json.loads(bruto)
    if "access_token" not in datos:
        raise ErrorSharePoint("La respuesta no trae access_token: " + str(datos))
    return datos["access_token"]


def descargar_graph(destino: Path) -> Path:
    """Baja el archivo usando una aplicación registrada en Entra ID.

    Variables de entorno:
        SP_TENANT_ID, SP_CLIENT_ID, SP_CLIENT_SECRET
        SP_HOST      contoso.sharepoint.com
        SP_SITIO     /sites/PlaneacionTIC
        SP_RUTA      /Documentos compartidos/General/sabana_unica_visor.xlsx
    """
    import json
    faltan = [v for v in ("SP_TENANT_ID", "SP_CLIENT_ID", "SP_CLIENT_SECRET",
                          "SP_HOST", "SP_SITIO", "SP_RUTA")
              if not os.environ.get(v)]
    if faltan:
        raise ErrorSharePoint("Faltan variables: " + ", ".join(faltan))

    token = _token(os.environ["SP_TENANT_ID"], os.environ["SP_CLIENT_ID"],
                   os.environ["SP_CLIENT_SECRET"])
    auth = {"Authorization": "Bearer " + token}

    host = os.environ["SP_HOST"]
    sitio = os.environ["SP_SITIO"].strip("/")
    info = json.loads(_pedir(f"{GRAPH}/sites/{host}:/{sitio}", None, auth))
    id_sitio = info["id"]

    ruta = urllib.parse.quote(os.environ["SP_RUTA"].strip("/"))
    contenido = _pedir(
        f"{GRAPH}/sites/{id_sitio}/drive/root:/{ruta}:/content", None, auth)

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    return destino


def descargar_enlace(destino: Path) -> Path:
    """Baja el archivo desde un enlace de descarga directa.

    Variable de entorno: SP_ENLACE
    Debe ser un enlace que no pida inicio de sesión.
    """
    enlace = os.environ.get("SP_ENLACE")
    if not enlace:
        raise ErrorSharePoint("Falta la variable SP_ENLACE")
    contenido = _pedir(enlace, None, {"User-Agent": "observatorio-build"})
    if contenido[:2] != b"PK":          # un .xlsx es un ZIP
        raise ErrorSharePoint(
            "Lo descargado no es un Excel. Probablemente el enlace pide "
            "inicio de sesión y devolvió la página de login.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    return destino


def sincronizar(destino: Path, modo: str | None = None) -> tuple[bool, str]:
    """Intenta actualizar la copia local. Devuelve (se_actualizó, mensaje).

    Si falla, no interrumpe: el build sigue con la copia que haya en el
    repositorio. Un tablero con el dato de ayer sirve; uno que no compila,
    no.
    """
    modo = modo or os.environ.get("SP_MODO", "")
    if not modo:
        return False, "sin configurar (se usa la copia local)"
    try:
        if modo == "graph":
            descargar_graph(destino)
        elif modo == "enlace":
            descargar_enlace(destino)
        else:
            return False, f"modo desconocido: {modo}"
        tam = destino.stat().st_size / 1024
        return True, f"descargado de SharePoint ({tam:.0f} KB)"
    except ErrorSharePoint as e:
        return False, f"no se pudo descargar ({e}) — se usa la copia local"
