FROM python:3.12-slim

# Tesseract für OCR (7 Sprachen), LibreOffice für Office→PDF, Fonts für die Konvertierung
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
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
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

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
