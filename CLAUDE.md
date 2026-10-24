## Desarrollo

El programa nuevo vive en `src/mgitems/` (núcleo en Python, interfaz web en `src/mgitems/ui/`). La carpeta `Codificador Base64 MG/` es el programa viejo, que se retira en el issue #10.

- Instalar: `python -m venv .venv` y `.venv/Scripts/python -m pip install -e ".[dev]"`
- FFDec y Java (imágenes de los Items): `.venv/Scripts/python scripts/obtener_binarios.py` los descarga a `vendor/` (no se versiona)
- Abrir el programa: `.venv/Scripts/python -m mgitems`
- Pruebas: `.venv/Scripts/python -m pytest`
- Instalador: `.venv/Scripts/python scripts/armar_instalador.py` arma `dist/MGItems/` (PyInstaller) y, si está Inno Setup 6, `dist/MGItems-Setup-<versión>.exe`

Las pruebas usan una sola costura: la API del núcleo (`Nucleo`). La interfaz no tiene lógica de dominio y no se prueba automáticamente.

## Agent skills

### Issue tracker

Issues y specs viven en GitHub Issues (CapitanBeto1/Encoder-Base64-Mundo-Gaturro-Items-SWF), vía `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

Etiquetas por defecto: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: un `GLOSSARY.md` + `docs/adr/` en la raíz. See `docs/agents/domain.md`.
