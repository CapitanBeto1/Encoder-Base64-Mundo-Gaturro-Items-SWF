// La interfaz no tiene lógica de dominio: todo pasa por window.pywebview.api (el núcleo).
// Solo guarda la lista de Items elegidos ({ruta, cantidad}), que el jugador arma
// buscando, a mano o importando un Encode.

const $ = (id) => document.getElementById(id);
const api = () => window.pywebview.api;

let items = [];
let ocupado = 0; // tareas del núcleo en curso: mientras haya alguna, la interfaz queda bloqueada
let conectado = false; // true cuando pywebview expuso la API
let swfAbierto = false;
let swfAbiertoActual = null; // nombre del SWF abierto

function avisar(elemento, texto, tipo = "") {
  elemento.textContent = texto;
  elemento.className = "mensaje " + tipo;
}

const contarItems = (n) => (n === 1 ? "1 Item" : `${n} Items`);

const avisarLista = (texto, tipo) => avisar($("mensaje"), texto, tipo);
const avisarEncode = (texto, tipo) => avisar($("mensaje-encode"), texto, tipo);

// Mientras el núcleo trabaja se bloquean los botones y se muestra qué está pasando.
async function mientras(texto, tarea) {
  ocupado++;
  actualizarControles();
  avisarLista(texto, "progreso");
  try {
    return await tarea();
  } finally {
    ocupado--;
    actualizarControles();
  }
}

// Agrega rutas nuevas con cantidad 1; las que ya están en la lista no cambian.
function agregarItems(rutas) {
  const nuevas = rutas.filter((ruta) => !items.some((i) => i.ruta === ruta));
  items = [...items, ...nuevas.map((ruta) => ({ ruta, cantidad: 1 }))];
  mostrarLista();
  return nuevas.length;
}

function quitarItem(ruta) {
  items = items.filter((i) => i.ruta !== ruta);
  mostrarLista();
}

function cambiarCantidad(ruta, valor) {
  const item = items.find((i) => i.ruta === ruta);
  if (item) item.cantidad = valor;
  // El Encode mostrado deja de corresponder a la lista.
  mostrarEncode(null);
}

function filaDeItem({ ruta, cantidad }) {
  const fila = document.createElement("li");

  const nombre = document.createElement("span");
  nombre.className = "nombre";
  nombre.textContent = ruta;
  nombre.title = ruta;

  const campoCantidad = document.createElement("input");
  campoCantidad.type = "number";
  campoCantidad.min = "1";
  campoCantidad.step = "1";
  campoCantidad.value = cantidad;
  campoCantidad.className = "cantidad";
  campoCantidad.title = "Cantidad";
  campoCantidad.setAttribute("aria-label", `Cantidad de ${ruta}`);
  campoCantidad.addEventListener("input", () => cambiarCantidad(ruta, campoCantidad.value));

  const quitar = document.createElement("button");
  quitar.className = "quitar";
  quitar.textContent = "✕";
  quitar.title = `Quitar ${ruta}`;
  quitar.setAttribute("aria-label", `Quitar ${ruta}`);
  quitar.addEventListener("click", () => quitarItem(ruta));

  fila.append(elementoIcono(ruta), nombre, campoCantidad, quitar);
  return fila;
}

function mostrarLista() {
  $("lista").replaceChildren(...items.map(filaDeItem));
  cargarIconos(items.map((i) => i.ruta));
  $("cantidad").textContent = items.length ? `(${items.length})` : "";
  $("lista-vacia").hidden = items.length > 0;
  // El Encode mostrado deja de corresponder a la lista.
  mostrarEncode(null);
}

function mostrarEncode(resultado) {
  $("encode").value = resultado ? resultado.encode : "";
  if (resultado?.look) {
    const n = Object.keys(resultado.prenda.partes).length;
    $("resumen").textContent = `Look «${resultado.look.nombre}»: ${resultado.prenda.ruta} con ${n === 1 ? "1 Pieza" : `${n} Piezas`}.` + (resultado.prenda.tipo === "mochila" ? " Está en la mochila: usalo para vestirte." : "");
  } else if (resultado?.prenda) {
    const [[parteElegida, piezaElegida]] = Object.entries(resultado.prenda.partes);
    const nombreParte = partesDelCuerpo.find((p) => p.id === parteElegida)?.nombre ?? parteElegida;
    $("resumen").textContent = `Prenda trucada: ${resultado.prenda.ruta} muestra ${piezaElegida} en ${nombreParte}.` + (resultado.prenda.tipo === "mochila" ? " Está en la mochila: usalo para vestirte." : "");
  } else if (resultado) {
    $("resumen").textContent = `Encode con ${contarItems(resultado.items.length)}.`;
  } else {
    $("resumen").textContent =
      vista === "trucar"
        ? base && pieza && parte ? "Tocá «Trucar Prenda» para generar el Encode." : "Elegí el Item base, la Pieza y la Parte del cuerpo."
        : vista === "looks"
          ? Object.keys(lookActual.partes).length ? "Tocá «Aplicar Look» para generar el Encode." : "Elegí las Piezas del Look."
          : items.length ? "Generá el Encode con los Items de la lista." : "Todavía no generaste ningún Encode.";
    avisarEncode("");
  }
  actualizarControles();
}

