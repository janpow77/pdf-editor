/**
 * Übergabe eines Ergebnisses von einem Werkzeug ans nächste ohne erneuten
 * Upload: Der Absender (z. B. die Werkbank) legt die Datei hier ab, FileDrop
 * holt sie beim Einhängen genau einmal ab und validiert sie wie eine normale
 * Auswahl. Bewusst nur im Arbeitsspeicher gehalten — die Datei berührt weder
 * Web Storage noch den Server.
 */
let pending: File | null = null

export function setPendingHandoff(file: File): void {
  pending = file
}

export function takePendingHandoff(): File | null {
  const file = pending
  pending = null
  return file
}
