/**
 * Globales Benachrichtigungssystem für Erfolg, Hinweise, Warnungen und Fehler.
 *
 * Der Zustand liegt außerhalb einzelner Komponenten und ist deshalb in allen
 * Werkzeugen identisch verfügbar. Meldungen werden automatisch entfernt,
 * können aber für wichtige Fehler dauerhaft angezeigt werden. Duplikate und
 * eine unbegrenzte Toast-Schlange werden bewusst verhindert, damit mehrere
 * parallele Preview-Aufrufe die Oberfläche nicht überdecken.
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

const MAX_VISIBLE_NOTIFICATIONS = 4
const notifications = ref<AppNotification[]>([])
const timers = new Map<number, number>()
let nextId = 1

function remove(id: number): void {
  const timer = timers.get(id)
  if (timer !== undefined && typeof window !== 'undefined') window.clearTimeout(timer)
  timers.delete(id)
  notifications.value = notifications.value.filter((item) => item.id !== id)
}

function notify(
  type: NotificationType,
  title: string,
  message?: string,
  timeout = type === 'error' ? 6500 : 4200,
): number {
  // Identische parallele Fehler werden zu einer sichtbaren Meldung zusammengefasst.
  const duplicate = notifications.value.find((item) =>
    item.type === type && item.title === title && item.message === message,
  )
  if (duplicate) {
    remove(duplicate.id)
  }

  const id = nextId++
  notifications.value.push({ id, type, title, message, timeout })

  while (notifications.value.length > MAX_VISIBLE_NOTIFICATIONS) {
    const oldest = notifications.value[0]
    if (oldest) remove(oldest.id)
  }

  if (timeout > 0 && typeof window !== 'undefined') {
    const timer = window.setTimeout(() => remove(id), timeout)
    timers.set(id, timer)
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
