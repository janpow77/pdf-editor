"""API der erweiterten PDF-Werkzeuge (siehe pdf_extras_service)."""

import io
import json
import math

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.api.deps import current_limits
from app.config import settings
from app.offload import run_cpu
from app.services import redaction as redaction_engine
from app.services.pdf_extras_service import NER_PATTERN_ID, REDACTION_PATTERNS, get_pdf_extras

router = APIRouter(prefix="/pdf-extras", tags=["PDF Extras"])

_PREVIEW_REQUIRED = (
    "Schwärzen ohne Vorschau ist abgeschaltet. Bitte /redact/plan und "
    "/redact/apply verwenden (Plan → Auswahl → Anwendung)."
)


def _require_legacy_redaction() -> None:
    """Alte Endpunkte schwärzen ohne Vorschau — nur auf ausdrücklichen Wunsch."""
    if not settings.redact_without_preview:
        raise HTTPException(status_code=410, detail=_PREVIEW_REQUIRED)


def _validate_pdf(file: UploadFile, content: bytes):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Nur PDF-Dateien erlaubt")
    limits = current_limits()
    if len(content) > limits.max_file:
        raise HTTPException(
            status_code=400, detail=f"Datei zu groß (max {limits.max_file_mb} MB)"
        )


def _safe_name(name: str) -> str:
    """Anführungszeichen/Steuerzeichen aus Dateinamen entfernen (Header-Injection)."""
    import re as _re

    return _re.sub(r'[\r\n"\\;]+', "_", name)[:150] or "datei"


def _pdf_response(data: bytes, filename: str, headers: dict | None = None):
    h = {"Content-Disposition": f'attachment; filename="{_safe_name(filename)}"'}
    if headers:
        h.update(headers)
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf", headers=h)


def _name(file: UploadFile) -> str:
    return (file.filename or "document").rsplit(".", 1)[0]


@router.get("/status")
async def check_status():
    return get_pdf_extras().check_features()


@router.post("/to-text")
async def pdf_to_text(file: UploadFile = File(...)):
    content = await file.read()
    _validate_pdf(file, content)
    result = await run_cpu(get_pdf_extras().extract_text, content)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return StreamingResponse(
        io.BytesIO(result.file_content),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{_safe_name(_name(file))}.txt"'},
    )


@router.post("/form/fields")
async def form_fields(file: UploadFile = File(...)):
    content = await file.read()
    _validate_pdf(file, content)
    result = await run_cpu(get_pdf_extras().get_form_fields, content)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.metadata


@router.post("/form/fill")
async def form_fill(
    file: UploadFile = File(...),
    values: str = Form(..., description='JSON-Objekt {"feldname": "wert"}'),
    flatten: bool = Form(False, description="Felder nach dem Ausfüllen einbrennen"),
):
    content = await file.read()
    _validate_pdf(file, content)
    try:
        values_dict = json.loads(values)
        assert isinstance(values_dict, dict)
    except (json.JSONDecodeError, AssertionError):
        raise HTTPException(status_code=400, detail="values muss ein JSON-Objekt sein")
    result = await run_cpu(get_pdf_extras().fill_form, content, values_dict, flatten=flatten)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return _pdf_response(
        result.file_content,
        f"{_name(file)}_ausgefuellt.pdf",
        headers={"X-Fields-Filled": str((result.metadata or {}).get("filled", 0))},
    )


@router.post("/form/export-csv")
async def form_export_csv(
    file: UploadFile = File(...),
    template: bool = Form(
        False, description="Statt der Werte eine leere Vorlage für die Serienbefüllung"
    ),
):
    """Formularfelder als CSV (Semikolon, UTF-8-BOM — Excel-tauglich)."""
    content = await file.read()
    _validate_pdf(file, content)
    service = get_pdf_extras()
    result = await run_cpu(
        service.export_values_template_csv
        if template
        else service.export_field_values_csv,
        content,
    )
    if not result.success:
        raise HTTPException(status_code=422, detail=result.error)
    suffix = "_vorlage" if template else "_formulardaten"
    return StreamingResponse(
        io.BytesIO(result.file_content),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{_safe_name(_name(file))}{suffix}.csv"',
            "X-Fields": str((result.metadata or {}).get("fields", 0)),
        },
    )


