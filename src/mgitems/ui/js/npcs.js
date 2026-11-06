// Tiendas, Portales, Minijuegos y Fondos: cualquier Item que, puesto en la casa, hace lo mismo que un NPC.

// --- Tiendas y Portales: cualquier Item que, puesto en la casa, hace lo mismo que un NPC del juego ---

const ICONO_NPC = { tienda: "shopping-cart", portal: "door", minijuego: "game-controller", fondo: "image" };
const comportamientosConocidos = {}; // tipo → [{comportamiento, tipo, descripcion, objeto}]
const descripciones = new Map(); // comportamiento → su fila (también los escritos a mano)
const tiposDeItems = new Map(); // ruta → tipo ("casa", "prenda", "mochila"…), de la ventana del Item base

// El que se está armando (`base` y `comportamiento`) y la lista de los que se reciben juntos.
function nuevoNpc() {
  return { id: "", nombre: "", base: null, comportamiento: null, partes: {}, colores: {}, lista: [] };
}

// --- Fondos: un objeto cuyo dibujo tiene varios cuadros (como socialNetBackgrounds) que muestra el que se elija,
// para todos y para siempre (`mgitems.fondos`). Comparte la pantalla de Tiendas, Portales y Minijuegos: la grilla
// muestra los objetos y, elegido uno, sus cuadros. ---

let comportamientoFondo = "painting";
let fondosConocidos = null; // [{ruta, clase, swf, cuadros}]
const cuadrosDeFondo = new Map(); // ruta → [data URL de cada cuadro], o una promesa mientras se exportan
let verObjetos = true; // la grilla muestra los objetos (si no, los cuadros del elegido)
// Los objetos se ven por páginas, como en el buscador de Items (con todos juntos se pedirían las imágenes de
// cientos de SWF a la vez).
const OBJETOS_POR_PAGINA = 12;
let paginaFondos = 0;
let filtroFondos = "";

function nuevoFondo() {
  return { ...nuevoNpc(), comportamiento: comportamientoFondo, cuadro: null };
}

async function cargarFondos() {
  if (!fondosConocidos) {
    const resultado = await conEsqueleto($("grilla-comportamientos"), "tarjetas", () => api().fondos());
    if (!resultado.ok) return avisarLista(resultado.error, "error");
    fondosConocidos = resultado.fondos;
    comportamientoFondo = resultado.comportamiento;
  }
  $("filtro-comportamientos").value = "";
  verObjetos = !lookActual.base;
  await cargarLooks(); // los guardados y el armado
  mostrarComportamientos();
}

// Los cuadros de un objeto, exportados por el núcleo (la primera vez tarda unos segundos).
async function cuadrosDe(ruta) {
  if (!cuadrosDeFondo.has(ruta)) {
    cuadrosDeFondo.set(ruta, api().cuadros_de_fondo(ruta).then((r) => {
      if (!r.ok) {
        cuadrosDeFondo.delete(ruta);
        avisarLista(r.error, "error");
        return null;
      }
      cuadrosDeFondo.set(ruta, r.cuadros);
      return r.cuadros;
    }));
  }
  return cuadrosDeFondo.get(ruta);
}

// El mismo objeto puede ir varias veces a la lista, con otro cuadro: cada uno llega como un objeto aparte.
function elegirObjetoDeFondo(ruta) {
  if (lookActual.base !== ruta) lookActual.cuadro = null;
  lookActual.base = ruta;
  tiposDeItems.set(ruta, "casa");
  verObjetos = false;
  mostrarEncode(null);
  mostrarLook();
  mostrarComportamientos();
}

function elegirCuadro(n) {
  lookActual.cuadro = n;
  mostrarEncode(null);
  mostrarLook();
  mostrarComportamientos();
}

function casilleroFondo(contenido, titulo, presionado, alTocar) {
  const li = document.createElement("li");
  const boton = Object.assign(document.createElement("button"), { type: "button", className: "casillero-npc", title: titulo });
  boton.setAttribute("aria-pressed", String(presionado));
  boton.append(...contenido);
  boton.addEventListener("click", alTocar);
  li.append(boton);
  return li;
}

