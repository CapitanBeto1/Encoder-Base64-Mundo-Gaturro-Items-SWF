// La personalización de las Piezas del documento (`lookActual.personalizacion`: Parte → {colores, ajuste}, ya
// validada por el núcleo, ver `mgitems.personalizar`): viaja con él a la vista previa, a la entrega y a los guardados.

// Si la Pieza de una Parte está personalizada (para marcar su casillero).
const tienePersonalizacion = (parte) => !!lookActual.partes[parte] && !!lookActual.personalizacion?.[parte];

// Lo que se olvida al cambiar la Pieza de una Parte: los colores por capa eran de la Pieza anterior.
function olvidarPersonalizacion(parte) {
  if (lookActual.personalizacion) delete lookActual.personalizacion[parte];
}
