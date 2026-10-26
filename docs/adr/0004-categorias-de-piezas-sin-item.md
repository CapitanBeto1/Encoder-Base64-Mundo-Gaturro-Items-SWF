# En "Otros" solo queda lo que no se viste; lo demás se ubica por su dibujo y su nombre

La categoría de una Pieza sale de los datos del juego: la Parte del cuerpo donde la ponen las Prendas (`clothes`) y los Items de mochila (`adds`). Pero de 9221 Piezas del catálogo, unas 660 no las usa ningún Item del juego (quedaron sueltas en el SWF, como las remeras de `goblinTrajes` o las máscaras de `unicefClothes`), y otras ~1040 se usan para algo que no es ropa (vehículos de transportes, animaciones de Items de mochila, decoración de la casa, ropa de la mascota).

El usuario quiere que en "Otros" quede solo lo que no se le pone al Gaturro, y ver debajo de cada Pieza qué es. El índice que trae el programa (`scripts/armar_indice.py`) ubica cada Pieza con lo primero que corresponda: lo que la viste en el juego; si el juego la usa para otra cosa, "Otros" con ese uso (transporte, acción, casa, mascota); la misma Pieza (mismo nombre y mismo dibujo) en otro SWF; dónde está dibujada respecto del punto donde el juego la pega al Gaturro, más las palabras de su nombre, si es muy seguro (98-99 % de aciertos al probarlo); si no, la Parte más probable según el dibujo y el nombre leído por partes, por separado; y, si los dos dicen que no es ropa, la primera palabra del nombre cuando en el juego casi siempre va en la misma Parte. Lo que queda en "Otros" sin uso conocido se muestra como "Objeto".

## Considered Options

- **Clasificar solo por el nombre con reglas a mano** (`remera` → Torso, `gorro` → Sombrero): descartado; los nombres no siguen una regla (`torsoDuende`, `varonCanchero`, `Kpop_JardineroJean`). La regla de la primera palabra se aprende de los datos del juego y es el último recurso.
- **Ubicar solo lo que es muy seguro y dejar el resto en "Otros"**: fue la primera versión; el usuario seguía viendo ropa en "Otros" y prefirió que toda la ropa tenga categoría, aunque alguna pueda caer en una Parte equivocada.

## Consequences

- Armar el índice necesita scikit-learn (`pip install -e ".[indice]"`); el programa no.
- Un SWF que no está en el índice o que cambió se clasifica en la computadora del jugador solo con sus Items (lo que visten y para qué usan lo que no visten): sus Piezas sueltas quedan en "Otros" hasta que se vuelva a armar el índice.
