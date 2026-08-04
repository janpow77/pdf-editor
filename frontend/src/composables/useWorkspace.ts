/**
 * Kleiner globaler UI-Zustand für den aktuell geöffneten Arbeitsbereich.
 *
 * Der eigentliche Werkzeugzustand bleibt weiterhin in der Werkzeugkomponente.
 * Global gespeichert werden ausschließlich Bezeichnung und Kategorie, damit
 * Header, Startseiten-Hero und Footer ihre Darstellung konsistent anpassen
 * können, ohne Komponenten über mehrere Ebenen mit Events zu koppeln.
 */
import { computed, readonly, ref } from 'vue'

export interface WorkspaceInfo {
  toolId: string
  toolName: string
  groupName: string
}

const activeWorkspace = ref<WorkspaceInfo | null>(null)
const workspaceRevision = ref(0)

export function useWorkspace() {
  function openWorkspace(info: WorkspaceInfo): void {
    activeWorkspace.value = info
  }

  /**
   * Der Revisionszähler erzwingt beim globalen Schließen eine neue Instanz der
   * Werkzeugübersicht. Das ist insbesondere beim Klick auf das Logo wichtig:
   * Nicht nur der kompakte Header, sondern auch die lokal geladene Fachkomponente
   * und deren Datei-/Canvas-Zustände werden dadurch zuverlässig verworfen.
   */
  function closeWorkspace(): void {
    if (activeWorkspace.value === null) return
    activeWorkspace.value = null
    workspaceRevision.value += 1
  }

  return {
    activeWorkspace: readonly(activeWorkspace),
    isWorkspaceActive: computed(() => activeWorkspace.value !== null),
    workspaceRevision: readonly(workspaceRevision),
    openWorkspace,
    closeWorkspace,
  }
}
