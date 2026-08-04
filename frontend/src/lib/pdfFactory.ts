/**
 * Erzeugt ein minimales, standardskonformes PDF mit einer leeren DIN-A4-Seite.
 *
 * Für diesen Anwendungsfall wäre eine zusätzliche PDF-Bibliothek unnötig groß.
 * Die vier benötigten PDF-Objekte werden deshalb direkt als ASCII aufgebaut.
 * Die Byte-Offsets der Querverweistabelle werden programmatisch berechnet,
 * damit das Dokument von pdf.js, PyMuPDF und üblichen PDF-Readern akzeptiert
 * wird. Das Dokument verbleibt vollständig im Arbeitsspeicher des Browsers.
 */
export function createBlankA4Pdf(): Blob {
  const header = '%PDF-1.4\n% Blank A4 form generated locally\n'
  const objects = [
    '1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n',
    '2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n',
    // DIN A4 im PDF-Punktmaß: 210 × 297 mm entsprechen rund 595,28 × 841,89 pt.
    '3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.89] /Resources << >> /Contents 4 0 R >>\nendobj\n',
    '4 0 obj\n<< /Length 0 >>\nstream\n\nendstream\nendobj\n',
  ]

  let body = header
  const offsets = [0]
  for (const object of objects) {
    offsets.push(body.length)
    body += object
  }

  const xrefOffset = body.length
  const xrefRows = offsets
    .slice(1)
    .map((offset) => `${String(offset).padStart(10, '0')} 00000 n \n`)
    .join('')

  const pdf = `${body}xref\n0 ${objects.length + 1}\n0000000000 65535 f \n${xrefRows}`
    + `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\n`
    + `startxref\n${xrefOffset}\n%%EOF\n`

  return new Blob([pdf], { type: 'application/pdf' })
}
