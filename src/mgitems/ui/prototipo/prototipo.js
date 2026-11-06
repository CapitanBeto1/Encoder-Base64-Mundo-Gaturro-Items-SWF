// PROTOTIPO (rama prototipo-ui, no va a main): variantes de diseño sobre el programa real. La barra de abajo cambia
// cada eje; lo elegido queda en <html data-…>. Todo en su propio ámbito: los <script> de la interfaz comparten el
// global y un nombre igual pisaría al suyo.
(() => {

// El primero de cada eje es lo elegido hasta ahora; «actual» es como está en main.
const EJES = [
  { id: "distribucion", nombre: "Distribución", variantes: [["agrupada", "Lateral agrupada"], ["riel", "Riel + carrito"], ["pasos", "Lateral con pasos"], ["lateral", "Barra lateral"], ["actual", "Actual"]] },
  { id: "textos", nombre: "Textos", variantes: [["pulido", "Pulidos"], ["actual", "Actuales"]] },
  { id: "carga", nombre: "Cargas", variantes: [["esqueleto", "Esqueleto"], ["texto", "Texto (actual)"]] },
  { id: "letra", nombre: "Letra", variantes: [["fredoka", "Fredoka"], ["actual", "Cooper (actual)"], ["nunito", "Nunito + Cooper"], ["baloo", "Baloo"]] },
  { id: "nombres", nombre: "Nombres", variantes: [["ficha", "Ficha"], ["actual", "Actual"]] },
  { id: "iconos", nombre: "Íconos", variantes: [["trazo", "Trazo"], ["emoji", "Emojis (actual)"], ["relleno", "Relleno"], ["duotono", "Duotono"]] },
  { id: "toques", nombre: "Toques", variantes: [["si", "Animados"], ["no", "Sin (actual)"]] },
];

const html = document.documentElement;
const $id = (id) => document.getElementById(id);
const elegido = (() => {
  try { return JSON.parse(localStorage.getItem("prototipo-ui-2")) || {}; } catch { return {}; }
})();
let ejeActivo = "distribucion";

function aplicarVariantes() {
  for (const eje of EJES) html.dataset[eje.id] = elegido[eje.id] ?? eje.variantes[0][0];
  try { localStorage.setItem("prototipo-ui-2", JSON.stringify(elegido)); } catch {}
  pintarBarra();
  document.querySelectorAll(".pi").forEach(pintarIcono);
  pulirTextos(document.body);
  for (const r of regiones.values()) { r.capa?.remove(); r.capa = null; r.el?.classList.remove("bajo-esqueleto"); }
  if (html.dataset.carga !== "esqueleto") document.querySelectorAll(".bajo-esqueleto").forEach((x) => x.classList.remove("bajo-esqueleto"));
}

function cambiar(ejeId, paso) {
  const eje = EJES.find((e) => e.id === ejeId);
  const i = eje.variantes.findIndex(([v]) => v === html.dataset[ejeId]);
  elegido[ejeId] = eje.variantes[(i + paso + eje.variantes.length) % eje.variantes.length][0];
  ejeActivo = ejeId;
  aplicarVariantes();
}

// ============ La barra del prototipo ============

const barra = document.createElement("div");
barra.className = "barra-prototipo";
barra.dataset.sinIconos = "";
document.body.append(barra);

function pintarBarra() {
  const boton = (texto, accion, titulo = "") => {
    const b = Object.assign(document.createElement("button"), { textContent: texto, type: "button", title: titulo });
    b.addEventListener("click", (e) => { e.stopPropagation(); accion(); });
    return b;
  };
  barra.replaceChildren(
    boton(barra.classList.contains("plegada") ? "▲" : "▼", () => { barra.classList.toggle("plegada"); pintarBarra(); }, "Plegar la barra"),
    Object.assign(document.createElement("strong"), { textContent: "PROTOTIPO" }),
    ...EJES.map((eje) => {
      const grupo = document.createElement("span");
      grupo.className = "grupo-prototipo" + (eje.id === ejeActivo ? " activo" : "");
      const [, nombre] = eje.variantes.find(([v]) => v === html.dataset[eje.id]);
      grupo.append(boton("‹", () => cambiar(eje.id, -1)), Object.assign(document.createElement("span"), { textContent: `${eje.nombre}: ${nombre}` }), boton("›", () => cambiar(eje.id, 1)));
      grupo.addEventListener("click", () => { ejeActivo = eje.id; pintarBarra(); });
      return grupo;
    }),
    boton("Probar carga", probarCarga, "Muestra 4 segundos la carga de la grilla y del Gaturro")
  );
}

document.addEventListener("keydown", (e) => {
  if (e.target.closest("input, textarea, select, [contenteditable]")) return;
  if (e.key === "ArrowLeft" || e.key === "ArrowRight") cambiar(ejeActivo, e.key === "ArrowLeft" ? -1 : 1);
  if (e.key === "ArrowUp" || e.key === "ArrowDown") {
    const i = EJES.findIndex((x) => x.id === ejeActivo);
    ejeActivo = EJES[(i + (e.key === "ArrowUp" ? -1 : 1) + EJES.length) % EJES.length].id;
    pintarBarra();
  }
});

// ============ Íconos en vez de emojis ============

const EMOJI_A_ICONO = {
  "✕": "x", "✗": "x", "◀": "caret-left", "▶": "caret-right", "→": "arrow-right", "✓": "check",
  "👕": "t-shirt", "🎒": "backpack", "🗑": "trash", "↻": "arrow-clockwise", "🔍": "magnifying-glass", "🔎": "magnifying-glass",
  "🛹": "scooter", "🛋": "couch", "✨": "sparkle", "✂": "scissors", "🖼": "image", "🦸": "mask-happy", "🧪": "flask",
  "🐶": "dog", "🎀": "gift", "🦴": "bone", "🎩": "baseball-cap", "💇": "hair-dryer", "👄": "smiley", "👓": "eyeglasses",
  "🧣": "coat-hanger", "💪": "hand-fist", "✋": "hand", "👖": "pants", "👟": "sneaker", "🛒": "shopping-cart", "🚪": "door",
  "🎮": "game-controller", "📍": "map-pin", "❔": "question", "🏠": "house", "📦": "package", "⚙": "gear", "🔨": "hammer",
  "🎨": "palette", "📋": "clipboard",
};
const PATRON_EMOJI = new RegExp(`(${Object.keys(EMOJI_A_ICONO).join("|")})️?`, "gu");
// Para saber si hay alguno: sin «g», que guarda dónde quedó la última búsqueda y haría saltear emojis.
const HAY_EMOJI = new RegExp(PATRON_EMOJI.source, "u");
// Las ventanas que copian las del juego quedan idénticas al juego.
const SIN_CAMBIOS = "#dialogo-mis-looks, #dialogo-colores, [data-sin-iconos], option, select, textarea, script, style";
const ESTILO = { relleno: "fill", trazo: "bold", duotono: "duotone" };

const svg = (nombre, estilo = ESTILO[html.dataset.iconos] ?? "bold") =>
  `<svg viewBox="0 0 256 256" fill="currentColor" aria-hidden="true">${ICONOS_PROTOTIPO[nombre]?.[estilo] ?? ""}</svg>`;

function pintarIcono(span) {
  if (html.dataset.iconos === "emoji") span.textContent = span.dataset.emoji;
  else span.innerHTML = svg(span.dataset.icono);
}

function cambiarEmojis(raiz) {
  const recorrido = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT);
  const nodos = [];
  for (let n = recorrido.nextNode(); n; n = recorrido.nextNode()) {
    if (HAY_EMOJI.test(n.nodeValue) && !n.parentElement?.closest(SIN_CAMBIOS) && !n.parentElement?.closest(".pi")) nodos.push(n);
  }
  for (const nodo of nodos) {
    const partes = document.createDocumentFragment();
    let ultimo = 0;
    for (const m of nodo.nodeValue.matchAll(PATRON_EMOJI)) {
      partes.append(nodo.nodeValue.slice(ultimo, m.index));
      const span = Object.assign(document.createElement("span"), { className: "pi" });
      span.dataset.emoji = m[0];
      span.dataset.icono = EMOJI_A_ICONO[m[1]];
      pintarIcono(span);
      partes.append(span);
      ultimo = m.index + m[0].length;
    }
    partes.append(nodo.nodeValue.slice(ultimo));
    nodo.replaceWith(partes);
  }
}

// Íconos de las pestañas (los muestran las distribuciones con barra lateral y dock).
const ICONO_PESTANA = { agregar: "plus-circle", trucar: "magic-wand", looks: "t-shirt", acciones: "person-simple-run",
  tiendas: "storefront", portales: "door-open", minijuegos: "game-controller", fondos: "images-square" };
for (const [pestana, icono] of Object.entries(ICONO_PESTANA)) {
  const b = $id(`pestana-${pestana}`);
  if (!b) continue;
  const caja = Object.assign(document.createElement("span"), { className: "icono-pestana", innerHTML: svg(icono, "bold") });
  caja.dataset.sinIconos = "";
  b.prepend(caja);
}
// El dibujo de «sin imagen», como máscara para el CSS.
html.style.setProperty("--icono-sin-imagen",
  `url("data:image/svg+xml,${encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 256 256'>${ICONOS_PROTOTIPO["image"].bold}</svg>`)}")`);
