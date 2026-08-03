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
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Arbeitsstand der Editoren</h2>
        <p>
          Damit Sie eine Bearbeitung unterbrechen und später fortsetzen können, legen die
          Editoren (Text bearbeiten, Anmerkungen, Formular-Designer) den Arbeitsstand —
          also die Arbeitskopie des Dokuments und die noch nicht angewandten Änderungen —
          <strong>in Ihrem Browser</strong> ab (IndexedDB, auf Ihrem Gerät). Diese Daten
          werden nicht an den Server übertragen. Sie können sie jederzeit über
          „Browser-Sicherung löschen" im jeweiligen Werkzeug entfernen; das Löschen der
          Browserdaten entfernt sie ebenfalls. Alternativ speichern Sie den Arbeitsstand
          als Datei auf Ihrem Rechner und laden ihn beim Weiterarbeiten wieder hoch.
        </p>
      </section>

      <section>
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">KI-Funktionen (optional)</h2>
        <p>
          Sofern der Betreiber die KI-Funktionen (Zusammenfassen, Fragen zum Dokument)
          aktiviert hat, wird der Textinhalt des Dokuments zur Beantwortung an ein
          Sprachmodell auf <strong>eigener Infrastruktur des Betreibers</strong> übertragen —
          nicht an externe Cloud- oder KI-Anbieter. Auch dort erfolgt die Verarbeitung nur
          transient im Arbeitsspeicher; weder Dokumentinhalte noch Fragen oder Antworten
          werden gespeichert.
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
        <p>
          Verantwortlich im Sinne von Art. 4 Nr. 7 DSGVO:
        </p>
        <p>
          Jan Riener<br />
          Am Amalienbad 6<br />
          76669 Bad Schönborn-Bad Langenbrücken<br />
          <a
            href="mailto:jan.riener@googlemail.com"
            class="text-primary-700 dark:text-primary-400 underline hover:no-underline"
          >jan.riener@googlemail.com</a>
        </p>
        <p>
          Ein Datenschutzbeauftragter ist nicht bestellt; die Voraussetzungen
          nach Art. 37 DSGVO und § 38 BDSG liegen bei diesem privat betriebenen
          Angebot nicht vor.
        </p>
      </section>

      <section>
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Ihre Rechte</h2>
        <p>
          Sie haben das Recht auf Auskunft (Art. 15 DSGVO), Berichtigung
          (Art. 16), Löschung (Art. 17), Einschränkung der Verarbeitung
          (Art. 18), Datenübertragbarkeit (Art. 20) und Widerspruch
          (Art. 21). Wenden Sie sich dafür an die oben genannte Adresse.
        </p>
        <p>
          Unabhängig davon können Sie sich bei einer Aufsichtsbehörde
          beschweren (Art. 77 DSGVO). Zuständig ist der Landesbeauftragte für
          den Datenschutz und die Informationsfreiheit Baden-Württemberg,
          Lautenschlagerstraße 20, 70173 Stuttgart.
        </p>
        <p>
          Für die Werkzeuge selbst laufen diese Rechte weitgehend ins Leere —
          und das ist beabsichtigt: Ihre Dateien werden nicht gespeichert, es
          gibt also nichts, worüber Auskunft zu erteilen oder was zu löschen
          wäre. Praktisch bedeutsam werden die Rechte nur, wenn Sie ein
          freiwilliges Konto anlegen.
        </p>
      </section>
    </div>
  </div>
</template>
