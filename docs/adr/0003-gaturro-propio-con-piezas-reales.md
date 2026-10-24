# El editor visual dibuja un Gaturro propio en SVG con las Piezas reales del juego encima

El cuerpo del Gaturro común (`GaturroMC`, con un clip vacío y con nombre por cada Parte del cuerpo, donde el juego mete cada Pieza) solo existe dentro del cliente del juego (`MMO.swf`), que está cifrado tanto en la instalación como en el CDN. El programa no lo descifra: sería saltear una protección del juego y se rompería cada vez que el juego la cambie. Por eso el editor dibuja un Gaturro propio en SVG, con el estilo del programa, con un punto de anclaje por Parte del cuerpo; cada Pieza es el primer cuadro real de su SWF de assets, exportado a SVG con FFDec (que deja el punto de anclaje de la Pieza en el `<g transform>` exterior) y puesto en el anclaje de su Parte, en el orden de capas del cuerpo.

Los anclajes del prototipo salieron de medir, por Parte, la caja de cientos de Piezas reales respecto de su punto de anclaje (`clothes1`, `costumes`, `china`): el torso queda en (0, 0) y mide unos 29×31; la cabeza, unos 70 de ancho. Brazo, pierna y pie van dos veces, la segunda reflejada.

## Considered Options

- **PNG de las Piezas compuestos en capas, con el cuerpo original del juego**: descartado; el cuerpo no se puede sacar del cliente cifrado. Componer las Piezas sí funciona, y en SVG mejor que en PNG (nítido a cualquier tamaño).
- **Ruffle (reproductor de Flash en WebAssembly) con un SWF propio que instancia las clases del juego**: descartado. Tiene el mismo problema del cuerpo, necesita compilar AS3 (no hay compilador en el proyecto), suma unos 10 MB al programa y su única ventaja es la animación.
- **Cuerpos de transformación (`avatars/*.swf`, sin cifrar)**: descartado; son animales y disfraces, no el Gaturro común.
- **Solo las Piezas, sin cuerpo**: descartado por el dueño del proyecto; el Gaturro propio se ve mucho mejor y cuesta poco más.

## Consequences

- El cuerpo es una aproximación del Gaturro del juego: las Piezas caen en su lugar, pero las proporciones no son exactas. Los anclajes se calibran a ojo con Piezas reales y pueden ajustarse sin cambiar nada más.
- Se ve el primer cuadro de cada Pieza, sin animación, y sin los tintes que el juego aplica a las Piezas personalizables (`pieza,color`); el color del pelaje del Gaturro sí se puede cambiar, porque el cuerpo es nuestro.
- No hay vista de espaldas: el juego la arma con otras Piezas (`…Back`) y otros clips del cuerpo, que tampoco se pueden sacar.
- Las imágenes del juego se exportan en la computadora del jugador, como los íconos; el repositorio no contiene arte del juego.