const engranaje = Object.assign(document.createElement("span"), { className: "icono-pestana icono-config", innerHTML: svg("gear", "bold") });
engranaje.dataset.sinIconos = "";
$id("abrir-entorno")?.prepend(engranaje);

// ============ Distribuciones: lo que agregan a la página ============

// Las pestañas en grupos (barra lateral agrupada y con pasos).
for (const [antes, titulo] of [["agregar", "Items"], ["trucar", "Ropa y Gaturro"], ["tiendas", "Para la casa"]]) {
  const t = Object.assign(document.createElement("span"), { className: "grupo-pestanas", textContent: titulo });
  t.dataset.sinIconos = "";
  $id(`pestana-${antes}`)?.before(t);
}

// El carrito (riel): abre «Items a recibir» como un cajón y dice cuántos hay.
const carrito = Object.assign(document.createElement("button"), { className: "boton-carrito", type: "button", title: "Items a recibir" });
carrito.dataset.sinIconos = "";
carrito.innerHTML = `<span class="icono-carrito">${svg("basket", "bold")}</span><span class="cuenta-carrito">0</span>`;
carrito.addEventListener("click", () => { html.dataset.carrito = html.dataset.carrito === "abierto" ? "" : "abierto"; });
document.body.append(carrito);

// Los pasos de cada pestaña (lateral con pasos): hecho, el que sigue y los que faltan.
const guia = Object.assign(document.createElement("ol"), { className: "pasos-proto" });
guia.dataset.sinIconos = "";
document.body.append(guia);
function pasosDe(v) {
  const doc = typeof lookActual === "undefined" ? {} : lookActual;
  const hayEncode = Boolean($id("encode")?.value);
  const piezas = Object.keys(doc.partes ?? {}).length > 0;
  const enLista = (doc.lista ?? []).length > 0;
  if (v === "agregar") return [["Elegí Items", (typeof items !== "undefined" ? items : []).length > 0], ["Generá el Encode", hayEncode], ["Agregá al juego", false]];
  if (v === "looks") return [["Elegí las Piezas", piezas], ["Elegí dónde se guarda", Boolean(doc.base)], ["Aplicá el Look", hayEncode], ["Agregá al juego", false]];
  if (v === "acciones") return [["Elegí la animación", Boolean(doc.animacion)], ["Elegí el Item", Boolean(doc.base)], ["Aplicá la acción", hayEncode], ["Agregá al juego", false]];
  if (v === "trucar") return [["Elegí el Item base", Boolean(doc.base)], ["Elegí la Pieza", piezas], ["Sumala a la lista", enLista], ["Trucá todas", hayEncode], ["Agregá al juego", false]];
  const fondos = v === "fondos";
  return [[fondos ? "Elegí un objeto" : "Elegí un Item", Boolean(doc.base)], [fondos ? "Elegí el fondo" : "Elegí qué hace", fondos ? doc.cuadro != null : Boolean(doc.comportamiento)],
          ["Sumalo a la lista", enLista], ["Convertí todos", hayEncode], ["Agregá al juego", false]];
}
let ultimaGuia = "";
setInterval(() => {
  try {
    const n = $id("cantidad")?.textContent.replace(/\D/g, "") || "0";
    if (carrito.lastChild.textContent !== n) { carrito.lastChild.textContent = n; carrito.classList.remove("salta"); void carrito.offsetWidth; carrito.classList.add("salta"); }
    if (html.dataset.distribucion !== "pasos") return;
    const pasos = pasosDe(typeof vista === "undefined" ? "agregar" : vista);
    const actual = pasos.findIndex(([, hecho]) => !hecho);
    const clave = JSON.stringify([pasos, actual]);
    if (clave === ultimaGuia) return;
    ultimaGuia = clave;
    guia.replaceChildren(...pasos.map(([texto, hecho], i) => {
      const li = document.createElement("li");
      li.className = hecho && i !== actual ? "hecho" : i === actual ? "actual" : "falta";
      li.innerHTML = `<span class="numero-paso">${hecho && i !== actual ? svg("check", "bold") : i + 1}</span><span>${texto}</span>`;
      return li;
    }));
  } catch {}
}, 250);