function actualizarControles() {
  const listo = conectado && !ocupado;
  $("abrir").disabled = $("buscar-swf").disabled = !listo;
  $("prefijos").disabled = $("buscar").disabled = !listo || !swfAbierto;
  $("manual").disabled = $("agregar").disabled = !listo;
  $("quitar-todos").disabled = !listo || items.length === 0;
  $("importar").disabled = !listo;
  $("abrir-entorno").disabled = !conectado;
  const puedeGenerar = { agregar: items.length > 0, trucar: base && pieza && parte, looks: Object.keys(lookActual.partes).length > 0 }[vista];
  $("generar").disabled = !listo || !puedeGenerar;
  $("guardar-look").disabled = $("nuevo-look").disabled = $("importar-look").disabled = !listo;
  $("exportar-look").disabled = !listo || !Object.keys(lookActual.partes).length;
  $("duplicar-look").disabled = $("borrar-look").disabled = !listo || !lookActual.id;
  $("nombre-look").disabled = $("buscar-base-look").disabled = $("buscar-swf-look").disabled = !listo;
  document.querySelectorAll("#partes-look input").forEach((c) => (c.disabled = !listo));
  $("buscar-base").disabled = $("buscar-pieza").disabled = $("buscar-parte").disabled = !listo || !prendas.length;
  $("buscar-swf-pieza").disabled = !listo || !prendas.length;
  $("pestana-agregar").disabled = $("pestana-trucar").disabled = $("pestana-looks").disabled = !conectado || ocupado;
  $("copiar").disabled = $("guardar").disabled = $("entregar").disabled = !listo || !$("encode").value;
}

// --- Imágenes de los Items ---

const imagenes = new Map(); // ruta del Item → data URL, o null si no tiene

function elementoIcono(ruta) {
  const caja = document.createElement("span");
  caja.className = "icono";
  caja.dataset.ruta = ruta;
  pintarIcono(caja);
  return caja;
}

function pintarIcono(caja) {
  const src = imagenes.get(caja.dataset.ruta);
  if (src) {
    caja.replaceChildren(Object.assign(document.createElement("img"), { src, alt: "" }));
    caja.classList.remove("sin-imagen");
    caja.title = "";
  } else {
    caja.replaceChildren();
    caja.classList.add("sin-imagen");
    caja.title = imagenes.has(caja.dataset.ruta) ? "Sin imagen" : "";
  }
}

// Pide al núcleo las imágenes que todavía no se conocen y repinta las que estén en pantalla.
async function cargarIconos(rutas) {
  const faltan = [...new Set(rutas)].filter((r) => !imagenes.get(r));
  if (!faltan.length || !conectado) return;
  const resultado = await api().iconos(faltan);
  if (!resultado.ok) return;
  for (const [ruta, src] of Object.entries(resultado.iconos)) imagenes.set(ruta, src);
  document.querySelectorAll(".icono[data-ruta]").forEach(pintarIcono);
}

async function prepararIconos(swf) {
  const etiqueta = $("estado-imagenes");
  etiqueta.textContent = " · preparando imágenes…";
  etiqueta.title = "";
  const resultado = await api().preparar_iconos();
  if (resultado.swf && resultado.swf !== swf) return; // mientras tanto se abrió otro SWF
  etiqueta.textContent = resultado.ok ? "" : resultado.sin_exportador ? " · sin imágenes (falta Java)" : " · sin imágenes";
  etiqueta.title = resultado.ok ? "" : resultado.error;
  if (!resultado.ok) return;
  // Pudo cambiar la versión del SWF: olvidar lo conocido de sus Items y volver a pedirlo.
  for (const ruta of [...imagenes.keys()]) if (ruta.startsWith(swf + ".")) imagenes.delete(ruta);
  cargarIconos([...document.querySelectorAll(".icono[data-ruta]")].map((c) => c.dataset.ruta));
}

function mostrarSwfAbierto(resultado) {
  if (resultado.cancelado) return avisarLista("");
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  swfAbierto = true;
  swfAbiertoActual = resultado.swf;
  actualizarControles();
  $("nombre-swf").textContent = `${resultado.swf}.swf · ${contarItems(resultado.cantidad_items)}`;
  if (resultado.aviso) avisarLista(resultado.aviso, "advertencia");
  else avisarLista("SWF abierto. Escribí el comienzo de un nombre para buscar.", "exito");
  olvidarPrendas();
  prepararIconos(resultado.swf);
  if (vista === "agregar") $("prefijos").focus();
  else cargarParaLaVista();
}

// Lo que necesita la pestaña elegida, en orden (las cargas no se pisan entre sí).
async function cargarParaLaVista() {
  if ((vista === "trucar" || vista === "looks") && swfAbierto && !prendas.length) await cargarPrendas();
  if (vista === "looks") await cargarLooks();
}

async function abrirArchivo() {
  mostrarSwfAbierto(await mientras("Abriendo SWF…", () => api().abrir_swf()));
}

// --- Desplegable de sugerencias (para elegir un SWF y para elegir Items) ---

/**
 * Lista de sugerencias bajo un campo de texto, que se actualiza mientras se escribe.
 * consultar(texto) devuelve las opciones; fila(opcion) arma su contenido; elegir(opcion)
 * se llama con un clic o con Enter sobre la opción marcada. Si existe sinElegir(),
 * Enter sin una opción marcada la llama.
 */
