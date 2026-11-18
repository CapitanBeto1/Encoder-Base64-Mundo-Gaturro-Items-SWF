# La estética del programa es la del celular del juego, en modo claro y oscuro

En noviembre de 2026 el dueño del proyecto pidió cambiar por completo la estética, usando la del juego y no una
inventada. En la rama `prototipo-ui` se probaron varias (la mochila y el ropero amarillos, el celular violeta del
juego, la anterior), con una barra para cambiarlas sobre el programa real. Eligió la del **celular** (GatuPhone): su
fondo violeta con estrellas, sus tarjetas blancas, sus letras (Fredoka y Cooper) y sus íconos. Sobre esa base eligió,
también entre variantes: los botones de la tarjeta del Gaturro en una barra con lugares fijos (nada se mueve al cambiar
de pestaña), la ventana del Item base como catálogo (la lista y el Item grande al lado), las tarjetas de las grillas como
renglones («Lista»), «más color» (cada grupo de pestañas con su color) y un modo oscuro.

**La estética es `ui/css/celular.css`, la última hoja.** Tiene la apariencia; las demás hojas, la forma. El modo es `<html data-modo="claro|oscuro">`: lo cambia el botón de la columna de pestañas
(`js/modo.js`) y queda para la próxima vez. El fondo del perfil del juego detrás del Gaturro se elige con las flechas del
juego (`js/fondo_del_perfil.js`).

**El arte sale del juego al instalar, no del repositorio.** `scripts/sacar_arte.py` (desde `obtener_binarios.py`, después
del Gaturro en vivo) saca a `ui/arte/` las letras, el fondo del celular, las formas de los íconos, las caras de las
emociones y los fondos del perfil. Git no lleva esa carpeta. Sin ella el programa se ve con las letras y los íconos de
siempre (`data-ic` dice qué ícono es cada uno; `arte/iconos.css` le pone la forma del juego).

## Consecuencias

- Cambiar la estética es cambiar `celular.css` (y lo que haga falta del arte en `sacar_arte.py`, subiendo su `VERSION`).
- Las demás hojas ya no tienen colores de la estética anterior (#222, #223): la forma de las cosas está en su hoja y la
  apariencia en `celular.css`. Las ventanas que copian al juego (`ventanas-del-juego.css`) siguen con los suyos.
- Las decisiones de diseño se siguen probando en una rama de prototipo antes de pasar a `main` (CLAUDE.md).
