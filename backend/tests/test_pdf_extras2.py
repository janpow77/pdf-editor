"""Tests für digitale Signatur, Scan-Optimierung und Batch-Verarbeitung."""

import io
import json
import zipfile
from datetime import UTC, datetime, timedelta

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import pdf_extras_service as svc
from tests.test_smoke import make_pdf


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _make_p12(passphrase: bytes) -> bytes:
    """Selbstsigniertes Zertifikat als PKCS#12 für den Signatur-Test."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test Signer")])
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        b"test",
        key,
        cert,
        None,
        serialization.BestAvailableEncryption(passphrase),
    )


@pytest.mark.skipif(not svc.PYHANKO_AVAILABLE, reason="pyHanko nicht verfügbar")
def test_sign_digital_roundtrip(client):
    pdf = make_pdf(1, "Vertragstext")
    p12 = _make_p12(b"geheim")
    r = client.post(
        "/api/pdf-extras/sign-digital",
        data={"passphrase": "geheim", "reason": "Freigabe", "location": "Wiesbaden"},
        files={
            "file": ("v.pdf", pdf, "application/pdf"),
            "certificate": ("test.p12", p12, "application/octet-stream"),
        },
    )
    assert r.status_code == 200, r.text
    # Signaturfeld vorhanden?
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        sig_fields = [
            w
            for p in doc
            for w in (p.widgets() or [])
            if w.field_type_string == "Signature"
        ]
        assert len(sig_fields) == 1


@pytest.mark.skipif(not svc.PYHANKO_AVAILABLE, reason="pyHanko nicht verfügbar")
def test_sign_digital_wrong_passphrase_400(client):
    pdf = make_pdf(1, "x")
    p12 = _make_p12(b"richtig")
    r = client.post(
        "/api/pdf-extras/sign-digital",
        data={"passphrase": "falsch"},
        files={
            "file": ("v.pdf", pdf, "application/pdf"),
            "certificate": ("test.p12", p12, "application/octet-stream"),
        },
    )
    assert r.status_code == 400
    # Fehlermeldung darf keine Zertifikatsdetails enthalten
    assert "Test Signer" not in r.text


@pytest.mark.skipif(
    not svc.OCRMYPDF_AVAILABLE, reason="OCRmyPDF/Ghostscript nicht verfügbar"
)
def test_scan_optimize(client):
    pdf = make_pdf(1, "Scan-Inhalt")
    r = client.post(
        "/api/pdf-extras/scan-optimize",
        data={"language": "deu"},
        files={"file": ("s.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text


def test_scan_optimize_unavailable_503(client, monkeypatch):
    monkeypatch.setattr(svc, "OCRMYPDF_AVAILABLE", False)
    r = client.post(
        "/api/pdf-extras/scan-optimize",
        files={"file": ("s.pdf", make_pdf(1, "x"), "application/pdf")},
    )
    assert r.status_code == 503


def test_batch_compress_and_rotate(client):
    files = [
        ("files", ("a.pdf", make_pdf(2, "A"), "application/pdf")),
        ("files", ("b.pdf", make_pdf(1, "B"), "application/pdf")),
    ]
    r = client.post(
        "/api/pdf-extras/batch",
        data={"operation": "compress", "params": json.dumps({"quality": "medium"})},
        files=files,
    )
    assert r.status_code == 200, r.text
    assert r.headers["X-Batch-Ok"] == "2"
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = zf.namelist()
        assert "a_komprimiert.pdf" in names and "b_komprimiert.pdf" in names
        assert "fehler.txt" not in names

    r = client.post(
        "/api/pdf-extras/batch",
        data={"operation": "rotate", "params": json.dumps({"rotation": 90})},
        files=[("files", ("a.pdf", make_pdf(1, "A"), "application/pdf"))],
    )
    assert r.status_code == 200, r.text
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        rotated = zf.read("a_rotiert.pdf")
    with fitz.open(stream=rotated, filetype="pdf") as doc:
        assert doc[0].rotation == 90


def test_batch_bates_continuous_numbering(client):
    """Bates-Nummern laufen über Dateigrenzen hinweg weiter."""
    files = [
        ("files", ("a.pdf", make_pdf(2, "A"), "application/pdf")),
        ("files", ("b.pdf", make_pdf(1, "B"), "application/pdf")),
    ]
    r = client.post(
        "/api/pdf-extras/batch",
        data={
            "operation": "bates",
            "params": json.dumps({"prefix": "X-", "start": 1, "digits": 4}),
        },
        files=files,
    )
    assert r.status_code == 200, r.text
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        b_content = zf.read("b_bates.pdf")
    with fitz.open(stream=b_content, filetype="pdf") as doc:
        # Datei a hat 2 Seiten → b beginnt bei X-0003
        assert "X-0003" in doc[0].get_text()


def test_batch_partial_failure_lists_errors(client):
    files = [
        ("files", ("ok.pdf", make_pdf(1, "OK"), "application/pdf")),
        ("files", ("kaputt.pdf", b"%PDF-1.4 kaputt", "application/pdf")),
    ]
    r = client.post(
        "/api/pdf-extras/batch",
        data={"operation": "compress", "params": "{}"},
        files=files,
    )
    assert r.status_code == 200, r.text
    assert r.headers["X-Batch-Ok"] == "1"
    assert r.headers["X-Batch-Failed"] == "1"
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        assert "fehler.txt" in zf.namelist()


def test_batch_unknown_operation_422(client):
    r = client.post(
        "/api/pdf-extras/batch",
        data={"operation": "explodieren", "params": "{}"},
        files=[("files", ("a.pdf", make_pdf(1, "A"), "application/pdf"))],
    )
    assert r.status_code == 422


def test_batch_redact_patterns(client):
    """Automatisierte Schwärzung über mehrere Dateien: Fundstellen raus, Rest bleibt."""
    files = [
        ("files", ("a.pdf", make_pdf(1, "Kontakt Geheimwort a@example.com Ende"), "application/pdf")),
        ("files", ("b.pdf", make_pdf(1, "Ohne Treffer hier"), "application/pdf")),
    ]
    r = client.post(
        "/api/pdf-extras/batch",
        data={
            "operation": "redact",
            "params": json.dumps({"patterns": ["email"], "terms": "Geheimwort"}),
        },
        files=files,
    )
    assert r.status_code == 200, r.text
    assert r.headers["X-Batch-Ok"] == "2"
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = zf.namelist()
        assert "a_geschwaerzt.pdf" in names
        assert "b.pdf" in names  # keine Fundstelle → unverändert, kein Fehler
        assert "schwaerzungen.txt" in names
        manifest = zf.read("schwaerzungen.txt").decode()
        assert "a.pdf" in manifest and "b.pdf" in manifest
        with fitz.open(stream=zf.read("a_geschwaerzt.pdf"), filetype="pdf") as doc:
            text = doc[0].get_text()
            assert "Geheimwort" not in text
            assert "a@example.com" not in text


def test_batch_redact_unknown_pattern_400(client):
    r = client.post(
        "/api/pdf-extras/batch",
        data={"operation": "redact", "params": json.dumps({"patterns": ["nonsense"]})},
        files=[("files", ("a.pdf", make_pdf(1, "A"), "application/pdf"))],
    )
    assert r.status_code == 400


@pytest.mark.skipif(not svc.get_pdf_extras().ner_available(), reason="spaCy-Modell nicht installiert")
def test_redact_patterns_ner_preview(client):
    """KI-Namenserkennung findet Personennamen, die kein Regex-Muster abdeckt."""
    pdf = make_pdf(1, "Sehr geehrter Herr Max Mustermann, herzliche Gruesse")
    r = client.post(
        "/api/pdf-extras/redact-patterns",
        data={"patterns": json.dumps([svc.NER_PATTERN_ID]), "preview": "true"},
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 1
    assert any(f["pattern"] == svc.NER_PATTERN_ID for f in body["findings"])


def test_redact_patterns_lists_ai_flag(client):
    r = client.get("/api/pdf-extras/redact/patterns")
    assert r.status_code == 200, r.text
    body = r.json()
    by_id = {p["id"]: p for p in body["patterns"]}
    assert by_id[svc.NER_PATTERN_ID]["ai"] is True
    assert by_id["email"]["ai"] is False
    assert "ner_available" in body


def test_ink_annotation_regression(client):
    """Regressionstest: add_ink_annot braucht Float-Paare (PyMuPDF-Kompatibilität)."""
    pdf = make_pdf(1, "Zeichnung")
    anns = [
        {
            "type": "ink",
            "page": 1,
            "paths": [
                [{"x": 0.2, "y": 0.5}, {"x": 0.3, "y": 0.52}, {"x": 0.4, "y": 0.5}]
            ],
            "color": "#ff0000",
            "width": 2,
        }
    ]
    r = client.post(
        "/api/pdf-editor/annotations",
        data={"annotations": json.dumps(anns)},
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert len(list(doc[0].annots() or [])) == 1


def _preview(client, text: str, patterns: list[str]) -> dict:
    r = client.post(
        "/api/pdf-extras/redact-patterns",
        data={"patterns": json.dumps(patterns), "preview": "true"},
        files={"file": ("d.pdf", make_pdf(1, text), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_redact_patterns_overlapping_matches_resolved(client):
    """Eine IBAN ist genau eine Fundstelle — nicht zusätzlich Telefon und Kreditkarte.

    Vor der Überlappungsauflösung meldete die Vorschau dieselbe Ziffernfolge
    dreifach: als IBAN, als Telefonnummer („0000 0000 2020 51") und als
    Kreditkartennummer („1203 0000 0000 2020").
    """
    body = _preview(
        client,
        "IBAN DE02 1203 0000 0000 2020 51",
        ["iban", "telefon", "kreditkarte"],
    )
    assert body["total"] == 1
    treffer = body["findings"][0]
    assert treffer["pattern"] == "iban"
    assert treffer["text"].startswith("DE02")


def test_redact_patterns_telefon_nicht_in_belegnummer(client):
    """Rechnungs- und Aktenzeichen sind keine Rufnummern."""
    body = _preview(client, "Rechnung 2026-001 Aktenzeichen HMdF-2026-0815", ["telefon"])
    assert body["total"] == 0


def test_redact_patterns_telefon_weiterhin_gefunden(client):
    """Gegenprobe zur Umschließung: echte Rufnummern bleiben Treffer."""
    body = _preview(client, "Telefon 069 12345678 und +49 611 9876543", ["telefon"])
    texte = [f["text"].strip() for f in body["findings"]]
    assert body["total"] == 2
    assert any(t.startswith("069") for t in texte)
    assert any(t.startswith("+49") for t in texte)


def test_redact_patterns_getrennte_treffer_bleiben_erhalten(client):
    """Die Auflösung greift nur bei Überlappung, nicht bei Nachbarschaft."""
    body = _preview(
        client,
        "Mail a@example.com IBAN DE02 1203 0000 0000 2020 51",
        ["iban", "email"],
    )
    assert body["total"] == 2
    assert {f["pattern"] for f in body["findings"]} == {"iban", "email"}