@router.post("/form/fill-csv")
async def form_fill_csv(
    file: UploadFile = File(...),
    data: UploadFile = File(..., description="CSV mit Kopfzeile aus Feldnamen"),
    flatten: bool = Form(False),
):
    """Serienbefüllung: eine CSV-Zeile ergibt ein ausgefülltes PDF."""
    content = await file.read()
    _validate_pdf(file, content)
    if not data.filename or not data.filename.lower().endswith((".csv", ".txt")):
        raise HTTPException(status_code=400, detail="Datenquelle muss eine CSV-Datei sein")
    csv_content = await data.read()
    if len(csv_content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="CSV-Datei zu groß (max 5 MB)")
    result = await run_cpu(get_pdf_extras().fill_from_csv, content, csv_content, flatten=flatten)
    if not result.success:
        raise HTTPException(status_code=422, detail=result.error)
    meta = result.metadata or {}
    headers = {
        "X-Rows": str(meta.get("rows", 0)),
        "X-Warnings": str(len(result.warnings or [])),
    }
    if result.output_format == "pdf":
        return _pdf_response(result.file_content, str(meta.get("filename", "formular.pdf")), headers)
    return StreamingResponse(
        io.BytesIO(result.file_content),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="formulare.zip"',
            **headers,
        },
    )


@router.post("/form/create")
async def form_create(
    file: UploadFile = File(...),
    fields: str = Form(
        ...,
        description=(
            'JSON-Liste [{"page":1,"type":"text","name":"vorname",'
            '"x0":0.1,"y0":0.2,"x1":0.5,"y1":0.24,"font_size":11,'
            '"required":false,"options":[],"value":""}] — Koordinaten 0–1'
        ),
    ),
    dry_run: bool = Form(
        False, description="Nur prüfen: JSON mit Hinweisen statt PDF zurückgeben"
    ),
):
    """Formularfelder aus einem Designer-Layout anlegen (AcroForm).

    `dry_run=true` liefert das Prüfergebnis als JSON (inkl. Hinweistexte), weil
    Hinweise sich nicht verlustfrei in HTTP-Headern transportieren lassen.
    """
    content = await file.read()
    _validate_pdf(file, content)
    try:
        fields_list = json.loads(fields)
        assert isinstance(fields_list, list)
        assert all(isinstance(f, dict) for f in fields_list)
    except (json.JSONDecodeError, AssertionError):
        raise HTTPException(
            status_code=400, detail="fields muss eine JSON-Liste aus Objekten sein"
        )
    result = await run_cpu(get_pdf_extras().create_form_fields, content, fields_list)
    if dry_run:
        meta = result.metadata or {}
        return {
            "ok": result.success,
            "created": meta.get("created", 0),
            "skipped": meta.get("skipped", len(fields_list)),
            "warnings": result.warnings or [],
            "error": result.error,
        }
    if not result.success:
        raise HTTPException(status_code=422, detail=result.error)
    meta = result.metadata or {}
    return _pdf_response(
        result.file_content,
        f"{_name(file)}_formular.pdf",
        headers={
            "X-Fields-Created": str(meta.get("created", 0)),
            "X-Fields-Skipped": str(meta.get("skipped", 0)),
            "X-Warnings": str(len(result.warnings or [])),
        },
    )


