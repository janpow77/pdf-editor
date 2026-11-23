"""Schwärzung mit Pflicht-Vorschau: Plan → Auswahl → Anwendung → Nachprüfung.

Ablauf
------
1. :func:`build_plan` durchsucht die Datei und liefert jede Fundstelle mit
   fester Kennung, Rechteck, Fundtext und Quelle. Gesucht wird auf dem
   Seitentext (zeichengenau, über Zeilenumbrüche und Silbentrennung hinweg)
   und in versteckten Ablagen: Metadaten, XMP, Lesezeichen, Kommentare,
   Links, Formularfelder und Dateianhänge.
2. Die Nutzerin oder der Nutzer wählt Fundstellen ab oder wieder aus und
   ergänzt bei Bedarf eigene Bereiche.
3. :func:`apply_plan` sucht mit denselben Kriterien erneut, prüft, dass
   Datei (SHA-256) und Kennungen zum Plan passen, und schwärzt genau die
   bestätigte Auswahl.
4. Anschließend wird die Ausgabe erneut durchsucht. Ist eine ausgewählte
   Fundstelle noch lesbar, wird keine Datei ausgeliefert (fail-closed).

Das Modul hängt nur von PyMuPDF ab und hält keinen Zustand; der Plan wird
nirgends gespeichert. Es ist so geschnitten, dass es später ohne Umbau in
die Bibliothek ``auditcore_pdf`` übernommen werden kann.
"""

from __future__ import annotations

import bisect
import datetime as _dt
import hashlib
import math
import re
import unicodedata
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any

# PyMuPDF wird projektweit nur in app.pdf_backend importiert.
from app.pdf_backend import fitz

PLAN_VERSION = 1
MAX_TERMS = 200
MAX_TERM_LENGTH = 200
MAX_AREAS = 500
MAX_AREAS_PER_PAGE = 100
REDACTED_MARK = "[geschwärzt]"
NER_PATTERN_ID = "ki_namen"
MANUAL_SOURCE = "bereich"

# Trennzeichen im Suchtext. HARD trennt Spalten oder Absätze, über die kein
# Treffer laufen darf (kein Leerraum für ``\s``), SOFT steht für einen
# gewöhnlichen Zeilenumbruch im Fließtext.
_HARD = "\x00"
_SOFT = " "
_HYPHENS = "-­‐‑"


class RedactionError(ValueError):
    """Eingabe ungeeignet (HTTP 400)."""


class RedactionStaleError(RedactionError):
    """Plan passt nicht zur Datei oder zu den Fundstellen (HTTP 409)."""


class RedactionNerError(RuntimeError):
    """Die KI-Namenserkennung lieferte ein ungültiges Ergebnis (HTTP 502)."""


