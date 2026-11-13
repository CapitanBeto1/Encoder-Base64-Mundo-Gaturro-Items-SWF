// PROTOTIPO — Personalizar una Pieza: colores por forma y ajuste de posición, rotación y escala.
// El cliente del juego lee "pack.Clase_on[,c0,c1,…][//x,y,rot,escala]" (ver mgitems/personalizar.py). Acá se arma
// ese valor y se le pasa al Gaturro en vivo (que es el cliente real, así que se ve 1:1) y, al entregar, al Encode.

const PERS_LIMITES = { x: [-15, 15], y: [-15, 15], rot: [-180, 180], escala: [5, 10] };
const PERS_AJUSTE_DEFECTO = { x: 0, y: 0, rot: 0, escala: 10 };
const PERS_ROTABLES = ["hairs", "hats", "accesories", "mouths", "neck", "cloth", "leg", "grip", "glove"];
const esParteRotable = (parte) => PERS_ROTABLES.some((c) => parte === c || parte.startsWith(c));
const pers = () => (lookActual.personalizacion ??= {}); // Parte → {colores:[{color,quitar,opacidad}], ajuste}

function tokenColor(c) {
  if (c.quitar) return "-3";
  if (c.color == null) return "-2";
  const t = String(c.color & 0xffffff);
  return c.opacidad != null && c.opacidad >= 1 && c.opacidad < 10 ? `${t};${c.opacidad}` : t;
}

// El valor extendido de la Pieza `ruta` con la personalización `p` (o la Pieza sola si no hay nada que agregar).
function componerPieza(ruta, p) {
  if (!p) return ruta;
  const tokens = (p.colores ?? []).map(tokenColor);
  while (tokens.length && tokens[tokens.length - 1] === "-2") tokens.pop();
  let valor = tokens.length ? `${ruta},${tokens.join(",")}` : ruta;
  const a = p.ajuste;
  if (a && Object.keys(PERS_AJUSTE_DEFECTO).some((k) => (a[k] ?? PERS_AJUSTE_DEFECTO[k]) !== PERS_AJUSTE_DEFECTO[k])) {
    const v = (k) => Math.max(PERS_LIMITES[k][0], Math.min(PERS_LIMITES[k][1], a[k] ?? PERS_AJUSTE_DEFECTO[k]));
    valor += `//${v("x")},${v("y")},${v("rot")},${v("escala")}`;
  }
  return valor;
}

// Las Partes de un documento con la personalización ya puesta en cada valor (lo que ve el Gaturro y el Encode).
function partesConPersonalizacion(documento) {
  const p = documento.personalizacion;
  if (!p) return documento.partes;
  return Object.fromEntries(Object.entries(documento.partes).map(([parte, ruta]) => [parte, componerPieza(ruta, p[parte])]));
}

// Si una Parte tiene algo personalizado (para marcar su casillero).
const tienePersonalizacion = (parte) => {
  const p = lookActual.personalizacion?.[parte];
  return !!p && (componerPieza(lookActual.partes[parte] ?? "", p) !== (lookActual.partes[parte] ?? ""));
};

// --- El diálogo ---

const hexAEntero = (hex) => parseInt(hex.slice(1), 16);
const enteroAHex = (n) => "#" + (n & 0xffffff).toString(16).padStart(6, "0");
let parteEnEdicion = null;

function abrirPersonalizar(parte) {
  parteEnEdicion = parte;
  const p = (pers()[parte] ??= { colores: [], ajuste: { ...PERS_AJUSTE_DEFECTO } });
  p.colores ??= [];
  p.ajuste ??= { ...PERS_AJUSTE_DEFECTO };
  $("titulo-personalizar").textContent = `Personalizar ${nombreDeParte(parte)}: ${claseDeRuta(lookActual.partes[parte])}`;
  $("ajuste-personalizar").hidden = !esParteRotable(parte);
  dibujarFilasColor();
  dibujarSlidersAjuste();
  $("dialogo-personalizar").showModal();
}

