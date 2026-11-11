# 0009 — El Gaturro del programa es el del juego, corriendo en vivo con el código del juego

## Contexto

El ADR 0003 dibuja al Gaturro como una imagen: el `assets.GaturroMC` que el juego publica sin cifrar (una versión anterior), con las Piezas puestas por código propio que copia las reglas del cliente. El ADR 0006 hacía lo mismo con las animaciones de las Acciones: un simulador propio de la línea de tiempo, cuadro por cuadro.

En noviembre de 2026 se probó en la rama `prototipo-ui` un Gaturro corriendo en Ruffle, un reproductor de Flash, con archivos de naw-trucador (otra herramienta de la comunidad). El dueño del proyecto lo eligió en lugar del anterior. La primera versión (PRs #183 a #185) usó su `preview.swf`, que trae el Gaturro de pantalla del juego (`assets.ScreenGaturro`): no tiene iris, ni lugar para el transporte o el efecto de cabeza, ni animaciones. El dueño del proyecto pidió las tres cosas, y el mismo Gaturro en todas las pestañas.

## Decisiones

**El Gaturro en vivo es el `Gaturro` del juego: su dibujo actual y su propio código.** El otro archivo de naw-trucador, `anim_preview.swf`, trae el cliente del juego sin cifrar: `assets.GaturroMC` de hoy (con iris, color de nariz, lugar para el transporte y sus 106 animaciones) y la clase `Gaturro` que lo viste, lo pinta, lo monta y lo anima. El programa no copia esas reglas: crea un `Gaturro` del juego y le pasa los atributos que tendría el avatar en el juego (cada Parte del cuerpo, `transport`, `effect`, `color1`…`color4`, `emote`, `action`). Lo que se ve es lo que hace el juego con esos atributos, incluidas las reglas que antes había que averiguar (qué esconde cada Pieza, qué tamaños no dibuja, «Accesorio 2», la pose de cada vehículo).

**Al archivo solo se le cambian tres clases** (`scripts/armar_gaturro.py`, con FFDec, al bajarlo): `MMO`, la principal, por la nuestra (`scripts/gaturro_en_vivo/MMO.as`: crea el `Gaturro` y recibe sus atributos de la página con `mgVestir`); y `api` y `user`, dos globales que el `Gaturro` consulta, para poder darle un juego mínimo, sin sala ni usuario ni restricciones del servidor. El código del `Gaturro` queda como vino.

**Corre en un marco de la interfaz** (`ui/gaturro_vivo.html`), que le pide sus archivos a un servidor local (`mgitems.servidor`): Ruffle, el Gaturro y el SWF de cada Pieza. El resto de la interfaz sigue abriéndose como archivo, así no cambia de origen y no pierde lo que guarda el navegador. El núcleo arma los atributos (`Nucleo.gaturro_en_vivo`).

**Es el mismo en todas partes:** la tarjeta de Looks, Trucar Prenda y Acciones (haciendo la animación de verdad), el escenario de los guardados y «Elige tus colores».

**Se baja, no se versiona.** `scripts/obtener_binarios.py` baja `anim_preview.swf` del repositorio de naw-trucador, fijado por commit y por hash, igual que FFDec, Java y Ruffle. El repositorio sigue sin contener arte ni código del juego.

## Opciones consideradas

- **El Gaturro de pantalla (`preview.swf`)**: fue la primera versión; le faltaban el iris, el transporte, el efecto de cabeza y las animaciones, y el código que lo vestía no era el del juego.
- **Código propio sobre el `GaturroMC` actual**: habría que volver a copiar las reglas del cliente (lo que hacían los ADR 0003 y 0006), con el riesgo de copiarlas mal.
- **Copiar el Gaturro de la memoria del juego abierto**: cada usuario tendría que hacerlo, y es frágil.
- **Publicar el archivo en un release propio**: el repositorio pasaría a alojar el cliente del juego.

## Consecuencias

- **El archivo que se baja es el cliente del juego sin cifrar**, publicado por un tercero y sin licencia declarada. El ADR 0003 había descartado descifrar el cliente; acá no se descifra nada, pero se usa una copia que descifró otro. Si naw-trucador deja de publicarlo, `obtener_binarios.py` no puede bajarlo: las copias ya instaladas siguen andando, y el instalador lo lleva adentro.
- **Es el cliente de una fecha.** Si el juego cambia el Gaturro o sus reglas, la vista previa queda atrás hasta que se fije una copia nueva.
- **Sin las restricciones del servidor**: las listas de Items prohibidos o válidos por sala vienen de la configuración que el juego baja al entrar, y acá van vacías. Lo que el programa sabe que el juego no dibuja (`se_ve`) se sigue avisando debajo del Gaturro.
- Se borró el simulador de animaciones del ADR 0006 (`mgitems.animacion`): las Acciones las anima el juego.
- El Gaturro de las imágenes (ADR 0003) sigue en las miniaturas de los guardados y en la búsqueda por imagen, donde hay muchos a la vez.
- El programa suma unos 31 MB (Ruffle y el archivo del Gaturro).
