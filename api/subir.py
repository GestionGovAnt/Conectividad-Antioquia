"""
Recibe la sábana desde la página subir.html y la guarda en el repositorio.

Al guardarla se crea un commit en GitHub. Ese commit dispara las dos
publicaciones que ya existen: Vercel reconstruye el sitio y GitHub Actions
reconstruye GitHub Pages. Esta función no construye nada: solo valida el
archivo y lo deja donde el build lo espera.

    POST /api/subir
        X-Clave:          la clave de carga (SUBIDA_CLAVE)
        X-Nombre-Archivo: nombre original, codificado con encodeURIComponent
        X-Autor:          quién sube, opcional, mismo formato
        cuerpo:           el .xlsx tal cual (application/octet-stream)

    GET /api/subir        dice si la carga está configurada (sin revelar nada)

Variables de entorno (Vercel -> Settings -> Environment Variables):
    GITHUB_TOKEN   Token fine-grained de GitHub con permiso «Contents: Read and
                   write» SOLO sobre este repositorio. Nada más.
    SUBIDA_CLAVE   Clave que se escribe en el formulario. Mínimo 12 caracteres.
    GITHUB_REPO    Opcional. Por defecto GestionGovAnt/Conectividad-Antioquia.
    GITHUB_RAMA    Opcional. Por defecto main.
    RUTA_SABANA    Opcional. Por defecto observatorio/datos/sabana_unica_visor.xlsx.

Solo usa la librería estándar: no hay requirements.txt que mantener.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler
from xml.etree import ElementTree

# Vercel corta el cuerpo de la petición en 4,5 MB. La sábana pesa ~0,6 MB.
TAMANO_MAXIMO = 4 * 1024 * 1024
CLAVE_MINIMA = 12

# Debe coincidir con HOJAS en observatorio/src/config.py. Se exigen todas:
# el build tolera un extracto con hojas faltantes, pero en producción eso
# deja ejes en blanco sin avisar a nadie. Mejor rechazar aquí.
HOJAS_REQUERIDAS = (
    "Municipios",
    "SEDES EDUCATIVAS",
    "SALUD",
    "SEGURIDAD",
    "D. GESTION TERRITORIAL TIC",
    "Consolidados",
    "INVENTARIO GENERAL",
    "Diagnosticos DataCenters",
    "PETI-PAMUDA",
    "USO Y APROPIACION",
    "CAPACITACIONES",
    "Enlaces TIC",
)

NS_HOJA = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
COLOMBIA = timezone(timedelta(hours=-5))


class ErrorCarga(Exception):
    """Error que se le puede mostrar tal cual a quien sube el archivo."""

    def __init__(self, estado: int, mensaje: str):
        super().__init__(mensaje)
        self.estado = estado
        self.mensaje = mensaje


# --------------------------------------------------------------------------
# Configuración
# --------------------------------------------------------------------------
def _config() -> dict:
    return {
        "token": os.environ.get("GITHUB_TOKEN", "").strip(),
        "clave": os.environ.get("SUBIDA_CLAVE", ""),
        "repo": os.environ.get("GITHUB_REPO", "GestionGovAnt/Conectividad-Antioquia").strip(),
        "rama": os.environ.get("GITHUB_RAMA", "main").strip(),
        "ruta": os.environ.get("RUTA_SABANA",
                               "observatorio/datos/sabana_unica_visor.xlsx").strip("/ "),
        # Solo para pruebas locales; en Vercel no se define.
        "api": os.environ.get("GITHUB_API", "https://api.github.com").rstrip("/"),
    }


def _faltantes_config(cfg: dict) -> list[str]:
    faltan = []
    if not cfg["token"]:
        faltan.append("GITHUB_TOKEN")
    if len(cfg["clave"]) < CLAVE_MINIMA:
        faltan.append(f"SUBIDA_CLAVE (mínimo {CLAVE_MINIMA} caracteres)")
    return faltan


# --------------------------------------------------------------------------
# Validación del libro
# --------------------------------------------------------------------------
def validar_libro(datos: bytes) -> list[str]:
    """Devuelve los nombres de hoja, o lanza ErrorCarga con el motivo."""
    if not datos:
        raise ErrorCarga(400, "El archivo llegó vacío.")
    if len(datos) > TAMANO_MAXIMO:
        raise ErrorCarga(413, "El archivo pesa más de 4 MB. La sábana normal "
                              "pesa menos de 1 MB: revise que sea el archivo correcto.")
    if not zipfile.is_zipfile(io.BytesIO(datos)):
        raise ErrorCarga(415, "No es un libro .xlsx. Si es .xls o .csv, ábralo en "
                              "Excel y guárdelo como «Libro de Excel (.xlsx)».")
    try:
        with zipfile.ZipFile(io.BytesIO(datos)) as z:
            nombres = set(z.namelist())
            if "xl/workbook.xml" not in nombres:
                raise ErrorCarga(415, "El archivo es un .zip pero no un libro de Excel.")
            if "xl/vbaProject.bin" in nombres:
                raise ErrorCarga(415, "El libro trae macros. Guárdelo como "
                                      "«Libro de Excel (.xlsx)», sin macros.")
            info = z.getinfo("xl/workbook.xml")
            if info.file_size > 2 * 1024 * 1024:   # un workbook.xml normal pesa KB
                raise ErrorCarga(415, "El libro tiene una estructura inesperada.")
            raiz = ElementTree.fromstring(z.read(info))
    except ErrorCarga:
        raise
    except (zipfile.BadZipFile, ElementTree.ParseError, KeyError):
        raise ErrorCarga(415, "El archivo está dañado o no es un libro de Excel válido.")

    hojas = [h.get("name", "") for h in raiz.iter(NS_HOJA + "sheet")]
    faltan = [h for h in HOJAS_REQUERIDAS if h not in hojas]
    if faltan:
        raise ErrorCarga(422, "Al libro le faltan hojas que el tablero necesita: " +
                              ", ".join(f"«{h}»" for h in faltan) +
                              ". Revise que sea la sábana única completa y que "
                              "los nombres de las hojas no hayan cambiado.")
    return hojas


def sha_git(datos: bytes) -> str:
    """El SHA que GitHub le asigna a un archivo con este contenido."""
    return hashlib.sha1(b"blob %d\0" % len(datos) + datos).hexdigest()


# --------------------------------------------------------------------------
# GitHub
# --------------------------------------------------------------------------
def _github(cfg: dict, metodo: str, ruta: str, cuerpo: dict | None = None):
    req = urllib.request.Request(
        cfg["api"] + ruta,
        method=metodo,
        data=None if cuerpo is None else json.dumps(cuerpo).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + cfg["token"],
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "observatorio-conectividad-carga",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, _json(r.read())
    except urllib.error.HTTPError as e:
        return e.code, _json(e.read())
    except (urllib.error.URLError, TimeoutError):
        raise ErrorCarga(502, "No se pudo contactar a GitHub. Intente de nuevo en un minuto.")


def _json(crudo: bytes) -> dict:
    try:
        return json.loads(crudo or b"{}")
    except ValueError:
        return {}


def guardar_en_github(cfg: dict, datos: bytes, archivo: str, autor: str) -> dict:
    ruta_api = (f"/repos/{cfg['repo']}/contents/"
                f"{urllib.parse.quote(cfg['ruta'])}")
    rama = urllib.parse.quote(cfg["rama"])

    estado, actual = _github(cfg, "GET", f"{ruta_api}?ref={rama}")
    if estado in (401, 403):
        raise ErrorCarga(503, "GitHub rechazó el token configurado (vencido o sin "
                              "permiso de escritura sobre el repositorio). Hay que "
                              "renovar GITHUB_TOKEN en Vercel.")
    if estado not in (200, 404):
        raise ErrorCarga(502, f"GitHub respondió {estado} al leer la sábana actual.")
    sha_actual = actual.get("sha") if estado == 200 else None

    if sha_actual and sha_actual == sha_git(datos):
        return {"estado": "sin_cambios"}

    ahora = datetime.now(COLOMBIA).strftime("%Y-%m-%d %H:%M")
    mensaje = ("Actualizar sábana desde el formulario web\n\n"
               f"Archivo: {archivo or 'sin nombre'}\n"
               f"Subido por: {autor or 'sin nombre'}\n"
               f"Fecha: {ahora} (hora Colombia)")
    cuerpo = {
        "message": mensaje,
        "content": base64.b64encode(datos).decode("ascii"),
        "branch": cfg["rama"],
    }
    if sha_actual:
        cuerpo["sha"] = sha_actual

    estado, resp = _github(cfg, "PUT", ruta_api, cuerpo)
    if estado in (409, 422) and sha_actual:
        raise ErrorCarga(409, "Otra actualización llegó al mismo tiempo. "
                              "Espere un minuto y vuelva a subir el archivo.")
    if estado in (401, 403):
        raise ErrorCarga(503, "El token de GitHub no tiene permiso de escritura "
                              "sobre el repositorio. Hay que revisar GITHUB_TOKEN.")
    if estado not in (200, 201):
        raise ErrorCarga(502, f"GitHub respondió {estado} al guardar el archivo.")

    commit = resp.get("commit") or {}
    return {
        "estado": "actualizado",
        "commit": (commit.get("sha") or "")[:7],
        "url": commit.get("html_url", ""),
    }


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
def _texto_cabecera(valor: str | None, limite: int = 120) -> str:
    """Decodifica una cabecera enviada con encodeURIComponent y la limpia."""
    if not valor:
        return ""
    try:
        valor = urllib.parse.unquote(valor, errors="strict")
    except UnicodeDecodeError:
        return ""
    valor = re.sub(r"[\x00-\x1f\x7f]", " ", valor).strip()
    return valor[:limite]


def procesar(cabeceras, leer_cuerpo) -> tuple[int, dict]:
    # La clave se revisa ANTES de leer el cuerpo: a quien no la tenga no se
    # le reciben 4 MB.
    cfg = _config()
    faltan = _faltantes_config(cfg)
    if faltan:
        raise ErrorCarga(503, "La carga todavía no está configurada en Vercel. "
                              "Falta: " + ", ".join(faltan) + ".")

    clave = cabeceras.get("X-Clave", "")
    if not hmac.compare_digest(clave.encode("utf-8"), cfg["clave"].encode("utf-8")):
        time.sleep(1.5)   # frena intentos repetidos de adivinar la clave
        raise ErrorCarga(401, "La clave de carga no es correcta.")

    largo = cabeceras.get("Content-Length")
    if largo is None:
        raise ErrorCarga(411, "La petición no indica el tamaño del archivo.")
    try:
        largo = int(largo)
    except ValueError:
        raise ErrorCarga(400, "Tamaño de archivo inválido.")
    if largo > TAMANO_MAXIMO:
        raise ErrorCarga(413, "El archivo pesa más de 4 MB.")

    datos = leer_cuerpo(largo)
    hojas = validar_libro(datos)
    archivo = _texto_cabecera(cabeceras.get("X-Nombre-Archivo"))
    autor = _texto_cabecera(cabeceras.get("X-Autor"), 80)

    resultado = guardar_en_github(cfg, datos, archivo, autor)
    resultado.update({"ok": True, "hojas": len(hojas), "bytes": len(datos)})
    return 200, resultado


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        faltan = _faltantes_config(_config())
        self._responder(200, {"ok": True, "configurado": not faltan})

    def do_POST(self):
        try:
            estado, cuerpo = procesar(self.headers, self.rfile.read)
        except ErrorCarga as e:
            estado, cuerpo = e.estado, {"ok": False, "error": e.mensaje}
        except Exception as e:  # noqa: BLE001 — nunca devolver la traza al navegador
            print(f"subir: error inesperado: {type(e).__name__}: {e}")
            estado, cuerpo = 500, {"ok": False,
                                   "error": "Error inesperado al procesar el archivo."}
        self._responder(estado, cuerpo)

    def _responder(self, estado: int, cuerpo: dict) -> None:
        crudo = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        self.send_response(estado)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(crudo)))
        self.end_headers()
        self.wfile.write(crudo)
