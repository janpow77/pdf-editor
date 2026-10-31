<!-- graphify-kira:arch:start -->
## 🗺 Architektur (auto-generiert von graphify-kira)

Code-Graph: 2326 Knoten, 4160 Kanten, 0 Zyklen. Details: [`ARCHITEKTUR.md`](ARCHITEKTUR.md).

**Module:** pdf_tools.py, pdf_extras_service.py, PdfTextEditor.vue, PdfWorkbench.vue, ToolGrid.vue, test_restpunkte.py, pdf_extras.py, UiAlert.vue.

**Zentrale Bausteine (vorsichtig ändern):** `PdfToolResult`, `make_pdf()`, `PdfWorkbench.vue`, `PdfAnnotate.vue`, `PdfFormDesigner.vue`, `PdfTextEditor.vue`.

**Fachagenten (ohne Aufforderung einsetzen):** `@code-audit` vor Merge/PR unabhängig prüfen · `@ops` bei Migrations-, Container- oder Deploy-Fehlern zuerst · `@frontend-e2e` nach UI-Änderungen, bevor sie als fertig gelten · `@ux-review` nach Layout-/Style-Änderungen.

**Empfohlene Spezialisten:** `/deutsche-formulierung`, `@code-audit`, `/auto-verify`, `@ops`, `/db-migration-helper`, `/docker-debug`, `/cross-project-health`, `@frontend-e2e`, `@ux-review`, `/modern-gui-builder` … +3 weitere via `/graphify`.

Vor Refactorings die Abhängigkeiten über den **graphify-MCP** prüfen („Was hängt an `<datei>`?"). Voller Projekt-Überblick: `/graphify`.
<!-- graphify-kira:arch:end -->
