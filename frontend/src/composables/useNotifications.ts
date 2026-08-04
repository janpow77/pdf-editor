/**
 * Globales Benachrichtigungssystem für Erfolg, Hinweise, Warnungen und Fehler.
 *
 * Der Zustand liegt außerhalb einzelner Komponenten und ist deshalb in allen
 * Werkzeugen identisch verfügbar. Meldungen werden automatisch entfernt,
 * können aber für wichtige Fehler dauerhaft angezeigt werden.
 */
import { readonly, ref } from 'vue'

export type NotificationType = 'success' | 'info' | 'warning' | 'error'

export interface AppNotification {
  id: number
  type: NotificationType
  title: string
  message?: string
  timeout: number
}

const notifications = ref<AppNotification[]>([])
let nextId = 1

function remove(id: number): void {
  notifications.value = notifications.value.filter((item) => item.id !== id)
}

function notify(
  type: NotificationType,
  title: string,
  message?: string,
  timeout = type === 'error' ? 6500 : 4200,
): number {
  const id = nextId++
  notifications.value.push({ id, type, title, message, timeout })

  if (timeout > 0) {
    window.setTimeout(() => remove(id), timeout)
  }
  return id
}

/** Übersetzt technische Ausnahmeobjekte in eine verständliche Meldung. */
function errorFromUnknown(error: unknown, fallback = 'Die Aktion konnte nicht abgeschlossen werden.'): string {
  if (error instanceof DOMException && error.name === 'AbortError') {
    return 'Die Verarbeitung hat zu lange gedauert und wurde abgebrochen.'
  }
  if (error instanceof Error && error.message.trim()) return error.message
  return fallback
}

export function useNotifications() {
  return {
    notifications: readonly(notifications),
    remove,
    errorFromUnknown,
    success: (title: string, message?: string) => notify('success', title, message),
    info: (title: string, message?: string) => notify('info', title, message),
    warning: (title: string, message?: string) => notify('warning', title, message, 5500),
    error: (title: string, message?: string) => notify('error', title, message),
  }
}
