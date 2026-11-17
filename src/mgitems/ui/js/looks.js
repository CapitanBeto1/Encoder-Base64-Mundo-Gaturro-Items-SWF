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
  if (!esNpc()) return conEsqueleto(img.parentElement, "foto", async () => {
    const foto = await fotoDelGaturro(partesQuietas(documento), coloresDe(documento), documento.emote ?? null, documento.personalizacion ?? null);
    img.hidden = !foto;
    if (foto) img.src = foto;
  });
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
  nombrarBotonesDelGuardado();
  mostrarListaLooks();
  mostrarLook();
  if (!inventario.cargado && !esNpc()) await cargarInventario();
}

// Los botones que guardan, borran o pasan lo que se edita nombran lo de la pestaña (el Look, la acción, la tienda…).
function nombrarBotonesDelGuardado() {
  const { el, lo, nuevo, mis } = guardados();
  const elegido = lo === "la" ? "elegida" : "elegido";
  const nombrar = (id, texto) => { $(id).title = texto; $(id).setAttribute("aria-label", texto); };
  nombrar("guardar-look", `Guardar ${el}`);
  nombrar("borrar-look", `Borrar ${el}`);
  nombrar("eliminar-look-elegido", `Borrar ${el} ${elegido}`);
  nombrar("nuevo-look", nuevo);
  nombrar("reiniciar-look", `Volver ${el.replace(/^el /, "al ").replace(/^la /, "a la ")} que tenés abiert${lo === "la" ? "a" : "o"}`);
  $("importar-look").title = `Agregar el archivo de ${dePestana().tocaUno} de otra persona`;
  $("exportar-look").title = `Guardar ${el} ${elegido} en un archivo para pasárselo a otra persona`;
  $("duplicar-look").title = `Hacer una copia de ${el} ${elegido}`;
  $("grilla-looks").setAttribute("aria-label", mis);
}

// --- Mis Looks: la ventana "Guarda tu Look", como en el juego ---

let lookElegido = null; // el Look tocado en la ventana (su id), o null
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
    const miniatura = Object.assign(document.createElement("img"), { alt: look.nombre, hidden: true });
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
// se toca otro de la grilla; «Volver al Look que tenés abierto» lo muestra de nuevo.
let mostrandoPuesto = true;

