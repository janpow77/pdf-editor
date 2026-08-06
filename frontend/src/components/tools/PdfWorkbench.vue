<template>
  <!--
    Vollbild-Arbeitsplatz: öffnet sich sofort mit dem Werkzeug (nicht erst nach
    dem ersten Upload). Kopfleiste oben, Seitenübersicht links, große zoombare
    Seitenansicht rechts. „Zurück" verlässt den Arbeitsplatz.
  -->
  <div class="fixed inset-0 z-40 flex flex-col bg-gray-100 dark:bg-gray-950" role="dialog" aria-modal="true" aria-label="Werkbank — PDF-Arbeitsplatz">
    <!-- Kopf-/Werkzeugleiste -->
    <header class="flex flex-wrap items-center gap-2 border-b border-gray-200 bg-white/95 px-3 py-2 backdrop-blur dark:border-gray-700 dark:bg-gray-900/95">
      <UiButton size="sm" variant="ghost" @click="$emit('back')">‹ Zurück</UiButton>
      <span class="flex items-center gap-1.5 font-semibold text-gray-950 dark:text-white"><span aria-hidden="true">🛠️</span> Werkbank</span>

      <input ref="fileInput" type="file" accept=".pdf" multiple class="hidden" @change="onFileSelect" />
      <UiButton size="sm" variant="secondary" :loading="loadingDocs > 0" @click="fileInput?.click()">+ PDF</UiButton>

      <span
        v-for="(doc, index) in docs"
        :key="doc.uid"
        class="hidden items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-black/5 md:inline-flex dark:ring-white/10"
        :class="docBadgeClass(index)"
      >
        <strong>D{{ index + 1 }}</strong>
        <span class="max-w-32 truncate">{{ doc.label }}</span>
        <button
          type="button"
          class="ml-0.5 grid h-4 w-4 place-items-center rounded-full transition hover:bg-black/10 dark:hover:bg-white/20"
          :aria-label="`Dokument D${index + 1} (${doc.label}) samt Seiten aus der Werkbank entfernen`"
          @click="removeDoc(doc.uid)"
        >×</button>
      </span>

      <span class="flex-1"></span>

      <template v-if="items.length">
        <!-- Werkzeugkategorien als Menüleiste: jede Kategorie öffnet ihr
             eigenes kurzes Menü — statt einem langen Gesamt-Dropdown -->
        <nav class="flex flex-wrap items-center gap-0.5" aria-label="Werkzeugkategorien">
          <UiButton
            v-for="group in menuGroups"
            :key="group.key"
            size="sm"
            variant="ghost"
            :disabled="busy || !activeItems.length"
            aria-haspopup="menu"
            :aria-expanded="openMenuKey === group.key"
            :title="group.title"
            @click="toggleCategory(group.key, $event)"
          >
            {{ group.icon }} {{ group.shortTitle }}
          </UiButton>
        </nav>
        <span class="mx-1 h-6 w-px bg-gray-300 dark:bg-gray-600" aria-hidden="true"></span>
        <UiButton v-if="history.length" size="sm" variant="secondary" :title="`Rückgängig: ${history[history.length - 1]?.label}`" @click="undo">↩ Rückgängig</UiButton>
        <UiButton size="sm" variant="primary" :loading="busy" :disabled="!activeItems.length" @click="nameDialogSubset = 'alle'">
          Ergebnis ({{ activeItems.length }} S.)
        </UiButton>
        <!-- Dateiname erfragen statt stumpf „werkbank.pdf" -->
        <Teleport to="body">
          <div v-if="nameDialogSubset" class="fixed inset-0 z-[70] grid place-items-center bg-black/30 p-4" @click.self="nameDialogSubset = null">
            <div class="w-full max-w-sm space-y-3 rounded-2xl bg-white p-5 shadow-apple ring-1 ring-gray-300 dark:bg-gray-900 dark:ring-gray-600" role="dialog" aria-label="Dateiname für das Ergebnis">
              <h3 class="font-semibold text-gray-950 dark:text-white">Ergebnis speichern</h3>
              <label class="block text-sm">
                <span class="mb-1 block font-medium text-gray-800 dark:text-gray-100">Name</span>
                <input
                  v-model="exportName"
                  type="text"
                  class="w-full rounded-xl bg-white px-3 py-2 text-sm text-gray-950 ring-1 ring-gray-400/70 focus:ring-2 focus:ring-primary-500 dark:bg-gray-950 dark:text-white dark:ring-gray-600"
                  @keydown.enter.prevent="confirmExport"
                />
              </label>
              <p class="text-xs text-gray-600 dark:text-gray-300">Dateiname: <strong>{{ exportFilename }}</strong>{{ nameDialogSubset === 'auswahl' ? ` — nur die ${selectedActiveItems.length} ausgewählten Seiten` : '' }}</p>
              <div class="flex justify-end gap-2">
                <UiButton variant="ghost" @click="nameDialogSubset = null">Abbrechen</UiButton>
                <UiButton variant="primary" :loading="busy" @click="confirmExport">Herunterladen</UiButton>
              </div>
            </div>
          </div>
        </Teleport>
        <!-- Kategorienmenü: per Teleport aus der Kopfleiste gelöst und an den
             Viewport geklemmt, Außenklick schließt -->
        <Teleport to="body">
          <div v-if="openMenu" class="fixed inset-0 z-[60]" @click="openMenuKey = null">
            <div
              class="absolute w-72 overflow-y-auto rounded-2xl bg-white p-2 shadow-apple ring-1 ring-gray-300 dark:bg-gray-900 dark:ring-gray-600"
              :style="menuStyle"
              role="menu"
              :aria-label="`Werkzeuge: ${openMenu.title}`"
              @click.stop
            >
            <p class="px-2 pb-0.5 pt-1 text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">{{ openMenu.icon }} {{ openMenu.title }}</p>
              <button
                v-for="tool in openMenu.tools"
                :key="tool.id"
                type="button"
                role="menuitem"
                class="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm transition"
                :class="tool.reason
                  ? 'cursor-not-allowed text-gray-400 dark:text-gray-500'
                  : 'text-gray-800 hover:bg-primary-50 dark:text-gray-100 dark:hover:bg-primary-500/15'"
                :disabled="Boolean(tool.reason)"
                :title="tool.reason ?? (tool.panel ? `${tool.label} direkt hier im Editor anwenden` : `Aktuellen Stand in „${tool.label}“ weiterbearbeiten`)"
                @click="openTool(tool.id)"
              >
                <span aria-hidden="true">{{ tool.icon }}</span>
                <span class="flex-1">{{ tool.label }}</span>
                <span v-if="tool.panel" class="rounded bg-primary-100 px-1 text-[10px] font-semibold text-primary-700 dark:bg-primary-500/20 dark:text-primary-300" title="Läuft direkt im Editor">direkt</span>
                <span v-else-if="tool.reason" class="text-[10px]" aria-hidden="true">—</span>
              </button>
            </div>
          </div>
        </Teleport>
      </template>
    </header>

    <!-- Kontextleiste: erscheint nur bei aktiver Auswahl, mit Klartext statt Symbolen -->
    <div
      v-if="selectedItems.length"
      class="flex flex-wrap items-center gap-2 border-b border-gray-200 bg-gray-50 px-3 py-1.5 text-sm dark:border-gray-700 dark:bg-white/5"
      aria-label="Aktionen für die Seitenauswahl"
    >
      <span class="font-semibold tabular-nums text-gray-800 dark:text-gray-100">{{ selectedItems.length }} ausgewählt</span>
      <UiButton size="sm" variant="ghost" @click="selectAll(false)">Auswahl aufheben</UiButton>
      <span class="mx-1 h-5 w-px bg-gray-300 dark:bg-gray-600" aria-hidden="true"></span>
      <UiButton size="sm" variant="secondary" @click="rotateSelection(-90)">↺ Links drehen</UiButton>
      <UiButton size="sm" variant="secondary" @click="rotateSelection(90)">↻ Rechts drehen</UiButton>
      <UiButton size="sm" variant="secondary" @click="duplicateSelection">⧉ Duplizieren</UiButton>
      <UiButton size="sm" variant="danger" @click="removeSelection(true)">✕ Entfernen</UiButton>
      <UiButton size="sm" variant="secondary" @click="removeSelection(false)">⤺ Wiederherstellen</UiButton>
      <span class="mx-1 h-5 w-px bg-gray-300 dark:bg-gray-600" aria-hidden="true"></span>
      <UiButton v-if="selectedActiveItems.length" size="sm" variant="secondary" :disabled="busy" @click="nameDialogSubset = 'auswahl'">
        Auswahl als PDF exportieren ({{ selectedActiveItems.length }})
      </UiButton>
    </div>

    <!-- Rückweg: neues Ergebnis aus einem Werkzeug übernehmen -->
    <div
      v-if="newestResult"
      class="flex flex-wrap items-center gap-2 border-b border-primary-200 bg-primary-50 px-3 py-2 text-sm dark:border-primary-800 dark:bg-primary-500/10"
    >
      <span class="font-medium text-primary-900 dark:text-primary-200">Neues Ergebnis: „{{ newestResult.name }}"</span>
      <UiButton size="sm" variant="primary" :loading="loadingDocs > 0" @click="adoptResult(true)">Als neuen Stand laden</UiButton>
      <UiButton size="sm" variant="secondary" :loading="loadingDocs > 0" @click="adoptResult(false)">Als Dokument hinzufügen</UiButton>
      <UiButton size="sm" variant="ghost" @click="markResultsSeen">Ausblenden</UiButton>
    </div>

    <!-- Rumpf -->
    <div class="flex min-h-0 flex-1">
      <!-- Seitenübersicht -->
      <aside
        v-if="items.length"
        class="flex shrink-0 flex-col overflow-hidden border-r border-gray-200 bg-white/60 dark:border-gray-700 dark:bg-gray-900/50"
        :style="{ width: sidebarWidth + 'px' }"
        aria-label="Seitenübersicht"
      >
        <!-- Aktionsleiste der Übersicht: Auswahl und Leerseite gehören zu den
             Seiten — deshalb hier statt in der Kopfleiste -->
        <div class="flex shrink-0 flex-wrap items-center gap-1 border-b border-gray-200 bg-white/80 p-1.5 dark:border-gray-700 dark:bg-gray-900/70">
          <UiButton size="sm" variant="ghost" @click="selectAll(selectedItems.length < items.length)">
            {{ selectedItems.length < items.length ? 'Alle auswählen' : 'Aufheben' }}
          </UiButton>
          <UiButton size="sm" variant="ghost" title="Leerseite einfügen (nach der letzten Auswahl, sonst ans Ende)" @click="insertBlank">➕ Leerseite</UiButton>
        </div>

        <div
          class="min-h-0 flex-1 space-y-2 overflow-y-auto p-2"
          role="list"
          aria-label="Seiten. Klick zeigt die Seite groß, das Häkchen wählt für Mehrfach-Aktionen aus. Reihenfolge per Ziehen ändern."
        >
        <div
          v-for="(item, index) in items"
          :key="item.uid"
          role="listitem"
          class="group relative rounded-xl bg-white p-1.5 shadow-apple-sm ring-1 transition dark:bg-gray-900"
          :class="[
            item.uid === focusedUid ? 'ring-2 ring-primary-500' : item.selected ? 'ring-2 ring-primary-300 dark:ring-primary-700' : 'ring-gray-300 dark:ring-gray-600',
            item.removed ? 'opacity-55 grayscale' : '',
            dragIndex === index ? 'opacity-60' : '',
          ]"
          draggable="true"
          @dragstart="dragIndex = index"
          @dragend="dragIndex = -1"
          @dragover.prevent
          @drop.prevent="reorderTo(index)"
        >
          <div class="flex items-center justify-between gap-1 px-0.5 pb-1">
            <span class="rounded-full px-1.5 py-0.5 text-[10px] font-semibold" :class="badgeClass(item)">{{ badgeText(item) }}</span>
            <span v-if="item.rotation" class="text-[10px] font-semibold text-gray-600 dark:text-gray-300">{{ item.rotation }}°</span>
            <span class="text-[10px] font-medium tabular-nums text-gray-600 dark:text-gray-300">{{ index + 1 }}</span>
            <button
              type="button"
              class="grid h-5 w-5 place-items-center rounded-md text-[11px] ring-1 transition"
              :class="item.selected ? 'bg-primary-600 text-white ring-primary-600' : 'text-gray-500 ring-gray-300 hover:ring-primary-400 dark:text-gray-300 dark:ring-gray-600'"
              :aria-pressed="item.selected"
              :aria-label="`Position ${index + 1} ${item.selected ? 'abwählen' : 'für Mehrfach-Aktionen auswählen'}`"
              @click.stop="item.selected = !item.selected"
            >✓</button>
          </div>
          <button
            type="button"
            class="relative block h-32 w-full overflow-hidden rounded-lg bg-gray-100 outline-none transition focus-visible:ring-2 focus-visible:ring-primary-500 dark:bg-white/10"
            :aria-label="cardLabel(item, index)"
            :aria-current="item.uid === focusedUid ? 'true' : undefined"
            @click="focusItem(item)"
          >
            <img v-if="thumbSrc(item)" :src="thumbSrc(item) ?? undefined" alt="" class="mx-auto h-full object-contain" :style="thumbStyle(item)" />
            <span v-else class="grid h-full place-items-center text-3xl" aria-hidden="true">📄</span>
            <span v-if="item.removed" class="absolute inset-0 grid place-items-center bg-white/75 text-xs font-bold text-rose-700 dark:bg-gray-950/75 dark:text-rose-300">Entfernt</span>
          </button>

          <!-- Seiten-Aktionen direkt auf der Kachel (bei Zeigen/Fokus) — hält
               die obere Leiste und den Hauptbereich frei -->
          <div class="pointer-events-none absolute inset-x-0 bottom-2 flex justify-center gap-1 opacity-0 transition group-focus-within:opacity-100 group-hover:opacity-100">
            <button type="button" class="pointer-events-auto grid h-6 w-6 place-items-center rounded-md bg-white/95 text-xs text-gray-700 shadow ring-1 ring-gray-300 hover:text-primary-700 disabled:opacity-40 dark:bg-gray-800/95 dark:text-gray-200 dark:ring-gray-600" :disabled="index === 0" :aria-label="`Position ${index + 1} nach vorn`" title="Nach vorn" @click.stop="moveItem(index, -1)">↑</button>
            <button type="button" class="pointer-events-auto grid h-6 w-6 place-items-center rounded-md bg-white/95 text-xs text-gray-700 shadow ring-1 ring-gray-300 hover:text-primary-700 disabled:opacity-40 dark:bg-gray-800/95 dark:text-gray-200 dark:ring-gray-600" :disabled="index === items.length - 1" :aria-label="`Position ${index + 1} nach hinten`" title="Nach hinten" @click.stop="moveItem(index, 1)">↓</button>
            <button type="button" class="pointer-events-auto grid h-6 w-6 place-items-center rounded-md bg-white/95 text-xs text-gray-700 shadow ring-1 ring-gray-300 hover:text-primary-700 dark:bg-gray-800/95 dark:text-gray-200 dark:ring-gray-600" :aria-label="`Position ${index + 1} um 90 Grad drehen`" title="Drehen" @click.stop="rotateItem(item)">⟳</button>
            <button type="button" class="pointer-events-auto grid h-6 w-6 place-items-center rounded-md bg-white/95 text-xs text-gray-700 shadow ring-1 ring-gray-300 hover:text-primary-700 dark:bg-gray-800/95 dark:text-gray-200 dark:ring-gray-600" :aria-label="`Position ${index + 1} duplizieren`" title="Duplizieren" @click.stop="duplicateItemAt(index)">⧉</button>
            <button type="button" class="pointer-events-auto grid h-6 w-6 place-items-center rounded-md bg-white/95 text-xs shadow ring-1 ring-gray-300 dark:bg-gray-800/95 dark:ring-gray-600" :class="item.removed ? 'text-emerald-700 dark:text-emerald-300' : 'text-rose-700 dark:text-rose-300'" :aria-label="item.removed ? `Position ${index + 1} wiederherstellen` : `Position ${index + 1} entfernen`" :title="item.removed ? 'Wiederherstellen' : 'Entfernen'" @click.stop="item.removed = !item.removed">{{ item.removed ? '⤺' : '✕' }}</button>
          </div>
        </div>
        </div>
      </aside>

      <!-- Trennlinie Seitenübersicht ↔ Hauptbereich: ziehbar, per Tastatur mit Pfeiltasten -->
      <div
        v-if="items.length"
        class="w-1.5 shrink-0 cursor-col-resize bg-transparent transition hover:bg-primary-300/60 focus-visible:bg-primary-400 focus-visible:outline-none dark:hover:bg-primary-500/40"
        role="separator"
        aria-orientation="vertical"
        aria-label="Breite der Seitenübersicht ändern — Ziehen oder Pfeiltasten"
        tabindex="0"
        @pointerdown="startResize('sidebar', $event)"
        @keydown.left.prevent="resizeByKey('sidebar', -24)"
        @keydown.right.prevent="resizeByKey('sidebar', 24)"
      ></div>

      <!-- Große Seitenansicht -->
      <main class="min-w-0 flex-1 overflow-auto p-3 sm:p-4">
        <!-- Leerzustand: Ablagefläche mitten im Arbeitsplatz -->
        <div v-if="!docs.length" class="mx-auto flex h-full max-w-2xl items-center">
          <UiDropZone
            class="w-full"
            :active="isDragging"
            :accepted="false"
            :invalid="Boolean(errorText)"
            @drag-active="isDragging = $event"
            @drop="onDroppedFiles"
          >
            <div>
              <div class="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-primary-50 text-3xl text-primary-700 shadow-sm dark:bg-primary-500/15 dark:text-primary-300" aria-hidden="true">🛠️</div>
              <p class="mt-3 text-lg font-semibold text-gray-950 dark:text-white">PDFs hierher ziehen</p>
              <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">Mehrere Dateien gleichzeitig möglich — jede Seite wird einzeln bearbeitbar, das Ergebnis lässt sich an jedes Werkzeug übergeben.</p>
              <UiButton variant="primary" class="mt-4" :loading="loadingDocs > 0" @click="fileInput?.click()">Dateien auswählen</UiButton>
            </div>
          </UiDropZone>
        </div>

        <template v-else>
          <!-- Eingebettetes Werkzeug: läuft im Hauptbereich, die Werkbank bleibt -->
          <div v-if="embeddedToolId" class="space-y-3">
            <div class="flex flex-wrap items-center gap-2 rounded-xl bg-primary-50 px-3 py-2 text-sm dark:bg-primary-500/10">
              <span class="font-semibold text-primary-900 dark:text-primary-200">Modus: {{ embeddedLabel }}</span>
              <span class="text-xs text-primary-800/80 dark:text-primary-200/80">arbeitet auf dem übergebenen Stand — Ergebnis erscheint oben zur Übernahme</span>
              <span class="flex-1"></span>
              <UiButton size="sm" variant="secondary" @click="closeEmbedded">✕ Modus verlassen</UiButton>
            </div>
            <component :is="TOOL_COMPONENTS[embeddedToolId]" @back="closeEmbedded" />
          </div>

          <!-- Einheitliche Übernahme: beim Modus-Verlassen mit frischem Ergebnis
               direkt fragen, statt nur die Leiste oben anzubieten -->
          <div
            v-else-if="adoptPromptLabel && newestResult"
            class="mx-auto mt-8 max-w-lg space-y-3 rounded-2xl bg-white p-5 text-center shadow-apple ring-1 ring-primary-300 dark:bg-gray-900 dark:ring-primary-700"
          >
            <p class="font-semibold text-gray-950 dark:text-white">Ergebnis aus „{{ adoptPromptLabel }}“ liegt vor</p>
            <p class="text-sm text-gray-600 dark:text-gray-300">„{{ newestResult.name }}“ — wie soll es weitergehen?</p>
            <div class="flex flex-wrap justify-center gap-2">
              <UiButton variant="primary" :loading="loadingDocs > 0" @click="adoptFromPrompt(true)">Als neuen Stand laden</UiButton>
              <UiButton variant="secondary" :loading="loadingDocs > 0" @click="adoptFromPrompt(false)">Als Dokument hinzufügen</UiButton>
              <UiButton variant="ghost" @click="adoptPromptLabel = null">Später (bleibt oben angeboten)</UiButton>
            </div>
          </div>

          <div v-else-if="focusedItem" class="space-y-3">
            <!-- Schlanke Infozeile — die Seiten-Aktionen liegen als Overlay auf
                 den Kacheln der Übersicht, das spart hier eine ganze Zeile -->
            <div class="flex flex-wrap items-center gap-2 text-xs text-gray-600 dark:text-gray-300">
              <span class="rounded-full px-2.5 py-0.5 font-semibold" :class="badgeClass(focusedItem)">{{ badgeText(focusedItem) }}</span>
              <span v-if="focusedItem.rotation" class="font-medium">gedreht {{ focusedItem.rotation }}°</span>
              <span v-if="focusedItem.removed" class="font-semibold text-rose-700 dark:text-rose-300">entfernt</span>
            </div>

            <PdfViewer
              v-if="focusedItem.docUid !== null && focusedDocFile"
              v-model="viewerPage"
              :source="focusedDocFile"
              :rotation="focusedItem.rotation"
              @update:model-value="onViewerPageChange"
            />
            <div v-else class="grid h-[70vh] place-items-center rounded-[1.35rem] bg-white shadow-apple ring-1 ring-gray-300 dark:bg-gray-100 dark:ring-gray-600">
              <p class="text-sm font-medium text-gray-500">Leerseite ({{ focusedItem.rotation % 180 !== 0 ? 'A4 quer' : 'A4 hoch' }})</p>
            </div>
          </div>
          <p v-else class="mt-10 text-center text-sm text-gray-600 dark:text-gray-300">Links eine Seite anklicken, um sie groß anzuzeigen.</p>
        </template>

        <UiAlert v-if="errorText" tone="danger" class="mt-3">{{ errorText }}</UiAlert>
      </main>

      <!-- Trennlinie Hauptbereich ↔ Panel: ziehbar, per Tastatur mit Pfeiltasten -->
      <div
        v-if="activePanel"
        class="w-1.5 shrink-0 cursor-col-resize bg-transparent transition hover:bg-primary-300/60 focus-visible:bg-primary-400 focus-visible:outline-none dark:hover:bg-primary-500/40"
        role="separator"
        aria-orientation="vertical"
        aria-label="Breite des Panels ändern — Ziehen oder Pfeiltasten"
        tabindex="0"
        @pointerdown="startResize('panel', $event)"
        @keydown.left.prevent="resizeByKey('panel', 24)"
        @keydown.right.prevent="resizeByKey('panel', -24)"
      ></div>

      <!-- Seitenpanel: Transformation direkt auf dem aktuellen Stand -->
      <aside
        v-if="activePanel"
        class="flex shrink-0 flex-col gap-3 overflow-y-auto border-l border-gray-200 bg-white/80 p-3 dark:border-gray-700 dark:bg-gray-900/70"
        :style="{ width: panelWidth + 'px' }"
        :aria-label="`Panel: ${activePanel.title}`"
      >
        <div class="flex items-center justify-between gap-2">
          <h3 class="flex items-center gap-1.5 font-semibold text-gray-950 dark:text-white">
            <span aria-hidden="true">{{ activePanel.icon }}</span> {{ activePanel.title }}
          </h3>
          <button
            type="button"
            class="grid h-7 w-7 place-items-center rounded-lg text-gray-500 ring-1 ring-gray-300 transition hover:text-gray-900 dark:text-gray-300 dark:ring-gray-600 dark:hover:text-white"
            aria-label="Panel schließen"
            @click="activePanel = null"
          >×</button>
        </div>

        <p class="text-xs text-gray-600 dark:text-gray-300">
          Wird auf den aktuellen Stand ({{ activeItems.length }} Seiten) angewendet{{ activePanel.output === 'pdf' ? ' und ersetzt ihn — Rückgängig über ↩ in der Leiste.' : '.' }}
        </p>

        <label v-if="activePanel.variants?.length" class="block text-sm">
          <span class="mb-1 block font-medium text-gray-800 dark:text-gray-100">{{ activePanel.variantLabel ?? 'Aktion' }}</span>
          <select
            v-model="panelValues._variant"
            class="w-full rounded-xl bg-white px-3 py-2 text-sm text-gray-950 ring-1 ring-gray-400/70 focus:ring-2 focus:ring-primary-500 dark:bg-gray-900 dark:text-white dark:ring-gray-600"
          >
            <option v-for="variant in activePanel.variants" :key="variant.value" :value="variant.value">{{ variant.label }}</option>
          </select>
        </label>

        <label v-for="field in activePanel.fields" :key="field.name" class="block text-sm">
          <template v-if="field.type === 'checkbox'">
            <span class="flex items-center gap-2 font-medium text-gray-800 dark:text-gray-100">
              <input v-model="panelValues[field.name]" type="checkbox" class="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
              {{ field.label }}
            </span>
          </template>
          <template v-else>
            <span class="mb-1 block font-medium text-gray-800 dark:text-gray-100">{{ field.label }}<span v-if="field.required" aria-hidden="true"> *</span></span>
            <select
              v-if="field.type === 'select'"
              v-model="panelValues[field.name]"
              class="w-full rounded-xl bg-white px-3 py-2 text-sm text-gray-950 ring-1 ring-gray-400/70 focus:ring-2 focus:ring-primary-500 dark:bg-gray-900 dark:text-white dark:ring-gray-600"
            >
              <option v-for="option in field.options" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
            <input
              v-else
              v-model="panelValues[field.name]"
              :type="field.type"
              :placeholder="field.placeholder"
              :min="field.min" :max="field.max" :step="field.step"
              :required="field.required"
              class="w-full rounded-xl bg-white px-3 py-2 text-sm text-gray-950 ring-1 ring-gray-400/70 focus:ring-2 focus:ring-primary-500 dark:bg-gray-900 dark:text-white dark:ring-gray-600"
            />
          </template>
        </label>

        <UiButton variant="primary" :loading="panelBusy" :disabled="!activeItems.length" @click="applyPanel">
          {{ activePanel.applyLabel }}
        </UiButton>

        <pre
          v-if="panelReport"
          class="max-h-72 overflow-auto rounded-xl bg-gray-100 p-2 text-[11px] leading-relaxed text-gray-800 dark:bg-black/40 dark:text-gray-200"
        >{{ panelReport }}</pre>
      </aside>
    </div>

    <p class="sr-only" aria-live="polite" aria-atomic="true">{{ liveSummary }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import PdfViewer from '@/components/PdfViewer.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiDropZone from '@/components/ui/UiDropZone.vue'
import { useNotifications } from '@/composables/useNotifications'
import { usePdfTools } from '@/composables/usePdfTools'
import {
  docs, focusedUid, history, items, lastSeenResultId, nextUid, pushHistory,
  resetWorkbench, undoHistory, viewerPage, type WorkbenchItem,
} from '@/composables/useWorkbench'
import { apiPost, downloadBlob } from '@/lib/api'
import { currentFileLimit, formatFileSize, validatePdfFile } from '@/lib/fileValidation'
import { setPendingHandoff } from '@/lib/handoff'
import { results } from '@/lib/results'
import { TOOL_GROUPS, type ToolId } from '@/lib/toolCatalog'
import { TOOL_COMPONENTS } from '@/lib/toolComponents'
import { WORKBENCH_PANELS, type PanelSpec } from '@/lib/workbenchPanels'

defineEmits<{ (event: 'back'): void }>()

const MAX_DOCS = 50
const MAX_PAGES = 2000
const COMPOSE_TIMEOUT = 5 * 60 * 1000

const notifications = useNotifications()
const { getThumbnails } = usePdfTools()

const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const loadingDocs = ref(0)
const busy = ref(false)
const errorText = ref('')
const dragIndex = ref(-1)
const openMenuKey = ref<string | null>(null)
const menuStyle = ref<Record<string, string>>({})

/** Kategorienmenü am geklickten Knopf öffnen und an den Viewport klemmen:
 *  nie über einen Bildschirmrand hinaus, Resthöhe nach unten als Maximum. */
function toggleCategory(key: string, event: MouseEvent): void {
  if (openMenuKey.value === key) { openMenuKey.value = null; return }
  const anchor = (event.currentTarget as HTMLElement | null)?.getBoundingClientRect()
  const MENU_WIDTH = 288
  const left = anchor
    ? Math.max(8, Math.min(anchor.left, window.innerWidth - MENU_WIDTH - 8))
    : 8
  const top = anchor ? anchor.bottom + 6 : 56
  menuStyle.value = {
    left: `${Math.round(left)}px`,
    top: `${Math.round(top)}px`,
    maxHeight: `${Math.max(160, window.innerHeight - top - 12)}px`,
  }
  openMenuKey.value = key
}

const focusedItem = computed(() => items.value.find((item) => item.uid === focusedUid.value) ?? null)
const focusedDocFile = computed(() => {
  const item = focusedItem.value
  if (!item || item.docUid === null) return null
  return docs.value.find((doc) => doc.uid === item.docUid)?.file ?? null
})

function focusItem(item: WorkbenchItem): void {
  focusedUid.value = item.uid
  if (item.docUid !== null) viewerPage.value = item.page
}

/** Blättern im Viewer folgt der Zusammenstellung: existiert die Seite als
 *  Eintrag desselben Dokuments, wird sie fokussiert (erste Fundstelle). */
function onViewerPageChange(page: number): void {
  const current = focusedItem.value
  if (!current || current.docUid === null) return
  const match = items.value.find((item) => item.docUid === current.docUid && item.page === page)
  if (match) focusedUid.value = match.uid
}

function duplicateItemAt(index: number): void {
  const item = items.value[index]
  if (!item) return
  items.value.splice(index + 1, 0, { ...item, uid: nextUid(), selected: false })
}

// Hinter dem Vollbild-Arbeitsplatz darf die Seite nicht mitscrollen.
onMounted(() => { document.body.style.overflow = 'hidden' })
onBeforeUnmount(() => { document.body.style.overflow = '' })

const selectedItems = computed(() => items.value.filter((item) => item.selected))
const activeItems = computed(() => items.value.filter((item) => !item.removed))
const selectedActiveItems = computed(() => items.value.filter((item) => item.selected && !item.removed))
const liveSummary = computed(() =>
  `${items.value.length} Seiten in der Werkbank, ${selectedItems.value.length} ausgewählt, ${items.value.length - activeItems.value.length} entfernt.`)

/**
 * Vollständiges Werkzeugmenü: Übergabefähig sind Werkzeuge, deren Eingabe die
 * gemeinsame FileDrop-Fläche mit einzelner PDF ist — nur dort holt FileDrop
 * die Übergabe automatisch ab. Alle übrigen erscheinen ausgegraut mit dem
 * Grund, statt kommentarlos zu fehlen.
 */
const DISABLED_REASON: Record<string, string> = {
  workbench: 'Die Werkbank ist bereits geöffnet.',
  merge: 'Kann die Werkbank selbst — einfach weitere PDFs hinzufügen.',
  split: 'Kann die Werkbank selbst — Seiten auswählen und „Auswahl exportieren".',
  pageEditor: 'Kann die Werkbank selbst — Seiten ziehen, drehen, entfernen.',
  batch: 'Arbeitet mit vielen Dateien — Ergebnis erst herunterladen.',
  pruefakte: 'Arbeitet mit mehreren Akten-Dateien — Ergebnis erst herunterladen.',
  aiAssistant: 'Nur mit konfigurierter lokaler KI verfügbar.',
  imagesToPdf: 'Erwartet Bilder als Eingabe, keine PDF.',
  wordToPdf: 'Erwartet eine Word-Datei als Eingabe.',
  wordMerge: 'Erwartet Word-Dateien als Eingabe.',
  wordDiff: 'Erwartet Word-Dateien als Eingabe.',
  wordMeta: 'Erwartet eine Word-Datei als Eingabe.',
  excelMeta: 'Erwartet eine Excel-Datei als Eingabe.',
  officeToPdf: 'Erwartet eine Office-Datei als Eingabe.',
}

/** Kurztitel für die Menüleiste im Kopf — die vollen Titel stehen im Tooltip
 *  und als Überschrift im aufgeklappten Menü. */
const SHORT_TITLES: Record<string, string> = {
  bearbeiten: 'Bearbeiten',
  seiten: 'Seiten',
  umwandeln: 'Umwandeln',
  schuetzen: 'Schützen',
  stempel: 'Stempel',
  pruefen: 'Prüfen',
  office: 'Office',
}

// Die Rubrik „PDF-Editor" enthält nur die Werkbank selbst — die ist hier
// bereits offen und hat in der eigenen Menüleiste nichts zu suchen.
const menuGroups = computed(() => TOOL_GROUPS.filter((group) => group.key !== 'editor').map((group) => ({
  key: group.key,
  title: group.title,
  shortTitle: SHORT_TITLES[group.key] ?? group.title,
  icon: group.icon,
  tools: group.tools.map((tool) => ({
    id: tool.id as ToolId,
    label: tool.label,
    icon: tool.icon,
    reason: DISABLED_REASON[tool.id] ?? null,
    panel: Boolean(WORKBENCH_PANELS[tool.id]),
  })),
})))

const openMenu = computed(() => menuGroups.value.find((group) => group.key === openMenuKey.value) ?? null)

// ── Seitenpanels: Transformation direkt im Editor ────────────

const activePanel = ref<PanelSpec | null>(null)
const panelValues = ref<Record<string, string | number | boolean>>({})
const panelBusy = ref(false)
const panelReport = ref<string | null>(null)

function openTool(id: ToolId): void {
  openMenuKey.value = null
  const spec = WORKBENCH_PANELS[id]
  if (!spec) { void embedTool(id); return }
  embeddedToolId.value = null
  const values: Record<string, string | number | boolean> = {}
  for (const field of spec.fields) values[field.name] = field.default ?? (field.type === 'checkbox' ? false : '')
  if (spec.variants?.length) values._variant = spec.variants[0]!.value
  panelValues.value = values
  panelReport.value = null
  activePanel.value = spec
}

// ── Verschiebbare Trennlinien (Split-Panes) ──────────────────

const SIDEBAR_WIDTH_KEY = 'pdfapp_wb_sidebar_width'
const PANEL_WIDTH_KEY = 'pdfapp_wb_panel_width'

function storedWidth(key: string, fallback: number): number {
  const value = Number(localStorage.getItem(key))
  return Number.isFinite(value) && value > 0 ? value : fallback
}

const sidebarWidth = ref(storedWidth(SIDEBAR_WIDTH_KEY, 224))
const panelWidth = ref(storedWidth(PANEL_WIDTH_KEY, 320))

function clampWidth(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

/** Ziehen der Trennlinie: sidebar wächst nach rechts, das Panel nach links. */
function startResize(which: 'sidebar' | 'panel', event: PointerEvent): void {
  event.preventDefault()
  const startX = event.clientX
  const startWidth = which === 'sidebar' ? sidebarWidth.value : panelWidth.value
  const onMove = (move: PointerEvent) => {
    const delta = move.clientX - startX
    if (which === 'sidebar') sidebarWidth.value = clampWidth(startWidth + delta, 140, 480)
    else panelWidth.value = clampWidth(startWidth - delta, 240, 560)
  }
  const onUp = () => {
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
    try {
      localStorage.setItem(SIDEBAR_WIDTH_KEY, String(sidebarWidth.value))
      localStorage.setItem(PANEL_WIDTH_KEY, String(panelWidth.value))
    } catch { /* Ohne Speicher bleibt die Breite nur für die Sitzung. */ }
  }
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
}

function resizeByKey(which: 'sidebar' | 'panel', delta: number): void {
  if (which === 'sidebar') sidebarWidth.value = clampWidth(sidebarWidth.value + delta, 140, 480)
  else panelWidth.value = clampWidth(panelWidth.value + delta, 240, 560)
}

// ── Eingebettete Editoren: Werkzeug läuft im Hauptbereich ────

const embeddedToolId = ref<ToolId | null>(null)
const adoptPromptLabel = ref<string | null>(null)

/** Modus verlassen: liegt ein frisches Ergebnis vor, sofort die Übernahme
 *  anbieten — gleiches Gefühl wie bei den Panels, die direkt ersetzen. */
function closeEmbedded(): void {
  const label = embeddedLabel.value
  embeddedToolId.value = null
  adoptPromptLabel.value = newestResult.value ? label : null
}

async function adoptFromPrompt(replace: boolean): Promise<void> {
  adoptPromptLabel.value = null
  await adoptResult(replace)
}

const embeddedLabel = computed(() => {
  if (!embeddedToolId.value) return ''
  for (const group of TOOL_GROUPS) {
    const tool = group.tools.find((entry) => entry.id === embeddedToolId.value)
    if (tool) return tool.label
  }
  return embeddedToolId.value
})

/** Aktuellen Stand komponieren, in die Übergabe legen und das Werkzeug im
 *  Hauptbereich einbetten — statt die Werkbank zu verlassen. */
async function embedTool(target: ToolId): Promise<void> {
  if (!guardSubset(activeItems.value)) return
  busy.value = true
  errorText.value = ''
  try {
    const response = await requestCompose(activeItems.value)
    const blob = await response.blob()
    setPendingHandoff(new File([blob], 'werkbank.pdf', { type: 'application/pdf' }))
    markResultsSeen()
    activePanel.value = null
    embeddedToolId.value = target
  } catch (caught: unknown) {
    errorText.value = notifications.errorFromUnknown(caught, 'Die Übergabe ist fehlgeschlagen.')
  } finally {
    busy.value = false
  }
}

async function applyPanel(): Promise<void> {
  const spec = activePanel.value
  if (!spec || !guardSubset(activeItems.value)) return
  for (const field of spec.fields) {
    if (field.required && !String(panelValues.value[field.name] ?? '').trim()) {
      notifications.warning('Angabe fehlt', `Bitte „${field.label}" ausfüllen.`)
      return
    }
  }
  panelBusy.value = true
  errorText.value = ''
  try {
    const composed = await requestCompose(activeItems.value)
    const fd = new FormData()
    fd.append('file', new File([await composed.blob()], 'werkbank.pdf', { type: 'application/pdf' }))
    for (const field of spec.fields) fd.append(field.name, String(panelValues.value[field.name] ?? ''))
    const endpoint = spec.variants?.find((variant) => variant.value === panelValues.value._variant)?.endpoint ?? spec.endpoint
    const response = await apiPost(endpoint, fd, { timeout: COMPOSE_TIMEOUT })
    if (spec.output === 'report') {
      const data: unknown = await response.json()
      panelReport.value = JSON.stringify(data, null, 2)
      notifications.success(spec.title, 'Prüfung abgeschlossen — Bericht im Panel.')
    } else {
      const blob = await response.blob()
      pushHistory(`vor „${spec.title}" (${items.value.length} Seiten)`)
      resetWorkbench()
      markResultsSeen()
      await addFiles([new File([blob], `werkbank_${spec.id}.pdf`, { type: 'application/pdf' })])
      notifications.success(spec.title, 'Angewendet — der neue Stand liegt in der Werkbank. Rückgängig über ↩.')
    }
  } catch (caught: unknown) {
    errorText.value = notifications.errorFromUnknown(caught, `${spec.title} ist fehlgeschlagen.`)
  } finally {
    panelBusy.value = false
  }
}

function undo(): void {
  const label = undoHistory()
  if (label) notifications.success('Rückgängig', `Stand ${label} wiederhergestellt.`)
}

// ── Rückweg: Ergebnisse aus Werkzeugen übernehmen ────────────

const newestResult = computed(() => {
  const fresh = results.value.filter((entry) =>
    entry.id > lastSeenResultId.value
    && (entry.blob.type === 'application/pdf' || entry.name.toLowerCase().endsWith('.pdf')))
  return fresh.length ? fresh[fresh.length - 1] : null
})

function markResultsSeen(): void {
  lastSeenResultId.value = results.value.reduce((max, entry) => Math.max(max, entry.id), lastSeenResultId.value)
}

async function adoptResult(replace: boolean): Promise<void> {
  const entry = newestResult.value
  if (!entry) return
  if (replace) resetWorkbench()
  markResultsSeen()
  await addFiles([new File([entry.blob], entry.name, { type: 'application/pdf' })])
}

const DOC_BADGES = [
  'bg-blue-100 text-blue-800 dark:bg-blue-400/20 dark:text-blue-200',
  'bg-violet-100 text-violet-800 dark:bg-violet-400/20 dark:text-violet-200',
  'bg-emerald-100 text-emerald-800 dark:bg-emerald-400/20 dark:text-emerald-200',
  'bg-amber-100 text-amber-900 dark:bg-amber-400/20 dark:text-amber-200',
  'bg-rose-100 text-rose-800 dark:bg-rose-400/20 dark:text-rose-200',
  'bg-cyan-100 text-cyan-900 dark:bg-cyan-400/20 dark:text-cyan-200',
]

function docBadgeClass(index: number): string {
  return DOC_BADGES[index % DOC_BADGES.length] ?? DOC_BADGES[0]!
}

function docIndexOf(item: WorkbenchItem): number {
  return docs.value.findIndex((doc) => doc.uid === item.docUid)
}

function badgeClass(item: WorkbenchItem): string {
  if (item.docUid === null) return 'bg-gray-200 text-gray-800 dark:bg-white/15 dark:text-gray-200'
  return docBadgeClass(docIndexOf(item))
}

function badgeText(item: WorkbenchItem): string {
  if (item.docUid === null) return 'Leerseite'
  return `D${docIndexOf(item) + 1} · S${item.page}`
}

function thumbSrc(item: WorkbenchItem): string | null {
  if (item.docUid === null) return null
  const doc = docs.value.find((entry) => entry.uid === item.docUid)
  const thumb = doc?.thumbs[String(item.page)]
  return thumb ? `data:image/png;base64,${thumb}` : null
}

function thumbStyle(item: WorkbenchItem): Record<string, string> {
  if (!item.rotation) return {}
  const quer = item.rotation % 180 !== 0
  return { transform: `rotate(${item.rotation}deg)${quer ? ' scale(0.72)' : ''}` }
}

function cardLabel(item: WorkbenchItem, index: number): string {
  const source = item.docUid === null ? 'Leerseite' : `Dokument D${docIndexOf(item) + 1}, Seite ${item.page}`
  const state = `${item.rotation ? `, gedreht ${item.rotation} Grad` : ''}${item.removed ? ', entfernt' : ''}${item.selected ? ', ausgewählt' : ''}`
  return `Position ${index + 1} von ${items.value.length}: ${source}${state}. Eingabetaste zeigt die Seite groß an.`
}

function onFileSelect(event: Event): void {
  const element = event.target as HTMLInputElement
  const files = Array.from(element.files ?? [])
  element.value = ''
  if (files.length) void addFiles(files)
}

function onDroppedFiles(files: File[]): void {
  isDragging.value = false
  if (files.length) void addFiles(files)
}

async function addFiles(list: File[]): Promise<void> {
  errorText.value = ''
  for (const file of list) {
    if (docs.value.length >= MAX_DOCS) {
      notifications.warning('Dokumentlimit erreicht', `Maximal ${MAX_DOCS} Dokumente je Zusammenstellung.`)
      break
    }
    const validation = await validatePdfFile(file)
    if (!validation.valid) {
      notifications.error('Datei nicht angenommen', validation.message ?? `${file.name} ist keine gültige PDF-Datei.`)
      continue
    }
    if (file.size > currentFileLimit()) {
      notifications.error('Datei zu groß', `${file.name} ist ${formatFileSize(file.size)} groß. Zulässig sind maximal ${formatFileSize(currentFileLimit())}.`)
      continue
    }
    loadingDocs.value += 1
    try {
      const data = await getThumbnails(file) as { thumbnails: Record<string, string> }
      const pages = Object.keys(data.thumbnails).map(Number).sort((a, b) => a - b)
      if (!pages.length) {
        notifications.error('Keine Seiten', `${file.name} enthält keine lesbaren Seiten.`)
        continue
      }
      if (items.value.length + pages.length > MAX_PAGES) {
        notifications.warning('Seitenlimit erreicht', `Mit ${file.name} läge die Zusammenstellung über ${MAX_PAGES} Seiten.`)
        continue
      }
      const docUid = nextUid()
      docs.value.push({ uid: docUid, file, label: file.name, pages: pages.length, thumbs: data.thumbnails })
      const newItems = pages.map((page) => ({
        uid: nextUid(), docUid, page, rotation: 0, removed: false, selected: false,
      }))
      items.value.push(...newItems)
      if (focusedUid.value === null && newItems[0]) focusItem(newItems[0])
      notifications.success('Dokument geladen', `${file.name}: ${pages.length} Seite(n) in der Werkbank.`)
    } catch (caught: unknown) {
      errorText.value = notifications.errorFromUnknown(caught, `Die Seitenvorschau für ${file.name} konnte nicht erzeugt werden.`)
    } finally {
      loadingDocs.value -= 1
    }
  }
}

function removeDoc(uid: number): void {
  docs.value = docs.value.filter((doc) => doc.uid !== uid)
  items.value = items.value.filter((item) => item.docUid !== uid)
  if (focusedItem.value === null) focusedUid.value = items.value[0]?.uid ?? null
}

function selectAll(selected: boolean): void {
  items.value.forEach((item) => { item.selected = selected })
}

function rotateSelection(delta: number): void {
  selectedItems.value.forEach((item) => { item.rotation = ((item.rotation + delta) % 360 + 360) % 360 })
}

function rotateItem(item: WorkbenchItem): void {
  item.rotation = (item.rotation + 90) % 360
}

function removeSelection(removed: boolean): void {
  selectedItems.value.forEach((item) => { item.removed = removed })
}

function duplicateSelection(): void {
  // Rückwärts, damit die Einfüge-Indizes durch frühere Duplikate nicht verrutschen.
  for (let index = items.value.length - 1; index >= 0; index -= 1) {
    const item = items.value[index]
    if (item?.selected) items.value.splice(index + 1, 0, { ...item, uid: nextUid(), selected: false })
  }
}

function insertBlank(): void {
  if (items.value.length >= MAX_PAGES) return
  const lastSelected = items.value.map((item) => item.selected).lastIndexOf(true)
  const at = lastSelected >= 0 ? lastSelected + 1 : items.value.length
  const blank: WorkbenchItem = { uid: nextUid(), docUid: null, page: 0, rotation: 0, removed: false, selected: false }
  items.value.splice(at, 0, blank)
  focusedUid.value = blank.uid
}

function moveItem(index: number, direction: number): void {
  const target = index + direction
  if (target < 0 || target >= items.value.length) return
  const [moved] = items.value.splice(index, 1)
  if (moved) items.value.splice(target, 0, moved)
}

function reorderTo(targetIndex: number): void {
  if (dragIndex.value < 0 || dragIndex.value === targetIndex) return
  const [moved] = items.value.splice(dragIndex.value, 1)
  if (moved) items.value.splice(targetIndex, 0, moved)
  dragIndex.value = -1
}

/** Sendet nur die tatsächlich referenzierten Dokumente und nummeriert den Plan darauf um. */
async function requestCompose(subset: WorkbenchItem[]): Promise<Response> {
  const usedDocUids = [...new Set(subset.filter((item) => item.docUid !== null).map((item) => item.docUid as number))]
  const indexByUid = new Map<number, number>()
  const fd = new FormData()
  usedDocUids.forEach((uid, index) => {
    indexByUid.set(uid, index)
    const doc = docs.value.find((entry) => entry.uid === uid)
    if (doc) fd.append('files', doc.file)
  })
  const plan = subset.map((item) => {
    if (item.docUid === null) {
      const quer = item.rotation % 180 !== 0
      return quer ? { blank: true, width: 841.89, height: 595.28 } : { blank: true, width: 595.28, height: 841.89 }
    }
    const entry: Record<string, unknown> = { file: indexByUid.get(item.docUid), page: item.page }
    if (item.rotation) entry.rotate = item.rotation
    return entry
  })
  fd.append('plan', JSON.stringify(plan))
  return apiPost('/api/pdf-tools/compose', fd, { timeout: COMPOSE_TIMEOUT })
}

function guardSubset(subset: WorkbenchItem[]): boolean {
  if (!subset.length) return false
  if (!subset.some((item) => item.docUid !== null)) {
    errorText.value = 'Mindestens eine Dokumentseite wird benötigt — nur Leerseiten ergeben keine Zusammenstellung.'
    return false
  }
  return true
}

// ── Ergebnis speichern: Name erfragen, Muster JJJJMMTT_Name.pdf ─

const nameDialogSubset = ref<'alle' | 'auswahl' | null>(null)
const exportName = ref('Werkbank')

function dateStamp(): string {
  const now = new Date()
  return `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
}

function sanitizeName(name: string): string {
  const clean = name.replace(/[\\/:*?"<>|]/g, '').trim()
  return clean || 'Werkbank'
}

const exportFilename = computed(() => `${dateStamp()}_${sanitizeName(exportName.value)}.pdf`)

async function confirmExport(): Promise<void> {
  const subset = nameDialogSubset.value === 'auswahl' ? selectedActiveItems.value : activeItems.value
  nameDialogSubset.value = null
  await composeAndDownload(subset, exportFilename.value)
}

async function composeAndDownload(subset: WorkbenchItem[], filename: string): Promise<void> {
  if (!guardSubset(subset)) return
  busy.value = true
  errorText.value = ''
  try {
    const response = await requestCompose(subset)
    await downloadBlob(response, filename, { forceName: true })
  } catch (caught: unknown) {
    errorText.value = notifications.errorFromUnknown(caught, 'Die Zusammenstellung ist fehlgeschlagen.')
  } finally {
    busy.value = false
  }
}

</script>
