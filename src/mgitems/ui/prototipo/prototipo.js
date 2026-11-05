// PROTOTIPO (rama prototipo-ui, no va a main): variantes de cargas, letras, nombres de Items, íconos y toques,
// sobre el programa real. La barra de abajo cambia cada una; lo elegido queda en <html data-…>.

// Todo en su propio ámbito: los <script> de la interfaz comparten el global y un nombre igual pisaría al suyo.
(() => {
const EJES = [
  { id: "carga", nombre: "Cargas", variantes: [["texto", "Texto (actual)"], ["huellitas", "Huellitas"], ["ovillo", "Ovillo"], ["esqueleto", "Esqueleto"]] },
  { id: "letra", nombre: "Letra", variantes: [["actual", "Cooper (actual)"], ["fredoka", "Fredoka"], ["nunito", "Nunito + Cooper"], ["baloo", "Baloo"]] },
  { id: "nombres", nombre: "Nombres", variantes: [["actual", "Técnico (actual)"], ["legible", "Legible"], ["rotulo", "Rótulo"], ["ficha", "Ficha"]] },
  { id: "iconos", nombre: "Íconos", variantes: [["emoji", "Emojis (actual)"], ["relleno", "Relleno"], ["trazo", "Trazo"], ["duotono", "Duotono"]] },
  { id: "toques", nombre: "Toques", variantes: [["no", "Sin (actual)"], ["si", "Animados"]] },
];

const elegido = (() => {
  try { return JSON.parse(localStorage.getItem("prototipo-ui")) || {}; } catch { return {}; }
})();
let ejeActivo = "carga";

function aplicarVariantes() {
  for (const eje of EJES) document.documentElement.dataset[eje.id] = elegido[eje.id] ?? eje.variantes[0][0];
  const dibujo = document.documentElement.dataset.carga === "ovillo" ? ICONOS_PROTOTIPO.yarn.fill : ICONOS_PROTOTIPO["paw-print"].fill;
  document.documentElement.style.setProperty("--mascara-carga",
    `url("data:image/svg+xml,${encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 256 256'>${dibujo}</svg>`)}")`);
  try { localStorage.setItem("prototipo-ui", JSON.stringify(elegido)); } catch {}
  pintarBarra();
  repintarIconos();
  repintarNombres();
  repintarCargas();
}

function cambiar(ejeId, paso) {
  const eje = EJES.find((e) => e.id === ejeId);
  const actual = eje.variantes.findIndex(([v]) => v === document.documentElement.dataset[ejeId]);
  elegido[ejeId] = eje.variantes[(actual + paso + eje.variantes.length) % eje.variantes.length][0];
  ejeActivo = ejeId;
  aplicarVariantes();
}

// --- La barra flotante ---

const barra = document.createElement("div");
barra.className = "barra-prototipo";
barra.dataset.sinIconos = "";
document.body.append(barra);

function pintarBarra() {
  barra.replaceChildren(
    Object.assign(document.createElement("strong"), { textContent: "PROTOTIPO" }),
    ...EJES.map((eje) => {
      const grupo = document.createElement("span");
      grupo.className = "grupo-prototipo" + (eje.id === ejeActivo ? " activo" : "");
      const valor = document.documentElement.dataset[eje.id];
      const [, nombre] = eje.variantes.find(([v]) => v === valor);
      const boton = (texto, paso) => {
        const b = Object.assign(document.createElement("button"), { textContent: texto, type: "button" });
        b.addEventListener("click", () => cambiar(eje.id, paso));
        return b;
      };
      grupo.append(boton("‹", -1), Object.assign(document.createElement("span"), { textContent: `${eje.nombre}: ${nombre}` }), boton("›", 1));
      grupo.addEventListener("click", () => { ejeActivo = eje.id; pintarBarra(); });
      return grupo;
    }),
    (() => {
      const b = Object.assign(document.createElement("button"), { textContent: "Probar carga", type: "button", title: "Muestra 4 segundos una carga en la grilla" });
      b.addEventListener("click", probarCarga);
      return b;
    })()
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

// --- Íconos: cada emoji pasa a un <span class="pi"> que muestra el emoji o el ícono según la variante ---

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
// Las ventanas que copian las del juego quedan idénticas al juego.
const SIN_CAMBIOS = "#dialogo-mis-looks, #dialogo-colores, [data-sin-iconos], option, select, textarea, title, script, style";
const ESTILO = { relleno: "fill", trazo: "bold", duotono: "duotone" };

function iconoSvg(nombre) {
  const estilo = ESTILO[document.documentElement.dataset.iconos];
  if (!estilo) return "";
  return `<svg viewBox="0 0 256 256" fill="currentColor" aria-hidden="true">${ICONOS_PROTOTIPO[nombre]?.[estilo] ?? ""}</svg>`;
}

function pintarIcono(span) {
  const conIcono = document.documentElement.dataset.iconos !== "emoji";
  span.innerHTML = conIcono ? iconoSvg(span.dataset.icono) : "";
  if (!conIcono) span.textContent = span.dataset.emoji;
}

function cambiarEmojis(raiz) {
  const recorrido = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT);
  const nodos = [];
  for (let n = recorrido.nextNode(); n; n = recorrido.nextNode()) {
    if (PATRON_EMOJI.test(n.nodeValue) && !n.parentElement?.closest(SIN_CAMBIOS) && !n.parentElement?.closest(".pi")) nodos.push(n);
    PATRON_EMOJI.lastIndex = 0;
  }
  for (const nodo of nodos) {
    const partes = document.createDocumentFragment();
    let ultimo = 0;
    for (const m of nodo.nodeValue.matchAll(PATRON_EMOJI)) {
      partes.append(nodo.nodeValue.slice(ultimo, m.index));
      const span = document.createElement("span");
      span.className = "pi";
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
const repintarIconos = () => document.querySelectorAll(".pi").forEach(pintarIcono);

// --- Nombres: «jugoDurazno» → «Jugo durazno»; el nombre técnico queda debajo (Ficha) o al pasar el mouse ---

function nombreLegible(clase) {
  const limpio = clase.replace(/_/g, " ").replace(/([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])/g, "$1 $2").replace(/([a-zA-Z])(\d)/g, "$1 $2")
    .replace(/(\d)([a-zA-Z])/g, "$1 $2").replace(/\s+/g, " ").trim().toLowerCase();
  return limpio.charAt(0).toUpperCase() + limpio.slice(1);
}

function pintarNombre(el) {
  if (!el.dataset.tecnico) el.dataset.tecnico = el.textContent;
  const variante = document.documentElement.dataset.nombres;
  el.textContent = variante === "actual" ? el.dataset.tecnico : nombreLegible(el.dataset.tecnico);
  el.title = el.dataset.tecnico;
}
const repintarNombres = () => document.querySelectorAll(".nombre-item").forEach(pintarNombre);

// --- Cargas: los textos de «Leyendo…», «Preparando…» llevan una animación delante ---

const ES_CARGA = /^(Leyendo|Preparando|Buscando|Bajando|Aplicando|Revisando|Cerrando programas)\b/;

function animacionDeCarga() {
  const caja = document.createElement("span");
  caja.className = "animacion-carga";
  caja.dataset.sinIconos = "";
  const variante = document.documentElement.dataset.carga;
  if (variante === "huellitas") {
    caja.innerHTML = Array.from({ length: 5 }, (_, i) =>
      `<svg class="huella" style="--i:${i}" viewBox="0 0 256 256" fill="currentColor">${ICONOS_PROTOTIPO["paw-print"].fill}</svg>`).join("");
  } else if (variante === "ovillo") {
    caja.innerHTML = `<svg class="hilo" viewBox="0 0 120 40"><path d="M2 30 C 20 10, 35 38, 55 22 S 85 8, 100 26" /></svg>
      <span class="ovillo"><svg viewBox="0 0 256 256">${ICONOS_PROTOTIPO.yarn.duotone}</svg></span><span class="sombra-ovillo"></span>`;
  } else if (variante === "esqueleto") {
    caja.innerHTML = `<svg class="estrella-carga" viewBox="0 0 256 256" fill="currentColor">${ICONOS_PROTOTIPO.star.fill}</svg>`;
  }
  return caja;
}

function marcarCarga(el) {
  el.querySelector(":scope > .animacion-carga")?.remove();
  el.querySelector(":scope > .esqueleto-grilla")?.remove();
  const variante = document.documentElement.dataset.carga;
  el.classList.toggle("con-carga", variante !== "texto");
  el.classList.toggle("carga-grande", Boolean(el.closest(".grilla, .grilla-comportamientos, #grilla-items, #grilla-piezas")));
  if (variante === "texto") return;
  el.prepend(animacionDeCarga());
  // En una grilla, el esqueleto dibuja tarjetas vacías con brillo, con la forma de lo que viene.
  if (variante === "esqueleto" && el.closest(".grilla, .grilla-comportamientos, #grilla-items, #grilla-piezas")) {
    const tarjetas = document.createElement("span");
    tarjetas.className = "esqueleto-grilla";
    tarjetas.innerHTML = Array.from({ length: 12 }, () => '<span class="tarjeta-esqueleto"><span></span><span></span></span>').join("");
    el.append(tarjetas);
  }
}

function buscarCargas(raiz) {
  const candidatos = raiz.nodeType === 1 ? [raiz, ...raiz.querySelectorAll("*")] : [];
  for (const el of candidatos) {
    if (el.closest("[data-sin-iconos]")) continue;
    const propio = [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.nodeValue).join("").trim();
    const esCarga = ES_CARGA.test(propio);
    if (esCarga && !el.querySelector(":scope > .animacion-carga")) { el.classList.add("es-carga"); marcarCarga(el); }
    if (!esCarga && el.classList.contains("es-carga")) {
      el.classList.remove("es-carga", "con-carga");
      el.querySelectorAll(":scope > .animacion-carga, :scope > .esqueleto-grilla").forEach((x) => x.remove());
    }
  }
}
const repintarCargas = () => document.querySelectorAll(".es-carga").forEach(marcarCarga);

// «Probar carga»: pone 4 segundos un mensaje de carga en la grilla visible, para ver la animación sin esperar.
function probarCarga() {
  const grilla = [...document.querySelectorAll("#grilla-items, #grilla-piezas, #grilla-comportamientos")].find((g) => g.offsetParent);
  if (!grilla) return;
  const antes = [...grilla.childNodes];
  const li = Object.assign(document.createElement("li"), { className: "ayuda", textContent: "Leyendo los Items de todos los SWF…" });
  grilla.replaceChildren(li);
  setTimeout(() => grilla.replaceChildren(...antes), 4000);
}

// --- Todo lo que la interfaz agrega después también pasa por acá ---

new MutationObserver((cambios) => {
  for (const c of cambios) {
    for (const n of c.addedNodes) {
      if (n.nodeType === 3) { if (n.parentElement) { cambiarEmojis(n.parentElement); buscarCargas(n.parentElement); } continue; }
      if (n.nodeType !== 1 || n.closest?.(".barra-prototipo")) continue;
      cambiarEmojis(n);
      buscarCargas(n);
      if (n.tagName === "LI" && n.parentElement) n.style.setProperty("--n", [...n.parentElement.children].indexOf(n));
      if (n.classList?.contains("nombre-item")) pintarNombre(n);
      n.querySelectorAll?.(".nombre-item").forEach(pintarNombre);
    }
    if (c.type === "characterData" && c.target.parentElement?.classList.contains("nombre-item")) {
      const el = c.target.parentElement;
      if (el.textContent !== nombreLegible(el.dataset.tecnico ?? "") && el.textContent !== el.dataset.tecnico) { delete el.dataset.tecnico; pintarNombre(el); }
    }
  }
}).observe(document.body, { childList: true, subtree: true, characterData: true });

cambiarEmojis(document.body);
buscarCargas(document.body);
aplicarVariantes();
window.prototipo = { elegido, aplicarVariantes, probarCarga };
})();