@router.post("/bates")
async def bates_numbers(
    file: UploadFile = File(...),
    prefix: str = Form("", description="Präfix, z.B. AKTE-"),
    start: int = Form(1),
    digits: int = Form(6, ge=1, le=12),
    position: str = Form("bottom-right"),
    font_size: float = Form(9),
    color: str = Form("#000000"),
):
    content = await file.read()
    _validate_pdf(file, content)
    result = await run_cpu(get_pdf_extras().add_bates_numbers,
        content,
        prefix=prefix,
        start=start,
        digits=digits,
        position=position,
        font_size=font_size,
        color=color,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    meta = result.metadata or {}
    return _pdf_response(
        result.file_content,
        f"{_name(file)}_bates.pdf",
        headers={"X-Bates-First": str(meta.get("first", "")), "X-Bates-Last": str(meta.get("last", ""))},
    )


@router.post("/redact")
async def redact_by_search(
    file: UploadFile = File(...),
    term: str = Form(..., min_length=1, description="Zu schwärzender Text"),
    match_case: bool = Form(False),
):
    _require_legacy_redaction()
    content = await file.read()
    _validate_pdf(file, content)
    result = await run_cpu(get_pdf_extras().redact_search, content, term, match_case=match_case)
    if not result.success:
        raise HTTPException(status_code=_redaction_status(result.error), detail=result.error)
    return _pdf_response(
        result.file_content,
        f"{_name(file)}_geschwaerzt.pdf",
        headers={"X-Redactions": str((result.metadata or {}).get("redactions", 0))},
    )


@router.get("/redact/patterns")
async def list_redaction_patterns():
    """Verfügbare Suchmuster für die Schwärzung."""
    return {
        "patterns": [
            {"id": key, "label": p.label, "hint": p.hint, "ai": p.ai}
            for key, p in REDACTION_PATTERNS.items()
        ],
        "ner_available": get_pdf_extras().ner_available(),
    }


@router.post("/redact-patterns")
def redact_by_patterns(
    file: UploadFile = File(...),
    patterns: str = Form("[]", description='JSON-Liste, z.B. ["iban","email"]'),
    terms: str = Form("", description="Begriffe/Namen, einer pro Zeile"),
    case_sensitive: bool = Form(False),
    whole_word: bool = Form(True),
    preview: bool = Form(
        False, description="Nur Fundstellen melden, nichts schwärzen"
    ),
):
    """Musterbasierte Schwärzung (IBAN, E-Mail, Namenslisten …).

    Sync-Endpoint (Threadpool): jede Seite wird nach Wörtern durchsucht.
    `preview=true` liefert die Fundstellen als JSON — Schwärzen ist
    unumkehrbar und sollte vorher geprüft werden.
    """
    content = file.file.read()
    _validate_pdf(file, content)
    criteria = _criteria(patterns, terms, case_sensitive, whole_word)
    service = get_pdf_extras()
    if preview:
        plan = _plan_or_error(service, content, criteria)
        findings = [
            {
                "pattern": c["source"],
                "page": c["page"],
                "text": c["text"],
                "rect": c["pdf_rect"],
                "location": c["location"],
            }
            for c in plan["candidates"]
        ]
        return {
            "total": plan["total"],
            "by_pattern": plan["by_source"],
            "findings": findings,
            "truncated": False,
            "pages_without_text": plan["pages_without_text"],
        }

    _require_legacy_redaction()
    result = service.redact_patterns(
        content,
        list(criteria.patterns),
        list(criteria.terms),
        criteria.case_sensitive,
        criteria.whole_word,
    )
    if not result.success:
        raise HTTPException(status_code=_redaction_status(result.error), detail=result.error)
    meta = result.metadata or {}
    return _pdf_response(
        result.file_content,
        f"{_name(file)}_geschwaerzt.pdf",
        headers={"X-Redactions": str(meta.get("redactions", 0))},
    )


# ── Schwärzung mit Pflicht-Vorschau ───────────────────────────


def _redaction_status(error: str | None) -> int:
    text = error or ""
    if "Keine Fundstellen" in text or "Nachprüfung" in text:
        return 422
    if "nicht verfügbar" in text:
        return 503
    if any(k in text for k in ("keine lesbare PDF", "passwortgeschützt", "keine Seiten", "Höchstens", "Unbekannte Muster", "Begriffe dürfen")):
        return 400
    return 500


def _criteria(patterns: str, terms: str, case_sensitive: bool, whole_word: bool):
    try:
        pattern_list = json.loads(patterns)
        assert isinstance(pattern_list, list) and all(isinstance(p, str) for p in pattern_list)
    except (json.JSONDecodeError, AssertionError):
        raise HTTPException(status_code=400, detail="patterns muss eine JSON-Liste sein")
    try:
        criteria = redaction_engine.Criteria.from_input(
            pattern_list, terms.splitlines(), case_sensitive, whole_word
        )
    except redaction_engine.RedactionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not criteria.patterns and not criteria.terms:
        raise HTTPException(status_code=400, detail="Mindestens ein Muster oder Begriff nötig")
    if NER_PATTERN_ID in criteria.patterns and not get_pdf_extras().ner_available():
        raise HTTPException(
            status_code=503, detail="KI-Namenserkennung nicht verfügbar (spaCy-Modell fehlt)"
        )
    return criteria


def _plan_or_error(service, content: bytes, criteria) -> dict:
    try:
        return service.redaction_plan(content, criteria)
    except redaction_engine.RedactionError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Die Oberfläche schickt nur Kennungen und Bereiche; 45 000 Kennungen sind
# unter 1 MB. 8 MB lassen Luft, ohne den Speicher je Anfrage aufzublähen.
_MAX_PLAN_BYTES = 8 * 1024 * 1024


def _reject_constant(value: str):
    raise ValueError(f"{value} ist nicht erlaubt")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Zahl außerhalb des Wertebereichs")
    return number


def _json_field(text: str | None, upload: UploadFile | None, name: str):
    """JSON aus einem Formularfeld oder — für große Pläne — aus einem
    Datei-Teil lesen. Starlette begrenzt reine Formularfelder auf 1 MB."""
    if upload is not None:
        raw = upload.file.read(_MAX_PLAN_BYTES + 1)
        if len(raw) > _MAX_PLAN_BYTES:
            raise HTTPException(status_code=400, detail=f"{name} ist zu groß")
        text = raw.decode("utf-8", errors="replace")
    if text is None:
        raise HTTPException(status_code=400, detail=f"{name} fehlt")
    try:
        return json.loads(text, parse_constant=_reject_constant, parse_float=_finite_float)
    except (ValueError, RecursionError):  # JSONDecodeError ist ein ValueError
        raise HTTPException(status_code=400, detail=f"{name} muss gültiges JSON sein")


def _selection(payload):
    try:
        return redaction_engine.Selection.from_dict(payload)
    except redaction_engine.RedactionError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _apply_or_error(service, content: bytes, selection) -> tuple[bytes, dict]:
    try:
        return service.redaction_apply(content, selection)
    except redaction_engine.RedactionStaleError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except redaction_engine.RedactionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except redaction_engine.RedactionVerificationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/redact/plan")
def redaction_plan(
    file: UploadFile = File(...),
    patterns: str = Form("[]", description='JSON-Liste, z.B. ["iban","email"]'),
    terms: str = Form("", description="Begriffe/Namen, einer pro Zeile"),
    case_sensitive: bool = Form(False),
    whole_word: bool = Form(True),
):
    """Schritt 1: Fundstellen suchen, nichts verändern.

    Liefert jede Fundstelle mit fester Kennung, Rechteck (0…1, Anzeige),
    Fundtext und Fundort — auch in Metadaten, Lesezeichen, Kommentaren,
    Links, Formularfeldern und Anhängen. Die Datei wird nicht gespeichert.
    """
    content = file.file.read()
    _validate_pdf(file, content)
    criteria = _criteria(patterns, terms, case_sensitive, whole_word)
    return _plan_or_error(get_pdf_extras(), content, criteria)


@router.post("/redact/apply")
def redaction_apply(
    file: UploadFile = File(...),
    plan: str | None = Form(
        None,
        description=(
            'JSON: {"sha256", "criteria", "selected": [Kennungen], '
            '"areas": [{"page", "rect": [x0,y0,x1,y1]}], "sanitize": true}'
        ),
    ),
    plan_file: UploadFile | None = File(None, description="Wie plan, als Datei-Teil (große Pläne)"),
):
    """Schritt 2: genau die bestätigte Auswahl schwärzen.

    Die Datei muss dieselbe sein wie bei der Vorschau (SHA-256). Ist nach
    dem Schwärzen noch eine ausgewählte Fundstelle lesbar, wird keine
    Datei ausgeliefert (HTTP 422).
    """
    content = file.file.read()
    _validate_pdf(file, content)
    selection = _selection(_json_field(plan, plan_file, "plan"))
    out, report = _apply_or_error(get_pdf_extras(), content, selection)
    return _pdf_response(
        out,
        f"{_name(file)}_geschwaerzt.pdf",
        headers={
            "X-Redactions": str(report["redactions"]),
            "X-Redaction-Areas": str(report["areas"]),
            "X-Redaction-Hidden": str(report["hidden_removed"]),
            "X-Redaction-Verified": "true",
        },
    )


@router.post("/redact/apply-batch")
def redaction_apply_batch(
    files: list[UploadFile] = File(...),
    plans: str | None = Form(None, description="JSON-Liste mit je einem Plan pro Datei, gleiche Reihenfolge"),
    plans_file: UploadFile | None = File(None, description="Wie plans, als Datei-Teil (große Pläne)"),
):
    """Mehrere geprüfte Dateien schwärzen — Ergebnis als ZIP mit Protokoll.

    Jede Datei braucht ihren eigenen bestätigten Plan. Schlägt eine Datei
    fehl, wird keine Datei ausgeliefert: Teilweise geschwärzte Stapel sind
    leicht zu übersehen.
    """
    import zipfile

    if not files or len(files) > 50:
        raise HTTPException(status_code=400, detail="1 bis 50 Dateien")
    plan_list = _json_field(plans, plans_file, "plans")
    if not isinstance(plan_list, list):
        raise HTTPException(status_code=400, detail="plans muss eine JSON-Liste sein")
    if len(plan_list) != len(files):
        raise HTTPException(status_code=400, detail="Je Datei genau ein Plan")
    limits = current_limits()
    service = get_pdf_extras()
    total = 0
    log: list[str] = []
    buf = io.BytesIO()
    names: set[str] = set()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f, raw_plan in zip(files, plan_list):
            content = f.file.read()
            total += len(content)
            if total > limits.max_total:
                raise HTTPException(
                    status_code=400, detail=f"Gesamtgröße überschreitet {limits.max_total_mb} MB"
                )
            _validate_pdf(f, content)
            try:
                selection = redaction_engine.Selection.from_dict(raw_plan)
            except redaction_engine.RedactionError as e:
                raise HTTPException(status_code=400, detail=f"{f.filename}: {e}")
            nothing = not selection.selected and not selection.areas
            if nothing and not selection.sanitize:
                out, entry, suffix = content, "nichts ausgewählt, unverändert übernommen", ""
            else:
                # Auch ohne Auswahl wird bereinigt (Metadaten, Anhänge …) und nachgeprüft.
                try:
                    out, report = _apply_or_error(service, content, selection)
                except HTTPException as e:
                    raise HTTPException(status_code=e.status_code, detail=f"{f.filename}: {e.detail}")
                suffix = "_bereinigt" if nothing else "_geschwaerzt"
                entry = (
                    "nichts ausgewählt, nur bereinigt"
                    if nothing
                    else f"{report['redactions']} Fundstelle(n), {report['areas']} Bereich(e), "
                    f"{report['hidden_removed']} versteckte Inhalte entfernt, {report['deselected']} abgewählt"
                )
                if report["sanitized"]:
                    entry += f"; bereinigt: {', '.join(report['sanitized'])}"
            stem = _safe_name(_name(f)) + suffix
            name, n = f"{stem}.pdf", 1
            while name in names:
                name = f"{stem}_{n}.pdf"
                n += 1
            names.add(name)
            zf.writestr(name, out)
            log.append(f"{_safe_name(f.filename or name)} → {name}: {entry}")
        zf.writestr("schwaerzungen.txt", "\n".join(log) + "\n")
    return StreamingResponse(
        io.BytesIO(buf.getvalue()),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="geschwaerzt.zip"'},
    )


@router.post("/sign-image")
async def sign_with_image(
    file: UploadFile = File(...),
    image: UploadFile = File(..., description="Signatur-/Stempelbild (PNG/JPG)"),
    page: int = Form(1, ge=1),
    x: float = Form(0.6, ge=0, le=1),
    y: float = Form(0.85, ge=0, le=1),
    width: float = Form(0.25, gt=0, le=1, description="Breite relativ zur Seite"),
):
    content = await file.read()
    _validate_pdf(file, content)
    if not image.filename or not image.filename.lower().endswith(
        (".png", ".jpg", ".jpeg")
    ):
        raise HTTPException(status_code=400, detail="Bild muss PNG oder JPG sein")
    image_content = await image.read()
    if len(image_content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Bild zu groß (max 10 MB)")
    result = await run_cpu(get_pdf_extras().place_image,
        content, image_content, page_num=page, x=x, y=y, width_frac=width
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return _pdf_response(result.file_content, f"{_name(file)}_signiert.pdf")


@router.post("/edit-text-blocks")
async def edit_text_blocks(
    file: UploadFile = File(...),
    edits: str = Form(
        ...,
        description='JSON-Liste [{"page":1,"bbox":{...},"text":"...","font_size":11,"color":"#000000"}]',
    ),
):
    content = await file.read()
    _validate_pdf(file, content)
    try:
        edits_list = json.loads(edits)
        assert isinstance(edits_list, list)
    except (json.JSONDecodeError, AssertionError):
        raise HTTPException(status_code=400, detail="edits muss eine JSON-Liste sein")
    if len(edits_list) > 200:
        raise HTTPException(status_code=400, detail="Maximal 200 Änderungen pro Aufruf")
    result = await run_cpu(get_pdf_extras().edit_text_blocks, content, edits_list)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return _pdf_response(
        result.file_content,
        f"{_name(file)}_bearbeitet.pdf",
        headers={"X-Warnings": str(len(result.warnings or []))},
    )


@router.post("/sign-digital")
def sign_digital(
    file: UploadFile = File(...),
    certificate: UploadFile = File(..., description="PKCS#12-Zertifikat (.p12/.pfx)"),
    passphrase: str = Form("", description="Zertifikats-Passwort"),
    reason: str = Form(""),
    location: str = Form(""),
    tsa_url: str = Form("", description="Optionale Zeitstempel-URL (RFC 3161 TSA)"),
):
    """Zertifikatsbasierte digitale Signatur (PAdES). Zertifikat nur transient.

    Bewusst ein sync-Endpoint (Threadpool): pyhankos sign_pdf nutzt intern
    asyncio.run und darf nicht im laufenden Event-Loop aufgerufen werden.
    """
    content = file.file.read()
    _validate_pdf(file, content)
    if not certificate.filename or not certificate.filename.lower().endswith(
        (".p12", ".pfx")
    ):
        raise HTTPException(status_code=400, detail="Zertifikat muss .p12/.pfx sein")
    p12 = certificate.file.read()
    if len(p12) > 1024 * 1024:
        raise HTTPException(status_code=400, detail="Zertifikatsdatei zu groß")
    if tsa_url and not tsa_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="TSA-URL muss mit http(s):// beginnen")
    result = get_pdf_extras().sign_digital(
        content, p12, passphrase, reason=reason, location=location, tsa_url=tsa_url
    )
    if not result.success:
        status = 503 if "nicht verfügbar" in (result.error or "") else 400
        raise HTTPException(status_code=status, detail=result.error)
    return _pdf_response(result.file_content, f"{_name(file)}_signiert.pdf")


@router.post("/scan-optimize")
def scan_optimize(
    file: UploadFile = File(...),
    language: str = Form("deu"),
    deskew: bool = Form(True),
    rotate_pages: bool = Form(True),
    force_ocr: bool = Form(False),
    clean: bool = Form(False, description="Seiten vor OCR entrauschen (unpaper)"),
):
    """Sync-Endpoint (Threadpool): OCRmyPDF darf den Event-Loop nicht blockieren."""
    content = file.file.read()
    _validate_pdf(file, content)
    result = get_pdf_extras().scan_optimize(
        content,
        language=language,
        deskew=deskew,
        rotate_pages=rotate_pages,
        force_ocr=force_ocr,
        clean=clean,
    )
    if not result.success:
        status = 503 if "nicht verfügbar" in (result.error or "") else 500
        raise HTTPException(status_code=status, detail=result.error)
    return _pdf_response(result.file_content, f"{_name(file)}_optimiert.pdf")


@router.post("/batch")
def batch_apply(
    files: list[UploadFile] = File(...),
    operation: str = Form(
        ...,
        description=(
            "compress | rotate | protect | bates | pdfa | watermark | clean | sign | rename | redact"
        ),
    ),
    params: str = Form("{}", description="JSON-Objekt mit Operations-Parametern"),
    certificate: UploadFile | None = File(
        None, description="Nur für operation=sign: PKCS#12-Zertifikat (.p12/.pfx)"
    ),
    passphrase: str = Form("", description="Nur für operation=sign: Zertifikats-Passwort"),
):
    """Eine Operation auf viele Dateien anwenden — Ergebnis als ZIP."""
    if len(files) < 1:
        raise HTTPException(status_code=400, detail="Mindestens eine Datei erforderlich")
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="Maximal 50 Dateien")
    try:
        params_dict = json.loads(params)
        assert isinstance(params_dict, dict)
    except (json.JSONDecodeError, AssertionError):
        raise HTTPException(status_code=400, detail="params muss ein JSON-Objekt sein")

    if operation == "redact":
        _require_legacy_redaction()
        batch_terms = [t for t in str(params_dict.get("terms", "")).splitlines() if t.strip()]
        if len(batch_terms) > redaction_engine.MAX_TERMS:
            raise HTTPException(
                status_code=400,
                detail=f"Höchstens {redaction_engine.MAX_TERMS} Begriffe je Durchgang",
            )
        batch_patterns = params_dict.get("patterns") or []
        unknown = [p for p in batch_patterns if p not in REDACTION_PATTERNS]
        if unknown:
            raise HTTPException(status_code=400, detail=f"Unbekannte Muster: {', '.join(unknown)}")
        if NER_PATTERN_ID in batch_patterns and not get_pdf_extras().ner_available():
            raise HTTPException(
                status_code=503,
                detail="KI-Namenserkennung nicht verfügbar (spaCy-Modell fehlt)",
            )

    limits = current_limits()
    total = 0
    file_data: list[tuple[str, bytes]] = []
    for f in files:
        content = f.file.read()
        total += len(content)
        if total > limits.max_total:
            raise HTTPException(
                status_code=400,
                detail=f"Gesamtgröße überschreitet {limits.max_total_mb} MB",
            )
        _validate_pdf(f, content)
        file_data.append((f.filename or f"datei_{len(file_data)}.pdf", content))

    cert: tuple[bytes, str] | None = None
    if operation == "sign":
        if certificate is None or not certificate.filename:
            raise HTTPException(
                status_code=400, detail="Für die Stapelsignatur wird ein Zertifikat benötigt"
            )
        if not certificate.filename.lower().endswith((".p12", ".pfx")):
            raise HTTPException(status_code=400, detail="Zertifikat muss .p12/.pfx sein")
        p12 = certificate.file.read()
        if len(p12) > 1024 * 1024:
            raise HTTPException(status_code=400, detail="Zertifikatsdatei zu groß")
        cert = (p12, passphrase)

    result = get_pdf_extras().batch_apply(file_data, operation, params_dict, certificate=cert)
    if not result.success:
        raise HTTPException(status_code=422, detail=result.error)
    meta = result.metadata or {}
    return StreamingResponse(
        io.BytesIO(result.file_content),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="batch_ergebnisse.zip"',
            "X-Batch-Ok": str(meta.get("ok", 0)),
            "X-Batch-Failed": str(meta.get("failed", 0)),
        },
    )


