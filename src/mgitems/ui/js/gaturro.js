// El Gaturro original del juego con las Piezas del Look, y «Elige tus colores».

// --- El Gaturro original del juego con las Piezas del Look ---

// Colores del Gaturro (como en el juego: cara, cuerpo, ojos, nariz). Cada Look tiene los suyos; los que no
// tiene, los de fábrica del juego.
let coloresDeFabrica = { color1: "#FFF200", color2: "#DDB42D", color3: "#FFFFFF", color4: "#FB8CBB" };
const CLAVES_COLOR = ["color1", "color2", "color3", "color4"];
const coloresDe = (look) => ({ ...coloresDeFabrica, ...(look?.colores ?? {}) });

// Si se piden varios seguidos, se muestra solo el último (cada imagen lleva su propio contador).
const pedidosGaturro = new Map();
// El SVG encuadrado en el CUERPO del Gaturro (sin las Piezas), así todos los Gaturros se ven del mismo
// tamaño. `zoom` 1 es "grande" (el cuerpo llena el cuadro); menos aleja (se ven enteras las Piezas
// grandes, como un vestido puesto en los pies), más acerca. Se mide dibujándolo un momento fuera de la vista.
function encuadrar(svg, zoom = 1) {
  const documento = new DOMParser().parseFromString(svg, "image/svg+xml");
  const raiz = documento.documentElement;
  if (raiz.nodeName !== "svg") return svg;
  const medidor = document.createElement("div");
  medidor.style.cssText = "position:absolute;left:-10000px;top:0;width:10px;height:10px;overflow:hidden;visibility:hidden";
  const copia = document.importNode(raiz, true);
  copia.querySelectorAll("[data-parte]").forEach((pieza) => pieza.setAttribute("display", "none"));
  medidor.append(copia);
  document.body.append(medidor);
  try {
    const caja = copia.getBBox();
    if (!caja.width || !caja.height) return svg;
    const lado = (Math.max(caja.width, caja.height) * 1.12) / zoom;
    const x = caja.x + caja.width / 2 - lado / 2;
    const y = caja.y + caja.height / 2 - lado / 2;
    raiz.setAttribute("viewBox", `${x} ${y} ${lado} ${lado}`);
    raiz.removeAttribute("width");
    raiz.removeAttribute("height");
    return new XMLSerializer().serializeToString(documento);
  } catch {
    return svg;
  } finally {
    medidor.remove();
  }
}

// Zoom de cada imagen del Gaturro (data-zoom); el SVG recibido se guarda para cambiar el zoom sin pedirlo otra vez.
const svgsGaturro = new WeakMap();
function mostrarGaturroEn(img) {
  const svg = svgsGaturro.get(img);
  if (svg) img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(encuadrar(svg, Number(img.dataset.zoom) || 1));
}

async function pedirGaturro(img, colores, partes = lookActual.partes, emote = null) {
  const pedido = (pedidosGaturro.get(img) ?? 0) + 1;
  pedidosGaturro.set(img, pedido);
  const resultado = await api().gaturro({ ...partes }, colores, emote);
  if (pedidosGaturro.get(img) !== pedido) return null;
  img.hidden = !resultado.ok; // sin el Gaturro original no se muestra ninguno
  if (resultado.ok) {
    svgsGaturro.set(img, resultado.svg);
    mostrarGaturroEn(img);
    coloresDeFabrica = resultado.colores_de_fabrica;
  }
  return resultado;
}

// El Gaturro de la tarjeta (Looks, Trucar Prenda y Acciones).
const gaturroDelLook = gaturroVivo($("gaturro-vivo"));
// Los de las ventanas: el escenario de los guardados y «Elige tus colores».
const gaturroDelEscenario = gaturroVivo($("vivo-mis-looks"));
const gaturroDeColores = gaturroVivo($("gaturro-colores"));
cerrarAlRatoDeCerrarse($("dialogo-mis-looks"), () => gaturroDelEscenario.cerrar());
cerrarAlRatoDeCerrarse($("dialogo-colores"), () => gaturroDeColores.cerrar());
const mostrarColoresEnEdicion = () => gaturroDeColores.vestir(lookActual.partes, coloresEnEdicion, lookActual.emote ?? null);

// La acción que hace el Gaturro de un documento: solo en Acciones (en las demás pestañas se ve quieto).
const animacionDe = (documento) => (vista === "acciones" ? documento.animacion || null : null);
const vestirCon = (gaturro, documento) => gaturro.vestir(documento.partes, coloresDe(documento), documento.emote ?? null,
  animacionDe(documento), documento.personalizacion ?? null);

async function dibujarGaturro() {
  if (esNpc()) return; // en Tiendas y Portales no hay Gaturro
  const resultado = await conEsqueleto($("gaturro"), "gaturro", () => vestirCon(gaturroDelLook, lookActual));
  if (!resultado) return;
  $("repetir-accion").hidden = !(resultado.ok && animacionDe(lookActual));
  $("gaturro-vivo").hidden = !resultado.ok; // si no se pudo abrir, no se muestra ninguno
  if (!resultado.ok) {
    $("estado-gaturro").textContent = resultado.error;
    return;
  }
  coloresDeFabrica = resultado.colores_de_fabrica;
  const avisos = resultado.no_se_ven.map((n) => `No se ve en el juego: ${claseDeRuta(n.ruta)} (${n.motivo}).`);
  $("estado-gaturro").replaceChildren(...avisos.map((a) => Object.assign(etiqueta(a, "aviso-gaturro"), { title: a })));
}

