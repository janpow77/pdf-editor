FROM python:3.12-slim

# Tesseract für OCR (7 Sprachen), LibreOffice für Office→PDF, Fonts für die Konvertierung
#
# Spiegel ftp.de.debian.org statt deb.debian.org: dessen einzige Fastly-IP ist
# aus manchen Netzen (mobiles Internet) zeitweise nicht erreichbar.
# Download-Schleife: Bei instabiler Verbindung bleiben bereits geladene Pakete
# im apt-Cache liegen; jeder Durchlauf holt nur noch die fehlenden nach.
# Erst wenn alles lokal liegt, wird installiert.
RUN sed -i 's|deb.debian.org|ftp.de.debian.org|g' /etc/apt/sources.list.d/debian.sources && \
    pkgs="curl \
        tesseract-ocr \
        tesseract-ocr-deu \
        tesseract-ocr-eng \
        tesseract-ocr-fra \
        tesseract-ocr-ita \
        tesseract-ocr-spa \
        tesseract-ocr-nld \
        tesseract-ocr-pol \
        libreoffice-writer \
        libreoffice-calc \
        libreoffice-impress \
        default-jre-headless \
        ghostscript \
        unpaper \
        fonts-dejavu \
        fonts-liberation" && \
    for i in $(seq 1 30); do apt-get update && break || sleep 20; done && \
    ok=""; for i in $(seq 1 30); do \
        if apt-get install -y -d --no-install-recommends -o Acquire::Retries=5 $pkgs; then ok=1; break; fi; \
        echo "Download-Versuch $i unvollständig — 20s warten, dann fehlende Pakete nachladen"; sleep 20; \
    done && test -n "$ok" && \
    apt-get install -y --no-install-recommends $pkgs && \
    rm -rf /var/lib/apt/lists/* && apt-get clean

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Non-root
RUN groupadd --gid 1000 pdfapp && useradd --uid 1000 --gid 1000 -m pdfapp
USER pdfapp

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -sf http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