@router.post("/to-pdfa")
def to_pdfa(
    file: UploadFile = File(...),
    level: str = Form("2b", description="PDF/A-Level: 1b, 2b, 3b"),
):
    """Sync-Endpoint (Threadpool): Ghostscript darf den Event-Loop nicht blockieren."""
    content = file.file.read()
    _validate_pdf(file, content)
    result = get_pdf_extras().convert_pdfa(content, level=level)
    if not result.success:
        status = 503 if "nicht verfügbar" in (result.error or "") else 500
        raise HTTPException(status_code=status, detail=result.error)
    return _pdf_response(result.file_content, f"{_name(file)}_pdfa.pdf")


# ── Asynchrone Jobs für langlaufende Verarbeitungen ───────────
# OCR, Vergleich und Scan-Optimierung können bei großen Dateien länger dauern
# als Browser-Timeouts erlauben. Ablauf: POST /jobs/<op> → job_id,
# GET /jobs/{id} → Status, GET /jobs/{id}/result → Ergebnis (einmalig,
# danach aus dem RAM gelöscht). Jobs sind an Nutzer-ID bzw. Client-IP gebunden.

from fastapi import Request  # noqa: E402

from app import jobs as job_store  # noqa: E402
from app.ratelimit import tier_key  # noqa: E402


