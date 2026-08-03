<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-4">
      Erklärung zur Barrierefreiheit
    </h1>

    <div class="space-y-6 text-sm leading-relaxed text-gray-700 dark:text-gray-300">
      <div class="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
        <p class="text-blue-900 dark:text-blue-200">
          Diese Erklärung wird <strong>freiwillig</strong> abgegeben. Das
          Angebot wird privat betrieben; die Pflicht aus § 12b
          Behindertengleichstellungsgesetz und der BITV 2.0 trifft öffentliche
          Stellen und gilt hier nicht. Der Anspruch, ohne Barrieren nutzbar zu
          sein, gilt trotzdem — und was noch fehlt, steht weiter unten.
        </p>
      </div>

      <section>
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Geltungsbereich</h2>
        <p>
          Diese Erklärung gilt für die unter dieser Adresse erreichbare
          Web-Anwendung mit ihren PDF-, Word- und Excel-Werkzeugen.
        </p>
      </section>

      <section>
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Stand der Vereinbarkeit</h2>
        <p>
          Das Angebot ist mit den Anforderungen der WCAG 2.1 auf Stufe AA
          <strong>teilweise vereinbar</strong>. „Teilweise", weil die Prüfung
          nicht vollständig war — nicht, weil bekannte Verstöße bestehen
          blieben.
        </p>
      </section>

      <section>
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Wie geprüft wurde</h2>
        <p>
          Automatisiert mit axe-core gegen die Regelsätze WCAG 2.0 A/AA und
          2.1 A/AA, jeweils im hellen und im dunklen Farbschema, über
          Startseite, Anmeldung, Registrierung, Datenschutzerklärung,
          Passwort-Zurücksetzung, Lizenzseite, Impressum und die
          Karussell-Ansicht. Ergebnis: <strong>keine Verstöße</strong>.
        </p>
        <p>Ergänzend geprüft:</p>
        <ul class="list-disc pl-5 space-y-1">
          <li>Der Sprunglink „Zum Hauptinhalt springen" ist das erste Tab-Ziel und setzt den Fokus tatsächlich in den Hauptbereich.</li>
          <li>Bei aktivierter Systemeinstellung „Bewegung reduzieren" laufen keine Übergänge und keine Kartenrotation (WCAG 2.3.3).</li>
          <li>Der Tastaturfokus ist überall sichtbar.</li>
          <li>Farbkontraste erreichen mindestens 4,5:1; Links im Fließtext sind zusätzlich unterstrichen und nicht allein durch Farbe erkennbar.</li>
        </ul>
      </section>

      <section>
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Was nicht barrierefrei ist</h2>

        <p class="font-medium text-gray-900 dark:text-white">Nicht abschließend geprüft</p>
        <ul class="list-disc pl-5 space-y-1">
          <li>
            <strong>Kein Test mit Screenreader.</strong> Eine automatisierte
            Prüfung findet erfahrungsgemäß etwa die Hälfte der Barrieren.
            Sinnvolle Vorlesereihenfolge, verständliche Beschriftungen und
            Statusmeldungen lassen sich nur im tatsächlichen Gebrauch
            beurteilen. Dieser Test steht aus.
          </li>
          <li>
            <strong>Die einzelnen Werkzeugoberflächen wurden nicht
            durchgeprüft.</strong> Die automatisierte Prüfung umfasste die
            Übersichts- und Informationsseiten. Die Bedienoberflächen der
            Werkzeuge — insbesondere die Editoren mit Zeichen- und
            Ziehflächen — sind darin nicht enthalten.
          </li>
        </ul>

        <p class="font-medium text-gray-900 dark:text-white mt-4">Bekannte Grenzen</p>
        <ul class="list-disc pl-5 space-y-1">
          <li>
            <strong>Zeichnen mit der Maus.</strong> Anmerkungen und
            Formularfelder werden auf der Seite aufgezogen. Für diese
            Tätigkeiten gibt es derzeit keine gleichwertige Bedienung über die
            Tastatur.
          </li>
          <li>
            <strong>Erzeugte PDF-Dateien sind nicht getaggt.</strong> Die
            Anwendung erzeugt keine PDF/UA-konformen Dokumente; für ein
            Screenreader-taugliches PDF braucht es eine Strukturmarkierung, die
            die eingesetzte Bibliothek nicht liefert. Ein hochgeladenes
            Dokument behält seine vorhandene Struktur, gewinnt aber keine
            hinzu.
          </li>
          <li>
            <strong>Gescannte Dokumente ohne Textebene</strong> bleiben für
            Screenreader unlesbar. Das Werkzeug „OCR" legt eine Textebene an
            und behebt das — sofern Texterkennung auf dem Server verfügbar ist.
          </li>
        </ul>
      </section>

      <section>
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Rückmeldung</h2>
        <p>
          Sind Ihnen Barrieren aufgefallen, oder brauchen Sie eine Auskunft in
          zugänglicher Form? Schreiben Sie an
          <a
            href="mailto:jan.riener@vwvg.de"
            class="text-primary-700 dark:text-primary-400 underline hover:no-underline"
          >jan.riener@vwvg.de</a>.
          Bitte nennen Sie die Seite und, wenn möglich, das verwendete
          Hilfsmittel — damit lässt sich der Fehler nachstellen.
        </p>
        <p>
          Eine Schlichtungsstelle nach § 16 BGG steht für dieses Angebot nicht
          zur Verfügung; sie ist für öffentliche Stellen des Bundes
          eingerichtet.
        </p>
      </section>

      <section>
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Erstellung dieser Erklärung</h2>
        <p>
          Erstellt am 1. August 2026 auf Grundlage einer Selbstbewertung mit
          den oben beschriebenen automatisierten Prüfungen.
        </p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
// Reine Inhaltsseite — kein Zustand, keine Datenabfrage.
</script>
