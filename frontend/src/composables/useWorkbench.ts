/**
 * Zustand des Werkbank-Arbeitsplatzes auf Modulebene.
 *
 * Die Werkbank wird beim Wechsel zu einem anderen Werkzeug ausgehängt — ihr
 * Zustand (geladene Dokumente, Seitenfolge, Fokus) liegt deshalb hier statt in
 * der Komponente und übersteht so den Roundtrip „Übergeben → bearbeiten →
 * zurück zur Werkbank". Bewusst nur im Arbeitsspeicher: ein Neuladen der Seite
 * beginnt leer, genau wie beim Nutzungsversprechen „keine Datenspeicherung".
 */
import { ref } from 'vue'

export interface WorkbenchDoc {
  uid: number
  file: File
  label: string
  pages: number
  thumbs: Record<string, string>
}

/** Ein Eintrag der Zielreihenfolge; `docUid === null` steht für eine Leerseite. */
export interface WorkbenchItem {
  uid: number
  docUid: number | null
  page: number
  rotation: number
  removed: boolean
  selected: boolean
}

export const docs = ref<WorkbenchDoc[]>([])
export const items = ref<WorkbenchItem[]>([])
export const focusedUid = ref<number | null>(null)
export const viewerPage = ref(1)
export const targetToolId = ref('')

/** Höchste beim Verlassen bekannte Ergebnis-ID — alles darüber ist „neu". */
export const lastSeenResultId = ref(0)

let uidCounter = 0
export function nextUid(): number {
  return ++uidCounter
}

export function resetWorkbench(): void {
  docs.value = []
  items.value = []
  focusedUid.value = null
  viewerPage.value = 1
}
