/**
 * Composable for PDF & Document Tools API calls.
 * Shared download/upload/auth logic for all tool components.
 */
import { ref } from 'vue'
import { apiPost, apiGetJson, downloadBlob } from '@/lib/api'

const API_BASE = '/api/pdf-tools'
const TIMEOUT = 5 * 60 * 1000 // 5 minutes

function apiRequest(
  endpoint: string,
  formData: FormData,
  options?: { timeout?: number }
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
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Unbekannter Fehler'
      return null
    } finally {
      loading.value = false
    }
  }

  // Status
  async function getStatus() {
    return apiGet('/status')
  }

  // Thumbnails
  async function getThumbnails(file: File, pages?: string, maxWidth = 200) {
    const fd = new FormData()
    fd.append('file', file)
    if (pages) fd.append('pages', pages)
    const resp = await apiRequest(`/thumbnails?max_width=${maxWidth}`, fd)
    return resp.json()
  }

  // Merge
  async function mergePdfs(files: File[], pageSelections?: Record<string, string>) {
    const fd = new FormData()
    files.forEach((f) => fd.append('files', f))
    if (pageSelections) fd.append('page_selections', JSON.stringify(pageSelections))
    const resp = await apiRequest('/merge', fd)
    await downloadBlob(resp, 'zusammengefuehrt.pdf')
  }

  // Split
  async function splitPdf(file: File, mode: string, ranges?: string, everyN?: number) {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('mode', mode)
    if (ranges) fd.append('ranges', ranges)
    if (everyN) fd.append('every_n', String(everyN))
    const resp = await apiRequest('/split', fd)
    const ct = resp.headers.get('Content-Type') || ''
    const ext = ct.includes('zip') ? 'zip' : 'pdf'
    await downloadBlob(resp, `geteilt.${ext}`)
  }

  // Rotate
  async function rotatePdf(file: File, rotations: Record<number, number>) {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('rotations', JSON.stringify(rotations))
    const resp = await apiRequest('/rotate', fd)
    await downloadBlob(resp, 'rotiert.pdf')
  }

  // To Images
  async function pdfToImages(file: File, pages?: string, format = 'png', dpi = 150) {
    const fd = new FormData()
    fd.append('file', file)
    if (pages) fd.append('pages', pages)
    fd.append('format', format)
    fd.append('dpi', String(dpi))
    const resp = await apiRequest('/to-images', fd)
    await downloadBlob(resp, 'bilder.zip')
  }

  // Compress
  async function compressPdf(file: File, quality = 'medium') {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('quality', quality)
    const resp = await apiRequest('/compress', fd)
    const meta = {
      originalSize: Number(resp.headers.get('X-Original-Size') || 0),
      compressedSize: Number(resp.headers.get('X-Compressed-Size') || 0),
      savings: Number(resp.headers.get('X-Savings-Bytes') || 0),
      ratio: Number(resp.headers.get('X-Compression-Ratio') || 0),
    }
    await downloadBlob(resp, 'komprimiert.pdf')
    return meta
  }

  // Watermark
  async function addWatermark(
    file: File,
    opts: {
      text?: string
      image?: File
      position?: string
      opacity?: number
      rotation?: number
      fontSize?: number
      color?: string
      pages?: string
    }
  ) {
    const fd = new FormData()
    fd.append('file', file)
    if (opts.text) fd.append('text', opts.text)
    if (opts.image) fd.append('image', opts.image)
    if (opts.position) fd.append('position', opts.position)
    if (opts.opacity !== undefined) fd.append('opacity', String(opts.opacity))
    if (opts.rotation !== undefined) fd.append('rotation', String(opts.rotation))
    if (opts.fontSize !== undefined) fd.append('font_size', String(opts.fontSize))
    if (opts.color) fd.append('color', opts.color)
    if (opts.pages) fd.append('pages', opts.pages)
    const resp = await apiRequest('/watermark', fd)
    await downloadBlob(resp, 'wasserzeichen.pdf')
  }

  // Images to PDF
  async function imagesToPdf(files: File[], pageSize = 'a4', orientation = 'portrait') {
    const fd = new FormData()
    files.forEach((f) => fd.append('files', f))
    fd.append('page_size', pageSize)
    fd.append('orientation', orientation)
    const resp = await apiRequest('/images-to-pdf', fd)
    await downloadBlob(resp, 'bilder_zu_pdf.pdf')
  }

  // Page Operations
  async function pageOperations(file: File, newOrder: number[]) {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('new_order', JSON.stringify(newOrder))
    const resp = await apiRequest('/page-operations', fd)
    await downloadBlob(resp, 'bearbeitet.pdf')
  }

  // Metadata Read
  async function readMetadata(file: File) {
    const fd = new FormData()
    fd.append('file', file)
    const resp = await apiRequest('/metadata/read', fd)
    return resp.json()
  }

  // Metadata Set
  async function setMetadata(
    file: File,
    meta: {
      title?: string
      author?: string
      subject?: string
      keywords?: string
      creation_date?: string
      modification_date?: string
      creator?: string
      producer?: string
    }
  ) {
    const fd = new FormData()
    fd.append('file', file)
    if (meta.title !== undefined) fd.append('title', meta.title)
    if (meta.author !== undefined) fd.append('author', meta.author)
    if (meta.subject !== undefined) fd.append('subject', meta.subject)
    if (meta.keywords !== undefined) fd.append('keywords', meta.keywords)
    if (meta.creation_date !== undefined) fd.append('creation_date', meta.creation_date)
    if (meta.modification_date !== undefined) fd.append('modification_date', meta.modification_date)
    if (meta.creator !== undefined) fd.append('creator', meta.creator)
    if (meta.producer !== undefined) fd.append('producer', meta.producer)
    const resp = await apiRequest('/metadata', fd)
    await downloadBlob(resp, 'metadaten.pdf')
  }

  // Word to PDF
  async function wordToPdf(file: File) {
    const fd = new FormData()
    fd.append('file', file)
    const resp = await apiRequest('/word-to-pdf', fd)
    await downloadBlob(resp, file.name.replace(/\.docx?$/i, '.pdf'))
  }

  // Word Merge
  async function wordMerge(files: File[], addPageBreak = true) {
    const fd = new FormData()
    files.forEach((f) => fd.append('files', f))
    fd.append('add_page_break', String(addPageBreak))
    const resp = await apiRequest('/word-merge', fd)
    await downloadBlob(resp, 'zusammengefuehrt.docx')
  }

  // Word Diff
  async function wordDiff(fileA: File, fileB: File) {
    const fd = new FormData()
    fd.append('file_a', fileA)
    fd.append('file_b', fileB)
    const resp = await apiRequest('/word-diff', fd)
    return resp.json()
  }

  // Word Metadata Read
  async function readWordMetadata(file: File) {
    const fd = new FormData()
    fd.append('file', file)
    const resp = await apiRequest('/word-metadata/read', fd)
    return resp.json()
  }

  // Word Metadata Set
  async function setWordMetadata(
    file: File,
    meta: {
      title?: string
      author?: string
      subject?: string
      keywords?: string
      category?: string
      comments?: string
      last_modified_by?: string
      modified?: string
      created?: string
    }
  ) {
    const fd = new FormData()
    fd.append('file', file)
    Object.entries(meta).forEach(([key, val]) => {
      if (val !== undefined && val !== '') fd.append(key, val)
    })
    const resp = await apiRequest('/word-metadata', fd)
    await downloadBlob(resp, file.name.replace(/\.docx?$/i, '_meta.docx'))
  }

  // Excel Metadata Read
  async function readExcelMetadata(file: File) {
    const fd = new FormData()
    fd.append('file', file)
    const resp = await apiRequest('/excel-metadata/read', fd)
    return resp.json()
  }

  // Excel Metadata Set
  async function setExcelMetadata(
    file: File,
    meta: {
      title?: string
      creator?: string
      subject?: string
      keywords?: string
      category?: string
      description?: string
      last_modified_by?: string
      modified?: string
      created?: string
    }
  ) {
    const fd = new FormData()
    fd.append('file', file)
    Object.entries(meta).forEach(([key, val]) => {
      if (val !== undefined && val !== '') fd.append(key, val)
    })
    const resp = await apiRequest('/excel-metadata', fd)
    await downloadBlob(resp, file.name.replace(/\.xlsx?$/i, '_meta.xlsx'))
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
    const qs = params.toString()
    const resp = await apiPost(`/api/pdf-convert/to-word${qs ? `?${qs}` : ''}`, fd)
    await downloadBlob(resp, file.name.replace(/\.pdf$/i, '.docx'))
    return true
  }

  async function pdfToExcel(file: File, options?: { pages?: string; consolidate?: boolean }) {
    const fd = new FormData()
    fd.append('file', file)
    const params = new URLSearchParams()
    if (options?.pages) params.set('pages', options.pages)
    if (options?.consolidate === false) params.set('consolidate', 'false')
    const qs = params.toString()
    const resp = await apiPost(`/api/pdf-convert/to-excel${qs ? `?${qs}` : ''}`, fd)
    await downloadBlob(resp, file.name.replace(/\.pdf$/i, '.xlsx'))
    return true
  }

  async function protectPdf(file: File, password: string, ownerPassword?: string) {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('password', password)
    if (ownerPassword) fd.append('owner_password', ownerPassword)
    const resp = await apiRequest('/protect', fd)
    await downloadBlob(resp, file.name.replace(/\.pdf$/i, '_geschuetzt.pdf'))
    return true
  }

  async function unlockPdf(file: File, password: string) {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('password', password)
    const resp = await apiRequest('/unlock', fd)
    await downloadBlob(resp, file.name.replace(/\.pdf$/i, '_entsperrt.pdf'))
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
