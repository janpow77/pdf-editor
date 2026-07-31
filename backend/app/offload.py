"""CPU-lastige Verarbeitung aus der Event-Loop auslagern.

Die Datei-Endpunkte sind ``async def`` (sie müssen ``await file.read()``
aufrufen), rechnen danach aber synchron mit PyMuPDF, pikepdf oder
LibreOffice. Ohne Auslagerung blockiert jede Verarbeitung den einzigen
Event-Loop-Thread: Solange ein 200-Seiten-PDF zusammengeführt wird, wartet
jede andere Anfrage — auch die Health-Abfrage und die Uploads anderer
Nutzerinnen und Nutzer.

``run_cpu`` schiebt den Aufruf in den Worker-Thread-Pool von AnyIO, den
FastAPI ohnehin für synchrone Endpunkte betreibt. PyMuPDF und pikepdf geben
das GIL während der C-Arbeit frei, deshalb laufen mehrere Dokumente dort
tatsächlich parallel.

Bewusst nicht per Prozess-Pool: die Dokumente lägen dann zusätzlich in einem
zweiten Prozessspeicher und müssten serialisiert werden — das widerspricht
dem Versprechen, Dateien so kurz wie möglich im Speicher zu halten.
"""

from collections.abc import Callable
from functools import partial
from typing import ParamSpec, TypeVar

from anyio import to_thread

P = ParamSpec("P")
R = TypeVar("R")


async def run_cpu(fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
    """``fn(*args, **kwargs)`` im Thread-Pool ausführen und Ergebnis liefern."""
    return await to_thread.run_sync(partial(fn, *args, **kwargs))