// ============ Textos pulidos: menos texto; el necesario, como etiquetas ============

const SOBRA = [/versión anterior del juego/i];
const CORTOS = {
  "Tocá Items de la grilla o agregalos a mano.": "Tocá un Item de la grilla para sumarlo",
  "Todavía no generaste ningún Encode.": "",
};

function pulirTextos(raiz) {
  const pulido = html.dataset.textos === "pulido";
  for (const el of document.querySelectorAll(".aviso-gaturro")) el.hidden = pulido && SOBRA.some((r) => r.test(el.textContent));
  for (const el of document.querySelectorAll("#lista-vacia, #resumen")) {
    if (el.dataset.original === undefined || (el.textContent !== el.dataset.original && el.textContent !== CORTOS[el.dataset.original])) el.dataset.original = el.textContent;
    const corto = CORTOS[el.dataset.original];
    const texto = pulido && corto !== undefined ? corto : el.dataset.original;
    if (el.textContent !== texto) el.textContent = texto;
  }
  // Los textos largos de ayuda quedan en un renglón; el resto, al pasar el mouse.
  for (const el of document.querySelectorAll("#aviso-npc, #ayuda-base, .dialogo-imagen p.ayuda")) if (el.textContent) el.title = el.textContent;
}

// ============ Cargas: un esqueleto con la forma de lo que viene, sobre todo lo que carga ============

