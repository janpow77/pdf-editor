# Architektur — pdf-editor

_Automatisch generiert von graphify-kira aus dem Code-Graphen. Nicht von Hand editieren — wird beim nächsten Lauf überschrieben._

**Umfang:** 2326 Knoten, 4160 Kanten, 20 größere Module, 0 zirkuläre Abhängigkeiten.

## Modulkarte

- **pdf_tools.py** (70): `pdf_tools.py`, `UploadFile`, `pdf_tools_service.py`, `BaseModel`, `StreamingResponse`
- **pdf_extras_service.py** (62): `Any`, `pdf_backend.py`, `pdf_extras_service.py`, `PdfToolResult`
- **PdfTextEditor.vue** (56): `PdfTextEditor.vue`
- **PdfWorkbench.vue** (54): `PdfWorkbench.vue`
- **ToolGrid.vue** (51): `ToolGrid.vue`, `LandingView.vue`
- **test_restpunkte.py** (48): `jobs.py`, `test_auth.py`, `test_restpunkte.py`
- **pdf_extras.py** (44): `pdf_extras.py`, `pdf_extras_service.py`, `Request`, `UploadFile`
- **UiAlert.vue** (44): `PdfClean.vue`, `PdfExport.vue`, `PdfInsertBlank.vue`, `PdfPdfa.vue`, `PdfPermissions.vue`
- **make_pdf** (41): `__init__.py`, `test_pdf_extras.py`, `test_pdf_more.py`, `test_smoke.py`, `PdfSignImage.vue`
- **PdfFormDesigner.vue** (41): `PdfFormDesigner.vue`
- **auth.py** (39): `auth.py`, `Request`, `Session`, `clock.py`, `models.py`
- **PdfAnnotate.vue** (38): `PdfAnnotate.vue`
- **PdfCompare.vue** (38): `PdfCompare.vue`, `jobs.ts`
- **pdf_editor.py** (36): `pdf_editor.py`, `StreamingResponse`, `UploadFile`, `pdf_editor_service.py`
- **pdf_more.py** (36): `pdf_more.py`, `UploadFile`
- **test_tool_access.py** (33): `tool_access.py`, `tool_catalog.py`, `test_tool_access.py`
- **test_form_advanced.py** (33): `test_form_advanced.py`
- **User** (31): `admin.py`, `Session`, `auth.py`, `deps.py`, `models.py`
- **main.py** (31): `auth.py`, `deps.py`, `Request`, `__init__.py`, `mail.py`
- **PdfToolsService** (31): `pdf_tools_service.py`

## Zentrale Bausteine (God Nodes)

_Hohe Zentralität ist nicht automatisch ein Defekt (zentrale Stores/Modelle sind oft legitim). Konkrete Refactoring-Prioritäten siehe Optimierungs-Report._

- `PdfToolResult (backend/app/services/pdf_tools_service.py)` — Grad 52 (ein 52/aus 0)
- `make_pdf() (backend/tests/test_smoke.py)` — Grad 60 (ein 60/aus 0)
- `PdfWorkbench.vue (frontend/src/components/tools/PdfWorkbench.vue)` — Grad 79 (ein 0/aus 79)
- `PdfAnnotate.vue (frontend/src/components/tools/PdfAnnotate.vue)` — Grad 77 (ein 0/aus 77)
- `PdfFormDesigner.vue (frontend/src/components/tools/PdfFormDesigner.vue)` — Grad 72 (ein 0/aus 72)
- `PdfTextEditor.vue (frontend/src/components/tools/PdfTextEditor.vue)` — Grad 70 (ein 0/aus 70)
- `main.py (backend/app/main.py)` — Grad 60 (ein 19/aus 41)
- `FileDrop.vue (frontend/src/components/FileDrop.vue)` — Grad 54 (ein 40/aus 14)
- `UiAlert.vue (frontend/src/components/ui/UiAlert.vue)` — Grad 49 (ein 46/aus 3)
- `UiButton.vue (frontend/src/components/ui/UiButton.vue)` — Grad 48 (ein 46/aus 2)

## Schnittstellen / Brücken (Betweenness)

- `main.py (backend/app/main.py)` — Betweenness 0.003
- `pdf_extras.py (backend/app/api/pdf_extras.py)` — Betweenness 0.001
- `test_form_advanced.py (backend/tests/test_form_advanced.py)` — Betweenness 0.001
- `test_pdf_tools_werkzeuge.py (backend/tests/test_pdf_tools_werkzeuge.py)` — Betweenness 0.001
- `test_redact_fonts.py (backend/tests/test_redact_fonts.py)` — Betweenness 0.001
- `App.vue (frontend/src/App.vue)` — Betweenness 0.001
- `PdfToolsService (backend/app/services/pdf_tools_service.py)` — Betweenness 0.000
- `auth.py (backend/app/api/auth.py)` — Betweenness 0.000
- `get_pdf_tools() (backend/app/services/pdf_tools_service.py)` — Betweenness 0.000
- `PdfExtrasService (backend/app/services/pdf_extras_service.py)` — Betweenness 0.000

## Empfohlene Spezialisten

Passend zu Stack/Domäne dieses Projekts (Claude-Code-Agents/Skills):

`/deutsche-formulierung`, `@code-audit`, `/auto-verify`, `@ops`, `/db-migration-helper`, `/docker-debug`, `/cross-project-health`, `@frontend-e2e`, `@ux-review`, `/modern-gui-builder`, `/ux-completeness-check`, `/vue3-gui-builder`, `/excel-pro-design`.

## Hinweis für Änderungen

Vor dem Ändern eines zentralen Bausteins die Abhängigen prüfen — am schnellsten über den **graphify-MCP** (globaler Graph): „Was hängt an `<datei>`?". Brücken-Knoten stabil halten.