function crearDesplegable({ campo, lista, consultar, fila, elegir, vacio, sinElegir }) {
  let opciones = [];
  let activo = -1;

  function cerrar() {
    lista.hidden = true;
    campo.setAttribute("aria-expanded", "false");
    activo = -1;
  }

  function marcar(indice) {
    const filas = lista.querySelectorAll("li[role=option]");
    filas.forEach((f, i) => f.classList.toggle("activo", i === indice));
    filas[indice]?.scrollIntoView({ block: "nearest" });
    activo = indice;
  }

  async function mostrar() {
    const consultado = campo.value;
    const encontradas = await consultar(consultado);
    if (consultado !== campo.value || document.activeElement !== campo) return; // llegó tarde
    opciones = encontradas;
    if (!opciones.length) {
      if (!vacio || !consultado.trim()) return cerrar();
      lista.replaceChildren(Object.assign(document.createElement("li"), { className: "vacio", textContent: vacio }));
    } else {
      lista.replaceChildren(
        ...opciones.map((opcion) => {
          const li = document.createElement("li");
          li.setAttribute("role", "option");
          li.append(...fila(opcion));
          // mousedown en vez de click: se dispara antes de que el campo pierda el foco y cierre la lista.
          li.addEventListener("mousedown", (e) => {
            e.preventDefault();
            cerrar();
            elegir(opcion);
          });
          return li;
        })
      );
    }
    ubicar();
    lista.hidden = false;
    campo.setAttribute("aria-expanded", "true");
    activo = -1;
  }

  // Posición fija junto al campo (abajo, o arriba si no hay lugar): así no lo recorta una lista con scroll.
  function ubicar() {
    const r = campo.getBoundingClientRect();
    const abajo = window.innerHeight - r.bottom;
    const arriba = abajo < 220 && r.top > abajo;
    Object.assign(lista.style, {
      position: "fixed",
      left: `${r.left}px`,
      width: `${Math.max(r.width, 260)}px`,
      right: "auto",
      top: arriba ? "auto" : `${r.bottom + 6}px`,
      bottom: arriba ? `${window.innerHeight - r.top + 6}px` : "auto",
      maxHeight: `${Math.max(140, Math.min(270, (arriba ? r.top : abajo) - 16))}px`,
    });
  }

  campo.addEventListener("input", mostrar);
  campo.addEventListener("focus", mostrar);
  campo.addEventListener("blur", cerrar);
  campo.addEventListener("keydown", (e) => {
    const abierta = !lista.hidden;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!abierta) return mostrar();
      marcar(Math.min(activo + 1, opciones.length - 1));
    } else if (e.key === "ArrowUp" && abierta) {
      e.preventDefault();
      marcar(Math.max(activo - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      // Sin sinElegir, Enter con una sola opción la elige directamente.
      const elegida = abierta ? opciones[activo] ?? (!sinElegir && opciones.length === 1 ? opciones[0] : null) : null;
      cerrar();
      if (elegida) elegir(elegida);
      else if (sinElegir) sinElegir();
    } else if (e.key === "Escape") {
      cerrar();
    }
  });
  return { cerrar };
}

const etiqueta = (contenido, className) => Object.assign(document.createElement("span"), { textContent: contenido, className });

// Elegir un SWF del catálogo.
crearDesplegable({
  campo: $("buscar-swf"),
  lista: $("resultados-swf"),
  consultar: async (t) => (await api().buscar_en_catalogo(t)).swfs.slice(0, 80),
  fila: ({ swf, items }) => [etiqueta(swf, "nombre"), etiqueta(contarItems(items), "ayuda")],
  elegir: ({ swf }) => abrirDelCatalogo(swf),
  vacio: "No hay SWF con ese nombre.",
});

async function abrirDelCatalogo(nombre) {
  $("buscar-swf").value = nombre;
  mostrarSwfAbierto(await mientras(`Abriendo ${nombre} (se descarga del juego si hace falta)…`, () => api().abrir_swf_del_cdn(nombre)));
}

// Elegir Items del SWF abierto mientras se escribe.
const sugerencias = crearDesplegable({
  campo: $("prefijos"),
  lista: $("sugerencias-items"),
  consultar: async (t) => {
    const resultado = await api().sugerir_items(t);
    for (const { ruta, icono } of resultado.items) if (icono) imagenes.set(ruta, icono);
    return resultado.items;
  },
  fila: ({ ruta }) => [elementoIcono(ruta), etiqueta(ruta.slice(ruta.lastIndexOf(".") + 1), "nombre")],
  elegir: ({ ruta }) => {
    const agregado = agregarItems([ruta]);
    avisarLista(agregado ? `Se agregó ${ruta}.` : `${ruta} ya estaba en la lista.`, "exito");
  },
  vacio: "Ningún Item empieza así.",
  sinElegir: () => $("form-buscar").requestSubmit(),
});

async function buscar(evento) {
  evento.preventDefault();
  sugerencias.cerrar();
  const resultado = await mientras("Buscando…", () => api().buscar_items($("prefijos").value));
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  if (!resultado.items.length) return avisarLista("No se encontraron Items con ese comienzo.", "error");
  const agregados = agregarItems(resultado.items);
  const encontrados = resultado.items.length;
  avisarLista(
    agregados === encontrados
      ? `Se agregaron a la lista: ${contarItems(encontrados)}.`
      : `Se encontraron ${contarItems(encontrados)} (${agregados} nuevos en la lista).`,
    "exito"
  );
}

async function agregarAMano(evento) {
  evento.preventDefault();
  const resultado = await api().interpretar_items($("manual").value);
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  agregarItems(resultado.items);
  $("manual").value = "";
  avisarLista("");
}

async function generar() {
  if (vista === "trucar") return trucar();
  if (vista === "looks") return aplicarLook();
  const resultado = await api().generar_encode(items);
  if (!resultado.ok) return avisarEncode(resultado.error, "error");
  mostrarEncode(resultado);
  avisarEncode("Encode generado.", "exito");
}

async function copiar() {
  try {
    await navigator.clipboard.writeText($("encode").value);
  } catch {
    $("encode").select();
    document.execCommand("copy");
  }
  avisarEncode("Encode copiado al portapapeles.", "exito");
}

async function guardar() {
  const resultado = await api().guardar_encode($("encode").value);
  if (resultado.ok) avisarEncode(`Guardado en ${resultado.ruta}`, "exito");
  else if (!resultado.cancelado) avisarEncode(resultado.error, "error");
}

// --- Pestañas: Agregar Items / Trucar Prenda ---

let vista = "agregar";

