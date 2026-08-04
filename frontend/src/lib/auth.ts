/**
 * Auth-Modul-Store (bewusst ohne Pinia, Muster wie lib/results.ts).
 *
 * Token, Nutzer und Preferences bleiben zentral im Modul-State. Die optionale
 * Token-Persistenz läuft über `safeStorage`, damit Privatmodus, eingebettete
 * Browser und Tests ohne verfügbares `localStorage` die App nicht abbrechen.
 */

import { computed, ref } from 'vue'
import { readStoredValue, removeStoredValue, writeStoredValue } from '@/lib/safeStorage'

const TOKEN_KEY = 'pdfapp_token'

export interface AuthUser {
  id: number
  email: string
  role: 'USER' | 'ADMIN'
  is_active: boolean
  is_verified: boolean
  created_at: string
  last_login: string | null
}

export const token = ref<string | null>(readStoredValue(TOKEN_KEY))
export const user = ref<AuthUser | null>(null)
export const preferences = ref<Record<string, unknown>>({})

export const isAuthenticated = computed(() => !!token.value)
export const isAdmin = computed(() => user.value?.role === 'ADMIN')

function setToken(value: string | null): void {
  token.value = value
  if (value) writeStoredValue(TOKEN_KEY, value)
  else removeStoredValue(TOKEN_KEY)
}

export function authHeader(): Record<string, string> {
  return token.value ? { Authorization: `Bearer ${token.value}` } : {}
}

export function logout(): void {
  setToken(null)
  user.value = null
  preferences.value = {}
}

async function jsonOrThrow(response: Response): Promise<any> {
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }))
    const detail = err.detail
    throw new Error(
      typeof detail === 'string' ? detail : detail?.[0]?.msg || `Fehler ${response.status}`,
    )
  }
  return response.json()
}

export async function login(email: string, password: string): Promise<void> {
  const body = new URLSearchParams({ username: email, password })
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  const data = await jsonOrThrow(response)
  setToken(data.access_token)
  user.value = data.user
  await loadPreferences()
}

export async function register(
  email: string,
  password: string,
  turnstileToken?: string,
): Promise<void> {
  const response = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, turnstile_token: turnstileToken || undefined }),
  })
  const data = await jsonOrThrow(response)
  setToken(data.access_token)
  user.value = data.user
  preferences.value = {}
}

export async function fetchMe(): Promise<void> {
  if (!token.value) return
  const response = await fetch('/api/auth/me', { headers: authHeader() })
  if (response.status === 401) {
    logout()
    return
  }
  if (response.ok) {
    user.value = await response.json()
    await loadPreferences()
  }
}

export async function loadPreferences(): Promise<void> {
  if (!token.value) return
  const response = await fetch('/api/me/preferences', { headers: authHeader() })
  if (response.ok) preferences.value = await response.json()
}

export async function savePreferences(prefs: Record<string, unknown>): Promise<void> {
  const response = await fetch('/api/me/preferences', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(prefs),
  })
  preferences.value = await jsonOrThrow(response)
}

export async function deleteAccount(password: string): Promise<void> {
  const response = await fetch('/api/me', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify({ password }),
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(err.detail || `Fehler ${response.status}`)
  }
  logout()
}

/** Default-Wert eines Werkzeugs aus den Konto-Einstellungen (falls angemeldet). */
export function prefDefault<T>(key: string, fallback: T): T {
  const value = preferences.value[key]
  return value === undefined || value === null || value === '' ? fallback : (value as T)
}