class RedactionVerificationError(RuntimeError):
    """Nach dem Schwärzen ist noch etwas lesbar — keine Ausgabe (HTTP 422)."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__(
            "Schwärzung nicht ausgeliefert: Nachprüfung fand noch lesbare Fundstellen ("
            + "; ".join(problems[:5])
            + (" …" if len(problems) > 5 else "")
            + ")"
        )


# ── Muster ───────────────────────────────────────────────────


def _context_before(text: str, start: int, width: int = 40) -> str:
    return text[max(0, start - width) : start].replace(_HARD, " ")


def _iban_ok(compact: str) -> bool:
    compact = compact.upper()
    if not (15 <= len(compact) <= 34 and compact[:2].isalpha() and compact[2:4].isdigit()):
        return False
    if not compact.isalnum() or not compact.isascii():
        return False
    rearranged = compact[4:] + compact[:4]
    digits = "".join(str(int(c, 36)) for c in rearranged)
    return int(digits) % 97 == 1


def _validate_iban(text: str, start: int, end: int) -> tuple[int, int] | None:
    """Längstes Präfix aus ganzen Gruppen, das die Prüfziffer erfüllt.

    Das Muster läuft gierig über Vierergruppen und kann ein folgendes kurzes
    Wort mitnehmen („… 3201 in“); erst die Modulo-97-Prüfung entscheidet,
    wo die IBAN endet.
    """
    tokens = list(re.finditer(r"\S+", text[start:end]))
    for k in range(len(tokens), 0, -1):
        candidate_end = start + tokens[k - 1].end()
        if _iban_ok(re.sub(r"\s", "", text[start:candidate_end])):
            return start, candidate_end
    return None


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _validate_card(text: str, start: int, end: int) -> tuple[int, int] | None:
    digits = re.sub(r"\D", "", text[start:end])
    return (start, end) if 13 <= len(digits) <= 19 and _luhn_ok(digits) else None


def _steuer_id_ok(digits: str) -> bool:
    """Prüfziffer der Steuer-ID (ISO 7064, MOD 11,10); erste Ziffer ≠ 0."""
    if len(digits) != 11 or digits[0] == "0":
        return False
    product = 10
    for ch in digits[:10]:
        total = (int(ch) + product) % 10 or 10
        product = (total * 2) % 11
    check = 11 - product
    if check == 10:
        check = 0
    return check == int(digits[10])


def _validate_steuer_id(text: str, start: int, end: int) -> tuple[int, int] | None:
    return (start, end) if _steuer_id_ok(re.sub(r"\D", "", text[start:end])) else None


_PHONE_CONTEXT = re.compile(
    r"(?i)(?:\btel\b\.?|telefon|telefonisch|\bfon\b|\bfax\b|telefax|mobil|handy|"
    r"rufnummer|\bruf\b|durchwahl|erreichbar|anruf|☎|📞)[^\n\x00]{0,30}$"
)


def _validate_phone(text: str, start: int, end: int) -> tuple[int, int] | None:
    match = text[start:end]
    digits = re.sub(r"\D", "", match)
    if not 6 <= len(digits) <= 15:
        return None
    international = match.startswith("+") or match.startswith("00")
    separated = bool(re.search(r"\d[/-]\d", match))
    # Nur durch Leerzeichen gegliederte Ziffernfolgen wie „0701 686 11“ sind
    # häufig Haushaltsstellen oder Kundennummern — dann ist ein Hinweis wie
    # „Tel.“ oder „Telefon“ kurz davor nötig.
    if not (international or separated) and not _PHONE_CONTEXT.search(_context_before(text, start)):
        return None
    return start, end


def _validate_date(text: str, start: int, end: int) -> tuple[int, int] | None:
    try:
        day, month, year = (int(x) for x in text[start:end].split("."))
        _dt.date(year, month, day)
    except ValueError:
        return None
    return start, end


_IP_NEGATIVE_CONTEXT = re.compile(
    r"(?i)(?:version|ver\.|\bv\.?|release|build|kapitel|abschnitt|ziffer|ziff\.|"
    r"nr\.|tz\.|gliederung|punkt|anlage|randnummer|rn\.|§)\s*$"
)


def _validate_ip(text: str, start: int, end: int) -> tuple[int, int] | None:
    if any(int(octet) > 255 for octet in text[start:end].split(".")):
        return None
    if _IP_NEGATIVE_CONTEXT.search(_context_before(text, start, 25)):
        return None
    return start, end


# Kürzel vor Rechtsgrundlagen, Förderprogrammen und Normen — keine Aktenzeichen.
_AZ_BLOCKLIST = {
    "VO", "EU", "EG", "EWG", "EWR", "RL", "ART", "ABS", "NR", "EFRE", "ESF", "ELER",
    "EGFL", "EMFF", "BGBL", "ABL", "GVBL", "DIN", "ISO", "EN", "KOM", "COM", "SEC", "C",
}


def _validate_aktenzeichen(text: str, start: int, end: int) -> tuple[int, int] | None:
    prefix = re.match(r"[A-ZÄÖÜ]+", text[start:end])
    if prefix and prefix.group(0) in _AZ_BLOCKLIST:
        return None
    return start, end


Validator = Callable[[str, int, int], "tuple[int, int] | None"]


@dataclass(frozen=True)
class PatternSpec:
    label: str
    regex: str
    hint: str
    #: KI-basiert (spaCy-NER) statt Regex — kein fester Ausdruck, dafür
    #: unsicherer als die übrigen Muster.
    ai: bool = False
    flags: int = 0
    validate: Validator | None = None


PATTERNS: dict[str, PatternSpec] = {
    "iban": PatternSpec(
        "IBAN",
        r"(?<![A-Za-z0-9])[A-Za-z]{2}\d{2}(?: ?[A-Za-z0-9]){11,40}",
        "Kontonummern, auch in Vierergruppen geschrieben; nur mit gültiger Prüfziffer",
        validate=_validate_iban,
    ),
    "email": PatternSpec(
        "E-Mail-Adresse",
        r"(?<![\w.%+-])[\w.%+-]+@[\w-]+(?:\.[\w-]+)*\.[^\W\d_]{2,}(?![\w-])",
        "Adressen in Anschreiben und Verteilern",
    ),
    "telefon": PatternSpec(
        "Telefonnummer",
        r"(?<![\w/.,+-])(?:(?:\+|00)49[ /-]?(?:\(0\)[ /-]?)?[1-9]\d{1,4}|0[1-9]\d{1,4})"
        r"(?:[ /-]?\d{2,8}){1,3}(?![\w/-]|[.,]\d)",
        "deutsche Rufnummern; ohne „/“ oder „-“ nur nach „Tel.“, „Telefon“, „Fax“ o. Ä.",
        validate=_validate_phone,
    ),
    "steuer_id": PatternSpec(
        "Steuer-Identifikationsnummer",
        r"(?<![\d.,/-])(?:\d{11}|\d{2} \d{3} \d{3} \d{3})(?!\d|[.,/-]\d)",
        "11-stellige Steuer-ID; nur mit gültiger Prüfziffer",
        validate=_validate_steuer_id,
    ),
    "ust_id": PatternSpec(
        "Umsatzsteuer-Identifikationsnummer",
        r"(?<![\w])DE ?\d{9}(?!\d)",
        "USt-IdNr. der Begünstigten",
    ),
    "kreditkarte": PatternSpec(
        "Kreditkartennummer",
        r"(?<![\d.,/-])\d{4}([ -]?)\d{4}\1\d{4}\1\d{4}(?!\d|[.,/-]\d)",
        "16-stellige Kartennummern; nur mit gültiger Prüfziffer (Luhn)",
        validate=_validate_card,
    ),
    "geburtsdatum": PatternSpec(
        "Datum (TT.MM.JJJJ)",
        r"(?<![\d.])(?:0?[1-9]|[12]\d|3[01])\.(?:0?[1-9]|1[0-2])\.(?:19|20)\d{2}(?![\d])",
        "z. B. Geburtsdaten — trifft alle gültigen Datumsangaben dieses Formats",
        validate=_validate_date,
    ),
    "ip_adresse": PatternSpec(
        "IP-Adresse",
        r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w]|\.\d)",
        "IPv4-Adressen aus Protokollauszügen; nicht nach „Version“ oder „Kapitel“",
        validate=_validate_ip,
    ),
    "aktenzeichen": PatternSpec(
        "Aktenzeichen",
        r"(?<![\w/-])[A-ZÄÖÜ]{1,4}[-/ ]?\d{1,6}[-/]\d{2,4}(?![\w/]|-\d)",
        "Muster wie AZ-1234/26; nicht bei Rechtsgrundlagen wie „VO 2021/1060“",
        validate=_validate_aktenzeichen,
    ),
    NER_PATTERN_ID: PatternSpec(
        "Personennamen (KI-Erkennung)",
        "",
        "spaCy-NER statt Regex — erkennt Namen im Fließtext, ist aber "
        "unsicherer als die übrigen Muster: Vorschau vor dem Schwärzen prüfen",
        ai=True,
    ),
}


# ── Suchkriterien ────────────────────────────────────────────


@dataclass(frozen=True)
class Criteria:
    patterns: tuple[str, ...] = ()
    terms: tuple[str, ...] = ()
    case_sensitive: bool = False
    whole_word: bool = True

    @classmethod
    def from_input(
        cls,
        patterns: Iterable[str] = (),
        terms: Iterable[str] = (),
        case_sensitive: bool = False,
        whole_word: bool = True,
    ) -> Criteria:
        pattern_list = list(dict.fromkeys(p for p in patterns))
        unknown = [p for p in pattern_list if p not in PATTERNS]
        if unknown:
            raise RedactionError(f"Unbekannte Muster: {', '.join(unknown)}")
        term_list = list(dict.fromkeys(t.strip() for t in terms if t and t.strip()))
        if len(term_list) > MAX_TERMS:
            raise RedactionError(
                f"Höchstens {MAX_TERMS} Begriffe je Durchgang ({len(term_list)} angegeben)"
            )
        too_long = [t for t in term_list if len(t) > MAX_TERM_LENGTH]
        if too_long:
            raise RedactionError(f"Begriffe dürfen höchstens {MAX_TERM_LENGTH} Zeichen lang sein")
        return cls(tuple(pattern_list), tuple(term_list), bool(case_sensitive), bool(whole_word))

    def to_dict(self) -> dict[str, Any]:
        return {
            "patterns": list(self.patterns),
            "terms": list(self.terms),
            "case_sensitive": self.case_sensitive,
            "whole_word": self.whole_word,
        }


@dataclass(frozen=True)
class _Rule:
    source: str
    regex: re.Pattern
    validate: Validator | None = None
    is_term: bool = False


def _term_part(word: str, case_sensitive: bool) -> str:
    out: list[str] = []
    i = 0
    while i < len(word):
        ch = word[i]
        if ch in _HYPHENS:
            # Doppelnamen dürfen am Bindestrich umbrechen („Müller-“ / „Lüdenscheidt“).
            out.append(r"-\s*")
        elif not case_sensitive and ch in "ßẞ":
            out.append("(?:ß|ẞ|ss)")
        elif not case_sensitive and word[i : i + 2].lower() == "ss":
            out.append("(?:ss|ß|ẞ)")
            i += 1
        else:
            out.append(re.escape(ch))
        i += 1
    return "".join(out)


def _term_regex(term: str, case_sensitive: bool, whole_word: bool) -> re.Pattern:
    # Leerraum im Begriff trifft jeden Leerraum im Text, auch einen Zeilenumbruch.
    # NFKC wie im Seitentext, damit Ligaturen und Sonderformen gleich verglichen werden.
    term = unicodedata.normalize("NFKC", term)
    body = r"\s+".join(_term_part(part, case_sensitive) for part in term.split())
    if whole_word:
        body = rf"(?<!\w){body}(?!\w)"
    return re.compile(body, 0 if case_sensitive else re.IGNORECASE)


def _rules(criteria: Criteria) -> list[_Rule]:
    rules = [
        _Rule(f"begriff:{t}", _term_regex(t, criteria.case_sensitive, criteria.whole_word), is_term=True)
        for t in criteria.terms
    ]
    for key in criteria.patterns:
        spec = PATTERNS[key]
        if not spec.ai:
            rules.append(_Rule(key, re.compile(spec.regex, spec.flags), spec.validate))
    return rules


def source_label(source: str) -> str:
    if source.startswith("begriff:"):
        return f"Begriff „{source[8:]}“"
    if source == MANUAL_SOURCE:
        return "Bereich"
    if source == NER_PROPAGATED_ID:
        return "Namen (im Dokument nachgesucht)"
    spec = PATTERNS.get(source)
    return spec.label if spec else source


def _matches(rule: _Rule, text: str) -> Iterator[tuple[int, int]]:
    for m in rule.regex.finditer(text):
        span: tuple[int, int] | None = m.span()
        if span[0] == span[1]:
            continue
        if rule.validate:
            span = rule.validate(text, *span)
        if span:
            yield span


def _norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).split()).casefold()


# ── Seitentext mit Zeichenpositionen ─────────────────────────


@dataclass
class _PageText:
    text: str
    rects: list[tuple[float, float, float, float] | None]  # Zeichenrechteck oder None
    lines: list[int]  # Zeilennummer je Zeichen, -1 für Trenner
    hyphen_breaks: list[int]  # Index des Trennstrichs vor einem weichen Umbruch
    # Sichtbare Zeile je Zeilennummer: Fragmente derselben Grundlinie (großer
    # Wortabstand im Blocksatz oder in Formularen) teilen sich eine.
    rows: list[int] = field(default_factory=list)


def _break_kind(prev: tuple[float, ...], nxt: tuple[float, ...]) -> str | None:
    """Wie schließt die Zeile ``nxt`` an ``prev`` an?

    ``"below"``: nächste Zeile desselben Absatzes. ``"same"``: Fortsetzung auf
    derselben Grundlinie; MuPDF trennt dort bei großem Wortabstand, etwa im
    Blocksatz, in Tabellen oder in erzeugten Formularen. ``None``: harter
    Wechsel (Spalte, Absatz).
    """
    height = max(1.0, prev[3] - prev[1])
    below = prev[1] + 0.5 * height <= nxt[1] <= prev[3] + 1.5 * height
    overlap = nxt[0] < prev[2] and nxt[2] > prev[0]
    if below and overlap:
        return "below"
    if abs(nxt[3] - prev[3]) <= 0.3 * height and -0.5 * height <= nxt[0] - prev[2] <= 3 * height:
        return "same"
    return None


_INVISIBLE = frozenset("​‌‍⁠﻿")
_CHAR_MAP = {"‐": "-", "‑": "-"}


def _clean(text: str) -> str:
    """Freier Text (Metadaten, Felder) in dieselbe Form wie der Seitentext."""
    # MuPDF liefert ein weiches Trennzeichen in Lesezeichen als NUL-Zeichen.
    text = "".join(ch for ch in text if ch not in _INVISIBLE and ch != "\x00")
    return unicodedata.normalize("NFC", text.replace("\u00ad", ""))


def _text_flags() -> int:
    # Ohne MediaBox-Beschnitt: Text außerhalb der Seite steht trotzdem in der
    # Datei. Ohne Ligaturen: „ﬁ“ wird zu „f“ + „i“ und damit auffindbar.
    return (
        fitz.TEXTFLAGS_RAWDICT
        & ~fitz.TEXT_PRESERVE_IMAGES
        & ~fitz.TEXT_MEDIABOX_CLIP
        & ~fitz.TEXT_PRESERVE_LIGATURES
    )


def _page_text(page: Any) -> _PageText:
    chars: list[str] = []
    rects: list[tuple[float, float, float, float] | None] = []
    lines: list[int] = []
    hyphen_breaks: list[int] = []
    prev_bbox: tuple[float, ...] | None = None
    line_no = 0
    rows: list[int] = []
    raw = page.get_text("rawdict", flags=_text_flags(), clip=fitz.INFINITE_RECT())
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            glyphs = [c for span in line.get("spans", []) for c in span.get("chars", [])]
            # Unsichtbare Zeichen entfallen; ein weiches Trennzeichen zählt nur am Zeilenende.
            last_index = len(glyphs) - 1
            glyphs = [
                g for k, g in enumerate(glyphs)
                if g["c"] not in _INVISIBLE and (g["c"] != "­" or k == last_index)
            ]
            if not glyphs:
                continue
            bbox = tuple(line["bbox"])
            kind = None
            if prev_bbox is not None:
                kind = _break_kind(prev_bbox, bbox)
                last = chars[-1] if chars else ""
                if kind == "below" and last in _HYPHENS:
                    hyphen_breaks.append(len(chars) - 1)
                if kind is None:
                    chars.append(_HARD)
                    rects.append(None)
                    lines.append(-1)
                elif not last.isspace():
                    chars.append(_SOFT)
                    rects.append(None)
                    lines.append(-1)
            for g in glyphs:
                c = _CHAR_MAP.get(g["c"], g["c"])
                box = tuple(g["bbox"])
                if c.isspace():
                    chars.append(" ")
                    rects.append(None)
                    lines.append(line_no)
                    continue
                if unicodedata.combining(c):
                    # Zerlegter Umlaut (NFD): mit dem Grundbuchstaben vereinen.
                    prev_rect = rects[-1] if rects else None
                    if prev_rect is not None and lines[-1] == line_no:
                        composed = unicodedata.normalize("NFC", chars[-1] + c)
                        if len(composed) == 1:
                            chars[-1] = composed
                            rects[-1] = (
                                min(prev_rect[0], box[0]), min(prev_rect[1], box[1]),
                                max(prev_rect[2], box[2]), max(prev_rect[3], box[3]),
                            )
                    continue
                norm = unicodedata.normalize("NFKC", c) or c
                if len(norm) == 1:
                    chars.append(norm)
                    rects.append(box)
                    lines.append(line_no)
                    continue
                # Kompatibilitätszeichen wie „ﬁ“ oder „½“: Breite aufteilen.
                step = (box[2] - box[0]) / len(norm)
                for k, part in enumerate(norm):
                    chars.append(" " if part.isspace() else part)
                    rects.append(None if part.isspace() else (box[0] + k * step, box[1], box[0] + (k + 1) * step, box[3]))
                    lines.append(line_no)
            if not rows:
                rows.append(0)
            else:
                rows.append(rows[-1] if kind == "same" else rows[-1] + 1)
            line_no += 1
            prev_bbox = bbox
    return _PageText("".join(chars), rects, lines, hyphen_breaks, rows)



def _dehyphenated(pt: _PageText) -> tuple[str, list[int]] | None:
    """Suchtext ohne Trennstrich + Umbruch; Abbildung auf die Originalindizes."""
    if not pt.hyphen_breaks:
        return None
    drop: set[int] = set()
    for h in pt.hyphen_breaks:
        drop.add(h)
        if h + 1 < len(pt.text) and pt.text[h + 1] == _SOFT:
            drop.add(h + 1)
    keep = [i for i in range(len(pt.text)) if i not in drop]
    return "".join(pt.text[i] for i in keep), keep


def _span_rects(pt: _PageText, start: int, end: int, indices: Iterable[int] | None = None) -> list[Any]:
    """Je Zeile ein Rechteck über die getroffenen Zeichen."""
    by_line: dict[int, list[float]] = {}
    for i in indices if indices is not None else range(start, end):
        rect = pt.rects[i]
        if rect is None:
            continue
        line = pt.lines[i]
        box = by_line.get(line)
        if box is None:
            by_line[line] = list(rect)
        else:
            box[0] = min(box[0], rect[0])
            box[1] = min(box[1], rect[1])
            box[2] = max(box[2], rect[2])
            box[3] = max(box[3], rect[3])
    return [fitz.Rect(by_line[k]) for k in sorted(by_line)]


# ── Plan ─────────────────────────────────────────────────────


@dataclass
class Candidate:
    id: str
    kind: str  # "text" | "hidden"
    source: str
    text: str
    page: int | None = None  # 1-basiert
    rects: list[list[float]] = field(default_factory=list)  # PDF-Koordinaten (ungedreht)
    view_rects: list[list[float]] = field(default_factory=list)  # 0…1, Anzeige (gedreht)
    location: str = "Seitentext"
    ref: dict[str, Any] = field(default_factory=dict)  # Fundort versteckter Inhalte
    outside_view: bool = False
    start: int = 0
    end: int = 0
    priority: int = 0

    def union_rect(self) -> list[float] | None:
        if not self.rects:
            return None
        box = fitz.Rect(self.rects[0])
        for r in self.rects[1:]:
            box |= fitz.Rect(r)
        return [round(v, 2) for v in box]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "source": self.source,
            "label": source_label(self.source),
            "text": self.text,
            "page": self.page,
            "rects": self.view_rects,
            "pdf_rect": self.union_rect(),
            "location": self.location,
            "outside_view": self.outside_view,
            "selected": True,
        }


@dataclass
class PageInfo:
    page: int
    width: float
    height: float
    rotation: int
    has_text: bool
    image_only: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "page": self.page,
            "width": round(self.width, 2),
            "height": round(self.height, 2),
            "rotation": self.rotation,
            "has_text": self.has_text,
        }


@dataclass
class Plan:
    sha256: str
    criteria: Criteria
    pages: list[PageInfo]
    candidates: list[Candidate]
    cleanup: dict[str, Any]

    @property
    def text_candidates(self) -> list[Candidate]:
        return [c for c in self.candidates if c.kind == "text"]

    def by_source(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for c in self.candidates:
            counts[c.source] = counts.get(c.source, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": PLAN_VERSION,
            "sha256": self.sha256,
            "criteria": self.criteria.to_dict(),
            "page_count": len(self.pages),
            "pages": [p.to_dict() for p in self.pages],
            "pages_without_text": [p.page for p in self.pages if p.image_only],
            "total": len(self.candidates),
            "by_source": self.by_source(),
            "candidates": [c.to_dict() for c in self.candidates],
            "cleanup": self.cleanup,
        }


def _candidate_id(*parts: Any) -> str:
    return hashlib.sha256("\x1f".join(str(p) for p in parts).encode()).hexdigest()[:16]


def open_pdf(data: bytes) -> Any:
    if fitz is None:  # pragma: no cover
        raise RedactionError("PyMuPDF nicht verfügbar")
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise RedactionError("Die Datei ist keine lesbare PDF-Datei") from exc
    if doc.needs_pass or doc.is_encrypted:
        doc.close()
        raise RedactionError("Die PDF ist passwortgeschützt. Bitte zuerst entsperren.")
    if doc.page_count == 0:
        doc.close()
        raise RedactionError("Die PDF enthält keine Seiten")
    return doc


class _ViewTransform:
    """Umrechnung PDF-Koordinaten (bei CropBox = MediaBox) → Anzeige 0…1."""

    def __init__(self, page: Any):
        # Lage der CropBox in der aufgedeckten Seite. ``page.cropbox_position``
        # taugt nicht: Bei versetzter MediaBox ist dort x absolut, y relativ.
        crop, full = page.cropbox, _full_box(page)
        self.origin = fitz.Point(crop.x0 - full.x0, crop.y0 - full.y0)
        self.matrix = page.rotation_matrix
        self.view = fitz.Rect(page.rect)
        self.crop = fitz.Rect(0, 0, page.cropbox.width, page.cropbox.height)

    def to_view(self, rect: Any) -> tuple[list[float], bool]:
        local = fitz.Rect(rect) - (self.origin.x, self.origin.y, self.origin.x, self.origin.y)
        outside = not local.intersects(self.crop)
        r = local * self.matrix
        w, h = max(1.0, self.view.width), max(1.0, self.view.height)
        return [round(r.x0 / w, 5), round(r.y0 / h, 5), round(r.x1 / w, 5), round(r.y1 / h, 5)], outside

    def from_view(self, box: list[float]) -> Any:
        w, h = self.view.width, self.view.height
        r = fitz.Rect(box[0] * w, box[1] * h, box[2] * w, box[3] * h) * ~self.matrix
        r.normalize()
        return r + (self.origin.x, self.origin.y, self.origin.x, self.origin.y)


def _full_box(page: Any) -> Any:
    """Die MediaBox im Koordinatensystem von ``page.cropbox``.

    PyMuPDF führt die CropBox relativ zur Oberkante der MediaBox. Bei einer
    versetzten MediaBox (etwa ``[100 100 700 900]``) sind ``page.mediabox``
    und ``page.cropbox`` deshalb nicht direkt vergleichbar.
    """
    m = page.mediabox
    return fitz.Rect(m.x0, 0, m.x1, m.height)


def _expose_full_page(page: Any) -> Any | None:
    """CropBox vorübergehend auf die MediaBox setzen — sonst bleibt Text
    außerhalb des sichtbaren Bereichs für Suche und Schwärzung unsichtbar.
    Gibt die alte CropBox zurück, wenn sie geändert wurde."""
    full = _full_box(page)
    original = fitz.Rect(page.cropbox)
    if all(abs(a - b) < 0.01 for a, b in zip(original, full)):
        return None
    page.set_cropbox(full)
    return original


def _reveal_layers(doc: Any) -> list[tuple[int, str, str, str]]:
    """Ausgeblendete optionale Inhalte (Ebenen) einblenden, damit ihr Text
    gefunden und geschwärzt wird. Rückgabe: alte Werte für ``_restore_layers``.

    Neben ``/D/OFF`` und ``BaseState`` zählen Sichtbarkeitsregeln (OCMD):
    ``/P /AllOff`` oder ein Ausdruck ``/VE`` können Inhalte gerade dann
    ausblenden, wenn alle Ebenen an sind. Sie werden auf „sichtbar, wenn eine
    Ebene an ist“ gestellt. Scheitert ein Schritt, bleibt das bis dahin
    Geänderte in der Rückgabe, damit es wiederhergestellt wird."""
    saved: list[tuple[int, str, str, str]] = []

    def put(xref: int, key: str, value: str) -> None:
        kind, old = doc.xref_get_key(xref, key)
        saved.append((xref, key, kind, old))
        doc.xref_set_key(xref, key, value)

    try:
        cat = doc.pdf_catalog()
        if doc.xref_get_key(cat, "OCProperties")[0] == "null":
            return saved
        put(cat, "OCProperties/D/OFF", "[]")
        put(cat, "OCProperties/D/BaseState", "/ON")

        def open_rule(xref: int, prefix: str) -> None:
            kind = doc.xref_get_key(xref, prefix + "Type")[1]
            if kind == "/OCG" and doc.xref_get_key(xref, prefix + "Usage")[0] != "null":
                # /Usage/View/ViewState /OFF blendet die Ebene bei MuPDF aus.
                put(xref, prefix + "Usage", "null")
            elif kind == "/OCMD":
                if doc.xref_get_key(xref, prefix + "VE")[0] != "null":
                    put(xref, prefix + "VE", "null")
                if doc.xref_get_key(xref, prefix + "P")[1] not in ("", "/AnyOn"):
                    put(xref, prefix + "P", "/AnyOn")

        for xref in range(1, doc.xref_length()):
            open_rule(xref, "")
            # Regeln direkt in den Ressourcen: /Properties << /MD1 << /Type /OCMD … >> >>
            for base in ("Properties", "Resources/Properties"):
                kind, value = doc.xref_get_key(xref, base)
                if kind != "dict" or "/OCMD" not in value and "/OCG" not in value:
                    continue
                for name in set(re.findall(r"/([^\s/<>\[\]()]+)\s*<<", value)):
                    open_rule(xref, f"{base}/{name}/")
    except Exception:
        pass
    return saved


def _restore_layers(doc: Any, saved: list[tuple[int, str, str, str]]) -> None:
    for xref, key, kind, old in reversed(saved):
        if kind == "null":
            value = "null"
        elif kind == "string":
            value = fitz.get_pdf_str(old)
        else:
            value = old
        doc.xref_set_key(xref, key, value)
    # xref_set_key(…, "null") schreibt „/Key null“. Das ist gleichwertig mit
    # einem fehlenden Schlüssel, verändert aber die Datei; deshalb entfernen.
    for xref in {x for x, _k, kind, _o in saved if kind == "null"}:
        try:
            src = doc.xref_object(xref, compressed=True)
            names = {k.rsplit("/", 1)[-1] for x, k, kind, _o in saved if x == xref and kind == "null"}
            cleaned = re.sub(r"/(?:" + "|".join(map(re.escape, names)) + r")\s*null(?=[\s/>\]])", "", src)
            if cleaned != src:
                doc.update_object(xref, cleaned)
        except Exception:
            continue


def _resolve_overlaps(cands: list[Candidate]) -> list[Candidate]:
    """Überlappende Fundstellen einer Seite: Die längere gewinnt, bei gleicher
    Länge die mit höherer Priorität (Begriffe vor Mustern vor KI).

    Begriffe weichen nur anderen Begriffen. Ein eigener Begriff in einer
    E-Mail-Adresse oder einem KI-Namen bleibt als eigene Fundstelle stehen,
    damit er nicht unbemerkt lesbar bleibt, wenn die längere Fundstelle
    abgewählt wird.
    """
    ordered = sorted(cands, key=lambda c: (-(c.end - c.start), c.priority, c.start))
    kept: list[Candidate] = []
    taken_all: list[tuple[int, int]] = []
    taken_terms: list[tuple[int, int]] = []
    for c in ordered:
        is_term = c.source.startswith("begriff:")
        blockers = taken_terms if is_term else taken_all
        if any(c.start < e and c.end > s for s, e in blockers):
            continue
        kept.append(c)
        taken_all.append((c.start, c.end))
        if is_term:
            taken_terms.append((c.start, c.end))
    return sorted(kept, key=lambda c: c.start)


def _scan_page_text(
    pno: int,
    pt: _PageText,
    rules: list[_Rule],
    transform: _ViewTransform,
    ner_spans: list[tuple[int, int, str]] | None,
) -> list[Candidate]:
    found: list[Candidate] = []
    dehyph = _dehyphenated(pt)

    def add(source: str, start: int, end: int, priority: int, indices: list[int] | None = None) -> None:
        idx = indices if indices is not None else list(range(start, end))
        text = "".join(pt.text[i] for i in idx).replace(_SOFT, " ").strip()
        rects = _span_rects(pt, start, end, idx)
        if not rects or not text:
            return
        views = [transform.to_view(r) for r in rects]
        found.append(
            Candidate(
                id=_candidate_id(pno, source, start, end, _norm(text)),
                kind="text",
                source=source,
                text=" ".join(text.split()),
                page=pno + 1,
                rects=[[round(v, 2) for v in r] for r in rects],
                view_rects=[v for v, _ in views],
                outside_view=all(o for _, o in views),
                location="außerhalb des sichtbaren Bereichs" if all(o for _, o in views) else "Seitentext",
                start=start,
                end=end,
                priority=priority,
            )
        )

    for prio, rule in enumerate(rules):
        for s, e in _matches(rule, pt.text):
            add(rule.source, s, e, prio)
        if rule.is_term and dehyph:
            alt_text, mapping = dehyph
            for s, e in _matches(rule, alt_text):
                orig = mapping[s:e]
                # Nur Treffer, die tatsächlich über einen Trennstrich laufen
                if orig[-1] - orig[0] + 1 == len(orig):
                    continue
                full = list(range(orig[0], orig[-1] + 1))
                add(rule.source, orig[0], orig[-1] + 1, prio, full)
    for s, e, source in ner_spans or []:
        add(source, s, e, len(rules) + (1 if source == NER_PATTERN_ID else 2))
    return _resolve_overlaps(found)


_STANDARD_INFO = frozenset(
    ("Title", "Author", "Subject", "Keywords", "Creator", "Producer", "CreationDate", "ModDate", "Trapped")
)


def _info_xref(doc: Any) -> int:
    """Objektnummer des Info-Wörterbuchs, 0 wenn es keines gibt."""
    try:
        kind, value = doc.xref_get_key(-1, "Info")
        return int(value.split()[0]) if kind == "xref" else 0
    except Exception:
        return 0


def _custom_info(doc: Any) -> list[tuple[str, str]]:
    """Eigene Schlüssel im Info-Wörterbuch, die ``doc.metadata`` nicht zeigt."""
    xref = _info_xref(doc)
    if not xref:
        return []
    found = []
    for key in doc.xref_get_keys(xref):
        if key in _STANDARD_INFO:
            continue
        kind, value = doc.xref_get_key(xref, key)
        if kind == "string" and value:
            found.append((key, value))
    return found


def _iter_hidden_strings(doc: Any) -> Iterator[tuple[str, str, int | None, dict[str, Any]]]:
    """(Fundort, Text, Seite, Referenz) für alle versteckten Textablagen."""
    for key, value in (doc.metadata or {}).items():
        if value and key not in ("format", "encryption"):
            yield f"Metadaten ({key})", str(value), None, {"type": "metadata", "key": key}
    for key, value in _custom_info(doc):
        yield f"Metadaten ({key})", value, None, {"type": "infokey", "key": key}
    xmp = doc.get_xml_metadata() or ""
    if xmp:
        yield "XMP-Metadaten", xmp, None, {"type": "xmp"}
    for i, entry in enumerate(doc.get_toc(simple=True)):
        yield "Lesezeichen", str(entry[1]), entry[2] if entry[2] > 0 else None, {"type": "toc", "index": i}
    for page in doc:
        for annot in page.annots() or []:
            info = annot.info or {}
            text = " ".join(str(info.get(k) or "") for k in ("content", "title", "subject")).strip()
            if text:
                yield "Kommentar", text, page.number + 1, {"type": "annot", "page": page.number, "xref": annot.xref}
        for link in page.get_links():
            uri = link.get("uri") or link.get("file") or ""
            if uri:
                yield "Link", str(uri), page.number + 1, {"type": "link", "page": page.number, "xref": link.get("xref", 0), "uri": uri}
        for widget in page.widgets() or []:
            value = widget.field_value
            if value not in (None, "", False, "Off"):
                yield (
                    f"Formularfeld „{widget.field_name}“",
                    str(value),
                    page.number + 1,
                    {"type": "widget", "page": page.number, "xref": widget.xref},
                )
    for name in doc.embfile_names():
        try:
            data = doc.embfile_get(name)
        except Exception:
            continue
        text = name
        if len(data) <= 5 * 1024 * 1024:
            text += "\n" + data.decode("utf-8", errors="ignore")
        yield f"Dateianhang „{name}“", text, None, {"type": "attachment", "name": name}


def _scan_hidden(doc: Any, rules: list[_Rule]) -> list[Candidate]:
    found: list[Candidate] = []
    for location, text, page, ref in _iter_hidden_strings(doc):
        flat = " ".join(_clean(text).split())
        for prio, rule in enumerate(rules):
            for s, e in _matches(rule, flat):
                hit = flat[s:e]
                found.append(
                    Candidate(
                        id=_candidate_id("hidden", location, sorted(ref.items()), rule.source, s, _norm(hit)),
                        kind="hidden",
                        source=rule.source,
                        text=hit,
                        page=page,
                        location=location,
                        ref=ref,
                        priority=prio,
                        start=s,
                        end=e,
                    )
                )
    return found


def _cleanup_info(doc: Any) -> dict[str, Any]:
    meta = {k: v for k, v in (doc.metadata or {}).items() if v and k not in ("format", "encryption")}
    meta.update(_custom_info(doc))
    js = False
    try:
        js = any("/JavaScript" in doc.xref_object(x, compressed=True) or "/JS" in doc.xref_object(x, compressed=True)
                 for x in range(1, min(doc.xref_length(), 20000)))
    except Exception:
        js = False
    return {
        "metadata_fields": sorted(meta),
        "xmp": bool(doc.get_xml_metadata()),
        "attachments": len(doc.embfile_names()),
        "javascript": js,
    }


NerFn = Callable[[list[str]], list[list[tuple[int, int]]]]
# Namensbestandteil: großer Anfangsbuchstabe, auch mit Bindestrich („Meyer-Lüdenscheidt“).
_NAME_PART = r"[A-ZÄÖÜ][a-zäöüß]+(?:-[A-ZÄÖÜ][a-zäöüß]+)*"
# Titel vor einem Namen („Prof. Dr.“, „Dipl.-Ing.“). Mit Titel davor erkennt
# die KI „Prof. Dr. Rainer Zufall“ nicht als Person, ohne Titel schon.
_TITLES = re.compile(r"(?:(?:Prof|Dr|Dipl)\.(?:-[A-Za-zäöü]+\.)?\s*)+")
# Listenform „Nachname, Vorname“ am Zeilenanfang, auch mit Titel davor.
_LIST_NAME = re.compile(rf"(?:{_TITLES.pattern})?(?P<last>{_NAME_PART}),[ \t]*(?P<first>{_NAME_PART})(?![\w-])")
# Wörter, die die KI gelegentlich als Namen meldet, die aber nie im ganzen
# Dokument nachgesucht werden sollen.
# Kontaktangaben in Briefköpfen und Spaltenköpfen; spaCy hält „Telefon X“
# oft für eine Person, auch im Mustersatz.
_CONTACT_WORDS = frozenset("Telefon Telefonnummer Telefax Fax Tel Mobil Handy Durchwahl".split())
# Häufige Spaltenköpfe in Belegen und Rechnungen: Der Mustersatz bestätigt
# manche Paare davon als Person („Pos Menge“, „Netto Brutto“). Aus einer
# Zelle oder Kopfzeile belegt, werden sie nur mit Anrede davor nachgesucht;
# was die KI direkt meldet, bleibt Fundstelle. Aus einem Satz oder der
# Listenform neben einem anderen Wort belegt, sind es Nachnamen („Petra
# Preis“, „Menge, Wolfgang“) und gelten wie jeder andere Name; nur aus
# Spaltenköpfen („Summe Netto nach Skonto“) gilt der Beleg als Zellbeleg.
_TABLE_WORDS = frozenset(
    "Pos Position Menge Anzahl Einheit Preis Einzelpreis Gesamtpreis Gesamt Summe Zwischensumme"
    " Betrag Netto Brutto Steuer Umsatzsteuer Mehrwertsteuer USt MwSt Rabatt Skonto Kostenart"
    " Bemerkung Datum Nummer Rechnung Beleg".split()
)
_NOT_NAMES = frozenset(
    "Herr Herrn Frau Prof Dipl Montag Dienstag Mittwoch Donnerstag Freitag Samstag Sonntag "
    "Januar Februar März April Mai Juni Juli August September Oktober November Dezember".split()
    + list(_CONTACT_WORDS)
)
# Monatskürzel: „Jan“ ist ein Vorname, „15. Jan. 2026“ aber ein Datum.
_MONTH_ABBREVIATIONS = frozenset("Jan Feb Mär Apr Jun Jul Aug Sep Sept Okt Nov Dez".split())
# Nach einem Artikel ist ein nachgesuchtes Wort ein Substantiv
# („der Richter“, „ein Koch“), kein Name.
_ARTICLE_BEFORE = re.compile(
    r"(?:^|[^\w])(?:der|die|das|dem|den|des|ein|eine|einem|einen|einer|eines)\s+$", re.IGNORECASE
)
# … außer als Teil eines Namenszusatzes („von der Heide“, „van den Berg“).
_NAME_PREFIX_BEFORE = re.compile(r"(?:^|[^\w])(?:von|vom|van|zu|zur|ter|de)\s+\w+\s+$", re.IGNORECASE)
# Monatskürzel im Datum: „15. Jan.“, „Jan. 2026“.
_DAY_BEFORE = re.compile(r"\d{1,2}\.\s*$")
_YEAR_AFTER = re.compile(r"\.\s*\d{2,4}(?!\d)")
# Bestandteile eines KI-Treffers, auch Initialen („J.“) und Buchstaben
# außerhalb des deutschen Alphabets („Çelik“).
_SPAN_PART = re.compile(r"[^\W\d_]+")
# Nachsuche mit Grenze: Ein Wort, das über Zellgrenzen hinweg oder nur aus
# einer Zelle oder Kopfzeile belegt ist und das die KI dort nicht im
# Mustersatz bestätigt, wird höchstens max(Untergrenze, Faktor × direkt
# erkannt) Mal ohne Anrede nachgesucht, sonst gar nicht. „Direkt erkannt“
# zählt verschiedene Fundstellentexte, damit ein Spaltenkopf, der auf jeder
# Seite wiederkehrt, die Grenze nicht hebt. Grund: Ein Fehltreffer („Summe
# Netto“ als Person, zwei Spaltenköpfe nebeneinander) würde sonst jedes
# „Summe“ im Dokument schwärzen. Namen aus einem Satz, der Listenform oder
# dem Mustersatz gelten ohne Grenze: spaCy erkennt einen allein stehenden
# Nachnamen fast nie, ein häufig genannter Name wäre sonst überall lesbar.
_PROPAGATION_FLOOR = 10
_PROPAGATION_FACTOR = 4
# Belege über Zellgrenzen („Klaus / Wagner“ in getrennten Spalten) und
# Zellbelege, deren Name der Mustersatz nur zum Teil bestätigt
# („Auftragnehmer Thomas Berger“ → „Thomas Berger“), bekommen mit
# Bestätigung eine höhere Untergrenze, aber keine Freigabe: Der Mustersatz
# bestätigt so auch Spaltenköpfe („Belegart Auftraggeber“), die dann in
# einer Belegliste in jeder Zeile geschwärzt würden.
_PROPAGATION_FLOOR_CONFIRMED = 50
# Zellbelege bestätigt die KI in einem Mustersatz, Kontaktwörter vorher
# entfernt. Erprobt mit de_core_news_sm: 46 von 47 echten Namen bestätigt;
# bestätigt werden aber auch manche Paare aus Spaltenköpfen („Netto
# Brutto“). Belege über Zellgrenzen hinweg werden deshalb nicht bestätigt.
_CONFIRM_FRAME = "Gestern habe ich {} getroffen."
_CONFIRM_START = _CONFIRM_FRAME.index("{}")
# Anrede oder Titel vor dem Wort: Die Fundstelle bleibt auch über der Grenze.
_SALUTATION_BEFORE = re.compile(
    r"(?:^|[^\w])(?:(?:Herrn?|Frau)\s+|(?:Hr|Fr|Dr|Prof|Dipl)\.(?:\s*-?[A-Za-zäöüÄÖÜ]+\.)*(?:\s*\([A-Z]+\))?\s*)$"
)
_WORD_RUN = re.compile(r"[\w-]+")
_NAME_EDGE = " \t,;:()[]/"
# Abschnitte zwischen harten Grenzen bis zu dieser Wortzahl prüft die KI
# zusätzlich für sich (Tabellenzellen, Listeneinträge). Ein Absatz ist ein
# langer Abschnitt; Teile davon ohne Satzzusammenhang ergäben Fehltreffer
# wie „Förderantrag“.
_SHORT_SEGMENT_WORDS = 6
# Quelle der Fundstellen, die nicht die KI selbst gemeldet hat, sondern die
# als bereits erkannter Name im Dokument nachgesucht wurden. Eigene Gruppe,
# damit die Vorschau sie gesammelt abwählen kann.
NER_PROPAGATED_ID = "ki_namen_nachgesucht"


def _hard_parts(text: str, start: int, end: int) -> list[tuple[int, int]]:
    """Eine KI-Fundstelle an harten Grenzen (Zelle, Spalte, Absatz) teilen.

    spaCy fasst in Tabellen Namen aus benachbarten Zellen zu einem zusammen
    („Jan Reiter Stahl“). Über einen gewöhnlichen Zeilenumbruch im Fließtext
    darf ein Name dagegen laufen.
    """
    parts: list[tuple[int, int]] = []
    pos, end = max(0, start), min(end, len(text))
    while pos < end:
        stop = text.find(_HARD, pos, end)
        stop = end if stop < 0 else stop
        a, b = pos, stop
        while a < b and text[a] in _NAME_EDGE:
            a += 1
        while b > a and text[b - 1] in _NAME_EDGE:
            b -= 1
        if sum(ch.isalpha() for ch in text[a:b]) >= 2:
            parts.append((a, b))
        pos = stop + 1
    return parts


def _short_segments(text: str) -> list[tuple[int, int]]:
    """Kurze Abschnitte zwischen harten Grenzen, ohne Leerraum und Titel am Anfang."""
    segments: list[tuple[int, int]] = []
    pos = 0
    while pos <= len(text):
        stop = text.find(_HARD, pos)
        stop = len(text) if stop < 0 else stop
        a, b = pos, stop
        while a < b and text[a].isspace():
            a += 1
        while b > a and text[b - 1].isspace():
            b -= 1
        title = _TITLES.match(text, a, b)
        if title:
            a = title.end()
        if b > a and len(text[a:b].split()) <= _SHORT_SEGMENT_WORDS:
            segments.append((a, b))
        pos = stop + 1
    return segments


def _line_segments(pt: _PageText) -> list[tuple[int, int]]:
    """Zeichenbereiche der einzelnen Textzeilen, ohne Leerraum am Rand."""
    segments: list[tuple[int, int]] = []
    i, n = 0, len(pt.lines)
    while i < n:
        line = pt.lines[i]
        j = i
        while j < n and pt.lines[j] == line:
            j += 1
        if line >= 0:
            a, b = i, j
            while a < b and pt.text[a].isspace():
                a += 1
            while b > a and pt.text[b - 1].isspace():
                b -= 1
            if b > a:
                segments.append((a, b))
        i = j
    return segments


def _name_tokens(text: str) -> list[str]:
    """Wörter eines Namens, die im Dokument nachgesucht werden dürfen."""
    return [
        t
        for t in re.findall(r"[^\W\d_]+(?:-[^\W\d_]+)*", text)
        if len(t) >= 3
        and all(p[:1].isupper() and p[1:].islower() for p in t.split("-"))
        and t not in _NOT_NAMES
        and not any(p in _CONTACT_WORDS for p in t.split("-"))
    ]


_TITLE_IN_SPAN = re.compile(r"(?<![\w-])(?:(?:Herrn?|Frau)(?![\w-])|(?:Hr|Fr|Dr|Prof|Dipl)\.)")


def _free_tokens(text: str) -> list[str] | None:
    """Wörter eines Satz- oder Listenbelegs, die ohne Grenze nachgesucht
    werden. Besteht der Beleg nur aus Spaltenköpfen („Summe Netto nach
    Skonto“, „Netto, Brutto“), ist er kein Name: ``None``, er gilt dann wie
    ein Zellbeleg. Neben einem anderen Wort („Petra Preis“) oder nach Anrede
    oder Titel („Dr. Menge“) ist der Spaltenkopf ein Nachname."""
    tokens = _name_tokens(text)
    if any(t not in _TABLE_WORDS for t in tokens) or (tokens and _TITLE_IN_SPAN.search(text)):
        return tokens
    return None


def _is_name_noun(text: str, start: int, end: int) -> bool:
    """Steht das nachgesuchte Wort hier als Substantiv oder Datum statt als Name?"""
    before = text[max(0, start - 30) : start]
    if _ARTICLE_BEFORE.search(before) and not _NAME_PREFIX_BEFORE.search(before):
        return True
    if text[start:end] in _MONTH_ABBREVIATIONS and text[end : end + 1] == ".":
        return bool(_DAY_BEFORE.search(text[max(0, start - 6) : start]) or _YEAR_AFTER.match(text, end))
    return False


def _ner_document(pts: list[_PageText], ner: NerFn) -> list[list[tuple[int, int, str]]]:
    """KI-Namenserkennung über das ganze Dokument.

    Je Seite werden drei Quellen zusammengeführt:
    - der Seitentext im Zusammenhang (Namen über Zeilenumbrüche hinweg),
      geteilt an harten Grenzen;
    - jeder kurze Abschnitt für sich (Tabellenzellen, Listeneinträge),
      ohne Titel am Anfang; gleiche Abschnitte prüft die KI nur einmal;
    - die Listenform „Nachname, Vorname“, wenn die KI „Vorname Nachname“
      als Person erkennt.

    Alles, was die KI meldet, wird direkt übernommen: Ein übersehener Name
    wiegt schwerer als ein Fehltreffer, den die Vorschau abwählen kann.

    Nachgesucht werden die Bestandteile belegter Namen (Quelle
    ``NER_PROPAGATED_ID``), etwa ein allein stehender Nachname. Belegt ist
    ein Name, den die KI aus mindestens zwei Bestandteilen erkennt oder den
    die Listenform bestätigt. Nicht nachgesucht wird, wo das Wort als
    Substantiv oder Datum steht (``_is_name_noun``). Steht der Beleg nicht
    in einem Satz (``_has_context``), sondern in einer Zelle oder Kopfzeile,
    muss die KI ihn im Mustersatz ``_CONFIRM_FRAME`` als Person bestätigen;
    sonst gilt die Obergrenze ``_PROPAGATION_FLOOR``/``_PROPAGATION_FACTOR``.
    Belege über Zellgrenzen hinweg bekommen auch mit Bestätigung nur die
    höhere Untergrenze ``_PROPAGATION_FLOOR_CONFIRMED``, ebenso Zellbelege,
    deren Name der Mustersatz nur zum Teil bestätigt. Spaltenköpfe aus
    ``_TABLE_WORDS`` werden aus Zellbelegen nie ohne Anrede nachgesucht. Über der Grenze
    bleiben nur Fundstellen mit Anrede oder Titel davor. Der Mustersatz läuft
    nur für Wörter, die sonst an der Grenze scheitern.

    Rückgabe: je Seite (start, ende, quelle).
    """
    jobs: list[str] = []
    segment_job: dict[str, int] = {}
    layout = []
    for pt in pts:
        full = len(jobs)
        jobs.append(pt.text.replace(_HARD, "\n"))
        segments: list[tuple[int, int]] = []
        for a, b in _short_segments(pt.text):
            segment = pt.text[a:b]
            if segment not in segment_job:
                segment_job[segment] = len(jobs)
                jobs.append(segment)
            segments.append((a, segment_job[segment]))
        listed: list[tuple[int, int, int]] = []
        for a, b in _line_segments(pt):
            m = _LIST_NAME.match(pt.text, a, b)
            if m and m.group("last") not in _NOT_NAMES and m.group("first") not in _NOT_NAMES:
                listed.append((m.start("last"), m.end("first"), len(jobs)))
                jobs.append(f"{m.group('first')} {m.group('last')}")
        layout.append((full, segments, listed))
    results = _ner_results(ner, jobs)

    sure: set[str] = set()  # ohne Grenze nachgesucht
    loose: set[str] = set()  # Grenze _PROPAGATION_FLOOR_CONFIRMED
    cell_spans: dict[str, set[str]] = {}  # Zellbeleg → Wörter, vor der Bestätigung
    cross_spans: dict[str, set[str]] = {}  # Beleg über Zellgrenzen, ebenso

    def from_cell(text: str, into: dict[str, set[str]]) -> None:
        tokens = _name_tokens(text)
        if tokens:
            words = [
                w
                for w in text.replace(_HARD, " ").split()
                if not any(p.strip(".,;:") in _CONTACT_WORDS for p in re.split(r"[/-]", w))
            ]
            into.setdefault(" ".join(words), set()).update(tokens)

    direct_pages: list[list[tuple[int, int]]] = []
    for pt, (full, segments, listed) in zip(pts, layout):
        direct: set[tuple[int, int]] = set()
        for s, e in results[full]:
            s, e = max(0, s), min(e, len(pt.text))
            if e <= s:
                continue
            parts = _hard_parts(pt.text, s, e)
            direct.update(parts)
            for a, b in parts:
                if len(_SPAN_PART.findall(pt.text[a:b])) >= 2:
                    if _has_context(pt, a, b) and (free := _free_tokens(pt.text[a:b])) is not None:
                        sure.update(free)
                    else:
                        from_cell(pt.text[a:b], cell_spans)
            # Über Zellgrenzen erkannt („Klaus / Wagner“ in getrennten
            # Spalten, „Jan / Reiter / Stahl“).
            if len(parts) > 1 and len(_SPAN_PART.findall(pt.text[s:e])) >= 2:
                from_cell(pt.text[s:e], cross_spans)
        for offset, k in segments:
            length = len(jobs[k])
            for s, e in results[k]:
                s, e = max(0, s), min(e, length)
                for a, b in _hard_parts(pt.text, offset + s, offset + e):
                    direct.add((a, b))
                    if len(_SPAN_PART.findall(pt.text[a:b])) >= 2:
                        from_cell(pt.text[a:b], cell_spans)
        for s, e, k in listed:
            if any(a == 0 and b == len(jobs[k]) for a, b in results[k]):
                direct.add((s, e))
                free = _free_tokens(pt.text[s:e])
                if free is None:
                    from_cell(pt.text[s:e], cell_spans)
                else:
                    sure.update(free)
        direct_pages.append(sorted(direct))

    out = [[(a, b, NER_PATTERN_ID) for a, b in direct] for direct in direct_pages]
    strong = sure | {t for spans in (cell_spans, cross_spans) for tokens in spans.values() for t in tokens}
    if not strong:
        return out
    direct_texts: dict[str, set[str]] = {}
    found: dict[str, list[tuple[int, int, int, bool]]] = {}
    for pno, (pt, direct) in enumerate(zip(pts, direct_pages)):
        merged = _merge_spans(direct)
        starts = [a for a, _ in merged]
        for x, y in direct:
            for word in _WORD_RUN.findall(pt.text, x, y):
                if word in strong:
                    direct_texts.setdefault(word, set()).add(pt.text[x:y])
        for m in _WORD_RUN.finditer(pt.text):
            word = m.group()
            if word not in strong:
                continue
            a, b = m.span()
            i = bisect.bisect_right(starts, a) - 1
            if (i >= 0 and merged[i][1] > a) or (i + 1 < len(merged) and merged[i + 1][0] < b):
                continue
            if not _is_name_noun(pt.text, a, b):
                addressed = bool(_SALUTATION_BEFORE.search(pt.text[max(0, a - 30) : a]))
                found.setdefault(word, []).append((pno, a, b, addressed))

    def capped(word: str) -> bool:
        if word in sure:
            return False
        if word in _TABLE_WORDS:
            return True
        floor = _PROPAGATION_FLOOR_CONFIRMED if word in loose else _PROPAGATION_FLOOR
        limit = max(floor, _PROPAGATION_FACTOR * len(direct_texts.get(word, ())))
        return len(found[word]) > limit

    # Den Mustersatz braucht nur, wer sonst an der Grenze scheitert;
    # Spaltenköpfe hebt er nicht über die Grenze.
    over = {
        w for w in found if w not in _TABLE_WORDS and capped(w) and not all(addressed for *_, addressed in found[w])
    }
    # Über Zellgrenzen hilft die Bestätigung nur bis _PROPAGATION_FLOOR_CONFIRMED.
    loose_limit = {
        w: max(_PROPAGATION_FLOOR_CONFIRMED, _PROPAGATION_FACTOR * len(direct_texts.get(w, ()))) for w in over
    }
    probes = sorted(
        (t, k)
        for k, spans in enumerate((cell_spans, cross_spans))
        for t, tokens in spans.items()
        if len(_SPAN_PART.findall(t)) >= 2
        and any(w in over and (not k or len(found[w]) <= loose_limit[w]) for w in tokens)
    )
    frames = [_CONFIRM_FRAME.format(t) for t, _k in probes]
    for (text, k), spans in zip(probes, _ner_results(ner, frames)):
        # Bestätigt die KI nur einen Teil („Auftragnehmer Thomas Berger“ →
        # „Thomas Berger“), gelten dessen Wörter mit der höheren
        # Untergrenze, wenn er mindestens zwei Bestandteile hat; ohne Grenze
        # nur, wenn die bestätigten Teile alle Wörter des Zellbelegs decken.
        tokens = (cross_spans if k else cell_spans)[text]
        end = _CONFIRM_START + len(text)
        confirmed: set[str] = set()
        for a, b in spans:
            a, b = max(a, _CONFIRM_START), min(b, end)
            piece = text[a - _CONFIRM_START : b - _CONFIRM_START]
            if b > a and len(_SPAN_PART.findall(piece)) >= 2:
                confirmed.update(set(_name_tokens(piece)) & tokens)
        (sure if not k and confirmed == tokens else loose).update(confirmed - _TABLE_WORDS)
    for word, hits in found.items():
        limited = capped(word)
        for pno, a, b, addressed in hits:
            if addressed or not limited:
                out[pno].append((a, b, NER_PROPAGATED_ID))
    return [sorted(spans) for spans in out]


def _ner_results(ner: NerFn, jobs: list[str]) -> list[list[tuple[int, int]]]:
    """Ergebnis der KI prüfen: je Text eine Liste von (start, ende)."""
    if not jobs:
        return []
    failed = "KI-Namenserkennung ist fehlgeschlagen"
    invalid = "KI-Namenserkennung lieferte ein ungültiges Ergebnis"
    try:
        raw = ner(jobs)
    except Exception as exc:  # Fehler der KI-Funktion selbst: Serverseite
        raise RedactionNerError(failed) from exc
    try:
        items = iter(raw)
    except TypeError as exc:  # kein Ergebnis in Listenform
        raise RedactionNerError(invalid) from exc
    try:
        # Generatoren (auch innere) laufen erst hier: ihre Fehler sind
        # Fehler der KI-Funktion, falsche Werte ein ungültiges Ergebnis.
        results = [[(int(s), int(e)) for s, e in spans] for spans in items]
    except (TypeError, ValueError) as exc:
        raise RedactionNerError(invalid) from exc
    except Exception as exc:
        raise RedactionNerError(failed) from exc
    if len(results) != len(jobs):
        raise RedactionNerError("KI-Namenserkennung lieferte ein ungültiges Ergebnis")
    return results


# Kleinwörter, die auch in Kopfzeilen stehen („Betrag in EUR“, „Preis je
# Stück“, „Name und Anschrift“), und Abkürzungen („inkl. USt“, „lfd. Nr.“).
# Andere Präpositionen („Antrag von …“, „Rechnung an …“) zählen als Satz.
_NO_CONTEXT = frozenset(
    "in im je pro bis und oder inkl zzgl abzgl exkl einschl bzw ggf ggfs gem lt ca evtl vgl usw lfd nr max min".split()
)


def _has_context(pt: _PageText, start: int, end: int) -> bool:
    """Steht der Treffer in einem Satz? Verlangt wird ein kleingeschriebenes
    Wort in derselben Zelle, in der Zeile des Treffers oder einer Zeile direkt
    davor oder danach („Projektleiter ist Thomas Berger“, auch umbrochen).
    Weiter entfernte Zeilen desselben Blocks zählen nicht: Ein Formular, das
    MuPDF als einen Block liest, macht sonst aus einem Etikett oben
    („Kundennummer Belegart Auftraggeber“) einen Satz.
    Eine Kopfzeile aus Großwörtern („Ort Telefon Begünstigter Betrag“) liest
    MuPDF bei engen Spalten als eine Zeile; sie ist kein Satz. Wörter aus
    ``_NO_CONTEXT`` („in EUR“, „je Stück“, „inkl. USt“) stehen auch in
    Kopfzeilen und zählen nicht."""
    text = pt.text
    left = text.rfind(_HARD, 0, start) + 1
    right = text.find(_HARD, end)
    right = len(text) if right < 0 else right
    row = (lambda n: pt.rows[n]) if pt.rows else (lambda n: n)
    hit_lines = [row(n) for n in pt.lines[start:end] if n >= 0]
    first, last = (min(hit_lines) - 1, max(hit_lines) + 1) if hit_lines else (-1, -1)
    return any(
        m.group()[0].islower()
        and m.group() not in _NO_CONTEXT
        and (not hit_lines or (pt.lines[m.start()] >= 0 and first <= row(pt.lines[m.start()]) <= last))
        for lo, hi in ((left, start), (end, right))
        for m in _SPAN_PART.finditer(text, lo, hi)
    )


def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for a, b in sorted(spans):
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def build_plan(data: bytes, criteria: Criteria, ner: NerFn | None = None) -> Plan:
    """Alle Fundstellen ermitteln — Grundlage für Vorschau und Anwendung."""
    if NER_PATTERN_ID in criteria.patterns and ner is None:
        raise RedactionError("KI-Namenserkennung nicht verfügbar (spaCy-Modell fehlt)")
    rules = _rules(criteria)
    doc = open_pdf(data)
    try:
        _reveal_layers(doc)  # Text ausgeblendeter Ebenen mitsuchen; doc wird verworfen
        pages: list[PageInfo] = []
        candidates: list[Candidate] = []
        # Mit KI braucht die Erkennung alle Seiten zugleich (Nachsuche über das
        # ganze Dokument); ohne KI wird jede Seite sofort durchsucht.
        use_ner = NER_PATTERN_ID in criteria.patterns and ner is not None
        texts: list[tuple[_PageText, _ViewTransform]] = []
        for page in doc:
            transform = _ViewTransform(page)
            info = PageInfo(page.number + 1, page.rect.width, page.rect.height, page.rotation, False, False)
            _expose_full_page(page)
            pt = _page_text(page)
            info.has_text = any(r is not None for r in pt.rects)
            if not info.has_text:
                info.image_only = bool(page.get_images(full=False)) or bool(page.get_drawings()[:1])
            pages.append(info)
            if use_ner:
                texts.append((pt, transform))
            else:
                candidates.extend(_scan_page_text(page.number, pt, rules, transform, None))
        if use_ner and ner is not None:
            ner_spans = _ner_document([pt for pt, _ in texts], ner)
            for pno, ((pt, transform), spans) in enumerate(zip(texts, ner_spans)):
                candidates.extend(_scan_page_text(pno, pt, rules, transform, spans))
        candidates.extend(_scan_hidden(doc, rules))
        cleanup = _cleanup_info(doc)
    finally:
        doc.close()
    return Plan(hashlib.sha256(data).hexdigest(), criteria, pages, candidates, cleanup)


# ── Anwendung ────────────────────────────────────────────────


@dataclass(frozen=True)
class Area:
    page: int  # 1-basiert
    box: tuple[float, float, float, float]  # 0…1 in Anzeigekoordinaten


@dataclass(frozen=True)
class Selection:
    sha256: str
    criteria: Criteria
    selected: frozenset[str]
    areas: tuple[Area, ...] = ()
    sanitize: bool = True

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Selection:
        if not isinstance(payload, dict):
            raise RedactionError("Plan muss ein JSON-Objekt sein")
        crit = payload.get("criteria") or {}
        if not isinstance(crit, dict):
            raise RedactionError("„criteria“ muss ein JSON-Objekt sein")
        patterns, terms = crit.get("patterns") or [], crit.get("terms") or []
        for name, values in (("patterns", patterns), ("terms", terms)):
            if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
                raise RedactionError(f"„criteria.{name}“ muss eine Liste von Texten sein")
        criteria = Criteria.from_input(
            patterns,
            terms,
            bool(crit.get("case_sensitive", False)),
            bool(crit.get("whole_word", True)),
        )
        selected = payload.get("selected")
        if not isinstance(selected, list) or not all(isinstance(s, str) for s in selected):
            raise RedactionError("„selected“ muss eine Liste von Kennungen sein")
        raw_areas = payload.get("areas") or []
        if not isinstance(raw_areas, list) or len(raw_areas) > MAX_AREAS:
            raise RedactionError(f"Höchstens {MAX_AREAS} Bereiche")
        areas: list[Area] = []
        for a in raw_areas:
            if not isinstance(a, dict):
                raise RedactionError("Bereich braucht „page“ und „rect“ [x0, y0, x1, y1]")
            try:
                raw_page, raw_rect = a["page"], a["rect"]
                if isinstance(raw_page, bool) or not isinstance(raw_page, int):
                    raise TypeError("page")
                page = raw_page
                x0, y0, x1, y1 = (float(v) for v in raw_rect)
                if not all(math.isfinite(v) for v in (x0, y0, x1, y1)):
                    raise ValueError("rect")
            except (KeyError, TypeError, ValueError, OverflowError) as exc:
                raise RedactionError("Bereich braucht „page“ (ganze Zahl) und „rect“ [x0, y0, x1, y1]") from exc
            box = (
                max(0.0, min(x0, x1)), max(0.0, min(y0, y1)),
                min(1.0, max(x0, x1)), min(1.0, max(y0, y1)),
            )
            if box[2] - box[0] <= 0 or box[3] - box[1] <= 0:
                continue
            areas.append(Area(page, box))
        per_page: dict[int, int] = {}
        for area in areas:
            per_page[area.page] = per_page.get(area.page, 0) + 1
        crowded = [p for p, n in per_page.items() if n > MAX_AREAS_PER_PAGE]
        if crowded:
            raise RedactionError(f"Höchstens {MAX_AREAS_PER_PAGE} Bereiche je Seite (Seite {crowded[0]})")
        return cls(
            sha256=str(payload.get("sha256") or ""),
            criteria=criteria,
            selected=frozenset(selected),
            areas=tuple(areas),
            sanitize=bool(payload.get("sanitize", True)),
        )


@dataclass
class ApplyReport:
    redactions: int
    areas: int
    hidden_removed: int
    by_source: dict[str, int]
    pages: list[int]
    sanitized: list[str]
    deselected: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "redactions": self.redactions,
            "areas": self.areas,
            "hidden_removed": self.hidden_removed,
            "by_source": self.by_source,
            "pages": self.pages,
            "sanitized": self.sanitized,
            "deselected": self.deselected,
            "verified": True,
        }


def _literal(text: str) -> re.Pattern:
    return re.compile(r"\s+".join(re.escape(p) for p in text.split()), re.IGNORECASE)


def _remove_hidden(doc: Any, cands: list[Candidate]) -> None:
    """Versteckte Fundstellen eines Fundorts entfernen oder leeren."""
    ref = cands[0].ref
    kind = ref.get("type")
    if kind == "metadata":
        meta = dict(doc.metadata or {})
        meta[ref["key"]] = ""
        doc.set_metadata({k: v for k, v in meta.items() if k not in ("format", "encryption")})
    elif kind == "infokey":
        info = _info_xref(doc)
        if info:
            doc.xref_set_key(info, ref["key"], "null")
    elif kind == "xmp":
        doc.del_xml_metadata()
    elif kind == "toc":
        toc = doc.get_toc(simple=False)
        i = ref["index"]
        if i < len(toc):
            original = title = toc[i][1]
            # Nur die ausgewählten Treffer ersetzen, abgewählte bleiben stehen.
            for cand in cands:
                title = _literal(cand.text).sub(REDACTED_MARK, title)
            # Unsichtbare Zeichen (etwa „Kra\u200buse“) verhindern das Ersetzen im
            # Rohtext. Steht danach noch ein ausgewählter Text im bereinigten
            # Titel, wird der ganze Titel ersetzt.
            leftover = any(_flat(c.text) in _flat(_clean(title)) for c in cands)
            toc[i][1] = REDACTED_MARK if title == original or leftover else title
            doc.set_toc(toc)
    elif kind == "annot":
        page = doc[ref["page"]]
        for annot in page.annots() or []:
            if annot.xref == ref["xref"]:
                page.delete_annot(annot)
                break
    elif kind == "link":
        page = doc[ref["page"]]
        for link in page.get_links():
            if link.get("xref", 0) == ref["xref"] and (link.get("uri") or link.get("file") or "") == ref["uri"]:
                page.delete_link(link)
                break
    elif kind == "widget":
        page = doc[ref["page"]]
        for widget in page.widgets() or []:
            if widget.xref == ref["xref"]:
                page.delete_widget(widget)
                break
    elif kind == "attachment":
        try:
            doc.embfile_del(ref["name"])
        except Exception:
            pass


_ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f"}


def _decode_pdf_bytes(raw: bytes) -> str:
    if raw[:2] == b"\xfe\xff":
        return raw[2:].decode("utf-16-be", errors="ignore")
    if raw[:3] == b"\xef\xbb\xbf":
        return raw[3:].decode("utf-8", errors="ignore")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="ignore")


def _decode_literal(body: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(body):
        c = body[i]
        if c != "\\":
            out.append(c)
            i += 1
            continue
        i += 1
        if i >= len(body):
            break
        e = body[i]
        if e in _ESCAPES:
            out.append(_ESCAPES[e])
        elif e in "01234567":
            j = i
            while j < len(body) and j < i + 3 and body[j] in "01234567":
                j += 1
            out.append(chr(int(body[i:j], 8) & 0xFF))
            i = j
            continue
        elif e in "\r\n":
            if e == "\r" and body[i + 1 : i + 2] == "\n":
                i += 1
        else:
            out.append(e)
        i += 1
    return _decode_pdf_bytes("".join(out).encode("latin-1", errors="replace"))


def _pdf_strings(src: str, start: int = 0, only_at: int | None = None) -> Iterator[tuple[int, int, str]]:
    """Zeichenketten im Quelltext eines PDF-Objekts: (Anfang, Ende, Text).

    ``src`` ist latin-1-dekodiert, ein Zeichen je Byte. Mit ``only_at`` wird
    nur die Zeichenkette gelesen, die genau dort beginnt."""
    i = start
    n = len(src)
    while i < n:
        c = src[i]
        if c == "(":
            depth, j = 1, i + 1
            while j < n and depth:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == "(":
                    depth += 1
                elif src[j] == ")":
                    depth -= 1
                j += 1
            yield i, j, _decode_literal(src[i + 1 : j - 1])
            i = j
        elif c == "<" and src[i + 1 : i + 2] != "<":
            j = src.find(">", i)
            if j < 0:
                return
            digits = "".join(src[i + 1 : j].split())
            if len(digits) % 2:
                digits += "0"
            try:
                yield i, j + 1, _decode_pdf_bytes(bytes.fromhex(digits))
            except ValueError:
                pass
            i = j + 1
        elif c == "<":
            i += 2
        else:
            i += 1
        if only_at is not None:
            return


# Einträge in Inhaltsströmen, die Text unabhängig von den Glyphen tragen.
_STREAM_TEXT_KEYS = re.compile(r"/(?:ActualText|Alt|E)\s*(?=[(<])")


class _KeyIndex:
    """Schnelle Suche vieler Schlüssel (Vergleichsform) in vielen Texten:
    Index über die ersten drei Zeichen statt Schlüssel × Texte."""

    def __init__(self, keys: Iterable[str]):
        self.by_prefix: dict[str, list[str]] = {}
        self.short: list[str] = []
        for k in sorted(set(keys), key=len, reverse=True):
            if len(k) >= 3:
                self.by_prefix.setdefault(k[:3], []).append(k)
            elif k:
                self.short.append(k)

    def __bool__(self) -> bool:
        return bool(self.by_prefix or self.short)

    def found(self, text: str) -> Iterator[str]:
        """Schlüssel in ``text`` (bereinigt). Kurze Schlüssel zählen nur als
        ganzes Wort, sonst träfe „AB“ jede „Abbildung“."""
        if self.short:
            words = unicodedata.normalize("NFKC", text).casefold()
            yield from (k for k in self.short if _word_in(words, k))
        flat = _flat(text)
        for i in range(len(flat) - 2):
            for k in self.by_prefix.get(flat[i : i + 3], ()):
                if flat.startswith(k, i):
                    yield k


# Zeichenketten, die nur eine andere Darstellung sichtbarer Inhalte sind
# (Alternativtext, Ersatztext, Abkürzung, Feld-Tooltip). Sie werden ersetzt,
# sobald sie einen geschwärzten Text enthalten, auch wenn derselbe Text an
# anderer Stelle bewusst lesbar bleibt.
_ALT_KEYS = frozenset({"Alt", "ActualText", "E", "TU"})
_KEY_BEFORE = re.compile(r"/([A-Za-z]+)\s*$")


def _key_before(src: str, pos: int) -> str:
    m = _KEY_BEFORE.search(src, max(0, pos - 40), pos)
    return m.group(1) if m else ""


def _scrub_strings(doc: Any, keys: set[str], fully_selected: Callable[[str], bool]) -> int:
    """Zeichenketten in PDF-Objekten ersetzen, die einen geschwärzten Text
    enthalten: Alternativtext und ActualText im Strukturbaum und im
    Inhaltsstrom, Feldbeschriftungen, eigene Metadaten-Schlüssel und
    Ähnliches.

    Alternativtexte (``_ALT_KEYS``) werden immer ersetzt. Andere
    Zeichenketten nur, wenn ``fully_selected`` gilt, damit ein abgewählter
    Text an anderer Stelle (Lesezeichen, Feldwert) lesbar bleibt."""
    index = _KeyIndex(keys)
    if not index:
        return 0
    mark = fitz.get_pdf_str(REDACTED_MARK)

    def hit(text: str, alt: bool) -> bool:
        return any(alt or fully_selected(k) for k in index.found(_clean(text)))

    # Alternativtexte, die als eigenes Objekt abgelegt sind: /Alt 12 0 R
    alt_targets: set[int] = set()
    ref_rx = re.compile(r"/(?:" + "|".join(sorted(_ALT_KEYS)) + r")\s+(\d+)\s+0\s+R")
    for xref in range(1, doc.xref_length()):
        try:
            alt_targets.update(int(m.group(1)) for m in ref_rx.finditer(doc.xref_object(xref, compressed=True)))
        except Exception:
            continue

    replaced = 0
    for xref in range(1, doc.xref_length()):
        try:
            src = doc.xref_object(xref, compressed=False)
        except Exception:
            continue
        if "(" in src or "<" in src:
            parts: list[str] = []
            last = 0
            for s, e, text in _pdf_strings(src):
                if hit(text, xref in alt_targets or _key_before(src, s) in _ALT_KEYS):
                    parts.append(src[last:s] + mark)
                    last = e
                    replaced += 1
            if parts:
                doc.update_object(xref, "".join(parts) + src[last:])
        try:
            if not doc.xref_is_stream(xref) or doc.xref_get_key(xref, "Subtype")[1] == "/Image":
                continue
            raw = doc.xref_stream(xref) or b""
            is_xmp = doc.xref_get_key(xref, "Type")[1] == "/Metadata"
        except Exception:
            continue
        if is_xmp:
            # XMP-Paket (auch auf Seiten- oder Objektebene, die die Suche nicht
            # einzeln ausweist): enthält es einen geschwärzten Text, wird es geleert.
            if hit(raw.decode("utf-8", "replace"), True):
                doc.update_stream(xref, b"")
                replaced += 1
            continue
        if b"/ActualText" not in raw and b"/Alt" not in raw and b"/E" not in raw:
            continue
        stream = raw.decode("latin-1")
        out: list[str] = []
        last = 0
        for m in _STREAM_TEXT_KEYS.finditer(stream):
            if m.start() < last:
                continue
            for _s, e, text in _pdf_strings(stream, m.end(), only_at=m.end()):
                if hit(text, True):
                    # Eintrag entfernen: Die Textextraktion fällt dann auf die
                    # (geschwärzten) Glyphen zurück.
                    out.append(stream[last : m.start()])
                    last = e
                    replaced += 1
        if out:
            doc.update_stream(xref, ("".join(out) + stream[last:]).encode("latin-1"))
    return replaced


_EXTRA_SANITIZE_KEYS = ("PieceInfo", "Metadata")


def _sanitize(doc: Any) -> list[str]:
    done: list[str] = []
    info = _cleanup_info(doc)
    if info["metadata_fields"]:
        done.append("Metadaten")
    if info["xmp"]:
        done.append("XMP-Metadaten")
    if info["attachments"]:
        done.append("Dateianhänge")
    if info["javascript"]:
        done.append("JavaScript")
    doc.scrub(
        attached_files=True,
        clean_pages=False,
        embedded_files=True,
        hidden_text=False,  # unsichtbare OCR-Textebenen bleiben erhalten
        javascript=True,
        metadata=True,
        redactions=False,
        remove_links=False,
        reset_fields=False,
        reset_responses=True,
        thumbnails=True,
        xml_metadata=True,
    )
    doc.set_metadata({})
    doc.del_xml_metadata()
    info_xref = _info_xref(doc)
    if info_xref:
        for key in doc.xref_get_keys(info_xref):
            doc.xref_set_key(info_xref, key, "null")
    # Private Anwendungsdaten, XMP an Seiten und Bildern, XFA-Formulardaten.
    cat = doc.pdf_catalog()
    extra = False
    for xref in range(1, doc.xref_length()):
        try:
            names = doc.xref_get_keys(xref)
        except Exception:
            continue
        for key in _EXTRA_SANITIZE_KEYS:
            if key in names and not (key == "Metadata" and xref == cat):
                doc.xref_set_key(xref, key, "null")
                extra = True
    if extra:
        done.append("Anwendungsdaten")
    return done


# ── Prüfgruppen für die Nachprüfung ──────────────────────────

HIDDEN_GROUP = "versteckte Inhalte"


def _page_group(page: int | None) -> str:
    return f"Seite {page}" if page else HIDDEN_GROUP


def _flat(text: str) -> str:
    """Vergleichsform: NFKC, ohne Groß-/Kleinschreibung, ohne Leerraum."""
    return "".join(unicodedata.normalize("NFKC", text).casefold().split())


def _positions(hay: str, key: str) -> list[int]:
    if not key:
        return []
    found: list[int] = []
    i = hay.find(key)
    while i >= 0:
        found.append(i)
        i = hay.find(key, i + 1)
    return found


def _occurrences(hay: str, key: str) -> int:
    return len(_positions(hay, key))


def _flat_map(text: str) -> tuple[str, list[int]]:
    """Vergleichsform wie ``_flat`` und zu jedem Zeichen die Stelle im Seitentext."""
    out: list[str] = []
    origin: list[int] = []
    for i, ch in enumerate(text):
        if ch == _HARD:
            continue
        f = _flat(ch)
        out.append(f)
        origin.extend([i] * len(f))
    return "".join(out), origin


def _same_text(span: str, text: str) -> bool:
    """Passt der Ausschnitt des Seitentexts zur Fundstelle? Trennstriche am
    Zeilenende fallen bei Begriffen weg und zählen deshalb nicht."""
    a, b = _flat(span.replace(_HARD, "")), _flat(text)
    if a == b:
        return True
    strip = str.maketrans("", "", _HYPHENS)
    return a.translate(strip) == b.translate(strip)


def _text_groups(doc: Any) -> tuple[dict[str, str], list[_PageText]]:
    """Text je Prüfgruppe in Vergleichsform: eine Gruppe je Seite, eine für
    alle versteckten Ablagen. Ebenen und Bereiche außerhalb der CropBox
    zählen mit. Das Dokument wird dabei verändert und darf nicht gespeichert werden."""
    _reveal_layers(doc)
    groups: dict[str, str] = {}
    pts: list[_PageText] = []
    for page in doc:
        _expose_full_page(page)
        pt = _page_text(page)
        pts.append(pt)
        groups[_page_group(page.number + 1)] = _flat_map(pt.text)[0]
    groups[HIDDEN_GROUP] = "\x01".join(_flat(_clean(text)) for _l, text, _p, _r in _iter_hidden_strings(doc))
    return groups, pts


def _area_indices(pt: _PageText, region: Any) -> list[int]:
    """Stellen im Seitentext, deren Zeichenmitte im Bereich liegt."""
    x0, y0, x1, y1 = region.x0, region.y0, region.x1, region.y1
    return [
        i
        for i, r in enumerate(pt.rects)
        if r is not None and x0 <= (r[0] + r[2]) / 2 <= x1 and y0 <= (r[1] + r[3]) / 2 <= y1
    ]


def _inside_other(c: Candidate, others: list[Candidate]) -> bool:
    """Liegt eine versteckte Fundstelle ganz in einer längeren ausgewählten
    Fundstelle derselben Ablage? Dann zählt sie dort schon mit."""
    for o in others:
        if o is c or o.location != c.location or o.ref != c.ref or o.page != c.page:
            continue
        if o.start <= c.start and c.end <= o.end and (o.end - o.start) > (c.end - c.start):
            if _flat(c.text) in _flat(o.text):
                return True
    return False


def _area_snippets(pt: _PageText, region: Any) -> list[str]:
    """Text unter einem eigenen Bereich, je Zeile getrennt."""
    x0, y0, x1, y1 = region.x0, region.y0, region.x1, region.y1
    by_line: dict[int, list[str]] = {}
    for i, r in enumerate(pt.rects):
        if r is None:
            continue
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        if x0 <= cx <= x1 and y0 <= cy <= y1:
            by_line.setdefault(pt.lines[i], []).append(pt.text[i])
    return [s for s in ("".join(v) for v in by_line.values()) if len(_flat(s)) >= 3]


def _limits(
    groups: dict[str, str],
    selected: dict[str, list[str]],
    covered: dict[str, tuple[list[int], set[int]] | None] | None = None,
) -> dict[tuple[str, str], int]:
    """Höchstens zulässige Vorkommen je (Gruppe, Text) nach dem Schwärzen.

    Zulässig ist, was vorher in der Gruppe stand, abzüglich der Vorkommen in
    ausgewählten Stellen. So zählen Schreibvarianten („Krüger“, „KRÜGER“)
    und verschachtelte Begriffe („Max Mustermann“ und „Mustermann“) richtig,
    und abgewählte gleiche Texte bleiben erlaubt.

    Für Seiten liegt in ``covered`` die Lage: die Herkunft jedes Zeichens der
    Vergleichsform und die Menge der ausgewählten Stellen im Seitentext. Ein
    Vorkommen wird dann nur abgezogen, wenn es ganz in ausgewählten Stellen
    liegt, und nur einmal, auch wenn sich ausgewählte Fundstellen überlappen
    (Begriff in einer E-Mail-Adresse, Fundstelle unter einem eigenen Bereich).
    Ohne Lage (versteckte Ablagen, unsichere Lage) wird über die Texte gezählt.
    """
    covered = covered or {}
    limits: dict[tuple[str, str], int] = {}
    for group, keys in selected.items():
        hay = groups.get(group, "")
        where = covered.get(group)
        if where is not None:
            origin, mask = where
            for k in set(keys):
                spots = _positions(hay, k)
                inside = sum(
                    1 for i in spots if all(origin[j] in mask for j in range(i, min(i + len(k), len(origin))))
                )
                limits[(group, k)] = len(spots) - inside
            continue
        counts: dict[str, int] = {}
        for k in keys:
            counts[k] = counts.get(k, 0) + 1
        for k in counts:
            inside = sum(n * _occurrences(t, k) for t, n in counts.items() if k in t)
            limits[(group, k)] = max(0, _occurrences(hay, k) - inside)
    return limits


# ── Anwendung ────────────────────────────────────────────────


def apply_plan(data: bytes, selection: Selection, ner: NerFn | None = None) -> tuple[bytes, ApplyReport]:
    """Genau die bestätigte Auswahl schwärzen und das Ergebnis nachprüfen."""
    digest = hashlib.sha256(data).hexdigest()
    if selection.sha256 != digest:
        raise RedactionStaleError("Der Plan gehört zu einer anderen Datei. Bitte Fundstellen neu suchen.")
    plan = build_plan(data, selection.criteria, ner)
    by_id = {c.id: c for c in plan.candidates}
    unknown = selection.selected - by_id.keys()
    if unknown:
        raise RedactionStaleError(
            f"{len(unknown)} ausgewählte Fundstelle(n) passen nicht mehr zur Datei. Bitte neu suchen."
        )
    chosen = [by_id[i] for i in sorted(selection.selected)]
    if not chosen and not selection.areas and not selection.sanitize:
        raise RedactionError("Keine Fundstelle und kein Bereich ausgewählt")
    page_count = len(plan.pages)
    for area in selection.areas:
        if not 1 <= area.page <= page_count:
            raise RedactionError(f"Bereich auf Seite {area.page}: Seite gibt es nicht")
    deselected = [c for c in plan.candidates if c.id not in selection.selected]

    # Erwartung für die Nachprüfung, je Seite und für versteckte Ablagen.
    selected_keys: dict[str, list[str]] = {}
    originals: dict[tuple[str, str], set[str]] = {}

    def note(group: str, text: str) -> None:
        key = _flat(text)
        if key:
            selected_keys.setdefault(group, []).append(key)
            originals.setdefault((group, key), set()).add(text)

    doc = open_pdf(data)
    try:
        transforms = [_ViewTransform(page) for page in doc]  # vor dem Aufdecken der CropBox
        before, pts = _text_groups(doc)
        # Lage der ausgewählten Stellen je Seite. None heißt: Lage unsicher,
        # für diese Seite wird über die Texte gezählt (strenger, nie lockerer).
        masks: dict[int, set[int] | None] = {}

        def cover(pno: int, indices: Any, ok: bool = True) -> None:
            mask = masks.get(pno, set())
            if mask is None or not ok:
                masks[pno] = None
                return
            mask.update(indices)
            masks[pno] = mask

        chosen_hidden = [c for c in chosen if c.kind != "text"]
        for c in chosen:
            if c.kind == "text":
                note(_page_group(c.page), c.text)
                pno = (c.page or 1) - 1
                ok = 0 <= pno < len(pts) and _same_text(pts[pno].text[c.start : c.end], c.text)
                cover(pno, range(c.start, c.end), ok)
                if ok:
                    # Mehrzeilige Fundstelle: jede Zeile einzeln prüfen, damit
                    # ein Teilausfall („Max“ weg, „Mustermann“ stehen) auffällt.
                    by_line: dict[int, list[str]] = {}
                    for i in range(c.start, c.end):
                        if pts[pno].lines[i] >= 0:
                            by_line.setdefault(pts[pno].lines[i], []).append(pts[pno].text[i])
                    if len(by_line) > 1:
                        for chars in by_line.values():
                            part = "".join(chars)
                            if len(_flat(part)) >= 3:
                                note(_page_group(c.page), part)
            elif not _inside_other(c, chosen_hidden):
                note(HIDDEN_GROUP, c.text)
        for area in selection.areas:
            pno = area.page - 1
            region = transforms[pno].from_view(list(area.box))
            for snippet in _area_snippets(pts[pno], region):
                note(_page_group(area.page), snippet)
            cover(pno, _area_indices(pts[pno], region))
        covered: dict[str, tuple[list[int], set[int]] | None] = {
            _page_group(pno + 1): None if mask is None else (_flat_map(pts[pno].text)[1], mask)
            for pno, mask in masks.items()
        }
    finally:
        doc.close()
    limits = _limits(before, selected_keys, covered)
    all_keys = {k for keys in selected_keys.values() for k in keys}
    cache: dict[str, bool] = {}

    def fully_selected(key: str) -> bool:
        """Kommt der Text nur innerhalb ausgewählter Stellen vor? Je Gruppe
        nach denselben (lagerichtigen) Grenzen wie die Nachprüfung, damit
        überlappende Auswahl nicht doppelt zählt."""
        if key not in cache:
            cache[key] = all(
                limits[(g, key)] == 0 if (g, key) in limits else _occurrences(hay, key) == 0
                for g, hay in before.items()
            )
        return cache[key]

    doc = open_pdf(data)
    try:
        layers = _reveal_layers(doc)
        # Versteckte Inhalte zuerst — danach ändern sich Kennungen der Seitenobjekte.
        hidden = [c for c in chosen if c.kind == "hidden"]
        by_ref: dict[str, list[Candidate]] = {}
        for cand in hidden:
            by_ref.setdefault(repr(sorted(cand.ref.items())), []).append(cand)
        for cands in by_ref.values():
            _remove_hidden(doc, cands)

        boxes: dict[int, list[Any]] = {}
        for cand in chosen:
            if cand.kind == "text" and cand.page:
                boxes.setdefault(cand.page - 1, []).extend(fitz.Rect(r) for r in cand.rects)
        area_boxes: dict[int, list[Any]] = {}
        for area in selection.areas:
            area_boxes.setdefault(area.page - 1, []).append(transforms[area.page - 1].from_view(list(area.box)))

        removed_annots = 0
        for pno in sorted(set(boxes) | set(area_boxes)):
            page = doc[pno]
            # Den gespeicherten Wert sichern: Eine CropBox, die über die MediaBox
            # hinausragt, ist zulässig, lässt sich mit set_cropbox aber nicht
            # zurückschreiben.
            saved_crop = [(page.xref, "CropBox", *doc.xref_get_key(page.xref, "CropBox"))]
            original_crop = _expose_full_page(page)
            rects = boxes.get(pno, []) + area_boxes.get(pno, [])
            # Formularfelder und Kommentare bringen eigene Darstellungen mit,
            # die apply_redactions nicht ändert. Liegen sie unter einer
            # Schwärzung, werden sie entfernt.
            for widget in list(page.widgets() or []):
                if any(widget.rect.intersects(r) for r in rects):
                    page.delete_widget(widget)
                    removed_annots += 1
            for annot in list(page.annots() or []):
                if any(annot.rect.intersects(r) for r in rects):
                    page.delete_annot(annot)
                    removed_annots += 1
            for rect in rects:
                page.add_redact_annot(rect, fill=(0, 0, 0))
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS)
            if original_crop is not None:
                _restore_layers(doc, saved_crop)

        replaced = _scrub_strings(doc, all_keys, fully_selected)
        # XFA-Formulardaten sind eine zweite, unabhängige Kopie der Feldinhalte.
        # Wie Acrobat beim Schwärzen: immer entfernen, es bleibt das AcroForm.
        cat = doc.pdf_catalog()
        if doc.xref_get_key(cat, "AcroForm/XFA")[0] != "null":
            doc.xref_set_key(cat, "AcroForm/XFA", "null")
            replaced += 1
        sanitized = _sanitize(doc) if selection.sanitize else []
        _restore_layers(doc, layers)
        out = doc.tobytes(garbage=4, deflate=True)
    finally:
        doc.close()

    _verify(out, selection, limits, originals)

    by_source: dict[str, int] = {}
    for c in chosen:
        by_source[c.source] = by_source.get(c.source, 0) + 1
    text_count = sum(1 for c in chosen if c.kind == "text")
    return out, ApplyReport(
        redactions=text_count,
        areas=len(selection.areas),
        hidden_removed=len(hidden) + replaced + removed_annots,
        by_source=by_source,
        pages=sorted({c.page for c in chosen if c.page} | {a.page for a in selection.areas}),
        sanitized=sanitized,
        deselected=len(deselected),
    )


# ── Nachprüfung ──────────────────────────────────────────────

_ESCAPED = [re.escape(bytes([b])) for b in range(256)]
_NO_START = frozenset(b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/")
_NO_END = frozenset(b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")


def _trie_pattern(forms: Iterable[bytes]) -> bytes:
    """Alternative vieler Bytefolgen als Präfixbaum. Eine flache Liste
    „a|b|c…“ mit Tausenden Einträgen kompiliert und sucht in Python sehr
    langsam; der Baum teilt gemeinsame Anfänge."""
    trie: dict = {}
    for form in forms:
        node = trie
        for byte in form:
            node = node.setdefault(byte, {})
        node[None] = True

    def build(node: dict) -> bytes:
        branches = [_ESCAPED[b] + build(child) for b, child in sorted((k, v) for k, v in node.items() if k is not None)]
        if not branches:
            return b""
        body = branches[0] if len(branches) == 1 else b"(?:" + b"|".join(branches) + b")"
        return b"(?:" + body + b")?" if None in node else body

    return build(trie)


class _RawScanner:
    """Sucht viele Bytefolgen (ohne Groß-/Kleinschreibung für ASCII).

    Ein kleiner Ausdruck aus den Anfängen der Formen findet in C-Geschwindigkeit
    die möglichen Fundorte; erst dort wird jede Form mit diesem Anfang
    verglichen. Die Formen werden nach Länge gruppiert (Anfang bis 16 Byte),
    damit eine kurze Form wie „Anna“ nicht alle langen Formen in wenige
    Gruppen zwingt. Mit ``bounded`` zählt ein Treffer nur mit Wortgrenze und
    nicht als PDF-Name („/Name“)."""

    def __init__(self, table: dict[bytes, str], bounded: bool):
        self.table, self.bounded = table, bounded
        groups: dict[int, dict[bytes, list[bytes]]] = {}
        for form in sorted(table, key=len, reverse=True):
            k = min(16, len(form))
            groups.setdefault(k, {}).setdefault(form[:k], []).append(form)
        self.parts = [
            (re.compile(b"(?=(" + _trie_pattern(by_prefix) + b"))"), by_prefix)
            for _k, by_prefix in sorted(groups.items())
        ]

    def scan(self, low: bytes, hits: set[str]) -> None:
        """``low``: bereits mit ``bytes.lower()`` umgewandelt."""
        size = len(low)
        for rx, by_prefix in self.parts:
            for m in rx.finditer(low):
                i = m.start()
                if self.bounded and i > 0 and low[i - 1] in _NO_START:
                    continue
                for form in by_prefix[m.group(1)]:
                    end = i + len(form)
                    if not low.startswith(form, i):
                        continue
                    if self.bounded and end < size and low[end] in _NO_END:
                        continue
                    hits.add(self.table[form])


def _byte_forms(text: str) -> tuple[set[bytes], set[bytes]]:
    """Mögliche Ablageformen eines Texts in PDF-Objekten: (Klartext, Hex).

    Bytevergleiche ignorieren Groß- und Kleinschreibung nur für ASCII, deshalb
    werden die üblichen Schreibweisen („Krüger“, „KRÜGER“) einzeln erzeugt.
    """
    plain: set[bytes] = set()
    utf16: set[bytes] = set()
    for variant in {text, text.upper(), text.lower(), text.capitalize(), text.title()}:
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                plain.add(variant.encode(enc))
            except UnicodeEncodeError:
                pass
        utf16.add(variant.encode("utf-16-be"))
    escaped = set()
    for form in plain:
        if any(b > 127 for b in form):
            escaped.add(b"".join(b"\\%03o" % b if b > 127 else bytes([b]) for b in form))
    hexes = {f.hex().encode() for f in plain | utf16}
    return plain | escaped | utf16, hexes


def _font_file_xrefs(doc: Any) -> set[int]:
    """Eingebettete Schriftdateien. Ihre Namenstabellen (Schriftname,
    Gestalter, Copyright) sind kein Dokumentinhalt und lösten sonst
    Fehlalarme aus, etwa „Vera“ in „Bitstream Vera“."""
    found: set[int] = set()
    for xref in range(1, doc.xref_length()):
        try:
            if doc.xref_get_key(xref, "Type")[1] != "/FontDescriptor":
                continue
            for key in ("FontFile", "FontFile2", "FontFile3"):
                kind, value = doc.xref_get_key(xref, key)
                if kind == "xref":
                    found.add(int(value.split()[0]))
        except Exception:
            continue
    return found


def _raw_contains(doc: Any, needles: list[str]) -> tuple[set[str], set[str]]:
    """Texte, die nach dem Entpacken aller Objekte noch in der Datei stehen.

    Rückgabe: (Treffer außerhalb von Inhaltsströmen, Treffer in Inhaltsströmen
    von Seiten und Form-XObjects). Im Inhaltsstrom steht Text oft in Stücken
    („(Krause) Tj (straße) Tj“); ein Stück ist dort kein eigenes Wort.

    Klartext zählt nur mit Wortgrenze und nicht als PDF-Name („/Name“), damit
    zufällige Wortbestandteile und Schlüsselnamen keinen Fehlalarm auslösen.
    Bilddaten und Schriftdateien werden übersprungen.
    """
    plain: dict[bytes, str] = {}
    hexes: dict[bytes, str] = {}
    for n in needles:
        p, h = _byte_forms(n)
        for form in p:
            plain.setdefault(form.lower(), n)
        for form in h:
            hexes.setdefault(form.lower(), n)
    scanners = [_RawScanner(plain, True), _RawScanner(hexes, False)]
    strict: set[str] = set()
    in_content: set[str] = set()
    fonts = _font_file_xrefs(doc)
    content = {x for page in doc for x in page.get_contents()}
    for xref in range(1, doc.xref_length()):
        try:
            if xref in fonts or doc.xref_get_key(xref, "Subtype")[1] == "/Image":
                continue
            head = doc.xref_object(xref, compressed=False).encode("latin-1", errors="ignore")
            body = (doc.xref_stream(xref) or b"") if doc.xref_is_stream(xref) else b""
            is_content = xref in content or doc.xref_get_key(xref, "Subtype")[1] == "/Form"
        except Exception:
            continue
        if is_content:
            blobs = ((head, strict), (body, in_content))
        else:
            blobs = ((head + b"\n" + body, strict),)
        for blob, hits in blobs:
            if blob:
                low = blob.lower()
                for scanner in scanners:
                    scanner.scan(low, hits)
        if len(strict) == len(needles):
            break
    return strict, in_content - strict


def _visible_text(doc: Any, pts: list[_PageText]) -> str:
    """Lesbarer Text der Ausgabe (Seiten und versteckte Ablagen), ohne
    Groß-/Kleinschreibung, mit Wortgrenzen."""
    parts = [pt.text.replace(_HARD, "\n") for pt in pts]
    parts += [_clean(text) for _l, text, _p, _r in _iter_hidden_strings(doc)]
    return unicodedata.normalize("NFKC", "\x01".join(parts)).casefold()


def _word_in(visible: str, text: str) -> bool:
    flat = _flat(text)
    if not flat:
        return False
    body = r"\s*".join(re.escape(ch) for ch in flat)
    return re.search(r"(?<!\w)" + body + r"(?!\w)", visible) is not None


def _verify(
    out: bytes,
    selection: Selection,
    limits: dict[tuple[str, str], int],
    originals: dict[tuple[str, str], set[str]],
) -> None:
    """Fail-closed: Je Gruppe darf jeder ausgewählte Text höchstens so oft
    vorkommen wie in ``limits``. Was vollständig geschwärzt sein soll, darf
    auch in den Rohdaten nicht mehr stehen."""
    problems: list[str] = []
    doc = fitz.open(stream=out, filetype="pdf")
    try:
        after, pts = _text_groups(doc)
        for (group, key), limit in limits.items():
            found = _occurrences(after.get(group, ""), key)
            if found > limit:
                sample = min(originals[(group, key)])
                problems.append(f"„{sample[:3]}…“ noch {found - limit}× lesbar ({group})")
        needles = sorted({
            text
            for (group, key), limit in limits.items()
            if limit == 0 and len(key) >= 4
            for text in originals[(group, key)]
        })
        if needles:
            visible = _visible_text(doc, pts)
            flat_visible = "\x01".join(_flat(part) for part in visible.split("\x01"))
            strict, in_content = _raw_contains(doc, needles)
            for hit in sorted(strict | in_content):
                # Bleibt derselbe Text an anderer Stelle bewusst lesbar
                # (abgewählt), steht er zu Recht noch in der Datei. Außerhalb
                # der Inhaltsströme wird wortgenau verglichen: „Krausestr.“
                # entschuldigt einen Alternativtext „Krause“ nicht. Im
                # Inhaltsstrom genügt der Text als Teil des Sichtbaren, denn
                # dort sind Wörter oft in Stücke zerlegt.
                ok = _word_in(visible, hit) if hit in strict else _flat(hit) in flat_visible
                if not ok:
                    problems.append(f"„{hit[:3]}…“ noch in den Rohdaten der Datei")
        if selection.sanitize:
            info = _cleanup_info(doc)
            if info["metadata_fields"] or info["xmp"] or info["attachments"]:
                problems.append("Metadaten oder Anhänge nicht entfernt")
    finally:
        doc.close()
    if problems:
        raise RedactionVerificationError(list(dict.fromkeys(problems)))


# ── Vereinfachte Aufrufe ─────────────────────────────────────


def redact_all(
    data: bytes,
    criteria: Criteria,
    ner: NerFn | None = None,
    sanitize: bool = True,
) -> tuple[bytes, ApplyReport, Plan]:
    """Alle Fundstellen schwärzen (Programmschnittstelle ohne Vorschau)."""
    plan = build_plan(data, criteria, ner)
    selection = Selection(plan.sha256, criteria, frozenset(c.id for c in plan.candidates), (), sanitize)
    if not plan.candidates and not sanitize:
        return data, ApplyReport(0, 0, 0, {}, [], [], 0), plan
    out, report = apply_plan(data, selection, ner)
    return out, report, plan


def spacy_ner(nlp: Any) -> NerFn:
    """Adapter: spaCy-Pipeline → Zeichenspannen der Personennamen je Text."""

    def run(texts: list[str]) -> list[list[tuple[int, int]]]:
        result: list[list[tuple[int, int]]] = []
        for doc in nlp.pipe(texts):
            result.append([(e.start_char, e.end_char) for e in doc.ents if e.label_ == "PER"])
        return result

    return run
