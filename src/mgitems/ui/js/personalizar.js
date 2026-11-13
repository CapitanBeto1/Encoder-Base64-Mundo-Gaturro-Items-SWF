// PROTOTIPO — Personalizar una Pieza: colores por forma y ajuste de posición, rotación y escala.
// La personalización vive en el documento (`lookActual.personalizacion`: Parte → {colores, ajuste}) y viaja tal cual
// al núcleo, que la valida y la agrega al valor de cada Pieza (mgitems/personalizar.py): para la vista previa, para
// entregarla y para guardarla. Acá no se arma ningún valor; las reglas (qué Partes, topes) también son del núcleo.

let reglasPersonalizar = null; // {sin_personalizar, rotables, limites, ajuste_defecto, maximo_formas}
async function cargarReglasPersonalizar() {
  if (!reglasPersonalizar) reglasPersonalizar = await api().reglas_de_personalizar();
}

const pers = () => (lookActual.personalizacion ??= {});
const esPersonalizable = (parte) => !!reglasPersonalizar && !reglasPersonalizar.sin_personalizar.includes(parte);
const esAjustable = (parte) => !!reglasPersonalizar && reglasPersonalizar.rotables.some((c) => parte === c || parte.startsWith(c));

// Si una Parte tiene algo personalizado (para marcar su casillero).
function tienePersonalizacion(parte) {
  const p = lookActual.personalizacion?.[parte];
  if (!p || !lookActual.partes[parte] || !esPersonalizable(parte)) return false;
  const defecto = reglasPersonalizar.ajuste_defecto;
  const colorTocado = (p.colores ?? []).some((c) => c.quitar || c.color != null);
  const ajustado = esAjustable(parte) && !!p.ajuste && Object.keys(defecto).some((k) => (p.ajuste[k] ?? defecto[k]) !== defecto[k]);
  return colorTocado || ajustado;
}

// Lo que se olvida al cambiar la Pieza de una Parte: los colores por forma eran de la Pieza anterior.
function olvidarPersonalizacion(parte) {
  if (lookActual.personalizacion) delete lookActual.personalizacion[parte];
}

// --- El diálogo ---

const hexAEntero = (hex) => parseInt(hex.slice(1), 16);
const enteroAHex = (n) => "#" + (n & 0xffffff).toString(16).padStart(6, "0");
let parteEnEdicion = null;

async function abrirPersonalizar(parte) {
  await cargarReglasPersonalizar();
  if (!esPersonalizable(parte)) return avisarLista(`${nombreDeParte(parte)} no se puede personalizar en el juego.`, "advertencia");
  parteEnEdicion = parte;
  const p = (pers()[parte] ??= {});
  p.colores ??= [];
  p.ajuste ??= { ...reglasPersonalizar.ajuste_defecto };
  $("titulo-personalizar").textContent = `Personalizar ${nombreDeParte(parte)}: ${claseDeRuta(lookActual.partes[parte])}`;
  $("ajuste-personalizar").hidden = !esAjustable(parte);
  dibujarFilasColor();
  dibujarSlidersAjuste();
  $("dialogo-personalizar").showModal();
}

const formas = () => pers()[parteEnEdicion].colores;

function dibujarFilasColor() {
  $("filas-color").replaceChildren(...formas().map(filaColor));
  $("agregar-forma").disabled = formas().length >= reglasPersonalizar.maximo_formas;
}

function filaColor(c, i) {
  const fila = Object.assign(document.createElement("div"), { className: "fila-color" });
  fila.append(etiqueta(`Forma ${i + 1}`, "nombre-forma"));
  const color = Object.assign(document.createElement("input"), { type: "color", value: enteroAHex(c.color ?? 0xff0000) });
  color.disabled = c.quitar || c.color == null;
  color.addEventListener("input", () => { c.color = hexAEntero(color.value); c.quitar = false; redibujarPersonalizacion(); });
  const defecto = botonAlterna("Por defecto", c.color == null && !c.quitar, () => {
    if (c.color == null && !c.quitar) c.color = hexAEntero(color.value); // volver a pintarla
    else { c.color = null; c.quitar = false; }
    dibujarFilasColor();
    redibujarPersonalizacion();
  });
  const quitar = botonAlterna("Quitar", !!c.quitar, () => { c.quitar = !c.quitar; dibujarFilasColor(); redibujarPersonalizacion(); });
  const borrar = Object.assign(document.createElement("button"), { type: "button", className: "quitar", title: "Sacar esta forma" });
  borrar.append(icono("x"));
  borrar.addEventListener("click", () => { formas().splice(i, 1); dibujarFilasColor(); redibujarPersonalizacion(); });
  fila.append(color, defecto, quitar, borrar);
  return fila;
}

function botonAlterna(texto, activo, alCliquear) {
  const b = Object.assign(document.createElement("button"), { type: "button", className: "chip-alterna", textContent: texto });
  b.setAttribute("aria-pressed", String(activo));
  b.addEventListener("click", alCliquear);
  return b;
}

function dibujarSlidersAjuste() {
  const a = pers()[parteEnEdicion].ajuste;
  const { limites } = reglasPersonalizar;
  const filas = [
    ["x", "Posición ←→", (v) => `${v} px`],
    ["y", "Posición ↑↓", (v) => `${v} px`],
    ["rot", "Rotación", (v) => `${v}°`],
    ["escala", "Tamaño", (v) => `${v * 10}%`],
  ];
  $("sliders-ajuste").replaceChildren(...filas.map(([clave, nombre, formato]) => {
    const fila = Object.assign(document.createElement("label"), { className: "fila-ajuste" });
    const val = Object.assign(document.createElement("span"), { className: "valor-ajuste", textContent: formato(a[clave]) });
    const barra = Object.assign(document.createElement("input"), { type: "range", min: limites[clave][0], max: limites[clave][1], step: 1, value: a[clave] });
    barra.addEventListener("input", () => { a[clave] = Number(barra.value); val.textContent = formato(a[clave]); redibujarPersonalizacion(); });
    fila.append(Object.assign(document.createElement("span"), { className: "nombre-ajuste", textContent: nombre }), barra, val);
    return fila;
  }));
}

// Redibuja el Gaturro con la personalización puesta (sin reconstruir la grilla).
function redibujarPersonalizacion() {
  mostrarEncode(null); // el Encode que había era sin estos cambios
  if (vista === "trucar") mostrarArmadoTrucar();
  else mostrarCasilleros();
  dibujarGaturro();
}

$("agregar-forma").addEventListener("click", () => {
  formas().push({ color: 0xff0000 });
  dibujarFilasColor();
  redibujarPersonalizacion();
});
$("reiniciar-ajuste").addEventListener("click", () => {
  pers()[parteEnEdicion].ajuste = { ...reglasPersonalizar.ajuste_defecto };
  dibujarSlidersAjuste();
  redibujarPersonalizacion();
});
$("quitar-personalizacion").addEventListener("click", () => {
  olvidarPersonalizacion(parteEnEdicion);
  $("dialogo-personalizar").close();
  mostrarEncode(null);
  mostrarLook();
});
$("cerrar-personalizar").addEventListener("click", () => $("dialogo-personalizar").close());
$("listo-personalizar").addEventListener("click", () => $("dialogo-personalizar").close());
$("personalizar-pieza").addEventListener("click", () => {
  if (casilleroMarcado && lookActual.partes[casilleroMarcado]) abrirPersonalizar(casilleroMarcado);
});
$("personalizar-trucada").addEventListener("click", () => {
  if (lookActual.partes[lookActual.parte]) abrirPersonalizar(lookActual.parte);
});
