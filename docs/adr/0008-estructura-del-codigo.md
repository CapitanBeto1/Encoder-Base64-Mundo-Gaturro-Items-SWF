# 0008 — Cómo está organizado el código, y por qué

## Contexto

En noviembre de 2026 se revisó todo el proyecto con un criterio de mantenibilidad muy estricto (la skill «thermo-nuclear code quality review»), en PRs #145 a #152. Había cuatro archivos de entre 1700 y 2900 líneas, lógica repetida en varias copias casi iguales, métodos que solo pasaban la llamada y tablas «según la pestaña» repartidas por la interfaz. Este ADR registra cómo quedó y por qué, para que los cambios siguientes mantengan esa forma.

## Decisiones

**Archivos chicos, uno por función.** Ningún archivo pasa de unas 1000 líneas: cuando uno crece, se parte por función. Así quedaron el núcleo, la interfaz y los estilos (el archivo más grande, `nucleo/swfs.py`, tiene ~320 líneas).

**El núcleo es un paquete con una parte por función** (`src/mgitems/nucleo/`: `entrega`, `swfs`, `trucar`, `acciones`, `looks`, `npcs`, `busqueda`, `imagenes`, `encodes`). Cada parte es una clase; `Nucleo` hereda de todas y arma en su `__init__` el estado que comparten. Sigue siendo la única puerta para la interfaz y las pruebas (`from mgitems.nucleo import Nucleo`). Se eligió esto en lugar de objetos separados con dependencias explícitas porque las partes comparten mucho estado (el SWF abierto, los SWF trucados de cada Encode, el entorno, los candados de FFDec) y moverlas tal cual no podía cambiar el comportamiento. Lo que usa una sola parte vive en esa parte; `_comun.py` es solo para lo que usan varias.

**Los guardados son uno solo** (`mgitems.guardados`). Looks, acciones, Prendas trucadas, tiendas, portales, minijuegos y fondos son todos un `Look` que se guarda, duplica, borra, exporta e importa igual; lo que cambia de un tipo a otro está en la tabla `TIPOS` (archivo, formato, extensión, cómo se valida, cómo se nombra). El núcleo lo expone como un atributo, `Nucleo.guardados`, no como métodos por tipo.

**`Puente` (app.py) es el núcleo tal cual, más los diálogos.** Toma los métodos públicos del núcleo sin reescribirlos: pywebview le pasa a Python todos los argumentos y expone también los objetos de adentro (`api().guardados.guardar(…)`). Solo escribe lo que agrega la ventana. El límite de seguridad: **lo que recibe una ruta (`ruta`, `carpeta`) no se expone**; la elige el usuario en un diálogo de la ventana, nunca la interfaz. Es una regla, no una lista, y la controla `tests/test_puente.py`.

**La interfaz dice lo que cambia de una pestaña a otra en una sola tabla**, `PESTANA` (`ui/js/pestanas.js`): textos, cómo empieza un documento nuevo, qué hace «Aplicar» y sus guardados. `dePestana()` completa con lo de Looks lo que una pestaña no dice. Las pestañas de NPC comparten lo común con `pestanaNpc`.

**La interfaz son `<script>` clásicos, en orden** (`ui/js/`), y los estilos son varios `<link>` en orden (`ui/css/`). No son módulos de ES porque la página se abre desde un archivo local (`file://`). Comparten el ámbito global: cada archivo puede usar al cargarse solo lo declarado en los anteriores (en un solo archivo andaba porque las funciones se elevan; entre `<script>` distintos, no). Lo que se registra al cargar y llama a una función de un archivo posterior va con una flecha (`() => entregar()`). En CSS el orden es la cascada: lo de abajo puede pisar a lo de arriba.

**Los atributos de un Item van en el Encode** (`inventory.addOptions`, ADR 0007) para Tiendas, Portales, Minijuegos y Fondos; trucar el SWF queda para Acciones y Trucar Prenda.

## Consecuencias

- Sumar una pestaña es una entrada en `PESTANA`; un tipo de guardado, una entrada en `guardados.TIPOS`; un método del núcleo va a la parte de su función.
- Al cambiar algo, lo que queda sin uso se borra en el mismo PR.
- Al dividir de nuevo un archivo de la interfaz hay que revisar el orden de carga (en #151 se comprobó con un análisis del árbol de sintaxis: qué usa cada tramo al cargarse).