function cambiarVista(nueva) {
  vista = nueva;
  for (const nombre of ["agregar", "trucar", "looks"]) {
    $(`vista-${nombre}`).hidden = nombre !== vista;
    $(`pestana-${nombre}`).setAttribute("aria-selected", String(nombre === vista));
  }
  $("gaturro").hidden = vista !== "looks";
  $("generar").textContent = { agregar: "Generar Encode", trucar: "Trucar Prenda", looks: "Aplicar Look" }[vista];
  avisarLista("");
  mostrarEncode(null);
  cargarParaLaVista();
}

// --- Trucar Prenda: un Item base que muestra una Pieza (cualquiera) en una Parte del cuerpo (cualquiera) ---

let prendas = []; // [{ruta, clase, partes}] del SWF abierto
let piezasDelSwf = []; // [{ruta, clase}]
let partesDelCuerpo = []; // [{id, nombre}]
let base = null;
let pieza = null; // {ruta, clase}: la ruta lleva el SWF de la Pieza, que puede ser otro
let parte = null;
let swfAbiertoNombre = null; // el SWF del Item base
let swfDePiezas = null; // de qué SWF se eligen las Piezas

function olvidarPrendas() {
  prendas = [];
  piezasDelSwf = [];
  base = pieza = parte = null;
  swfDePiezas = null;
  for (const id of ["buscar-base", "buscar-pieza", "buscar-parte", "buscar-swf-pieza"]) $(id).value = "";
  mostrarTruco();
}

async function cargarPrendas() {
  olvidarPrendas();
  const resultado = await mientras("Leyendo las Prendas e Items de mochila del SWF… (la primera vez tarda unos segundos)", () => api().prendas());
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  const resultadoPiezas = await api().piezas();
  prendas = resultado.prendas;
  partesDelCuerpo = resultado.partes_del_cuerpo;
  swfAbiertoNombre = swfDePiezas = resultado.swf;
  piezasDelSwf = resultadoPiezas.ok ? resultadoPiezas.piezas : [];
  actualizarControles();
  if (!prendas.length) return avisarLista("Este SWF no tiene Prendas ni Items de mochila.", "advertencia");
  const deMochila = prendas.filter((p) => p.tipo === "mochila").length;
  const cuantos = (n, uno, varios) => (n === 1 ? `1 ${uno}` : `${n} ${varios}`);
  avisarLista(`${cuantos(prendas.length - deMochila, "Prenda", "Prendas")}, ${cuantos(deMochila, "Item de mochila", "Items de mochila")} y ${cuantos(piezasDelSwf.length, "Pieza", "Piezas")}. Elegí el Item base.`, "exito");
  $("buscar-base").focus();
}

// Las opciones cuyo nombre contiene el texto; las que empiezan con él, primero.
// Pide las imágenes que falten (pueden no estar listas cuando se cargó el SWF).
function filtrarPorNombre(lista, texto, nombreDe = (o) => o.clase) {
  const t = texto.trim().toLowerCase();
  const coinciden = lista.filter((o) => nombreDe(o).toLowerCase().includes(t));
  const ordenadas = coinciden.sort((a, b) => !nombreDe(a).toLowerCase().startsWith(t) - !nombreDe(b).toLowerCase().startsWith(t)).slice(0, 80);
  cargarIconos(ordenadas.filter((o) => o.ruta).map((o) => o.ruta));
  return ordenadas;
}

const filaConImagen = (o) => [elementoIcono(o.ruta), etiqueta(o.clase, "nombre")];
// Un Item base: dónde queda en el juego.
const filaDeBase = (o) => [...filaConImagen(o), etiqueta(o.tipo === "mochila" ? "mochila" : "guardarropa", `ayuda tipo-${o.tipo}`)];

function mostrarTruco() {
  const caja = $("resumen-truco");
  if (!base && !pieza && !parte) {
    caja.replaceChildren(prendas.length ? "Elegí el Item base, la Pieza y la Parte del cuerpo." : "Abrí un SWF y elegí el Item base, la Pieza y la Parte del cuerpo.");
  } else {
    const hueco = (texto) => etiqueta(texto, "hueco");
    caja.replaceChildren(
      ...(base ? [elementoIcono(base.ruta), etiqueta(base.clase, "nombre")] : [hueco("Item base")]),
      etiqueta("→ muestra", "conector"),
      ...(pieza ? [elementoIcono(pieza.ruta), etiqueta(pieza.ruta.startsWith(swfAbiertoNombre + ".") ? pieza.clase : pieza.ruta, "nombre")] : [hueco("Pieza")]),
      etiqueta("en", "conector"),
      parte ? etiqueta(parte.nombre, "parte") : hueco("Parte del cuerpo")
    );
  }
  mostrarEncode(null);
}

async function trucar() {
  const resultado = await mientras("Trucando la Prenda… (tarda unos segundos)", () => api().trucar_prenda(base.clase, parte.id, pieza.ruta));
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  avisarLista("");
  mostrarEncode(resultado);
  avisarEncode("Prenda trucada. Tocá «Agregar al juego» para recibirla.", "exito");
}

crearDesplegable({
  campo: $("buscar-base"),
  lista: $("resultados-base"),
  consultar: async (t) => filtrarPorNombre(prendas, t),
  fila: filaDeBase,
  elegir: (p) => {
    base = p;
    $("buscar-base").value = p.clase;
    mostrarTruco();
    if (!pieza) $("buscar-pieza").focus();
  },
  vacio: "Ninguna Prenda ni Item de mochila se llama así.",
});

crearDesplegable({
  campo: $("buscar-pieza"),
  lista: $("resultados-pieza"),
  consultar: async (t) => filtrarPorNombre(piezasDelSwf, t),
  fila: filaConImagen,
  elegir: (p) => {
    pieza = p;
    $("buscar-pieza").value = p.clase;
    mostrarTruco();
    if (!parte) $("buscar-parte").focus();
  },
  vacio: "Ninguna Pieza se llama así.",
});