function dibujarFilasColor() {
  const p = pers()[parteEnEdicion];
  $("filas-color").replaceChildren(...p.colores.map((c, i) => filaColor(c, i)));
}

function filaColor(c, i) {
  const fila = Object.assign(document.createElement("div"), { className: "fila-color" });
  fila.append(etiqueta(`Forma ${i + 1}`, "nombre-forma"));
  const color = Object.assign(document.createElement("input"), { type: "color", value: enteroAHex(c.color ?? 0xff0000) });
  color.disabled = c.quitar || c.color == null;
  color.addEventListener("input", () => { c.color = hexAEntero(color.value); c.quitar = false; redibujarPersonalizacion(); });
  const quitar = botonAlterna("Quitar", c.quitar, () => { c.quitar = !c.quitar; dibujarFilasColor(); redibujarPersonalizacion(); });
  const defecto = botonAlterna("Por defecto", c.color == null && !c.quitar, () => { c.color = null; c.quitar = false; dibujarFilasColor(); redibujarPersonalizacion(); });
  const borrar = Object.assign(document.createElement("button"), { type: "button", className: "quitar", title: "Sacar esta forma" });
  borrar.append(icono("x"));
  borrar.addEventListener("click", () => { p_colores().splice(i, 1); dibujarFilasColor(); redibujarPersonalizacion(); });
  fila.append(color, defecto, quitar, borrar);
  return fila;
}

const p_colores = () => pers()[parteEnEdicion].colores;

function botonAlterna(texto, activo, alCliquear) {
  const b = Object.assign(document.createElement("button"), { type: "button", className: "chip-alterna", textContent: texto });
  b.setAttribute("aria-pressed", String(activo));
  b.addEventListener("click", alCliquear);
  return b;
}

function dibujarSlidersAjuste() {
  const a = pers()[parteEnEdicion].ajuste;
  const filas = [
    ["x", "Posición ←→", (v) => `${v} px`],
    ["y", "Posición ↑↓", (v) => `${v} px`],
    ["rot", "Rotación", (v) => `${v}°`],
    ["escala", "Tamaño", (v) => `${v * 10}%`],
  ];
  $("sliders-ajuste").replaceChildren(...filas.map(([clave, nombre, formato]) => {
    const fila = Object.assign(document.createElement("label"), { className: "fila-ajuste" });
    const val = Object.assign(document.createElement("span"), { className: "valor-ajuste", textContent: formato(a[clave]) });
    const barra = Object.assign(document.createElement("input"), { type: "range", min: PERS_LIMITES[clave][0], max: PERS_LIMITES[clave][1], step: 1, value: a[clave] });
    barra.addEventListener("input", () => { a[clave] = Number(barra.value); val.textContent = formato(a[clave]); redibujarPersonalizacion(); });
    fila.append(Object.assign(document.createElement("span"), { className: "nombre-ajuste", textContent: nombre }), barra, val);
    return fila;
  }));
}

// Redibuja el Gaturro con la personalización puesta (sin reconstruir la grilla ni los casilleros).
function redibujarPersonalizacion() {
  mostrarCasilleros();
  dibujarGaturro();
}

$("agregar-forma").addEventListener("click", () => {
  p_colores().push({ color: 0xff0000, opacidad: 10 });
  dibujarFilasColor();
  redibujarPersonalizacion();
});
$("reiniciar-ajuste").addEventListener("click", () => {
  pers()[parteEnEdicion].ajuste = { ...PERS_AJUSTE_DEFECTO };
  dibujarSlidersAjuste();
  redibujarPersonalizacion();
});
$("quitar-personalizacion").addEventListener("click", () => {
  delete pers()[parteEnEdicion];
  $("dialogo-personalizar").close();
  mostrarLook();
});
$("cerrar-personalizar").addEventListener("click", () => $("dialogo-personalizar").close());
$("listo-personalizar").addEventListener("click", () => $("dialogo-personalizar").close());
$("personalizar-pieza").addEventListener("click", () => { if (casilleroMarcado && lookActual.partes[casilleroMarcado]) abrirPersonalizar(casilleroMarcado); });