async function mostrarFondos() {
  const grilla = $("grilla-comportamientos");
  const base = lookActual.base;
  const enCuadros = !verObjetos && base;
  $("otros-fondos").hidden = !enCuadros;
  $("filtro-comportamientos").hidden = Boolean(enCuadros);
  grilla.classList.toggle("con-cuadros", Boolean(enCuadros));
  if (enCuadros) $("paginas-fondos").replaceChildren();
  if (!enCuadros) {
    $("filtro-comportamientos").placeholder = "Buscar un objeto por nombre";
    const todos = fondosConocidos ?? [];
    const texto = $("filtro-comportamientos").value.trim().toLowerCase();
    if (texto !== filtroFondos) {
      filtroFondos = texto;
      paginaFondos = 0;
    }
    const encontrados = todos.filter((f) => f.ruta.toLowerCase().includes(texto));
    const paginas = Math.ceil(encontrados.length / OBJETOS_POR_PAGINA);
    paginaFondos = Math.min(paginaFondos, Math.max(paginas - 1, 0));
    const filas = encontrados.slice(paginaFondos * OBJETOS_POR_PAGINA, (paginaFondos + 1) * OBJETOS_POR_PAGINA);
    $("cantidad-comportamientos").textContent = texto ? `${encontrados.length} de ${todos.length}` : `${todos.length}`;
    mostrarPaginas($("paginas-fondos"), filas.length ? paginaFondos : -1, paginas, (n) => {
      paginaFondos = n;
      mostrarComportamientos();
    });
    grilla.replaceChildren(...filas.map((f) => casilleroFondo(
      [elementoIcono(f.ruta), etiqueta(f.clase, "nombre"), etiqueta(`${f.swf} · ${f.cuadros} fondos`, "que-hace")],
      `${f.ruta}: ${f.cuadros} cuadros`, base === f.ruta, () => elegirObjetoDeFondo(f.ruta))));
    if (!filas.length) grilla.append(etiqueta("No hay ninguno con ese nombre.", "ayuda"));
    grilla.scrollTop = 0;
    cargarIconos(filas.map((f) => f.ruta));
    for (const swf of new Set(filas.map((f) => f.swf))) prepararIconosDe(swf);
    return;
  }
  const listos = cuadrosDeFondo.get(base);
  if (!Array.isArray(listos)) {
    $("cantidad-comportamientos").textContent = "";
    const cuadros = await conEsqueleto(grilla, "tarjetas", () => cuadrosDe(base));
    if (cuadros && esFondos() && lookActual.base === base) mostrarComportamientos();
    return;
  }
  $("cantidad-comportamientos").textContent = `${listos.length} cuadros`;
  grilla.replaceChildren(...listos.map((url, i) => casilleroFondo(
    [Object.assign(document.createElement("img"), { src: url, className: "cuadro-fondo", alt: `Cuadro ${i + 1}` }), etiqueta(`Cuadro ${i + 1}`, "nombre")],
    `Que se vea el cuadro ${i + 1}`, lookActual.cuadro === i + 1, () => elegirCuadro(i + 1))));
}

$("otros-fondos").addEventListener("click", () => {
  verObjetos = true;
  mostrarComportamientos();
});

async function cargarNpcs() {
  if (esFondos()) return cargarFondos();
  const tipo = PESTANAS_NPC[vista];
  if (!comportamientosConocidos[tipo] && !(await leerComportamientos(tipo))) return;
  $("filtro-comportamientos").value = "";
  await cargarLooks(); // los guardados y el armado
  mostrarComportamientos();
  buscarEnElJuego();
}

async function leerComportamientos(tipo) {
  const resultado = await conEsqueleto($("grilla-comportamientos"), "tarjetas", () => api().comportamientos(tipo));
  if (!resultado.ok) return avisarLista(resultado.error, "error"), false;
  comportamientosConocidos[tipo] = resultado.comportamientos;
  for (const c of resultado.comportamientos) descripciones.set(c.comportamiento, c);
  return true;
}

