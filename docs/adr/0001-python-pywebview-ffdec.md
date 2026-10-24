# Python + interfaz web en pywebview + FFDec con Java embebido

El programa se escribe en Python, con la interfaz en HTML/CSS/JS dentro de una ventana nativa de pywebview (WebView2 en Windows, WebKit en Linux), y se distribuye como un único instalador hecho con PyInstaller que incluye FFDec y un Java propio. Python porque es el lenguaje del proyecto original y porque existe mitmproxy para reemplazar a Fiddler; interfaz web porque deja abierta la opción de dibujar al Gaturro con Ruffle en el editor visual de Looks; FFDec + Java porque trucar Prendas exige recompilar el AS3 de los SWF de assets y no hay alternativa madura en Python. Se descartó Tauri (Rust): más liviano, pero obliga a cambiar de lenguaje y perder mitmproxy.

## Consequences

- El instalador pesa decenas de MB más por el Java embebido.
- La decisión entre exportar Piezas a PNG o renderizar con Ruffle se posterga a un prototipo en la fase del editor visual.
- La lista de clases de un SWF de assets (de donde salen los Items y las Piezas) se lee directamente en Python desde el tag `SymbolClass`, sin FFDec: es instantáneo y no necesita Java. FFDec se usa solo para lo que exige interpretar el contenido (imágenes, AS3 al trucar).