// Qué espera cada pedido al núcleo.
const QUE_CARGA = {
  // (Las imágenes de cada Item tienen su propio brillo: no tapan la grilla.)
  items_de_swfs: "grilla", decoracion_de_swfs: "grilla", items_base: "bases",
  comportamientos: "npc", fondos: "npc", buscar_comportamientos_en_el_juego: "npc", comportamiento: "npc",
  gaturro: "gaturro", animacion_de_accion: "gaturro",
  generar_encode: "encode", interpretar_items: "encode", importar_encode: "lista",
  buscar_por_imagen: "imagen", estado_entorno: "entorno",
};
const visible = (el) => Boolean(el) && el.offsetParent !== null && el.getBoundingClientRect().width > 0;
const abierto = (id) => Boolean($id(id)?.open);
// Dónde va el esqueleto de cada cosa, y con qué forma.
const DONDE = {
  grilla: () => abierto("dialogo-base") ? { el: $id("lista-bases"), forma: "filas" }
    : { el: [$id("grilla-items"), $id("grilla-piezas")].find(visible), forma: "tarjetas" },
  bases: () => ({ el: $id("lista-bases"), forma: "filas" }),
  npc: () => ({ el: $id("grilla-comportamientos"), forma: "tarjetas" }),
  gaturro: () => abierto("dialogo-mis-looks") ? {} : { el: $id("gaturro"), forma: "gaturro" },
  encode: () => ({ el: $id("encode"), forma: "renglones" }),
  lista: () => ({ el: $id("lista"), forma: "filas" }),
  imagen: () => ({ el: $id("resultados-imagen"), forma: "tarjetas" }),
  entorno: () => abierto("dialogo-entorno") ? { el: $id("componentes"), forma: "filas" } : {},
};

const regiones = new Map(); // clave → { buscar, el, capa, desde }
const enCurso = new Map();

function empezar(clave, buscar) {
  enCurso.set(clave, (enCurso.get(clave) ?? 0) + 1);
  if (!regiones.has(clave)) regiones.set(clave, { buscar, capa: null, desde: performance.now() });
}
function terminar(clave) {
  const n = (enCurso.get(clave) ?? 1) - 1;
  enCurso.set(clave, Math.max(0, n));
  if (n > 0) return;
  const region = regiones.get(clave);
  if (!region) return;
  regiones.delete(clave);
  const capa = region.capa;
  region.el?.classList.remove("bajo-esqueleto");
  capa?.classList.add("saliendo");
  setTimeout(() => capa?.remove(), 220);
}

