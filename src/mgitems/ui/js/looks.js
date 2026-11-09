// Looks: un Item base con una Pieza en cada Parte del cuerpo; «Mis Looks» y los casilleros.

// --- Looks: un Item base con una Pieza (de cualquier SWF) en cada una de varias Partes del cuerpo ---
// La pestaña se acomoda como el inventario del juego: el Gaturro a la izquierda, el inventario a la derecha.

let looksGuardados = [];
let lookActual = nuevoLook();
let partesConocidas = []; // [{id, nombre}]
let iconosPreparados = new Set(); // SWF cuyas imágenes ya se pidieron preparar

function nuevoLook() {
  return { id: "", nombre: "", base: null, partes: {}, colores: {}, emote: null };
}

async function prepararIconosDe(swf) {
  if (iconosPreparados.has(swf)) return;
  iconosPreparados.add(swf);
  preparandose.add(swf);
  let resultado;
  try {
    resultado = await api().preparar_iconos(swf);
  } finally {
    preparandose.delete(swf);
    document.querySelectorAll(".icono[data-ruta]").forEach(pintarIcono);
  }
  if (!resultado.ok) return;
  for (const ruta of [...imagenes.keys()]) if (ruta.startsWith(swf + ".")) imagenes.delete(ruta);
  cargarIconos([...document.querySelectorAll(".icono[data-ruta]")].map((c) => c.dataset.ruta));
}

const swfDeRuta = (ruta) => ruta.slice(0, ruta.lastIndexOf("."));
const claseDeRuta = (ruta) => ruta.slice(ruta.lastIndexOf(".") + 1);
// Las Partes que usan algunas Prendas y no tienen casillero en Looks (en Trucar Prenda van como casilleros extra).
const NOMBRES_DE_OTRAS_PARTES = {
  action: "Pieza de la acción", clothFront: "Torso de adelante", armFore: "Brazo de adelante", armBack: "Brazo de atrás",
  glove: "Guante", gloveFore: "Guante de adelante", gloveBack: "Guante de atrás", gripBack: "Mano de atrás",
};
const nombreDeParte = (id) => NOMBRES_DE_OTRAS_PARTES[id] ?? partesConocidas.find((p) => p.id === id)?.nombre ?? id;

// Los guardados de la pestaña (botón, ventana, guardar, descartar y borrar).
const guardados = () => dePestana().guardados;
// Una operación de los guardados de la pestaña: lista, guardar, duplicar, borrar, exportar o importar.
const llamarGuardados = (operacion, ...args) => api().guardados[operacion](guardados().tipo, ...args);
const documentoNuevo = (pestana = vista) => dePestana(pestana).nuevo();
const guardadoDe = (resultado) => resultado.documento;
// Lo que queda en el editor al abrir un guardado (o uno nuevo). En Trucar Prenda va al armado, con su Parte,
// y la lista de las que se reciben juntas sigue como estaba.
const enElEditor = (documento) => vista === "trucar"
  ? { ...nuevaPrendaATrucar(), ...structuredClone(documento), parte: Object.keys(documento.partes)[0] ?? lookActual.parte, lista: lookActual.lista }
  : esNpc() ? { ...documentoNuevo(), ...structuredClone(documento), lista: lookActual.lista }
  : structuredClone(documento);
// Lo que se dibuja quieto (miniaturas, escenario): en una acción, solo lo de la cabeza.
const partesQuietas = (documento) =>
  vista === "acciones" ? (documento.partes.effect ? { effect: documento.partes.effect } : {}) : documento.partes;
// Lo que se muestra de un guardado: el Gaturro, o en Tiendas y Portales, el Item que se convierte.
function mostrarGuardadoEn(img, documento) {
  if (!esNpc()) return pedirGaturro(img, coloresDe(documento), partesQuietas(documento));
  img.replaceWith(Object.assign(elementoIcono(documento.base), { title: documento.base }));
  cargarIconos([documento.base]);
}

async function cargarLooks() {
  if (!partesConocidas.length) partesConocidas = (await api().partes_del_cuerpo()).partes_del_cuerpo;
  const resultado = await llamarGuardados("lista");
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  looksGuardados = resultado.guardados;
  $("texto-mis-looks").textContent = guardados().mis;
  $("titulo-mis-looks").textContent = guardados().titulo;
  $("sub-mis-looks").textContent = guardados().sub;
  mostrarListaLooks();
  mostrarLook();
  if (!inventario.cargado && !esNpc()) await cargarInventario();
}

// --- Mis Looks: la ventana "Guarda tu Look", como en el juego ---

let lookElegido = null; // el Look tocado en la ventana (su id), o null
const ZOOM_MINIATURAS = "0.85"; // todas las miniaturas a la misma escala
const MINIMO_CASILLEROS = 9; // la grilla se completa con casilleros vacíos, como en el juego

function mostrarListaLooks() {
  $("cantidad-looks").textContent = looksGuardados.length ? `(${looksGuardados.length})` : "";
  $("look-abierto").textContent = lookActual.id ? `Editando «${lookActual.nombre}»` : lookActual.nombre ? `«${lookActual.nombre}» (sin guardar)` : `${guardados().nuevo} (sin guardar)`;
  if ($("dialogo-mis-looks").open) mostrarGrillaLooks();
}

