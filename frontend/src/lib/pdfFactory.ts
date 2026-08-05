/**
 * Erzeugt ein minimales, standardskonformes PDF mit einer leeren DIN-A4-Seite.
 *
 * Für diesen Anwendungsfall wäre eine zusätzliche PDF-Bibliothek unnötig groß.
 * Die vier benötigten PDF-Objekte werden deshalb direkt aufgebaut. Wichtig ist,
 * dass PDF-Querverweise Byte-Offsets und keine JavaScript-Zeichenpositionen
 * enthalten. `TextEncoder` macht die Berechnung deshalb auch dann korrekt, wenn
 * später Kommentare oder Inhalte mit Umlauten beziehungsweise Unicode ergänzt
 * werden. Das Dokument verbleibt vollständig im Arbeitsspeicher des Browsers.
 */
export function createBlankA4Pdf(orientation: 'hoch' | 'quer' = 'hoch'): Blob {
  const encoder = new TextEncoder()
  const header = '%PDF-1.4\n% Blank A4 form generated locally\n'

  // Der Inhaltsstrom ist absichtlich leer. `stream\nendstream` enthält nach dem
  // vorgeschriebenen Zeilenende hinter `stream` exakt null Datenbytes. Dadurch
  // stimmt `/Length 0` bytegenau und ein strenger PDF-Parser muss nichts reparieren.
  const emptyStream = ''
  const emptyStreamLength = encoder.encode(emptyStream).byteLength

  // DIN A4 im PDF-Punktmaß: 210 × 297 mm entsprechen rund 595,28 × 841,89 pt.
  const [width, height] = orientation === 'hoch' ? ['595.28', '841.89'] : ['841.89', '595.28']

  const objects = [
    '1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n',
    '2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n',
    `3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${width} ${height}] /Resources << >> /Contents 4 0 R >>\nendobj\n`,
    `4 0 obj\n<< /Length ${emptyStreamLength} >>\nstream\n${emptyStream}endstream\nendobj\n`,
  ]

  let body = header
  const offsets = [0]
  for (const object of objects) {
    offsets.push(encoder.encode(body).byteLength)
    body += object
  }

  const xrefOffset = encoder.encode(body).byteLength
  const xrefRows = offsets
    .slice(1)
    .map((offset) => `${String(offset).padStart(10, '0')} 00000 n \n`)
    .join('')

  const pdf = `${body}xref\n0 ${objects.length + 1}\n0000000000 65535 f \n${xrefRows}`
    + `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\n`
    + `startxref\n${xrefOffset}\n%%EOF\n`

  return new Blob([encoder.encode(pdf)], { type: 'application/pdf' })
}
