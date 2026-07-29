"""In-Memory-Job-Queue für langlaufende Verarbeitungen (OCR, Vergleich, Scan).

Bewusst ohne neue Infrastruktur (kein Redis/Celery): ThreadPool + RAM-Store.
Datenschutz-Verträge:
- Ergebnisse liegen nur im Arbeitsspeicher, werden beim ersten Abruf gelöscht
  und verfallen sonst nach TTL (Hintergrund-Aufräumen bei jedem Zugriff).
- Jobs sind an den Aufrufer gebunden (Nutzer-ID bzw. Client-IP) — fremde
  Job-IDs liefern 404.
Grenze: Der Store ist prozesslokal — bei mehreren Backend-Replikas braucht es
Sticky-Sessions oder einen externen Store (im KONZEPT vermerkt).
"""

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

_TTL_SECONDS = 15 * 60
_MAX_JOBS_PER_OWNER = 5
_MAX_ACTIVE_TOTAL = 20          # global queued+running
_MAX_STORED_JOBS = 60           # harte Obergrenze inkl. fertiger Ergebnisse
_MAX_RESULT_BYTES_TOTAL = 512 * 1024 * 1024  # RAM-Budget für Ergebnisse

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="pdfjob")
_lock = threading.Lock()


@dataclass
class Job:
    id: str
    owner: str
    status: str = "queued"  # queued | running | done | error
    created: float = field(default_factory=time.monotonic)
    filename: str = "ergebnis.pdf"
    media_type: str = "application/pdf"
    headers: dict = field(default_factory=dict)
    content: bytes | None = None
    error: str | None = None


_jobs: dict[str, Job] = {}


def _cleanup() -> None:
    now = time.monotonic()
    for job_id in [j for j, job in _jobs.items() if now - job.created > _TTL_SECONDS]:
        _jobs.pop(job_id, None)
    # RAM-Budget: älteste fertige Ergebnisse verwerfen, bis Budget eingehalten
    done = sorted(
        (j for j in _jobs.values() if j.status == "done" and j.content),
        key=lambda j: j.created,
    )
    total = sum(len(j.content or b"") for j in done)
    while done and (total > _MAX_RESULT_BYTES_TOTAL or len(_jobs) > _MAX_STORED_JOBS):
        victim = done.pop(0)
        total -= len(victim.content or b"")
        _jobs.pop(victim.id, None)


def submit(owner: str, filename: str, media_type: str, fn, *args) -> str:
    """Job einreihen. ``fn(*args)`` muss (content, headers) liefern oder werfen."""
    with _lock:
        _cleanup()
        active_all = [j for j in _jobs.values() if j.status in ("queued", "running")]
        if len(active_all) >= _MAX_ACTIVE_TOTAL:
            raise RuntimeError("Server ist ausgelastet — bitte kurz warten")
        active = [j for j in active_all if j.owner == owner]
        if len(active) >= _MAX_JOBS_PER_OWNER:
            raise RuntimeError("Zu viele laufende Aufträge — bitte warten")
        job = Job(id=uuid.uuid4().hex, owner=owner, filename=filename, media_type=media_type)
        _jobs[job.id] = job

    def _run() -> None:
        job.status = "running"
        try:
            content, headers = fn(*args)
            job.content = content
            job.headers = headers or {}
            job.status = "done"
        except Exception as e:  # Fehlertext ohne interne Details
            job.error = str(e)[:300]
            job.status = "error"

    _executor.submit(_run)
    return job.id


def get(job_id: str, owner: str) -> Job | None:
    with _lock:
        _cleanup()
        job = _jobs.get(job_id)
    if job is None or job.owner != owner:
        return None
    return job


def take_result(job_id: str, owner: str) -> Job | None:
    """Ergebnis einmalig abholen — danach ist der Job gelöscht."""
    with _lock:
        _cleanup()
        job = _jobs.get(job_id)
        if job is None or job.owner != owner or job.status != "done":
            return None
        _jobs.pop(job_id, None)
    return job
