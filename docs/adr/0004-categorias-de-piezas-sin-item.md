# Las Piezas que ningún Item viste se ubican por su dibujo, solo si es muy seguro

La categoría de una Pieza sale de los datos del juego: la Parte del cuerpo donde la ponen las Prendas (`clothes`) y los Items de mochila (`adds`). Pero de 9221 Piezas del catálogo, unas 660 no las usa ningún Item del juego (quedaron sueltas en el SWF, como las remeras de `goblinTrajes` o las máscaras de `unicefClothes`), y otras ~1040 se usan para algo que no es ropa (vehículos de transportes, animaciones de Items de mochila, decoración de la casa, ropa de la mascota).

El índice que trae el programa (`scripts/armar_indice.py`) ubica cada Pieza con lo primero que corresponda: lo que la viste en el juego; si el juego la usa para otra cosa, "Otros"; la misma Pieza (mismo nombre y mismo dibujo) en otro SWF; y, si nada de eso alcanza, dónde está dibujada respecto del punto donde el juego la pega al Gaturro, más las palabras de su nombre, comparadas con las Piezas ya ubicadas. Ese último paso solo se aplica con seguridad de 0.7 o más (al probarlo con las Piezas que el juego ya ubica acertó el 99 %); el resto queda en "Otros".

## Considered Options

- **Clasificar por el nombre con reglas a mano** (`remera` → Torso, `gorro` → Sombrero): descartado; los nombres no siguen una regla (`torsoDuende`, `varonCanchero`, `Kpop_JardineroJean`) y no dice nada de dónde se ve la Pieza.
- **Ubicar todas las Piezas sueltas, aunque la comparación dude**: descartado por el usuario; prefiere una Pieza en "Otros" antes que en una categoría equivocada.
- **Ninguna Pieza sin datos del juego**: descartado; dejaba en "Otros" la ropa que se ve claramente.

## Consequences

- Armar el índice necesita scikit-learn (`pip install -e ".[indice]"`); el programa no.
- Un SWF que no está en el índice o que cambió se clasifica en la computadora del jugador solo con lo que visten sus Items: sus Piezas sueltas quedan en "Otros" hasta que se vuelva a armar el índice.