// Los NPC de las salas que recorriste: el juego deja sus guiones en su caché. Se busca cada vez que se abre la
// pestaña, sin trabar nada; lo nuevo se suma a la grilla.
let buscandoEnElJuego = false;
async function buscarEnElJuego() {
  if (buscandoEnElJuego) return;
  buscandoEnElJuego = true;
  try {
    const resultado = await api().buscar_comportamientos_en_el_juego();
    if (!resultado.ok) return avisarLista(`No se pudieron buscar los NPC de las salas que recorriste: ${resultado.error}`, "advertencia");
    if (!resultado.nuevos.length) return;
    for (const tipo of new Set(resultado.nuevos.map((n) => n.tipo))) await leerComportamientos(tipo);
    mostrarComportamientos();
    const nombres = resultado.nuevos.map((n) => n.comportamiento).join(", ");
    avisarLista(`${resultado.nuevos.length === 1 ? "Se encontró 1 nuevo" : `Se encontraron ${resultado.nuevos.length} nuevos`} en las salas que recorriste: ${nombres}.`, "exito");
  } finally {
    buscandoEnElJuego = false;
  }
}

function mostrarComportamientos() {
  if (!esNpc()) return;
  if (esFondos()) return mostrarFondos();
  const todos = comportamientosConocidos[PESTANAS_NPC[vista]] ?? [];
  const texto = $("filtro-comportamientos").value.trim().toLowerCase();
  const filas = todos.filter((c) => `${c.comportamiento} ${c.descripcion}`.toLowerCase().includes(texto));
  $("cantidad-comportamientos").textContent = texto ? `${filas.length} de ${todos.length}` : `${todos.length}`;
  $("grilla-comportamientos").replaceChildren(
    ...filas.map((c) => {
      const li = document.createElement("li");
      const boton = Object.assign(document.createElement("button"), {
        type: "button", className: "casillero-npc",
        title: `${c.comportamiento}: ${c.descripcion}` + (c.encontrado ? " (encontrado en las salas que recorriste)" : ""),
      });
      boton.setAttribute("aria-pressed", String(lookActual.comportamiento === c.comportamiento));
      boton.append(
        c.objeto ? elementoIcono(c.objeto) : icono(ICONO_NPC[c.tipo], "icono-npc"),
        etiqueta(c.comportamiento, "nombre"),
        etiqueta(c.descripcion, "que-hace"),
        ...(c.encontrado ? [conIcono("map-pin", "En tus salas", "encontrado-npc")] : [])
      );
      boton.addEventListener("click", () => elegirComportamiento(c.comportamiento));
      li.append(boton);
      return li;
    })
  );
  if (!filas.length) $("grilla-comportamientos").append(etiqueta("No hay ninguno con ese nombre: podés escribirlo a mano a la izquierda.", "ayuda"));
  const objetos = filas.filter((c) => c.objeto).map((c) => c.objeto);
  cargarIconos(objetos);
  for (const swf of new Set(objetos.map(swfDeRuta))) prepararIconosDe(swf);
}

function elegirComportamiento(nombre) {
  lookActual.comportamiento = nombre;
  mostrarEncode(null);
  mostrarLook();
  mostrarComportamientos();
}

function mostrarArmadoFondo() {
  const base = lookActual.base;
  const cuadro = lookActual.cuadro;
  const cuadros = base && cuadrosDeFondo.get(base);
  $("comportamiento-elegido").replaceChildren(
    cuadro ? conIcono("image", `Cuadro ${cuadro}${Array.isArray(cuadros) ? ` de ${cuadros.length}` : ""}`, "nombre")
      : etiqueta(base ? "tocá un cuadro de la derecha" : "elegí un objeto de la derecha", "ayuda")
  );
  $("vista-npc").replaceChildren(
    ...(!base ? [etiqueta("Elegí a la derecha un objeto con varios fondos.", "ayuda")]
      : cuadro && Array.isArray(cuadros) && cuadros[cuadro - 1]
        ? [Object.assign(document.createElement("img"), { src: cuadros[cuadro - 1], className: "cuadro-fondo", alt: `Cuadro ${cuadro}` }),
           etiqueta(`${claseDeRuta(base)} (${swfDeRuta(base)})`, "ayuda")]
        : [elementoIcono(base), etiqueta(`${claseDeRuta(base)} (${swfDeRuta(base)})`, "ayuda")])
  );
  if (base && !Array.isArray(cuadros)) cuadrosDe(base).then((c) => c && esFondos() && lookActual.base === base && mostrarArmadoNpc());
  $("aviso-npc").textContent = base
    ? "Lo ven todos en tu casa; al tocarlo, pasa al cuadro siguiente. Cada cuadro que sumes llega aparte."
    : "";
  $("agregar-npc").disabled = !conectado || ocupado || !base || !cuadro;
}

