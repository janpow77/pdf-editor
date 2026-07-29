<template>
  <div class="max-w-3xl mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Datenschutzerklärung</h1>
    <div class="space-y-6 text-sm leading-relaxed text-gray-700 dark:text-gray-300">
      <section>
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Das Wichtigste in Kürze</h2>
        <ul class="list-disc pl-5 space-y-1">
          <li>Die Nutzung ist <strong>kostenlos</strong> und ohne Registrierung möglich.</li>
          <li>
            Hochgeladene Dateien werden <strong>ausschließlich im Arbeitsspeicher</strong> des
            Servers verarbeitet und nach Abschluss der Anfrage sofort verworfen. Es gibt keine
            Datenbank und keine dauerhafte Ablage.
          </li>
          <li>Es werden keine Analyse-Cookies und keine Tracking-Dienste eingesetzt.</li>
        </ul>
      </section>

      <section>
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Verarbeitung Ihrer Dateien</h2>
        <p>
          Dateien, die Sie in ein Werkzeug laden, werden zur Verarbeitung an unseren Server
          übertragen (TLS-verschlüsselt), dort im Arbeitsspeicher bearbeitet und als Ergebnis
          direkt an Ihren Browser zurückgeliefert. Weder die Originaldatei noch das Ergebnis
          werden gespeichert oder protokolliert. Die Ergebnisliste für ZIP-Download und
          Mailversand existiert nur in Ihrem Browser und wird beim Neuladen der Seite geleert.
        </p>
      </section>

      <section>
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Mailversand</h2>
        <p>
          Wenn Sie Ergebnisse per E-Mail versenden, wird die angegebene Empfängeradresse
          ausschließlich für diesen einen Versand verwendet. Sie wird weder gespeichert noch
          protokolliert. Die Dateien werden als Anhang übertragen und danach serverseitig
          verworfen.
        </p>
      </section>

      <section>
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Technisch notwendige Daten</h2>
        <p>
          Zum Schutz vor Missbrauch (Rate-Limiting) wird die IP-Adresse während der Anfrage
          kurzzeitig im Arbeitsspeicher verarbeitet. Der Dienst wird über Cloudflare
          ausgeliefert; dabei gelten zusätzlich die Datenschutzhinweise von Cloudflare.
        </p>
      </section>

      <section>
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Benutzerkonten (optional)</h2>
        <p class="mb-2">
          Die Werkzeuge sind vollständig ohne Konto nutzbar. Wer sich freiwillig
          registriert, erhält höhere Limits und kann Werkzeug-Voreinstellungen speichern.
          In diesem Fall speichern wir ausschließlich:
        </p>
        <ul class="list-disc pl-5 space-y-1 mb-2">
          <li>Ihre E-Mail-Adresse (als Anmeldename),</li>
          <li>Ihr Passwort als bcrypt-Hash (niemals im Klartext),</li>
          <li>Ihre Werkzeug-Voreinstellungen (z.&nbsp;B. Standard-OCR-Sprache),</li>
          <li>Zeitstempel der Kontoerstellung und der letzten Anmeldung.</li>
        </ul>
        <p class="mb-2">
          Rechtsgrundlage ist Art. 6 Abs. 1 lit. b DSGVO (Bereitstellung der von Ihnen
          gewünschten Konto-Funktionen). Die Einwilligung erfolgt ausdrücklich bei der
          Registrierung. <strong>Auch mit Konto werden Ihre verarbeiteten Dateien
          niemals gespeichert.</strong>
        </p>
        <p>
          Sie können Ihr Konto jederzeit selbst auf der Konto-Seite endgültig löschen
          (Art. 17 DSGVO); dabei werden alle Kontodaten unwiderruflich entfernt.
        </p>
      </section>

      <section>
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Verantwortlicher</h2>
        <!-- TODO: Vor Veröffentlichung ausfüllen -->
        <p>[Name und Kontaktdaten des Verantwortlichen — siehe Impressum]</p>
      </section>
    </div>
  </div>
</template>
