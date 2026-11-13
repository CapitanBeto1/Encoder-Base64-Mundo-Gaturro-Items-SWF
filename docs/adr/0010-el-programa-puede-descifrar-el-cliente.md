# 0010 — El programa puede descifrar el cliente del juego por su cuenta (hoy no hace falta, queda como plan B)

> Borrador para revisión del dueño del proyecto (noviembre de 2026). Nace de una investigación de ingeniería inversa del cliente hecha aparte; el alcance es solo la **vista previa y el catálogo** (leer y renderizar el Gaturro localmente). No toca la entrega ni nada del servidor.

## Contexto

El ADR 0003 descartó **descifrar el cliente** ("sería saltear una protección del juego y se rompería cada vez que la cambien"). El ADR 0009 lo evitó usando `anim_preview.swf` de **naw-trucador** (un tercero), que trae el `Gaturro` del juego sin cifrar: `scripts/obtener_binarios.py` lo baja fijado por commit y hash.

El propio ADR 0009 anota los riesgos de esa dependencia:

- Si naw-trucador deja de publicarlo, `obtener_binarios.py` no puede bajarlo.
- Es "el cliente de una fecha": si el juego cambia el Gaturro o sus reglas, la vista previa queda atrás **hasta que un tercero publique una copia nueva**.

En noviembre de 2026, una investigación aparte mostró cómo el propio cargador del juego descifra el cliente: `MMOLoader.swf` baja `MMO<versión>.swf` y lo descifra con **HMAC-SHA256 + XOR**, con una clave que sale de los **tamaños del propio cargador** (sin servidor, sin sesión ni credenciales). Es derivable y se reprodujo con un script. Esto responde al "no se puede" del ADR 0003: el cliente **se puede descifrar solo, en la máquina del usuario, sin tocar nada del servidor**.

## Decisión

- Se deja registrado que MGItems **puede** obtener y descifrar el cliente actual por su cuenta: bajar `MMOLoader` + `MMO<versión>` del CDN público y descifrarlos localmente, como alternativa a depender de naw-trucador.
- **Por ahora no se cambia nada.** Una comparación del cliente descifrado actual contra el `anim_preview` que usa el programa muestra que son prácticamente la misma versión (ver Consecuencias). Mientras naw-trucador siga publicando una copia equivalente, se sigue usando esa (es menos código propio y ya está probada).
- El autodescifrado queda como **plan de contingencia y de futuro**: si naw-trucador deja de publicar, o si su copia queda atrás del juego, `obtener_binarios.py` puede bajar y descifrar el cliente actual en vez de esperar al tercero.

## Opciones consideradas

- **Cambiar ya a un cliente autodescifrado**: descartado por ahora. No aporta fidelidad (las versiones coinciden) y perdería las pequeñas adaptaciones que trae el `anim_preview`, que habría que rehacer.
- **Seguir solo con naw-trucador, sin plan B**: es lo que se hace hoy, pero deja al programa sin salida si el repo del tercero desaparece o se desactualiza.
- **Publicar el cliente en un release propio**: descartado (igual que en el ADR 0009); el repo pasaría a alojar el cliente del juego.

## Consecuencias

- **Comparación (noviembre de 2026).** Entre el cliente actual descifrado y el `anim_preview`:
  - `GaturroColorManager` y `AvatarBodyEnum`: **idénticos**.
  - `GaturroMC`: difiere en **3 líneas** — un número de símbolo embebido (`symbol151`/`symbol152`) y una llamada `eyes("reseted")` que el `anim_preview` tiene **de más**.
  - `Gaturro`: difiere en **unas pocas** — dos son coerciones `Boolean(...)` (artefactos del decompilador) y la real es un guard `checkTransport` que el `anim_preview` trae **de más**.
  - El dibujo de `GaturroMC` va **embebido** (`[Embed(source="/_assets/assets.swf", symbol=...)]`) en los dos.
  - **Ninguna** de las diferencias es de las que parchea el ADR 0003 (`accesories2`, nariz, iris, Espalda): esos ya los resolvió el ADR 0009 al pasar a `anim_preview`.
- Por eso: **el autodescifrado no mejora hoy la fidelidad.** Su valor es la **independencia del tercero** y poder actualizar el cliente sin esperar a que naw-trucador publique.
- **El `anim_preview` no es "el cliente pelado".** Trae pequeñas adaptaciones propias (`checkTransport`, `eyes("reseted")`). Un cliente autodescifrado necesitaría las mismas adaptaciones que ya hace `scripts/armar_gaturro.py` (reemplazar `MMO`, `api`, `user`), y habría que revisar si esas dos líneas hacen falta para el uso del programa.
- **El descifrado ata el MMO a la versión exacta del cargador** (por el HMAC): hay que bajar y descifrar `MMOLoader` + `MMO<versión>` **juntos**, y rehacerlo cuando el juego actualiza. Es automatizable (lo hace el script de la investigación), pero es un paso más que `obtener_binarios.py` hoy no tiene.
- **No se versiona el cliente** (se mantiene la política del ADR 0009): se descifra en la PC del usuario; el repo no aloja el cliente ni su arte.
- **Alcance.** Esto es solo para leer y renderizar el Gaturro localmente (vista previa y catálogo). No cambia nada de la entrega.

## Pendiente de verificar (si algún día el `anim_preview` se desactualiza)

- Comparación a nivel **dibujo** (no solo código): exportar `GaturroMC` a SVG desde el cliente descifrado y desde el `anim_preview` con FFDec y diferenciar los `id` de los clips (`accesories2`, `nose`, `clothBack`, `clothFront`). La comparación de arriba es de código; el arte se dio por equivalente por el `[Embed]` y por coincidir el código, no por un diff del SVG.