def _job_ocr(content: bytes, language: str):
    from app.services.pdf_editor_service import get_pdf_editor

    result = get_pdf_editor().ocr_pdf(content, language=language)
    if not result.success:
        raise RuntimeError(result.error or "OCR fehlgeschlagen")
    meta = result.metadata or {}
    return result.file_content, {
        "X-Pages-Processed": str(meta.get("pages_processed", 0)),
        "X-Characters-Recognized": str(meta.get("characters_recognized", 0)),
    }


def _job_compare(content_a: bytes, content_b: bytes, include_visual: bool):
    import json as _json

    from app.services.pdf_editor_service import get_pdf_editor

    result = get_pdf_editor().compare_pdfs(content_a, content_b, include_visual)
    if not result.success:
        raise RuntimeError(result.error or "Vergleich fehlgeschlagen")
    return _json.dumps(result.metadata or {}).encode(), {}


def _job_scan(
    content: bytes, language: str, deskew: bool, rotate: bool, force: bool, clean: bool
):
    result = get_pdf_extras().scan_optimize(
        content,
        language=language,
        deskew=deskew,
        rotate_pages=rotate,
        force_ocr=force,
        clean=clean,
    )
    if not result.success:
        raise RuntimeError(result.error or "Scan-Optimierung fehlgeschlagen")
    return result.file_content, {}