function mostrarArmadoNpc() {
  if (esFondos()) {
    mostrarArmadoFondo();
    mostrarListaNpc();
    return;
  }
  const nombre = lookActual.comportamiento;
  const fila = nombre && descripciones.get(nombre);
  $("comportamiento-elegido").replaceChildren(
    ...(nombre
      ? [conIcono(ICONO_NPC[fila?.tipo] ?? "question", nombre, "nombre"), ...(fila ? [etiqueta(`· ${fila.descripcion}`, "ayuda")] : [])]
      : [etiqueta("tocá uno de la grilla", "ayuda")])
  );
  if (nombre && !fila) leerComportamiento(nombre); // uno guardado que no está en la grilla
  const base = lookActual.base;
  $("vista-npc").replaceChildren(
    ...(base ? [elementoIcono(base), etiqueta(`${claseDeRuta(base)} (${swfDeRuta(base)})`, "ayuda")] : [etiqueta("Elegí el Item que se convierte con «Cambiar…».", "ayuda")])
  );
  if (base) prepararIconosDe(swfDeRuta(base));
  const tipo = base && tiposDeItems.get(base);
  $("aviso-npc").textContent = !base ? ""
    : tipo === "casa" ? "Llega a la casa. Si tenía una función propia (sentarse, acostarse…), deja de tenerla."
    : tipo ? `Llega a la casa, no ${tipo === "prenda" ? "al guardarropa" : tipo === "mochila" ? "a la mochila" : "adonde llega hoy"}.`
    : "Llega a la casa.";
  $("agregar-npc").disabled = !conectado || ocupado || !base || !nombre;
  mostrarListaNpc();
}

function mostrarListaNpc() {
  const base = lookActual.base;
  $("titulo-lista-trucadas").textContent = dePestana().lista;
  $("cantidad-trucadas").textContent = `(${lookActual.lista.length})`;
  $("lista-trucadas").replaceChildren(
    ...lookActual.lista.map((t, i) => {
      const li = document.createElement("li");
      li.title = `${t.base}: ${t.comportamiento}`;
      const cantidad = Object.assign(document.createElement("input"), { type: "number", min: 1, value: t.cantidad, className: "cantidad-npc", title: "Cantidad" });
      cantidad.addEventListener("change", () => {
        t.cantidad = Math.max(1, parseInt(cantidad.value, 10) || 1);
        cantidad.value = t.cantidad;
        mostrarEncode(null);
      });
      const quitar = Object.assign(document.createElement("button"), { className: "quitar", title: "Sacar de la lista" });
      quitar.append(icono("x"));
      quitar.addEventListener("click", () => {
        lookActual.lista.splice(i, 1);
        mostrarEncode(null);
        mostrarLook();
      });
      const texto = `${claseDeRuta(t.base)} → ${t.cuadro ? `cuadro ${t.cuadro}` : t.comportamiento}`;
      li.append(elementoIcono(t.base), etiqueta(t.nombre ? `${t.nombre}: ${texto}` : texto, "nombre"), cantidad, quitar);
      return li;
    })
  );
  cargarIconos([...(base ? [base] : []), ...lookActual.lista.map((t) => t.base)]);
}

async function leerComportamiento(nombre) {
  const resultado = await api().comportamiento(nombre);
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  descripciones.set(nombre, resultado.comportamiento);
  if (esNpc() && lookActual.comportamiento === nombre) mostrarArmadoNpc();
  return resultado.comportamiento;
}

$("filtro-comportamientos").addEventListener("input", mostrarComportamientos);
$("form-comportamiento").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const nombre = $("comportamiento-a-mano").value.trim();
  if (!nombre) return;
  const fila = descripciones.get(nombre) ?? (await mientras(`Leyendo el comportamiento ${nombre}…`, () => leerComportamiento(nombre)));
  if (!fila) return;
  $("comportamiento-a-mano").value = "";
  elegirComportamiento(nombre);
  const otro = fila.tipo !== PESTANAS_NPC[vista];
  avisarLista(`«${nombre}»: ${fila.descripcion}.${otro ? " Se puede usar igual." : ""}`, otro ? "advertencia" : "exito");
});

