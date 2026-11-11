# 0009 — El Gaturro de Looks y Trucar Prenda es el Gaturro de pantalla del juego, en vivo

## Contexto

El ADR 0003 dibuja al Gaturro como una imagen: el `assets.GaturroMC` que el juego publica sin cifrar, con las Piezas puestas con las reglas del cliente. Ese es el Gaturro de las salas, y la copia publicada es de una versión anterior.

En noviembre de 2026 se probó en la rama `prototipo-ui` otra vista previa: el Gaturro de pantalla del juego (`assets.ScreenGaturro`, el grande, de trazo grueso) corriendo en Ruffle, un reproductor de Flash. Tiene lugar para «Accesorio 2», la nariz con su color y las caras de cada emoción. El dueño del proyecto lo comparó con el anterior y decidió que lo reemplaza.

## Decisiones

**En la tarjeta de Looks y de Trucar Prenda se ve el Gaturro en vivo**, y también en el escenario de los guardados y en «Elige tus colores». Corre en un marco de la interfaz (`ui/gaturro_vivo.html`), que le pide sus archivos a un servidor local (`mgitems.servidor`): Ruffle, el Gaturro y el SWF de cada Pieza. El resto de la interfaz sigue abriéndose como archivo, así no cambia de origen y no pierde lo que guarda el navegador. El núcleo dice con qué se viste (`Nucleo.gaturro_en_vivo`): cada Parte del cuerpo con su Pieza, los colores y la emoción; lo que el juego no dibujaría (`se_ve`) no se pone, igual que antes.

**El Gaturro de pantalla sale del `preview.swf` de naw-trucador.** `assets.ScreenGaturro` solo existe dentro del cliente cifrado del juego: no está en ningún SWF del servidor ni de la caché. Ese archivo, de otra herramienta de la comunidad, lo trae junto con el código que lo viste. `scripts/obtener_binarios.py` lo baja de su repositorio, fijado por commit y por hash, igual que FFDec, Java y Ruffle. El repositorio sigue sin contener arte del juego.

**Lo que le falta al archivo se le agrega al bajarlo** (`scripts/parchear_preview.py`, con FFDec): un llamado `mgVestir` que pone todas las Partes juntas, pinta los clips de color como el juego (`ColorTransform.color`; el archivo original no pintaba ninguno) y lleva la cabeza a la emoción.

## Opciones consideradas

- **El `GaturroMC` del servidor corriendo en Ruffle, con código propio**: no depende de nadie, pero es el dibujo anterior, no el elegido.
- **Copiar el Gaturro de pantalla de la memoria del juego abierto**: es descifrar el cliente, que el ADR 0003 ya había descartado, y cada usuario tendría que hacerlo.
- **Publicar el archivo en un release propio**: el repositorio pasaría a alojar arte del juego y código de terceros.

## Consecuencias

- Si naw-trucador deja de publicar el archivo, `obtener_binarios.py` no puede bajarlo: las copias ya instaladas siguen andando, y el instalador lo lleva adentro. El archivo no tiene licencia declarada.
- **El color de ojos no se ve.** El ojo de este Gaturro no trae clip de iris, y no se le dibuja uno a ojo (ADR 0003: nunca una aproximación). `color3` solo pinta las Piezas que tienen ese clip.
- **No dibuja el transporte ni el efecto de cabeza**: el Gaturro de pantalla no tiene lugar para ellos. La tarjeta lo avisa («se ve en el juego, pero la vista previa no lo dibuja»).
- El Gaturro de las imágenes (ADR 0003) sigue en uso donde hay muchos a la vez o hace falta animarlo cuadro por cuadro: las miniaturas de los guardados, las Acciones (ADR 0006, también su escenario de guardados) y la búsqueda por imagen.
- El programa suma unos 28 MB (Ruffle).
