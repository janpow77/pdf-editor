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

export function useWorkspace() {
  function openWorkspace(info: WorkspaceInfo): void {
    activeWorkspace.value = info
  }

  function closeWorkspace(): void {
    activeWorkspace.value = null
  }

  return {
    activeWorkspace: readonly(activeWorkspace),
    isWorkspaceActive: computed(() => activeWorkspace.value !== null),
    openWorkspace,
    closeWorkspace,
  }
}