// Cada función del núcleo avisa cuándo empieza y termina. Se envuelve en la fase de captura de «pywebviewready»,
// antes de que la interfaz haga sus primeros pedidos.
function envolver(objeto, adentro = false) {
  for (const [nombre, valor] of Object.entries(objeto ?? {})) {
    if (typeof valor === "function") {
      if (valor.__prototipo || !(QUE_CARGA[nombre] || nombre === "preparar_iconos")) continue;
      const envuelta = async (...args) => {
        // preparar_iconos(swf) lista las Piezas de un SWF (la grilla); sin SWF solo prepara imágenes, que tienen su brillo.
        const forma = nombre === "preparar_iconos" ? (args[0] ? "grilla" : null) : QUE_CARGA[nombre];
        if (!forma) return valor.apply(objeto, args);
        empezar(`api:${forma}`, DONDE[forma]);
        try { return await valor.apply(objeto, args); } finally { terminar(`api:${forma}`); }
      };
      envuelta.__prototipo = true;
      objeto[nombre] = envuelta;
    } else if (valor && typeof valor === "object" && !adentro) envolver(valor, true);
  }
}
window.addEventListener("pywebviewready", () => envolver(window.pywebview?.api), true);
if (window.pywebview?.api) envolver(window.pywebview.api);

// Lo que la interfaz escribe como «Leyendo…» también es una carga: en su lugar va el esqueleto.
const ES_CARGA = /^(Leyendo|Preparando|Buscando|Bajando|Aplicando|Revisando|Cerrando programas)\b/;
const textoPropio = (el) => [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.nodeValue).join("").trim();
const textosDeCarga = new Set();
function buscarTextosDeCarga(raiz) {
  for (const el of [raiz, ...raiz.querySelectorAll("*")]) {
    if (textosDeCarga.has(el) || el.closest("[data-sin-iconos], .barra-prototipo") || !ES_CARGA.test(textoPropio(el))) continue;
    textosDeCarga.add(el);
    el.classList.add("texto-de-carga");
    const contenedor = el.closest("#grilla-items, #grilla-piezas, #grilla-comportamientos, #lista-bases, #componentes, #resultados-imagen");
    const delGaturro = el.id === "estado-gaturro";
    const forma = delGaturro ? "gaturro" : !contenedor ? "linea" : contenedor.matches("#lista-bases, #componentes") ? "filas" : "tarjetas";
    empezar(el, () => ({ el: delGaturro ? $id("gaturro") : contenedor ?? el, forma }));
  }
}
function revisarTextosDeCarga() {
  for (const el of textosDeCarga) {
    if (el.isConnected && ES_CARGA.test(textoPropio(el))) continue;
    textosDeCarga.delete(el);
    el.classList.remove("texto-de-carga");
    enCurso.set(el, 1);
    terminar(el);
  }
}

// El fondo de verdad detrás de un elemento, para tapar lo que había mientras carga.
function fondoDe(el) {
  for (let x = el; x; x = x.parentElement) {
    const v = (getComputedStyle(x).backgroundColor.match(/[\d.]+/g) || []).map(Number);
    if (v.length >= 3 && (v[3] === undefined || v[3] > 0.6)) return `rgb(${v[0]}, ${v[1]}, ${v[2]})`;
  }
  return "#4f9a3a";
}

function armarCapa(region, el, forma) {
  const capa = document.createElement("div");
  capa.className = `capa-carga forma-${forma}`;
  capa.dataset.sinIconos = "";
  const r0 = el.getBoundingClientRect();
  const r = r0.height >= 60 || !el.parentElement ? r0 : { width: r0.width, height: Math.max(60, el.parentElement.getBoundingClientRect().bottom - r0.top - 10) };
  if (forma === "tarjetas") {
    // La misma grilla que la de verdad: las tarjetas vacías tienen el tamaño de las que vienen.
    const estilo = getComputedStyle(el);
    const esGrilla = estilo.display.includes("grid");
    const columnas = esGrilla ? estilo.gridTemplateColumns.split(" ").length : Math.max(1, Math.floor(r.width / 90));
    const filas = esGrilla && estilo.gridTemplateRows !== "none" ? Math.min(6, estilo.gridTemplateRows.split(" ").length) : Math.max(1, Math.floor(r.height / 110));
    capa.style.gridTemplateColumns = `repeat(${columnas}, minmax(0, 1fr))`;
    capa.style.gridTemplateRows = `repeat(${filas}, minmax(0, 1fr))`;
    capa.style.gap = estilo.rowGap && estilo.rowGap !== "normal" ? `${estilo.rowGap} ${estilo.columnGap}` : "8px";
    capa.innerHTML = Array.from({ length: columnas * filas }, (_, i) =>
      `<span class="tarjeta-esqueleto" style="--i:${(i % columnas) + Math.floor(i / columnas)}"><span class="img"></span><span class="txt"></span><span class="txt corto"></span></span>`).join("");
  } else if (forma === "filas") {
    const n = Math.max(2, Math.min(10, Math.floor(r.height / 48)));
    capa.innerHTML = Array.from({ length: n }, (_, i) => `<span class="fila-esqueleto" style="--i:${i}"><span class="img"></span><span class="txt"></span></span>`).join("");
  } else if (forma === "renglones") {
    capa.innerHTML = Array.from({ length: 3 }, (_, i) => `<span class="renglon-esqueleto" style="--i:${i}"></span>`).join("");
  } else if (forma === "gaturro") {
    capa.innerHTML = `<span class="gaturro-esqueleto"></span><span class="sombra-esqueleto"></span>`;
  } else {
    capa.innerHTML = `<span class="linea-esqueleto"></span>`;
  }
  capa.style.setProperty("--fondo-capa", fondoDe(forma === "gaturro" ? el.parentElement : el));
  document.body.append(capa);
  region.capa = capa;
  region.el = el;
}