@router.post("/jobs/ocr", status_code=202)
async def start_ocr_job(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form("deu"),
):
    content = await file.read()
    _validate_pdf(file, content)
    try:
        job_id = job_store.submit(
            tier_key(request),
            f"{_name(file)}_ocr.pdf",
            "application/pdf",
            _job_ocr,
            content,
            language,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))
    return {"job_id": job_id}


@router.post("/jobs/compare", status_code=202)
async def start_compare_job(
    request: Request,
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
    include_visual: bool = Form(True),
):
    content_a = await file_a.read()
    content_b = await file_b.read()
    _validate_pdf(file_a, content_a)
    _validate_pdf(file_b, content_b)
    try:
        job_id = job_store.submit(
            tier_key(request),
            "vergleich.json",
            "application/json",
            _job_compare,
            content_a,
            content_b,
            include_visual,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))
    return {"job_id": job_id}


@router.post("/jobs/scan-optimize", status_code=202)
async def start_scan_job(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form("deu"),
    deskew: bool = Form(True),
    rotate_pages: bool = Form(True),
    force_ocr: bool = Form(False),
    clean: bool = Form(False),
):
    content = await file.read()
    _validate_pdf(file, content)
    try:
        job_id = job_store.submit(
            tier_key(request),
            f"{_name(file)}_optimiert.pdf",
            "application/pdf",
            _job_scan,
            content,
            language,
            deskew,
            rotate_pages,
            force_ocr,
            clean,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))
    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
async def job_status(job_id: str, request: Request):
    job = job_store.get(job_id, tier_key(request))
    if job is None:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    return {"job_id": job.id, "status": job.status, "error": job.error}


@router.get("/jobs/{job_id}/result")
async def job_result(job_id: str, request: Request):
    job = job_store.take_result(job_id, tier_key(request))
    if job is None:
        raise HTTPException(
            status_code=404, detail="Ergebnis nicht verfügbar (abgeholt, abgelaufen oder nicht fertig)"
        )
    headers = {
        "Content-Disposition": f'attachment; filename="{_safe_name(job.filename)}"',
        **job.headers,
    }
    return StreamingResponse(io.BytesIO(job.content), media_type=job.media_type, headers=headers)