crearDesplegable({
  campo: $("buscar-parte"),
  lista: $("resultados-parte"),
  consultar: async (t) => filtrarPorNombre(partesDelCuerpo, t, (p) => `${p.nombre} ${p.id}`),
  fila: (p) => [etiqueta(p.nombre, "nombre"), etiqueta(p.id, "ayuda")],
  elegir: (p) => {
    parte = p;
    $("buscar-parte").value = p.nombre;
    mostrarTruco();
  },
  vacio: "No hay una Parte del cuerpo con ese nombre.",
});

// Las Piezas pueden salir de otro SWF del juego (se escriben "<swf>.<clase>" y el juego las busca ahí).
async function usarPiezasDe(swf) {
  $("buscar-swf-pieza").value = swf === swfAbiertoNombre ? "" : swf;
  if (swf === swfDePiezas) return;
  const resultado = await mientras(`Leyendo las Piezas de ${swf}…`, () => api().piezas(swf));
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  swfDePiezas = swf;
  piezasDelSwf = resultado.piezas;
  pieza = null;
  $("buscar-pieza").value = "";
  mostrarTruco();
  avisarLista(`${piezasDelSwf.length} Piezas de ${swf}.`, "exito");
  $("buscar-pieza").focus();
  // Sus imágenes, en segundo plano.
  const iconos = await api().preparar_iconos(swf);
  if (iconos.ok) {
    for (const ruta of [...imagenes.keys()]) if (ruta.startsWith(swf + ".")) imagenes.delete(ruta);
    cargarIconos([...document.querySelectorAll(".icono[data-ruta]")].map((c) => c.dataset.ruta));
  }
}

crearDesplegable({
  campo: $("buscar-swf-pieza"),
  lista: $("resultados-swf-pieza"),
  consultar: async (t) => (await api().buscar_en_catalogo(t)).swfs.slice(0, 80),
  fila: ({ swf, items }) => [etiqueta(swf, "nombre"), etiqueta(swf === swfAbiertoNombre ? "el mismo" : contarItems(items), "ayuda")],
  elegir: ({ swf }) => usarPiezasDe(swf),
  vacio: "No hay SWF con ese nombre.",
});

$("pestana-agregar").addEventListener("click", () => cambiarVista("agregar"));
$("pestana-trucar").addEventListener("click", () => cambiarVista("trucar"));

// --- Looks: un Item base con una Pieza (de cualquier SWF) en cada una de varias Partes del cuerpo ---

let looksGuardados = [];
let lookActual = nuevoLook();
let partesConocidas = []; // [{id, nombre}]
let piezasLook = []; // Piezas del SWF elegido en "Piezas de:"
let swfPiezasLook = null;
let iconosPreparados = new Set(); // SWF cuyas imágenes ya se pidieron preparar

function nuevoLook() {
  return { id: "", nombre: "", base: null, partes: {} };
}

async function prepararIconosDe(swf) {
  if (iconosPreparados.has(swf)) return;
  iconosPreparados.add(swf);
  const resultado = await api().preparar_iconos(swf);
  if (!resultado.ok) return;
  for (const ruta of [...imagenes.keys()]) if (ruta.startsWith(swf + ".")) imagenes.delete(ruta);
  cargarIconos([...document.querySelectorAll(".icono[data-ruta]")].map((c) => c.dataset.ruta));
}

const swfDeRuta = (ruta) => ruta.slice(0, ruta.lastIndexOf("."));

async function cargarLooks() {
  if (!partesConocidas.length) partesConocidas = (await api().partes_del_cuerpo()).partes_del_cuerpo;
  const resultado = await api().looks();
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  looksGuardados = resultado.looks;
  mostrarListaLooks();
  mostrarLook();
  if (!swfPiezasLook && swfAbierto) await usarPiezasLookDe(swfAbiertoActual);
}

function mostrarListaLooks() {
  const lista = $("lista-looks");
  if (!looksGuardados.length) {
    lista.replaceChildren(etiqueta("Todavía no guardaste ningún Look.", "ayuda vacia-chica"));
    return;
  }
  lista.replaceChildren(
    ...looksGuardados.map((look) => {
      const boton = Object.assign(document.createElement("button"), { className: "chip-look", textContent: look.nombre });
      boton.setAttribute("aria-pressed", String(look.id === lookActual.id));
      boton.addEventListener("click", () => abrirLook(look));
      return boton;
    })
  );
}

function abrirLook(look) {
  lookActual = structuredClone(look);
  mostrarListaLooks();
  mostrarLook();
  // Las imágenes de todas las Piezas del Look (pueden ser de varios SWF).
  for (const swf of new Set(Object.values(lookActual.partes).map(swfDeRuta))) prepararIconosDe(swf);
  if (lookActual.base) prepararIconosDe(swfDeRuta(lookActual.base));
}

function filaDeParteLook({ id, nombre }) {
  const fila = document.createElement("li");
  const ruta = lookActual.partes[id];

  const icono = ruta ? elementoIcono(ruta) : Object.assign(document.createElement("span"), { className: "icono vacio" });

  // El campo muestra la Pieza elegida; al escribir, ofrece las del SWF de "Piezas de:".
  const selector = Object.assign(document.createElement("div"), { className: "selector-swf selector-parte" });
  const campo = Object.assign(document.createElement("input"), {
    type: "text", value: ruta ?? "", title: ruta ?? "", placeholder: "Elegir una Pieza…", spellcheck: false, autocomplete: "off",
  });
  campo.setAttribute("aria-label", `Pieza para ${nombre}`);
  campo.disabled = ocupado;
  campo.addEventListener("focus", () => campo.select());
  const lista = Object.assign(document.createElement("ul"), { className: "resultados-swf con-iconos", hidden: true });
  selector.append(campo, lista);
  crearDesplegable({
    campo,
    lista,
    // Si el campo muestra la ruta completa de la Pieza elegida, se busca por su nombre.
    consultar: async (t) => filtrarPorNombre(piezasLook, t === ruta ? "" : t),
    fila: filaConImagen,
    elegir: (pieza) => {
      lookActual.partes[id] = pieza.ruta;
      mostrarLook();
    },
    vacio: piezasLook.length ? "Ninguna Pieza se llama así." : "Elegí de qué SWF son las Piezas (Piezas de:).",
  });

  const quitar = Object.assign(document.createElement("button"), { className: "quitar", textContent: "✕", title: `Dejar ${nombre} vacío` });
  quitar.disabled = !ruta;
  quitar.addEventListener("click", () => {
    delete lookActual.partes[id];
    mostrarLook();
  });

  fila.append(etiqueta(nombre, "parte"), icono, selector, quitar);
  return fila;
}

