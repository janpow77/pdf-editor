/**
 * Gemeinsame API-Funktionen für PDF- und Office-Werkzeuge.
 *
 * Upload, Download und Fehlerbehandlung werden bewusst zentral gebündelt.
 * Dadurch verwenden alle Fachmodule dieselben Zeitlimits, Dateinamen und
 * Benachrichtigungen. Die Standardbreite der Vorschaubilder wurde von 200 auf
 * 320 Pixel erhöht; das entspricht einer Steigerung um 60 Prozent und verbessert
 * die Lesbarkeit, ohne die responsive Rasterdarstellung aufzugeben.
 */
import { ref } from 'vue'
import { apiPost, apiGetJson, downloadBlob } from '@/lib/api'

const API_BASE = '/api/pdf-tools'
const TIMEOUT = 5 * 60 * 1000

function apiRequest(
  endpoint: string,
  formData: FormData,
  options?: { timeout?: number },
): Promise<Response> {
  return apiPost(`${API_BASE}${endpoint}`, formData, {
    timeout: options?.timeout ?? TIMEOUT,
  })
}

function apiGet(endpoint: string): Promise<unknown> {
  return apiGetJson(`${API_BASE}${endpoint}`)
}

export function usePdfTools() {
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function withLoading<T>(fn: () => Promise<T>): Promise<T | null> {
    loading.value = true
    error.value = null
    try {
      return await fn()
    } catch (caught: unknown) {
      error.value = caught instanceof Error ? caught.message : 'Unbekannter Fehler'
      return null
    } finally {
      loading.value = false
    }
  }

  async function getStatus() {
    return apiGet('/status')
  }

  /**
   * `pages` und `max_width` sind FastAPI-Queryparameter. Eine frühere Fassung
   * legte `pages` irrtümlich in FormData ab; das Backend ignorierte den Wert und
   * renderte beispielsweise beim Merge alle Seiten statt nur Seite 1.
   */
  async function getThumbnails(file: File, pages?: string, maxWidth = 320) {
    const fd = new FormData()
    fd.append('file', file)
    const query = new URLSearchParams({ max_width: String(maxWidth) })
    if (pages) query.set('pages', pages)
    const response = await apiRequest(`/thumbnails?${query.toString()}`, fd)
    return response.json()
  }

  async function mergePdfs(files: File[], pageSelections?: Record<string, string>) {
    const fd = new FormData()
    files.forEach((file) => fd.append('files', file))
    if (pageSelections) fd.append('page_selections', JSON.stringify(pageSelections))
    const response = await apiRequest('/merge', fd)
    await downloadBlob(response, 'zusammengefuehrt.pdf')
  }

  async function splitPdf(file: File, mode: string, ranges?: string, everyN?: number) {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('mode', mode)
    if (ranges) fd.append('ranges', ranges)
    if (everyN) fd.append('every_n', String(everyN))
    const response = await apiRequest('/split', fd)
    const contentType = response.headers.get('Content-Type') || ''
    const extension = contentType.includes('zip') ? 'zip' : 'pdf'
    await downloadBlob(response, `geteilt.${extension}`)
  }

  async function rotatePdf(file: File, rotations: Record<number, number>) {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('rotations', JSON.stringify(rotations))
    const response = await apiRequest('/rotate', fd)
    await downloadBlob(response, 'rotiert.pdf')
  }

  async function pdfToImages(file: File, pages?: string, format = 'png', dpi = 150) {
    const fd = new FormData()
    fd.append('file', file)
    if (pages) fd.append('pages', pages)
    fd.append('format', format)
    fd.append('dpi', String(dpi))
    const response = await apiRequest('/to-images', fd)
    await downloadBlob(response, 'bilder.zip')
  }

  async function compressPdf(file: File, quality = 'medium') {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('quality', quality)
    const response = await apiRequest('/compress', fd)
    const metadata = {
      originalSize: Number(response.headers.get('X-Original-Size') || 0),
      compressedSize: Number(response.headers.get('X-Compressed-Size') || 0),
      savings: Number(response.headers.get('X-Savings-Bytes') || 0),
      ratio: Number(response.headers.get('X-Compression-Ratio') || 0),
    }
    await downloadBlob(response, 'komprimiert.pdf')
    return metadata
  }

  async function addWatermark(
    file: File,
    options: {
      text?: string
      image?: File
      position?: string
      opacity?: number
      rotation?: number
      fontSize?: number
      color?: string
      pages?: string
    },
  ) {
    const fd = new FormData()
    fd.append('file', file)
    if (options.text) fd.append('text', options.text)
    if (options.image) fd.append('image', options.image)
    if (options.position) fd.append('position', options.position)
    if (options.opacity !== undefined) fd.append('opacity', String(options.opacity))
    if (options.rotation !== undefined) fd.append('rotation', String(options.rotation))
    if (options.fontSize !== undefined) fd.append('font_size', String(options.fontSize))
    if (options.color) fd.append('color', options.color)
    if (options.pages) fd.append('pages', options.pages)
    const response = await apiRequest('/watermark', fd)
    await downloadBlob(response, 'wasserzeichen.pdf')
  }

  async function imagesToPdf(files: File[], pageSize = 'a4', orientation = 'portrait') {
    const fd = new FormData()
    files.forEach((file) => fd.append('files', file))
    fd.append('page_size', pageSize)
    fd.append('orientation', orientation)
    const response = await apiRequest('/images-to-pdf', fd)
    await downloadBlob(response, 'bilder_zu_pdf.pdf')
  }

  async function pageOperations(file: File, newOrder: number[]) {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('new_order', JSON.stringify(newOrder))
    const response = await apiRequest('/page-operations', fd)
    await downloadBlob(response, 'bearbeitet.pdf')
  }

  async function readMetadata(file: File) {
    const fd = new FormData()
    fd.append('file', file)
    const response = await apiRequest('/metadata/read', fd)
    return response.json()
  }

  async function setMetadata(
    file: File,
    metadata: {
      title?: string
      author?: string
      subject?: string
      keywords?: string
      creation_date?: string
      modification_date?: string
      creator?: string
      producer?: string
    },
  ) {
    const fd = new FormData()
    fd.append('file', file)
    if (metadata.title !== undefined) fd.append('title', metadata.title)
    if (metadata.author !== undefined) fd.append('author', metadata.author)
    if (metadata.subject !== undefined) fd.append('subject', metadata.subject)
    if (metadata.keywords !== undefined) fd.append('keywords', metadata.keywords)
    if (metadata.creation_date !== undefined) fd.append('creation_date', metadata.creation_date)
    if (metadata.modification_date !== undefined) fd.append('modification_date', metadata.modification_date)
    if (metadata.creator !== undefined) fd.append('creator', metadata.creator)
    if (metadata.producer !== undefined) fd.append('producer', metadata.producer)
    const response = await apiRequest('/metadata', fd)
    await downloadBlob(response, 'metadaten.pdf')
  }

  async function wordToPdf(file: File) {
    const fd = new FormData()
    fd.append('file', file)
    const response = await apiRequest('/word-to-pdf', fd)
    await downloadBlob(response, file.name.replace(/\.docx?$/i, '.pdf'))
  }

  async function wordMerge(files: File[], addPageBreak = true) {
    const fd = new FormData()
    files.forEach((file) => fd.append('files', file))
    fd.append('add_page_break', String(addPageBreak))
    const response = await apiRequest('/word-merge', fd)
    await downloadBlob(response, 'zusammengefuehrt.docx')
  }

  async function wordDiff(fileA: File, fileB: File) {
    const fd = new FormData()
    fd.append('file_a', fileA)
    fd.append('file_b', fileB)
    const response = await apiRequest('/word-diff', fd)
    return response.json()
  }

  async function readWordMetadata(file: File) {
    const fd = new FormData()
    fd.append('file', file)
    const response = await apiRequest('/word-metadata/read', fd)
    return response.json()
  }

  async function setWordMetadata(
    file: File,
    metadata: {
      title?: string
      author?: string
      subject?: string
      keywords?: string
      category?: string
      comments?: string
      last_modified_by?: string
      modified?: string
      created?: string
    },
  ) {
    const fd = new FormData()
    fd.append('file', file)
    Object.entries(metadata).forEach(([key, value]) => {
      if (value !== undefined && value !== '') fd.append(key, value)
    })
    const response = await apiRequest('/word-metadata', fd)
    await downloadBlob(response, file.name.replace(/\.docx?$/i, '_meta.docx'))
  }

  async function readExcelMetadata(file: File) {
    const fd = new FormData()
    fd.append('file', file)
    const response = await apiRequest('/excel-metadata/read', fd)
    return response.json()
  }

  async function setExcelMetadata(
    file: File,
    metadata: {
      title?: string
      creator?: string
      subject?: string
      keywords?: string
      category?: string
      description?: string
      last_modified_by?: string
      modified?: string
      created?: string
    },
  ) {
    const fd = new FormData()
    fd.append('file', file)
    Object.entries(metadata).forEach(([key, value]) => {
      if (value !== undefined && value !== '') fd.append(key, value)
    })
    const response = await apiRequest('/excel-metadata', fd)
    await downloadBlob(response, file.name.replace(/\.xlsx?$/i, '_meta.xlsx'))
  }

  async function pdfToWord(
    file: File,
    options?: { pages?: string; useOcr?: boolean; ocrLanguage?: string },
  ) {
    const fd = new FormData()
    fd.append('file', file)
    const params = new URLSearchParams()
    if (options?.pages) params.set('pages', options.pages)
    if (options?.useOcr) params.set('use_ocr', 'true')
    if (options?.ocrLanguage) params.set('ocr_language', options.ocrLanguage)
    const query = params.toString()
    const response = await apiPost(`/api/pdf-convert/to-word${query ? `?${query}` : ''}`, fd)
    await downloadBlob(response, file.name.replace(/\.pdf$/i, '.docx'))
    return true
  }

  async function pdfToExcel(file: File, options?: { pages?: string; consolidate?: boolean }) {
    const fd = new FormData()
    fd.append('file', file)
    const params = new URLSearchParams()
    if (options?.pages) params.set('pages', options.pages)
    if (options?.consolidate === false) params.set('consolidate', 'false')
    const query = params.toString()
    const response = await apiPost(`/api/pdf-convert/to-excel${query ? `?${query}` : ''}`, fd)
    await downloadBlob(response, file.name.replace(/\.pdf$/i, '.xlsx'))
    return true
  }

  async function protectPdf(file: File, password: string, ownerPassword?: string) {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('password', password)
    if (ownerPassword) fd.append('owner_password', ownerPassword)
    const response = await apiRequest('/protect', fd)
    await downloadBlob(response, file.name.replace(/\.pdf$/i, '_geschuetzt.pdf'))
    return true
  }

  async function unlockPdf(file: File, password: string) {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('password', password)
    const response = await apiRequest('/unlock', fd)
    await downloadBlob(response, file.name.replace(/\.pdf$/i, '_entsperrt.pdf'))
    return true
  }

  return {
    loading,
    error,
    withLoading,
    getStatus,
    protectPdf,
    unlockPdf,
    pdfToWord,
    pdfToExcel,
    getThumbnails,
    mergePdfs,
    splitPdf,
    rotatePdf,
    pdfToImages,
    compressPdf,
    addWatermark,
    imagesToPdf,
    pageOperations,
    readMetadata,
    setMetadata,
    wordToPdf,
    wordMerge,
    wordDiff,
    readWordMetadata,
    setWordMetadata,
    readExcelMetadata,
    setExcelMetadata,
  }
}
