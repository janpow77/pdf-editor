<template>
  <div class="max-w-3xl mx-auto px-4 py-8 prose dark:prose-invert">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-4">Impressum</h1>
    <div class="space-y-4 text-gray-700 dark:text-gray-300 text-sm leading-relaxed">
      <p><strong>Angaben gemäß § 5 DDG</strong></p>
      <p>
        Jan Riener<br />
        Am Amalienbad 6<br />
        76669 Bad Schönborn-Bad Langenbrücken
      </p>
      <p>
        Kontakt:
        <a
          href="mailto:jan.riener@googlemail.com"
          class="text-primary-700 dark:text-primary-400 underline hover:no-underline"
        >jan.riener@googlemail.com</a>
      </p>
      <p>
        Verantwortlich für den Inhalt: Jan Riener, Anschrift wie oben.
      </p>

      <p><strong>Art des Angebots</strong></p>
      <p>
        Dieses Angebot ist privat betrieben, kostenlos und ohne
        Gewinnerzielungsabsicht. Es besteht keine Verbindung zu einer Behörde
        oder einem Unternehmen.
      </p>

      <p><strong>Haftung für Inhalte und Verarbeitungsergebnisse</strong></p>
      <p>
        Die angebotenen Werkzeuge verarbeiten Ihre Dateien automatisiert. Für
        die Richtigkeit und Vollständigkeit der Ergebnisse wird keine Haftung
        übernommen — prüfen Sie jedes Ergebnis, bevor Sie es weiterverwenden.
        Das gilt besonders für das Schwärzen von Inhalten, für digitale
        Signaturen und für Texte, die von einem Sprachmodell erzeugt wurden.
      </p>
      <p>
        Da keine Datei gespeichert wird, kann eine verarbeitete Datei nach
        Abschluss der Verarbeitung nicht wiederhergestellt werden. Bewahren Sie
        Ihre Ausgangsdateien auf.
      </p>

      <p><strong>Verwendete Software</strong></p>
      <p>
        Diese Anwendung nutzt freie Software, darunter Komponenten unter der
        GNU Affero General Public License. Die vollständige Liste der
        Komponenten mit Lizenzen und der Zugang zum Quelltext stehen unter
        <RouterLink to="/lizenzen" class="text-primary-700 dark:text-primary-400 underline hover:no-underline">Open Source</RouterLink>.
      </p>

      <p><strong>Barrierefreiheit</strong></p>
      <p>
        Zum Stand der Barrierefreiheit und zu den bekannten Grenzen:
        <RouterLink to="/barrierefreiheit" class="text-primary-700 dark:text-primary-400 underline hover:no-underline">Erklärung zur Barrierefreiheit</RouterLink>.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>