function mostrarLook() {
  $("nombre-look").value = lookActual.nombre;
  $("buscar-base-look").value = lookActual.base ?? "";
  const conocidas = new Set(partesConocidas.map((p) => p.id));
  const extra = Object.keys(lookActual.partes).filter((p) => !conocidas.has(p)).map((id) => ({ id, nombre: id }));
  $("partes-look").replaceChildren(...[...partesConocidas, ...extra].map(filaDeParteLook));
  cargarIconos(Object.values(lookActual.partes));
  mostrarEncode(null);
  dibujarGaturro();
}

// --- El Gaturro original del juego con las Piezas del Look ---

const COLORES_GATURRO = ["color1", "color2", "color3"];
try {
  const guardados = JSON.parse(localStorage.getItem("coloresGaturro") || "{}");
  for (const c of COLORES_GATURRO) if (/^#[0-9a-f]{6}$/i.test(guardados[c] ?? "")) $(c).value = guardados[c];
} catch {}
for (const c of COLORES_GATURRO) {
  $(c).addEventListener("input", () => {
    try {
      localStorage.setItem("coloresGaturro", JSON.stringify(Object.fromEntries(COLORES_GATURRO.map((k) => [k, $(k).value]))));
    } catch {}
    dibujarGaturro();
  });
}

// Si se piden varios seguidos, se muestra solo el último.
let pedidoGaturro = 0;
async function dibujarGaturro() {
  const pedido = ++pedidoGaturro;
  const colores = Object.fromEntries(COLORES_GATURRO.map((c) => [c, $(c).value]));
  const espera = setTimeout(() => pedido === pedidoGaturro && ($("estado-gaturro").textContent = "Preparando las imágenes…"), 400);
  const resultado = await api().gaturro({ ...lookActual.partes }, colores);
  clearTimeout(espera);
  if (pedido !== pedidoGaturro) return;
  // Sin el Gaturro original no se muestra ninguno.
  $("imagen-gaturro").hidden = !resultado.ok;
  if (!resultado.ok) {
    $("estado-gaturro").textContent = resultado.error;
    return;
  }
  $("imagen-gaturro").src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(resultado.svg);
  const clases = (rutas) => rutas.map((r) => r.slice(r.lastIndexOf(".") + 1)).join(", ");
  const avisos = resultado.aviso ? [resultado.aviso] : [];
  if (resultado.sin_lugar.length) avisos.push(`No se dibuja: ${clases(resultado.sin_lugar)}.`);
  if (resultado.sin_imagen.length) avisos.push(`Sin imagen: ${clases(resultado.sin_imagen)}.`);
  $("estado-gaturro").replaceChildren(...avisos.map((a) => etiqueta(a, "aviso-gaturro")));
}

async function usarPiezasLookDe(swf) {
  $("buscar-swf-look").value = swf === swfAbiertoActual ? "" : swf;
  if (swf === swfPiezasLook) return;
  const resultado = await mientras(`Leyendo las Piezas de ${swf}…`, () => api().piezas(swf));
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  swfPiezasLook = swf;
  piezasLook = resultado.piezas;
  avisarLista(`${piezasLook.length} Piezas de ${swf} para elegir.`, "exito");
  mostrarLook();
  prepararIconosDe(swf);
}

async function guardarLook() {
  const resultado = await api().guardar_look(lookActual);
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  lookActual = resultado.look;
  avisarLista(`Se guardó el Look «${lookActual.nombre}».`, "exito");
  await cargarLooks();
}

async function duplicarLook() {
  const resultado = await api().duplicar_look(lookActual.id);
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  lookActual = resultado.look;
  avisarLista(`Se creó «${lookActual.nombre}».`, "exito");
  await cargarLooks();
}

async function borrarLook() {
  if (!confirm(`¿Borrar el Look «${lookActual.nombre}»?`)) return;
  const resultado = await api().borrar_look(lookActual.id);
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  avisarLista(`Se borró «${lookActual.nombre}».`, "exito");
  lookActual = nuevoLook();
  await cargarLooks();
}

async function aplicarLook() {
  const resultado = await mientras("Aplicando el Look… (tarda unos segundos)", () => api().aplicar_look(lookActual));
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  avisarLista(resultado.look.base_propuesta ? `Se usó ${resultado.look.base} como Item base.` : "");
  mostrarEncode(resultado);
  avisarEncode("Look aplicado. Tocá «Agregar al juego» para recibirlo.", "exito");
}

$("nombre-look").addEventListener("input", () => {
  lookActual.nombre = $("nombre-look").value;
  mostrarEncode(null);
});

crearDesplegable({
  campo: $("buscar-base-look"),
  lista: $("resultados-base-look"),
  consultar: async (t) => filtrarPorNombre(prendas, t),
  fila: filaDeBase,
  elegir: (p) => {
    lookActual.base = p.ruta;
    mostrarLook();
  },
  vacio: "Nada del SWF abierto se llama así (abrí otro SWF arriba).",
});

crearDesplegable({
  campo: $("buscar-swf-look"),
  lista: $("resultados-swf-look"),
  consultar: async (t) => (await api().buscar_en_catalogo(t)).swfs.slice(0, 80),
  fila: ({ swf, items }) => [etiqueta(swf, "nombre"), etiqueta(swf === swfAbiertoActual ? "el abierto" : contarItems(items), "ayuda")],
  elegir: ({ swf }) => usarPiezasLookDe(swf),
  vacio: "No hay SWF con ese nombre.",
});

$("nuevo-look").addEventListener("click", () => {
  lookActual = nuevoLook();
  mostrarListaLooks();
  mostrarLook();
  $("nombre-look").focus();
});
$("guardar-look").addEventListener("click", guardarLook);
$("exportar-look").addEventListener("click", async () => {
  const resultado = await api().exportar_look(lookActual);
  if (resultado.ok) avisarLista(`Look exportado en ${resultado.ruta}`, "exito");
  else if (!resultado.cancelado) avisarLista(resultado.error, "error");
});
$("importar-look").addEventListener("click", async () => {
  const resultado = await api().importar_look();
  if (resultado.cancelado) return;
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  await cargarLooks();
  abrirLook(resultado.look);
  avisarLista(`Se importó el Look «${resultado.look.nombre}». Tocá «Aplicar Look» para usarlo.`, "exito");
});
$("duplicar-look").addEventListener("click", duplicarLook);
$("borrar-look").addEventListener("click", borrarLook);
$("pestana-looks").addEventListener("click", () => cambiarVista("looks"));

// --- Importar un Encode ---

function abrirImportar() {
  $("texto-importar").value = "";
  avisar($("mensaje-importar"), "");
  $("dialogo-importar").showModal();
  $("texto-importar").focus();
}

// Reemplaza la lista por los Items del Encode importado.
function aplicarImportado(resultado) {
  if (!resultado.ok) return avisar($("mensaje-importar"), resultado.error, "error");
  if (items.length && !confirm("La lista actual se va a reemplazar por los Items del Encode. ¿Seguir?")) return;

  $("dialogo-importar").close();
  items = resultado.items.map(({ ruta, cantidad }) => ({ ruta, cantidad }));
  mostrarLista();

  const n = items.length;
  const avisos = [`Encode importado: ${contarItems(n)}.`];
  if (resultado.otros_comandos) {
    avisos.push("Este Encode hacía otras cosas además de agregar Items; al generarlo de nuevo solo se conservan los Items.");
  }
  if (resultado.ignorados.length) {
    avisos.push(`Se ignoraron Items con formato inválido: ${resultado.ignorados.join(", ")}.`);
  }
  avisarLista(avisos.join(" "), resultado.otros_comandos || resultado.ignorados.length ? "advertencia" : "exito");
}

async function importarPegado(evento) {
  evento.preventDefault();
  aplicarImportado(await api().importar_encode($("texto-importar").value));
}

async function importarDeArchivo() {
  const resultado = await api().importar_encode_de_archivo();
  if (!resultado.cancelado) aplicarImportado(resultado);
}

// --- Configuración: juego, Fiddler y lo que falta ---

function tarjetaDeComponente(c) {
  const tarjeta = document.createElement("li");
  tarjeta.className = "componente " + (c.ok ? "ok" : "falta");

  const marca = document.createElement("span");
  marca.className = "marca";
  marca.textContent = c.ok ? "✓" : "✗";
  marca.setAttribute("aria-label", c.ok ? "Listo" : "Falta");

  const titulo = document.createElement("span");
  titulo.className = "titulo";
  titulo.textContent = c.nombre;

  const botones = document.createElement("span");
  botones.className = "botones";
  if (c.corregible) {
    const elegir = document.createElement("button");
    elegir.textContent = "Elegir…";
    elegir.title = c.corregible === "carpeta" ? "Elegir la carpeta a mano" : "Elegir el programa a mano";
    elegir.addEventListener("click", () => elegirRuta(c));
    botones.append(elegir);
  }
  if (c.corregida) {
    const auto = document.createElement("button");
    auto.textContent = "Detectar solo";
    auto.title = "Olvidar la ruta elegida a mano y detectarla automáticamente";
    auto.addEventListener("click", () => restablecerRuta(c));
    botones.append(auto);
  }

  const detalle = document.createElement("p");
  detalle.className = "detalle";
  detalle.textContent = c.corregida && c.ok ? `${c.detalle} (elegido a mano)` : c.detalle;

  tarjeta.append(marca, titulo, botones, detalle);
  if (c.ruta) {
    const ruta = document.createElement("p");
    ruta.className = "ruta";
    ruta.textContent = c.ruta;
    tarjeta.append(ruta);
  }
  if (!c.ok && c.instrucciones.length) {
    const pasos = document.createElement("ol");
    pasos.append(...c.instrucciones.map((texto) => Object.assign(document.createElement("li"), { textContent: texto })));
    tarjeta.append(pasos);
  }
  return tarjeta;
}

function mostrarEntorno(estado) {
  if (!estado.ok) return avisar($("mensaje-entorno"), estado.error, "error");
  $("componentes").replaceChildren(...estado.componentes.map(tarjetaDeComponente));
  $("indicador-entorno").className = "indicador " + (estado.listo ? "ok" : "falta");
  $("abrir-entorno").title = estado.listo ? "Todo listo para enviar Items al juego" : "Falta configurar algo";
  $("aviso-entorno").hidden = estado.listo;
}

async function revisarEntorno() {
  avisar($("mensaje-entorno"), "Revisando…", "progreso");
  mostrarEntorno(await api().estado_entorno());
  avisar($("mensaje-entorno"), "");
}

async function elegirRuta(componente) {
  const resultado = await api().elegir_ruta(componente.id, componente.corregible);
  if (resultado.cancelado) return;
  if (!resultado.ok) return avisar($("mensaje-entorno"), resultado.error, "error");
  mostrarEntorno(resultado);
  avisar($("mensaje-entorno"), `Se guardó la ruta de ${componente.nombre}.`, "exito");
}

async function restablecerRuta(componente) {
  const resultado = await api().restablecer_ruta(componente.id);
  if (!resultado.ok) return avisar($("mensaje-entorno"), resultado.error, "error");
  mostrarEntorno(resultado);
  avisar($("mensaje-entorno"), "");
}

function abrirEntorno() {
  avisar($("mensaje-entorno"), "");
  $("dialogo-entorno").showModal();
  revisarEntorno();
}

async function desactivarReglas() {
  avisar($("mensaje-entorno"), "Quitando la regla… (Fiddler se reinicia si estaba abierto)", "progreso");
  $("desactivar-reglas").disabled = true;
  try {
    const resultado = await api().desactivar_reglas();
    if (!resultado.ok) {
      return avisar($("mensaje-entorno"), [resultado.error, resultado.que_hacer].filter(Boolean).join(" "), "error");
    }
    avisar(
      $("mensaje-entorno"),
      resultado.quitadas ? "Listo: se quitó la regla de MG Items. Tus reglas no se tocaron." : "No había reglas de MG Items en Fiddler.",
      "exito"
    );
  } finally {
    $("desactivar-reglas").disabled = false;
  }
}

// --- Agregar al juego ---

function mostrarPasos(pasos) {
  $("pasos-entrega").replaceChildren(
    ...pasos.map((p) => {
      const fila = document.createElement("li");
      fila.className = p.ok ? "ok" : "falla";
      const marca = Object.assign(document.createElement("span"), { className: "marca", textContent: p.ok ? "✓" : "✗" });
      const nombre = Object.assign(document.createElement("span"), { textContent: p.nombre });
      fila.append(marca, nombre);
      if (p.detalle) fila.append(Object.assign(document.createElement("span"), { className: "detalle", textContent: p.detalle }));
      return fila;
    })
  );
}

function mostrarResultadoEntrega(titulo, texto, tipo) {
  const caja = $("resultado-entrega");
  const fuerte = Object.assign(document.createElement("strong"), { textContent: titulo });
  caja.replaceChildren(fuerte, document.createTextNode(texto));
  caja.className = "resultado " + tipo;
  caja.hidden = false;
}

async function entregar() {
  const encode = $("encode").value;
  const abierto = await api().juego_abierto();
  const aviso = abierto
    ? "Para agregar los Items se van a cerrar Mundo Gaturro y Fiddler, y se van a volver a abrir. Si estás jugando, se corta la sesión. ¿Seguir?"
    : "Para agregar los Items se va a reiniciar Fiddler y se va a abrir Mundo Gaturro. ¿Seguir?";
  if (!confirm(aviso)) return;

  $("titulo-entrega").textContent = "Agregando al juego…";
  $("pasos-entrega").replaceChildren(
    Object.assign(document.createElement("li"), { className: "detalle", textContent: "Cerrando programas, escribiendo la regla y volviendo a abrir. Puede tardar unos segundos." })
  );
  $("resultado-entrega").hidden = true;
  $("cerrar-entrega").disabled = true;
  $("dialogo-entrega").showModal();

  let resultado;
  try {
    ocupado++;
    actualizarControles();
    resultado = await api().entregar_encode(encode);
  } finally {
    ocupado--;
    actualizarControles();
    $("cerrar-entrega").disabled = false;
  }

  if (resultado.ok) {
    $("titulo-entrega").textContent = "¡Listo!";
    mostrarPasos(resultado.pasos);
    mostrarResultadoEntrega("Qué hacer ahora", resultado.que_hacer, "");
  } else if (resultado.falta_configurar) {
    $("dialogo-entrega").close();
    avisarEncode(resultado.error, "error");
    abrirEntorno();
  } else {
    $("titulo-entrega").textContent = "No se pudo agregar al juego";
    mostrarPasos(resultado.pasos || []);
    mostrarResultadoEntrega(resultado.error, resultado.que_hacer || "", "error");
  }
}

$("entregar").addEventListener("click", entregar);
$("cerrar-entrega").addEventListener("click", () => $("dialogo-entrega").close());
// Mientras se entrega no se puede cerrar el diálogo con Escape.
$("dialogo-entrega").addEventListener("cancel", (e) => {
  if ($("cerrar-entrega").disabled) e.preventDefault();
});
$("desactivar-reglas").addEventListener("click", desactivarReglas);
$("abrir-entorno").addEventListener("click", abrirEntorno);
$("ver-entorno").addEventListener("click", abrirEntorno);
$("revisar-entorno").addEventListener("click", revisarEntorno);
$("cerrar-entorno").addEventListener("click", () => $("dialogo-entorno").close());

$("abrir").addEventListener("click", abrirArchivo);
$("form-buscar").addEventListener("submit", buscar);
$("form-agregar").addEventListener("submit", agregarAMano);
$("quitar-todos").addEventListener("click", () => {
  items = [];
  mostrarLista();
});
$("generar").addEventListener("click", generar);
$("copiar").addEventListener("click", copiar);
$("guardar").addEventListener("click", guardar);
$("importar").addEventListener("click", abrirImportar);
$("form-importar").addEventListener("submit", importarPegado);
$("importar-archivo").addEventListener("click", importarDeArchivo);
$("cancelar-importar").addEventListener("click", () => $("dialogo-importar").close());
$("texto-importar").addEventListener("input", () => avisar($("mensaje-importar"), ""));

window.addEventListener("pywebviewready", async () => {
  conectado = true;
  actualizarControles();
  mostrarEntorno(await api().estado_entorno());
});
mostrarLista();