// En cada cuadro, las capas siguen a lo que tapan (si se mueve, cambia de tamaño o se esconde).
function cuadro() {
  revisarTextosDeCarga();
  const conEsqueleto = html.dataset.carga === "esqueleto";
  for (const region of regiones.values()) {
    if (!conEsqueleto || performance.now() - region.desde < 120) continue; // lo que tarda poco no parpadea
    const { el, forma } = region.buscar?.() ?? {};
    if (!visible(el)) { region.capa?.remove(); region.capa = null; continue; }
    if (!region.capa || region.el !== el) { region.capa?.remove(); region.el?.classList.remove("bajo-esqueleto"); armarCapa(region, el, forma); }
    el.classList.add("bajo-esqueleto");
    const r = el.getBoundingClientRect();
    const alto = r.height >= 60 || !el.parentElement ? r.height : Math.max(60, el.parentElement.getBoundingClientRect().bottom - r.top - 10);
    Object.assign(region.capa.style, { left: `${r.left}px`, top: `${r.top}px`, width: `${r.width}px`, height: `${alto}px` });
  }
  requestAnimationFrame(cuadro);
}
requestAnimationFrame(cuadro);

// «Probar carga»: 4 segundos de carga en la grilla visible y en el Gaturro, sin esperar una de verdad.
function probarCarga() {
  empezar("prueba:grilla", DONDE.grilla);
  empezar("prueba:npc", DONDE.npc);
  empezar("prueba:gaturro", DONDE.gaturro);
  setTimeout(() => ["prueba:grilla", "prueba:npc", "prueba:gaturro"].forEach(terminar), 4000);
}

// ============ Todo lo que la interfaz agrega después también pasa por acá ============

let vueltas = 0;
setInterval(() => { vueltas = 0; }, 1000);
const observador = new MutationObserver((cambios) => {
  if (++vueltas > 2000) {
    observador.disconnect();
    window.__ronda = cambios.slice(0, 8).map((c) => `${c.target.id || c.target.className || c.target.tagName} +${[...c.addedNodes].map((n) => n.nodeType === 3 ? JSON.stringify(n.nodeValue.slice(0, 30)) : (n.className || n.tagName)).join(",")} -${c.removedNodes.length}`);
    return;
  }
  // Una tanda puede traer miles de filas («Agregar todos»): lo de cada fila tiene que costar poco y no depender de
  // cuántas hay; lo de toda la página, una vez por tanda.
  let hubo = false;
  for (const c of cambios) {
    for (const n of c.addedNodes) {
      const el = n.nodeType === 3 ? n.parentElement : n;
      if (!el || el.nodeType !== 1 || el.closest(".barra-prototipo, .capa-carga")) continue;
      hubo = true;
      cambiarEmojis(el);
      buscarTextosDeCarga(el);
      if (el.tagName === "LI") el.style.setProperty("--n", posicionHasta20(el));
    }
  }
  if (hubo) pulirTextos(document.body);
});
// La animación de entrada solo escalona las primeras 20: más atrás no hace falta mirar.
function posicionHasta20(el) {
  let i = 0;
  for (let x = el.previousElementSibling; x && i < 20; x = x.previousElementSibling) i++;
  return i;
}
observador.observe(document.body, { childList: true, subtree: true });

cambiarEmojis(document.body);
buscarTextosDeCarga(document.body);
aplicarVariantes();
window.prototipo = { elegido, aplicarVariantes, probarCarga, observador, regiones, enCurso };
})();
