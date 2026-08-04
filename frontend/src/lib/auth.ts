/**
 * Zentraler Auth-Modul-Store ohne zusätzliche State-Bibliothek.
 *
 * Die optionale Token-Persistenz läuft über `safeStorage`. Netzwerkaufrufe
 * besitzen ein Zeitlimit und sämtliche Antwortformen werden vor der Übernahme
 * in den reaktiven Zustand typisiert beziehungsweise normalisiert.
 */

import { computed, ref } from 'vue'
import { readStoredValue, removeStoredValue, writeStoredValue } from '@/lib/safeStorage'

const TOKEN_KEY = 'pdfapp_token'
const AUTH_TIMEOUT = 30_000

export interface AuthUser {
  id: number
  email: string
  role: 'USER' | 'ADMIN'
  is_active: boolean
  is_verified: boolean
  created_at: string
  last_login: string | null
}

interface AuthResponse {
  access_token: string
  user: AuthUser
}

export const token = ref<string | null>(readStoredValue(TOKEN_KEY))
export const user = ref<AuthUser | null>(null)
export const preferences = ref<Record<string, unknown>>({})

export const isAuthenticated = computed(() => Boolean(token.value))
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

function readableDetail(value: unknown, fallback: string): string {
  if (typeof value === 'string' && value.trim()) return value
  if (Array.isArray(value)) {
    const messages = value.map((entry) => {
      if (typeof entry === 'string') return entry
      if (entry && typeof entry === 'object' && 'msg' in entry) return String(entry.msg)
      return ''
    }).filter(Boolean)
    if (messages.length) return messages.join(' ')
  }
  return fallback
}

async function fetchAuth(url: string, init: RequestInit = {}): Promise<Response> {
  const controller = new AbortController()
  const timeoutError = new Error('Die Authentifizierungsanfrage hat zu lange gedauert.')
  timeoutError.name = 'AbortError'
  const timer = globalThis.setTimeout(() => controller.abort(timeoutError), AUTH_TIMEOUT)
  try {
    return await fetch(url, { ...init, signal: controller.signal })
  } finally {
    globalThis.clearTimeout(timer)
  }
}

async function jsonOrThrow<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText })) as { detail?: unknown }
    throw new Error(readableDetail(payload.detail, `Fehler ${response.status}`))
  }
  return response.json() as Promise<T>
}

function normalizeUser(value: unknown): AuthUser {
  if (!value || typeof value !== 'object') throw new Error('Der Server hat keine gültigen Kontodaten zurückgegeben.')
  const source = value as Record<string, unknown>
  const role = source.role === 'ADMIN' ? 'ADMIN' : 'USER'
  const id = Number(source.id)
  const email = String(source.email ?? '')
  if (!Number.isFinite(id) || !email) throw new Error('Der Server hat unvollständige Kontodaten zurückgegeben.')
  return {
    id,
    email,
    role,
    is_active: Boolean(source.is_active),
    is_verified: Boolean(source.is_verified),
    created_at: String(source.created_at ?? ''),
    last_login: source.last_login == null ? null : String(source.last_login),
  }
}

function normalizeAuthResponse(value: AuthResponse): AuthResponse {
  if (!value.access_token || typeof value.access_token !== 'string') {
    throw new Error('Der Server hat kein gültiges Zugriffstoken zurückgegeben.')
  }
  return { access_token: value.access_token, user: normalizeUser(value.user) }
}

export async function login(email: string, password: string): Promise<void> {
  const body = new URLSearchParams({ username: email, password })
  const response = await fetchAuth('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  const data = normalizeAuthResponse(await jsonOrThrow<AuthResponse>(response))
  setToken(data.access_token)
  user.value = data.user
  await loadPreferences()
}

export async function register(
  email: string,
  password: string,
  turnstileToken?: string,
): Promise<void> {
  const response = await fetchAuth('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, turnstile_token: turnstileToken || undefined }),
  })
  const data = normalizeAuthResponse(await jsonOrThrow<AuthResponse>(response))
  setToken(data.access_token)
  user.value = data.user
  preferences.value = {}
}

export async function fetchMe(): Promise<void> {
  if (!token.value) return
  const response = await fetchAuth('/api/auth/me', { headers: authHeader() })
  if (response.status === 401) {
    logout()
    return
  }
  user.value = normalizeUser(await jsonOrThrow<unknown>(response))
  await loadPreferences()
}

export async function loadPreferences(): Promise<void> {
  if (!token.value) return
  const response = await fetchAuth('/api/me/preferences', { headers: authHeader() })
  if (response.status === 401) {
    logout()
    return
  }
  const payload = await jsonOrThrow<unknown>(response)
  preferences.value = payload && typeof payload === 'object' && !Array.isArray(payload)
    ? payload as Record<string, unknown>
    : {}
}

export async function savePreferences(prefs: Record<string, unknown>): Promise<void> {
  const response = await fetchAuth('/api/me/preferences', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify(prefs),
  })
  const payload = await jsonOrThrow<unknown>(response)
  preferences.value = payload && typeof payload === 'object' && !Array.isArray(payload)
    ? payload as Record<string, unknown>
    : {}
}

export async function deleteAccount(password: string): Promise<void> {
  const response = await fetchAuth('/api/me', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify({ password }),
  })
  if (!response.ok) await jsonOrThrow<unknown>(response)
  logout()
}

function compatiblePreference<T>(value: unknown, fallback: T): value is T {
  if (Array.isArray(fallback)) return Array.isArray(value)
  if (fallback === null) return value === null
  return typeof value === typeof fallback
}

/** Default-Wert eines Werkzeugs aus den Konto-Einstellungen. */
export function prefDefault<T>(key: string, fallback: T): T {
  const value = preferences.value[key]
  return compatiblePreference(value, fallback) && value !== '' ? value : fallback
}