function mostrarGrillaLooks() {
  const casilleros = looksGuardados.map((look) => {
    const li = document.createElement("li");
    const boton = Object.assign(document.createElement("button"), { type: "button", className: "casillero-look", title: look.nombre });
    boton.dataset.id = look.id;
    boton.setAttribute("aria-pressed", String(look.id === lookElegido));
    const miniatura = Object.assign(document.createElement("img"), { alt: look.nombre });
    miniatura.dataset.zoom = ZOOM_MINIATURAS;
    boton.append(miniatura, etiqueta(look.nombre, "nombre-casillero-look"));
    boton.addEventListener("click", () => elegirLook(look.id));
    boton.addEventListener("dblclick", () => equiparLook(look.id));
    mostrarGuardadoEn(miniatura, look);
    li.append(boton);
    return li;
  });
  const vacios = Math.max(0, MINIMO_CASILLEROS - 1 - casilleros.length);
  for (let i = 0; i < vacios; i++) casilleros.push(Object.assign(document.createElement("li"), { className: "casillero-vacio" }));
  $("grilla-looks").replaceChildren($("nuevo-look").parentElement, ...casilleros);
  mostrarLookElegido();
}

// El escenario muestra el Look puesto (el que se está editando, con sus cambios sin guardar) hasta que
// se toca otro de la grilla; «Volver al Look que tenés puesto» lo muestra de nuevo.
let mostrandoPuesto = true;

function mostrarLookElegido() {
  const look = looksGuardados.find((l) => l.id === lookElegido);
  document.querySelectorAll("#grilla-looks .casillero-look:not(.nuevo)").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.id === lookElegido)));
  $("exportar-look").disabled = $("duplicar-look").disabled = $("eliminar-look-elegido").disabled = !look;
  // En Tiendas y Portales se ve el Item, no un Gaturro.
  const mostrar = (documento) => {
    $("gaturro-mis-looks").hidden = esNpc() || !documento;
    $("icono-mis-looks").hidden = !esNpc() || !documento?.base;
    document.querySelector(".zoom-escenario").hidden = esNpc();
    if (!documento) return;
    if (esNpc()) {
      if (documento.base) $("icono-mis-looks").replaceChildren(elementoIcono(documento.base));
      cargarIconos(documento.base ? [documento.base] : []);
    } else {
      pedirGaturro($("gaturro-mis-looks"), coloresDe(documento), partesQuietas(documento));
    }
  };
  if (mostrandoPuesto) {
    $("nombre-look-elegido").textContent = `${lookActual.nombre || guardados().nuevo} (puesto)`;
    $("equipar-look").disabled = true; // ya está puesto
    mostrar(lookActual);
    return;
  }
  $("nombre-look-elegido").textContent = look ? look.nombre : `Tocá ${dePestana().tocaUno} para verlo`;
  $("equipar-look").disabled = !look;
  mostrar(look);
}

function elegirLook(id) {
  lookElegido = id;
  mostrandoPuesto = false;
  mostrarLookElegido();
}

function equiparLook(id) {
  const look = looksGuardados.find((l) => l.id === id);
  if (!look) return;
  $("dialogo-mis-looks").close();
  casilleroMarcado = null;
  abrirLook(look);
  avisarLista(`Se abrió ${guardados().el} «${look.nombre}».`, "exito");
}

// Al abrir se ve el Look puesto, como en el juego.
function verLookPuesto() {
  lookElegido = lookActual.id || null;
  mostrandoPuesto = true;
}

$("abrir-mis-looks").addEventListener("click", () => {
  verLookPuesto();
  $("dialogo-mis-looks").showModal();
  mostrarGrillaLooks();
});
$("reiniciar-look").addEventListener("click", () => {
  verLookPuesto();
  mostrarLookElegido();
});
// Las barritas de zoom: cambian el encuadre de su imagen sin volver a pedir el Gaturro.
for (const barra of [$("zoom-gaturro"), $("zoom-escenario")]) {
  barra.addEventListener("input", () => {
    const img = $(barra.dataset.img);
    img.dataset.zoom = barra.value;
    if (img === $("imagen-gaturro") && animacion) encuadrarAnimacion();
    else mostrarGaturroEn(img);
  });
}
// Elimina el Look elegido; si es el que se está editando, el editor queda con un Look nuevo.
$("eliminar-look-elegido").addEventListener("click", async () => {
  const look = looksGuardados.find((l) => l.id === lookElegido);
  if (!look || !confirm(`¿Eliminar ${guardados().el} «${look.nombre}»?`)) return;
  const resultado = await llamarGuardados("borrar", look.id);
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  const posicion = looksGuardados.indexOf(look);
  if (lookActual.id === look.id) {
    lookActual = enElEditor(documentoNuevo());
    mostrarLook();
  }
  const quedan = looksGuardados.filter((l) => l.id !== look.id);
  lookElegido = quedan[Math.min(posicion, quedan.length - 1)]?.id ?? null;
  mostrandoPuesto = !lookElegido;
  avisarLista(`Se eliminó «${look.nombre}».`, "exito");
  await cargarLooks();
});
$("equipar-look").addEventListener("click", () => equiparLook(lookElegido));
$("cancelar-mis-looks").addEventListener("click", () => $("dialogo-mis-looks").close());
$("cerrar-mis-looks").addEventListener("click", () => $("dialogo-mis-looks").close());