// --- "Elige tus colores": un selector de tono + saturación y brillo por color, como en el juego ---

function hexAHsv(hex) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const max = Math.max(r, g, b);
  const d = max - Math.min(r, g, b);
  const h = d === 0 ? 0 : max === r ? ((g - b) / d + 6) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return { h: h * 60, s: max === 0 ? 0 : d / max, v: max };
}

function hsvAHex({ h, s, v }) {
  const f = (n) => {
    const k = (n + h / 60) % 6;
    return v - v * s * Math.max(0, Math.min(k, 4 - k, 1));
  };
  return "#" + [f(5), f(3), f(1)].map((x) => Math.round(x * 255).toString(16).padStart(2, "0")).join("").toUpperCase();
}

let coloresEnEdicion = {};
const selectoresColor = {};

// Arrastrar dentro de un elemento: llama a `mover(x, y)` con la posición entre 0 y 1.
function arrastrable(elemento, mover) {
  const actualizar = (e) => {
    const caja = elemento.getBoundingClientRect();
    mover(Math.min(Math.max((e.clientX - caja.left) / caja.width, 0), 1), Math.min(Math.max((e.clientY - caja.top) / caja.height, 0), 1));
  };
  elemento.addEventListener("pointerdown", (e) => {
    try {
      elemento.setPointerCapture(e.pointerId);
    } catch {}
    actualizar(e);
  });
  elemento.addEventListener("pointermove", (e) => {
    if (elemento.hasPointerCapture(e.pointerId)) actualizar(e);
  });
}

function crearSelectorColor(contenedor) {
  const clave = contenedor.dataset.color;
  const tono = Object.assign(document.createElement("div"), { className: "barra-tono" });
  const marcaTono = Object.assign(document.createElement("span"), { className: "marca-color" });
  tono.append(marcaTono);
  const cuadro = Object.assign(document.createElement("div"), { className: "cuadro-color" });
  const marcaCuadro = Object.assign(document.createElement("span"), { className: "marca-color" });
  cuadro.append(marcaCuadro);
  const zona = Object.assign(document.createElement("div"), { className: "zona-color" });
  zona.append(tono, cuadro);
  contenedor.append(zona);
  let hsv = { h: 0, s: 0, v: 1 };

  const pintar = () => {
    cuadro.style.backgroundColor = hsvAHex({ h: hsv.h, s: 1, v: 1 });
    marcaTono.style.top = `${(hsv.h / 360) * 100}%`;
    marcaCuadro.style.left = `${hsv.s * 100}%`;
    marcaCuadro.style.top = `${(1 - hsv.v) * 100}%`;
    marcaCuadro.style.backgroundColor = hsvAHex(hsv);
  };
  const cambiar = () => {
    pintar();
    coloresEnEdicion[clave] = hsvAHex(hsv);
    mostrarColoresEnEdicion();
  };
  arrastrable(tono, (_, y) => {
    hsv = { ...hsv, h: Math.min(y * 360, 359.9) };
    cambiar();
  });
  arrastrable(cuadro, (x, y) => {
    hsv = { ...hsv, s: x, v: 1 - y };
    cambiar();
  });
  selectoresColor[clave] = {
    mostrar(hex) {
      hsv = hexAHsv(hex);
      pintar();
    },
  };
}

document.querySelectorAll(".selector-color").forEach(crearSelectorColor);

function mostrarSelectoresColor() {
  for (const [clave, selector] of Object.entries(selectoresColor)) selector.mostrar(coloresEnEdicion[clave] ?? "#F49AC1");
}

$("colores-look").addEventListener("click", () => {
  coloresEnEdicion = coloresDe(lookActual);
  mostrarSelectoresColor();
  mostrarColoresEnEdicion();
  $("dialogo-colores").showModal();
});
$("reiniciar-colores").addEventListener("click", () => {
  coloresEnEdicion = { ...coloresDeFabrica };
  mostrarSelectoresColor();
  mostrarColoresEnEdicion();
});
// GUARDAR: los colores pasan a ser del Look abierto (se guardan con «Guardar el Look», como cualquier cambio).
$("guardar-colores").addEventListener("click", () => {
  lookActual.colores = Object.fromEntries(CLAVES_COLOR.map((c) => [c, coloresEnEdicion[c]]));
  $("dialogo-colores").close();
  dibujarGaturro();
  avisarLista(lookActual.id ? "Colores cambiados: guardá el Look para conservarlos." : "Colores cambiados.", "exito");
});
$("aplicar-colores").addEventListener("click", async () => {
  const colores = Object.fromEntries(CLAVES_COLOR.map((c) => [c, coloresEnEdicion[c]]).filter(([, v]) => v));
  const resultado = await mientras("Generando Encode de colores…", () => api().aplicar_colores(colores));
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  lookActual.colores = Object.fromEntries(CLAVES_COLOR.map((c) => [c, coloresEnEdicion[c]]));
  $("dialogo-colores").close();
  dibujarGaturro();
  mostrarEncode(resultado);
  avisarLista("Colores generados: recibí el Encode en el juego para aplicarlos.", "exito");
});
$("cerrar-colores").addEventListener("click", () => $("dialogo-colores").close());
