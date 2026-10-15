"""
Fecha de corte de los datos, que no es la fecha de construcción.

El sitio se reconstruye solo todos los días a las 6 de la mañana. Si la
ficha impresa mostrara la fecha de construcción, diría «hoy» aunque el
Excel lleve un mes sin cambiar, y quien la lea va a entender que el dato es
de hoy. En un documento que se imprime y circula, eso es peor que no poner
fecha.

La fecha buena es la del último guardado del Excel. Excel la escribe dentro
del propio archivo cada vez que alguien guarda, así que viaja con él:
sobrevive a git, a una descarga, a un correo y a un cambio de computador.
No depende de la fecha del sistema de archivos, que git no conserva y que
en la nube es siempre la de la descarga.

Si algún día un script vuelve a escribir el Excel, la fecha pasará a ser la
de esa corrida. Mientras el archivo se edite y se guarde en Excel, es
exactamente lo que se busca: cuándo cambiaron los datos por última vez.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import openpyxl

# Colombia no aplica horario de verano, así que un desfase fijo es exacto y
# evita depender de la base de zonas horarias del sistema.
UTC_A_COLOMBIA = timedelta(hours=-5)

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def corte_de_datos(archivo: Path | None) -> date | None:
    """Cuándo se guardó por última vez el Excel. None si no se puede saber.

    Devolver None es parte del contrato: es mejor que la ficha no muestre
    fecha a que muestre una inventada.
    """
    if archivo is None:
        return None

    guardado = _del_documento(archivo)
    if guardado is not None:
        return guardado

    # Respaldo para corridas locales. En la nube esta fecha es la de la
    # descarga del repositorio, no la del dato, así que no sirve sola.
    try:
        marca = datetime.fromtimestamp(Path(archivo).stat().st_mtime)
        return marca.date()
    except OSError:
        return None


def _del_documento(archivo: Path) -> date | None:
    """Propiedad «modified» del libro, en hora de Colombia."""
    try:
        libro = openpyxl.load_workbook(archivo, read_only=True)
    except Exception:
        return None
    try:
        marca = libro.properties.modified
    finally:
        libro.close()
    if marca is None:
        return None
    # openpyxl la entrega en UTC y sin zona.
    return (marca + UTC_A_COLOMBIA).date()


def en_letras(dia: date | None) -> str:
    """15 de octubre de 2026. Cadena vacía si no hay fecha."""
    if dia is None:
        return ""
    return f"{dia.day} de {MESES[dia.month - 1]} de {dia.year}"


def corta(dia: date | None) -> str:
    """15/10/2026. Cadena vacía si no hay fecha."""
    return dia.strftime("%d/%m/%Y") if dia else ""