function abrirLook(look) {
  lookActual = enElEditor(look);
  mostrarListaLooks();
  mostrarLook();
  // Las imágenes de todas las Piezas del Look (pueden ser de varios SWF).
  for (const swf of new Set(Object.values(lookActual.partes).map(swfDeRuta))) prepararIconosDe(swf);
  if (lookActual.base) prepararIconosDe(swfDeRuta(lookActual.base));
}

function mostrarLook() {
  $("nombre-look").value = lookActual.nombre;
  const emoteActual = lookActual.emote ?? "";
  document.querySelectorAll(".emote-btn").forEach(btn => {
    btn.setAttribute("aria-pressed", btn.dataset.emote === emoteActual ? "true" : "false");
  });
  $("emote-preview").innerHTML = lookActual.emote
    ? `<img src="img/emotes/${lookActual.emote}.png" alt="${lookActual.emote}">`
    : "";
  const base = lookActual.base;
  $("base-look").replaceChildren(
    ...(base
      ? [elementoIcono(base), etiqueta(`${claseDeRuta(base)} (${swfDeRuta(base)})`, "nombre")]
      : [etiqueta(dePestana().sinBase, "ayuda")])
  );
  if (vista === "acciones") $("animacion-accion").value = lookActual.animacion ?? "";
  if (vista === "trucar") mostrarArmadoTrucar();
  if (esNpc()) mostrarArmadoNpc();
  mostrarCasilleros();
  cargarIconos([...Object.values(lookActual.partes), ...(base ? [base] : [])]);
  if (!esNpc()) mostrarInventario();
  mostrarEncode(null);
  mostrarBarraLook();
  dibujarGaturro();
}

// --- Casilleros: una Parte del cuerpo cada uno, a los costados del Gaturro ---

const CASILLEROS_CABEZA = ["hats", "hairs", "mouths", "accesories", "accesories2", "neck", "effect"];
const CASILLEROS_CUERPO = ["cloth", "arm", "clothBack", "grip", "gripFore", "leg", "foot", "transport"];
let casilleroMarcado = null; // si hay uno, toda Pieza que se toque va a esa Parte

function casillero(id) {
  const ruta = lookActual.partes[id];
  const li = document.createElement("li");
  const boton = Object.assign(document.createElement("button"), { className: "casillero" });
  boton.title = ruta ? `${nombreDeParte(id)}: ${claseDeRuta(ruta)} · ${swfDeRuta(ruta)}` : `${nombreDeParte(id)}: vacío. Tocá para poner acá las Piezas que elijas.`;
  boton.setAttribute("aria-pressed", String(id === casilleroMarcado));
  boton.append(ruta ? elementoIcono(ruta) : Object.assign(document.createElement("span"), { className: "icono vacio" }), etiqueta(nombreDeParte(id), "nombre-casillero"));
  boton.addEventListener("click", () => {
    casilleroMarcado = casilleroMarcado === id ? null : id;
    mostrarLook();
  });
  li.append(boton);
  if (ruta) {
    const quitar = Object.assign(document.createElement("button"), { className: "quitar sacar-pieza", title: `Sacar la Pieza de ${nombreDeParte(id)}` });
    quitar.append(icono("x"));
    quitar.addEventListener("click", () => {
      delete lookActual.partes[id];
      mostrarLook();
    });
    li.append(quitar);
  }
  return li;
}

function mostrarCasilleros() {
  if (vista === "acciones") {
    $("casilleros-cabeza").replaceChildren(casillero("effect"));
    $("casilleros-cuerpo").replaceChildren(casillero("action"));
  } else {
    const ubicadas = new Set([...CASILLEROS_CABEZA, ...CASILLEROS_CUERPO]);
    // Partes del Look que no tienen casillero (de un Look importado, por ejemplo): van con el cuerpo.
    const extra = Object.keys(lookActual.partes).filter((p) => !ubicadas.has(p));
    $("casilleros-cabeza").replaceChildren(...CASILLEROS_CABEZA.map(casillero));
    $("casilleros-cuerpo").replaceChildren(...[...CASILLEROS_CUERPO, ...extra].map(casillero));
  }
  $("poniendo-en").hidden = !casilleroMarcado;
  $("texto-poniendo-en").textContent = casilleroMarcado ? `Poniendo en: ${nombreDeParte(casilleroMarcado)}` : "";
}

$("dejar-de-poner").addEventListener("click", () => {
  casilleroMarcado = null;
  mostrarLook();
});

document.querySelectorAll(".emote-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    lookActual.emote = btn.dataset.emote || null;
    mostrarLook();
    mostrarBarraLook();
  });
});