$("agregar-npc").addEventListener("click", () => {
  const { base, comportamiento, cuadro } = lookActual;
  if (!base || !comportamiento || (esFondos() && !cuadro)) return;
  if (esFondos() && lookActual.lista.some((t) => t.base === base && t.cuadro === cuadro)) {
    return avisarLista(`${claseDeRuta(base)} con el cuadro ${cuadro} ya está en la lista: si querés más, subí su cantidad.`, "advertencia");
  }
  // El mismo Item puede ir con otro comportamiento (llega como otro objeto); con el mismo, se sube la cantidad.
  if (!esFondos() && lookActual.lista.some((t) => t.base === base && t.comportamiento === comportamiento)) {
    return avisarLista(`${claseDeRuta(base)} con ${comportamiento} ya está en la lista: si querés más, subí su cantidad.`, "advertencia");
  }
  lookActual.lista.push({ base, comportamiento, cantidad: 1, nombre: lookActual.nombre.trim(), ...(esFondos() ? { cuadro } : {}) });
  avisarLista(`Se agregó ${claseDeRuta(base)} (${esFondos() ? `cuadro ${cuadro}` : comportamiento}). Armá otro o tocá «Convertir todos».`, "exito");
  Object.assign(lookActual, { id: "", nombre: "", base: null, comportamiento: esFondos() ? comportamientoFondo : null, cuadro: null });
  verObjetos = true;
  mostrarEncode(null);
  mostrarListaLooks();
  mostrarLook();
  mostrarComportamientos();
});

async function convertirNpcs() {
  const lista = lookActual.lista;
  // Un fondo es un NPC con `painting` y su cuadro.
  const resultado = await mientras("Armando el Encode…", () => api().convertir_en_npcs(
    lista.map(({ base, comportamiento, cantidad, cuadro }) => ({ base, comportamiento, cantidad, ...(cuadro ? { cuadro } : {}) }))));
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  mostrarEncode(resultado);
  avisarLista(`Listo: tocá «Agregar al juego» para recibir${lista.length === 1 ? "lo" : "los"}. ${lista.length === 1 ? "Llega" : "Llegan"} a la casa.`, "exito");
  mostrarBarraLook();
}

$("nombre-look").addEventListener("input", () => {
  lookActual.nombre = $("nombre-look").value;
  if (vista !== "trucar" && !esNpc()) mostrarEncode(null); // en Trucar Prenda, Tiendas y Portales, el Encode es de la lista
  mostrarBarraLook();
});

$("nuevo-look").addEventListener("click", () => {
  $("dialogo-mis-looks").close();
  lookActual = enElEditor(documentoNuevo());
  casilleroMarcado = null;
  mostrarListaLooks();
  mostrarLook();
  $("nombre-look").focus();
});
$("guardar-look").addEventListener("click", guardarLook);
// Descartar: vuelve a como estaba guardado (o vacío si el Look es nuevo).
$("descartar-look").addEventListener("click", () => {
  const guardado = looksGuardados.find((l) => l.id === lookActual.id);
  lookActual = enElEditor(guardado ?? documentoNuevo());
  mostrarListaLooks();
  mostrarLook();
  avisarLista(guardado ? `Se descartaron los cambios de «${guardado.nombre}».` : "", "exito");
});
$("exportar-look").addEventListener("click", async () => {
  const look = looksGuardados.find((l) => l.id === lookElegido);
  if (!look) return;
  const resultado = await llamarGuardados("exportar", look);
  if (resultado.ok) avisarLista(`Se exportó ${guardados().el} en ${resultado.ruta}`, "exito");
  else if (!resultado.cancelado) avisarLista(resultado.error, "error");
});
// El Look importado queda elegido en "Mis Looks" (EQUIPAR lo abre).
$("importar-look").addEventListener("click", async () => {
  const resultado = await llamarGuardados("importar");
  if (resultado.cancelado) return;
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  lookElegido = guardadoDe(resultado).id;
  mostrandoPuesto = false;
  await cargarLooks();
  avisarLista(`Se importó ${guardados().el} «${guardadoDe(resultado).nombre}». Tocá «Equipar» para abrir${guardados().lo}.`, "exito");
});
$("duplicar-look").addEventListener("click", duplicarLook);
$("borrar-look").addEventListener("click", borrarLook);
