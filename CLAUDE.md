## Desarrollo

El programa vive en `src/mgitems/` (núcleo en Python, interfaz web en `src/mgitems/ui/`). Los scripts de armado (catálogo, binarios de terceros, instalador) están en `scripts/`.

- Instalar: `python -m venv .venv` y `.venv/Scripts/python -m pip install -e ".[dev,imagen]"`. `imagen` (onnxruntime, para «Buscar por imagen») no existe para todos los Python: si pip no lo encuentra, `.[dev]` instala todo lo demás.
- FFDec y Java (imágenes de los Items): `.venv/Scripts/python scripts/obtener_binarios.py` los descarga a `vendor/` (no se versiona)
- Abrir el programa: `.venv/Scripts/python -m mgitems`
- Pruebas: `.venv/Scripts/python -m pytest`
- Instalador: `.venv/Scripts/python scripts/armar_instalador.py` arma `dist/MGItems/` (PyInstaller) y, si está Inno Setup 6, `dist/MGItems-Setup-<versión>.exe`

Las pruebas usan una sola costura: la API del núcleo (`Nucleo`). La interfaz no tiene lógica de dominio y no se prueba automáticamente.

## Cómo está organizado el código

Al cambiar código, mantené esta forma (el porqué de cada punto: `docs/adr/0008-estructura-del-codigo.md`):

- **Archivos chicos, uno por función**: cada archivo queda por debajo de ~1000 líneas; cuando uno crece, partilo por función.
- **Núcleo** (`src/mgitems/nucleo/`): cada método va a la parte de su función (`swfs`, `trucar`, `acciones`, `npcs`, `busqueda`…); el estado que comparten las partes se arma solo en `Nucleo.__init__`; lo que usa una sola parte vive en esa parte (`_comun.py`, solo lo que usan varias).
- **Guardados** («Mis …»): un tipo nuevo es una entrada en `guardados.TIPOS` y otra en `PESTANA[…].guardados`.
- **Puente** (`app.py`): expone el núcleo tal cual; lo que recibe una ruta (`ruta`, `carpeta`) lo pide la ventana con un diálogo (lo controla `tests/test_puente.py`).
- **Interfaz**: lo que cambia de una pestaña a otra va en la tabla `PESTANA` (`ui/js/pestanas.js`), no repartido en condicionales. Los `<script>` de `ui/js/` y los estilos de `ui/css/` se cargan en el orden de `index.html`: un archivo usa al cargarse solo lo declarado en los anteriores (si registra algo de uno posterior, con una flecha: `() => entregar()`).
- **Atributos de un Item**: van en el Encode (`inventory.addOptions`, `script.generar_script_con_atributos`); trucar el SWF es solo para Acciones y Trucar Prenda.
- **Reusá antes de escribir**: `mostrarPaginas`, `convertir_en_npcs`, `guardados`, `dePestana`… ya existen. Lo que queda sin uso se borra en el mismo PR.

## Agent skills

### Issue tracker

Issues y specs viven en GitHub Issues (CapitanBeto1/Encoder-Base64-Mundo-Gaturro-Items-SWF), vía `gh`. See `docs/agents/issue-tracker.md`.

### Triage labels

Etiquetas por defecto: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: un `GLOSSARY.md` + `docs/adr/` en la raíz. See `docs/agents/domain.md`.