function mostrarLookElegido() {
  const look = looksGuardados.find((l) => l.id === lookElegido);
  document.querySelectorAll("#grilla-looks .casillero-look:not(.nuevo)").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.id === lookElegido)));
  $("exportar-look").disabled = $("duplicar-look").disabled = $("eliminar-look-elegido").disabled = !look;
  // En Tiendas y Portales se ve el Item, no un Gaturro.
  const mostrar = (documento) => {
    $("vivo-mis-looks").hidden = esNpc() || !documento;
    $("icono-mis-looks").hidden = !esNpc() || !documento?.base;
    document.querySelector(".zoom-escenario").hidden = esNpc();
    if (!documento) return;
    if (esNpc()) {
      if (documento.base) $("icono-mis-looks").replaceChildren(elementoIcono(documento.base));
      cargarIconos(documento.base ? [documento.base] : []);
    } else {
      vestirCon(gaturroDelEscenario, documento);
    }
  };
  if (mostrandoPuesto) {
    $("nombre-look-elegido").textContent = `${lookActual.nombre || guardados().nuevo} (abierto)`;
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
// Las barritas de zoom acercan o alejan a su Gaturro.
$("zoom-gaturro").addEventListener("input", (e) => gaturroDelLook.zoom(Number(e.target.value)));
$("zoom-escenario").addEventListener("input", (e) => gaturroDelEscenario.zoom(Number(e.target.value)));
// Elimina el Look elegido; si es el que se está editando, el editor queda con un Look nuevo.
$("eliminar-look-elegido").addEventListener("click", async () => {
  const look = looksGuardados.find((l) => l.id === lookElegido);
  if (!look || !confirm(`¿Borrar ${guardados().el} «${look.nombre}»?`)) return;
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
  const icono = $("icono-emote-actual");
  icono.src = `img/emotes/${emoteActual || "normal"}.png`;
  icono.alt = emoteActual || "Sin emoción";
  document.querySelectorAll(".emote-btn").forEach(btn => {
    btn.setAttribute("aria-pressed", btn.dataset.emote === emoteActual ? "true" : "false");
  });
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

const CASILLEROS_CABEZA = ["hats", "hairs", "mouths", "accesories", "neck", "effect"];
const CASILLEROS_CUERPO = ["cloth", "arm", "clothBack", "grip", "gripFore", "leg", "foot", "transport"];
let casilleroMarcado = null; // si hay uno, toda Pieza que se toque va a esa Parte
// Las capas de arriba de una Parte («Configura tus accesorios») no tienen casillero: el de la Parte dice cuántas tienen Pieza.
const esCapaDeArriba = (id) => partesConocidas.some((p) => p.id === id && p.capa_de);
const capasDeArriba = (id) => partesConocidas.filter((p) => p.capa_de === id && lookActual.partes[p.id]).map((p) => p.id);
// Las capas de una Parte: [la Parte, su capa 2, su capa 3], o solo [la Parte] si no tiene (Torso, Piernas…).
const capasDe = (parte) => [parte, ...partesConocidas.filter((p) => p.capa_de === parte).map((p) => p.id)];
const parteConCapas = (parte) => Boolean(dePestana().capas) && capasDe(parte).length > 1;
// La capa elegida (1, 2 o 3) del casillero marcado, con los botones de «Poniendo en»; al marcar otro, vuelve a la 1.
let capaElegida = { parte: null, numero: 1 };
const numeroDeCapa = () => (capaElegida.parte === casilleroMarcado ? capaElegida.numero : 1);

// Dónde va una Pieza que se toca con `destino` marcado: en la capa elegida, salvo que abajo haya una vacía.
function capaDestino(destino) {
  if (!destino || destino !== casilleroMarcado || !parteConCapas(destino)) return destino;
  const capas = capasDe(destino);
  const elegida = numeroDeCapa() - 1;
  return capas.find((c, i) => i < elegida && !lookActual.partes[c]) ?? capas[elegida];
}

// Sin huecos, como en «Configura tus accesorios»: si se saca una capa, las de arriba bajan (con su personalización).
function compactarCapas(parte) {
  const capas = capasDe(parte);
  capas.filter((c) => lookActual.partes[c]).forEach((c, i) => {
    if (c === capas[i]) return;
    lookActual.partes[capas[i]] = lookActual.partes[c];
    delete lookActual.partes[c];
    if (lookActual.personalizacion?.[c]) {
      lookActual.personalizacion[capas[i]] = lookActual.personalizacion[c];
      delete lookActual.personalizacion[c];
    }
  });
}

function casillero(id) {
  const ruta = lookActual.partes[id];
  const li = document.createElement("li");
  const boton = Object.assign(document.createElement("button"), { className: "casillero" });
  boton.title = ruta ? `${nombreDeParte(id)}: ${claseDeRuta(ruta)} · ${swfDeRuta(ruta)}` : `${nombreDeParte(id)}: vacío. Tocá para poner acá las Piezas que elijas.`;
  boton.setAttribute("aria-pressed", String(id === casilleroMarcado));
  if (tienePersonalizacion(id)) boton.classList.add("personalizada");
  boton.append(ruta ? elementoIcono(ruta) : Object.assign(document.createElement("span"), { className: "icono vacio" }), etiqueta(nombreDeParte(id), "nombre-casillero"));
  const arriba = capasDeArriba(id);
  if (arriba.length) {
    boton.title += `\nY ${arriba.length === 1 ? "una capa" : `${arriba.length} capas`} más arriba: ${arriba.map((p) => claseDeRuta(lookActual.partes[p])).join(", ")} (marcá el casillero y elegí la capa).`;
    boton.append(etiqueta(`+${arriba.length}`, "capas-casillero"));
  }
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
      olvidarPersonalizacion(id);
      compactarCapas(id); // la capa 2 pasa a ser la 1
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
    const extra = Object.keys(lookActual.partes).filter((p) => !ubicadas.has(p) && !esCapaDeArriba(p));
    $("casilleros-cabeza").replaceChildren(...CASILLEROS_CABEZA.map(casillero));
    $("casilleros-cuerpo").replaceChildren(...[...CASILLEROS_CUERPO, ...extra].map(casillero));
  }
  $("poniendo-en").hidden = !casilleroMarcado;
  $("texto-poniendo-en").textContent = casilleroMarcado ? `Poniendo en: ${nombreDeParte(casilleroMarcado)}` : "";
  // En Sombrero, Pelo, Accesorio, Boca y Cuello, los botones 1 · 2 · 3 eligen en qué capa va lo que se toque.
  const capas = casilleroMarcado && parteConCapas(casilleroMarcado) ? capasDe(casilleroMarcado) : [];
  $("capas-poniendo").hidden = !capas.length;
  $("capas-poniendo").replaceChildren(...(capas.length ? [etiqueta("capa", "ayuda"), ...capas.map((c, i) => {
    const ruta = lookActual.partes[c];
    const boton = Object.assign(document.createElement("button"), { type: "button", className: "capa-poniendo", textContent: String(i + 1) });
    boton.title = `Capa ${i + 1}${i ? " (arriba de la " + i + ")" : ""}: ${ruta ? claseDeRuta(ruta) : "vacía"}`;
    boton.setAttribute("aria-pressed", String(numeroDeCapa() === i + 1));
    boton.classList.toggle("llena", Boolean(ruta));
    boton.addEventListener("click", () => {
      capaElegida = { parte: casilleroMarcado, numero: i + 1 };
      mostrarLook();
    });
    return boton;
  })] : []));
  const conCapas = dePestana().capas;
  const sePuede = conCapas || Object.keys(lookActual.partes).length > 0; // las capas se ponen también sin Piezas
  $("editar-piezas").disabled = !sePuede;
  $("editar-piezas").title = !sePuede ? "Personalizar las Piezas: poné primero una Pieza en el Gaturro"
    : conCapas ? "Personalizar: colores, mover y girar las Piezas, o poner accesorios uno arriba del otro"
    : "Personalizar las Piezas: colores por capa, mover, girar y ajustar";
}

$("dejar-de-poner").addEventListener("click", () => {
  casilleroMarcado = null;
  mostrarLook();
});

function cerrarPanelEmotes() {
  $("panel-emotes").hidden = true;
  $("emote-look").setAttribute("aria-expanded", "false");
}

$("emote-look").addEventListener("click", (e) => {
  e.stopPropagation();
  const abierto = !$("panel-emotes").hidden;
  if (abierto) {
    cerrarPanelEmotes();
  } else {
    $("panel-emotes").hidden = false;
    $("emote-look").setAttribute("aria-expanded", "true");
  }
});

document.addEventListener("click", cerrarPanelEmotes);

document.querySelectorAll(".emote-btn").forEach(btn => {
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    lookActual.emote = btn.dataset.emote || null;
    cerrarPanelEmotes();
    mostrarLook();
    mostrarBarraLook();
  });
});
