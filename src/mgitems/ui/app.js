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
  if (buscador.cargado) mostrarBuscador(); // los elegidos se marcan en la grilla
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
  $("agregar-fuente-items").disabled = $("todas-las-fuentes-items").disabled = $("abrir-archivo-items").disabled = !listo;
  $("agregar-todos").disabled = !listo || !itemsVisibles().length;
  $("manual").disabled = $("agregar").disabled = !listo;
  $("quitar-todos").disabled = !listo || items.length === 0;
  $("importar").disabled = !listo;
  $("abrir-entorno").disabled = !conectado;
  const puedeGenerar = { agregar: items.length > 0, trucar: base && pieza && parte, looks: Object.keys(lookActual.partes).length > 0 }[vista];
  $("generar").disabled = !listo || !puedeGenerar;
  $("guardar-look").disabled = $("descartar-look").disabled = $("nuevo-look").disabled = $("importar-look").disabled = !listo;
  $("abrir-mis-looks").disabled = !listo;
  $("borrar-look").disabled = !listo || !lookActual.id;
  $("nombre-look").disabled = $("cambiar-base").disabled = $("agregar-fuente").disabled = $("todas-las-fuentes").disabled = !listo;
  mostrarBarraLook();
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
  else avisarLista(`SWF abierto: ${resultado.swf}.`, "exito");
  olvidarPrendas();
  prepararIconos(resultado.swf);
  cargarParaLaVista();
}

// Lo que necesita la pestaña elegida, en orden (las cargas no se pisan entre sí).
async function cargarParaLaVista() {
  if (vista === "trucar" && swfAbierto && !prendas.length) await cargarPrendas();
  if (vista === "looks") await cargarLooks();
  if (vista === "agregar" && !buscador.cargado) await cargarItemsBuscados();
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

// Sin pasaporte, el juego no deja ponerse esto («ESTE OBJETO REQUIERE PASAPORTE») ni lo dibuja.
function marcarPasaporte(boton) {
  boton.append(etiqueta("Pasaporte", "marca-pasaporte"));
  boton.title += " · Requiere pasaporte: sin pasaporte, el juego no deja ponérselo.";
}

// Los números de página, como en Google: hasta 10 a la vista, y al avanzar se corren (en la 10 se ven
// de la 5 a la 14). `pagina` empieza en 0; -1 si no hay nada que mostrar.
function mostrarPaginas(nav, pagina, paginas, ir) {
  if (pagina < 0 || paginas <= 1) return nav.replaceChildren();
  const desde = Math.max(0, Math.min(pagina - 5, paginas - 10));
  const hasta = Math.min(paginas, desde + 10);
  const botones = [];
  for (let n = desde; n < hasta; n++) {
    const boton = Object.assign(document.createElement("button"), { className: "numero-de-pagina", textContent: String(n + 1) });
    boton.setAttribute("aria-label", `Página ${n + 1}`);
    if (n === pagina) boton.setAttribute("aria-current", "page");
    boton.disabled = ocupado;
    boton.addEventListener("click", () => ir(n));
    botones.push(boton);
  }
  nav.replaceChildren(...botones, etiqueta(`de ${paginas}`, "total-paginas"));
}

// `lista` ordenada por `clave` (un arreglo que se compara elemento por elemento), sin cambiar el orden
// de los que empatan.
function ordenarPor(lista, clave) {
  const claves = new Map(lista.map((x) => [x, clave(x).map(Number)]));
  return [...lista].sort((x, y) => {
    const [a, b] = [claves.get(x), claves.get(y)];
    for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return a[i] - b[i];
    return 0;
  });
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
  if (!resultado.avisos.length) return avisarEncode("Encode generado.", "exito");
  const nombre = (ruta) => ruta.slice(ruta.lastIndexOf(".") + 1);
  avisarEncode(
    "Encode generado, pero estos no van a quedar bien: " + resultado.avisos.map((a) => `${nombre(a.ruta)} (${a.motivo})`).join("; ") + ".",
    "advertencia"
  );
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
  document.querySelector("main").classList.toggle("modo-looks", vista === "looks");
  document.querySelector("main").classList.toggle("modo-agregar", vista === "agregar");
  $("items-a-recibir").hidden = vista !== "agregar";
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
const filaDeBase = (o) => [
  ...filaConImagen(o),
  etiqueta(o.tipo === "mochila" ? "🎒 mochila" : "👕 guardarropa", `ayuda tipo-${o.tipo === "mochila" ? "mochila" : "prenda"}`),
];

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
// La pestaña se acomoda como el inventario del juego: el Gaturro a la izquierda, el inventario a la derecha.

let looksGuardados = [];
let lookActual = nuevoLook();
let partesConocidas = []; // [{id, nombre}]
let iconosPreparados = new Set(); // SWF cuyas imágenes ya se pidieron preparar

function nuevoLook() {
  return { id: "", nombre: "", base: null, partes: {}, colores: {} };
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
const claseDeRuta = (ruta) => ruta.slice(ruta.lastIndexOf(".") + 1);
const nombreDeParte = (id) => partesConocidas.find((p) => p.id === id)?.nombre ?? id;

async function cargarLooks() {
  if (!partesConocidas.length) partesConocidas = (await api().partes_del_cuerpo()).partes_del_cuerpo;
  const resultado = await api().looks();
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  looksGuardados = resultado.looks;
  mostrarListaLooks();
  mostrarLook();
  if (!inventario.cargado) await cargarInventario();
}

// --- Mis Looks: la ventana "Guarda tu Look", como en el juego ---

let lookElegido = null; // el Look tocado en la ventana (su id), o null
const ZOOM_MINIATURAS = "0.85"; // todas las miniaturas a la misma escala
const MINIMO_CASILLEROS = 9; // la grilla se completa con casilleros vacíos, como en el juego

function mostrarListaLooks() {
  $("cantidad-looks").textContent = looksGuardados.length ? `(${looksGuardados.length})` : "";
  $("look-abierto").textContent = lookActual.id ? `Editando «${lookActual.nombre}»` : lookActual.nombre ? `«${lookActual.nombre}» (sin guardar)` : "Look nuevo (sin guardar)";
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
    pedirGaturro(miniatura, coloresDe(look), look.partes);
    li.append(boton);
    return li;
  });
  const vacios = Math.max(0, MINIMO_CASILLEROS - 1 - casilleros.length);
  for (let i = 0; i < vacios; i++) casilleros.push(Object.assign(document.createElement("li"), { className: "casillero-vacio" }));
  $("grilla-looks").replaceChildren($("nuevo-look").parentElement, ...casilleros);
  mostrarLookElegido();
}

// El escenario muestra el Look puesto (el que se está editando, con sus cambios sin guardar) hasta que
// se toca otro de la grilla; ↻ vuelve a mostrar el puesto.
let mostrandoPuesto = true;

function mostrarLookElegido() {
  const look = looksGuardados.find((l) => l.id === lookElegido);
  document.querySelectorAll("#grilla-looks .casillero-look:not(.nuevo)").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.id === lookElegido)));
  $("exportar-look").disabled = $("duplicar-look").disabled = $("eliminar-look-elegido").disabled = !look;
  if (mostrandoPuesto) {
    $("nombre-look-elegido").textContent = `${lookActual.nombre || "Look nuevo"} (puesto)`;
    $("equipar-look").disabled = true; // ya está puesto
    $("gaturro-mis-looks").hidden = false;
    pedirGaturro($("gaturro-mis-looks"), coloresDe(lookActual), lookActual.partes);
    return;
  }
  $("nombre-look-elegido").textContent = look ? look.nombre : "Tocá un Look para verlo";
  $("equipar-look").disabled = !look;
  $("gaturro-mis-looks").hidden = !look;
  if (look) pedirGaturro($("gaturro-mis-looks"), coloresDe(look), look.partes);
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
  avisarLista(`Se abrió el Look «${look.nombre}».`, "exito");
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
    mostrarGaturroEn(img);
  });
}
// Elimina el Look elegido; si es el que se está editando, el editor queda con un Look nuevo.
$("eliminar-look-elegido").addEventListener("click", async () => {
  const look = looksGuardados.find((l) => l.id === lookElegido);
  if (!look || !confirm(`¿Eliminar el Look «${look.nombre}»?`)) return;
  const resultado = await api().borrar_look(look.id);
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  const posicion = looksGuardados.indexOf(look);
  if (lookActual.id === look.id) {
    lookActual = nuevoLook();
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
  lookActual = structuredClone(look);
  mostrarListaLooks();
  mostrarLook();
  // Las imágenes de todas las Piezas del Look (pueden ser de varios SWF).
  for (const swf of new Set(Object.values(lookActual.partes).map(swfDeRuta))) prepararIconosDe(swf);
  if (lookActual.base) prepararIconosDe(swfDeRuta(lookActual.base));
}

function mostrarLook() {
  $("nombre-look").value = lookActual.nombre;
  const base = lookActual.base;
  $("base-look").replaceChildren(
    ...(base ? [elementoIcono(base), etiqueta(`${claseDeRuta(base)} (${swfDeRuta(base)})`, "nombre")] : [etiqueta("se elige al aplicar", "ayuda")])
  );
  mostrarCasilleros();
  cargarIconos([...Object.values(lookActual.partes), ...(base ? [base] : [])]);
  mostrarInventario();
  mostrarEncode(null);
  mostrarBarraLook();
  dibujarGaturro();
}

// --- Casilleros: una Parte del cuerpo cada uno, a los costados del Gaturro ---

const CASILLEROS_CABEZA = ["hats", "hairs", "mouths", "accesories", "accesories2", "neck"];
const CASILLEROS_CUERPO = ["cloth", "arm", "clothBack", "grip", "gripFore", "leg", "foot"];
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
    const quitar = Object.assign(document.createElement("button"), { className: "quitar sacar-pieza", textContent: "✕", title: `Sacar la Pieza de ${nombreDeParte(id)}` });
    quitar.addEventListener("click", () => {
      delete lookActual.partes[id];
      mostrarLook();
    });
    li.append(quitar);
  }
  return li;
}

function mostrarCasilleros() {
  const ubicadas = new Set([...CASILLEROS_CABEZA, ...CASILLEROS_CUERPO]);
  // Partes del Look que no tienen casillero (de un Look importado, por ejemplo): van con el cuerpo.
  const extra = Object.keys(lookActual.partes).filter((p) => !ubicadas.has(p));
  $("casilleros-cabeza").replaceChildren(...CASILLEROS_CABEZA.map(casillero));
  $("casilleros-cuerpo").replaceChildren(...[...CASILLEROS_CUERPO, ...extra].map(casillero));
  $("poniendo-en").hidden = !casilleroMarcado;
  $("texto-poniendo-en").textContent = casilleroMarcado ? `Poniendo en: ${nombreDeParte(casilleroMarcado)}` : "";
}

$("dejar-de-poner").addEventListener("click", () => {
  casilleroMarcado = null;
  mostrarLook();
});

// --- Inventario: Piezas de una o varias fuentes, por categoría, 5×3 por página ---

// Cada categoría junta las Piezas que el juego usa en esas Partes; tocar una la pone en `parte`.
// `que` es lo que se lee debajo de cada Pieza: el casillero del Gaturro donde va.
const CATEGORIAS = [
  { id: "hats", nombre: "Sombreros", que: "Sombrero", icono: "🎩", partes: ["hats"] },
  { id: "hairs", nombre: "Pelos", que: "Pelo", icono: "💇", partes: ["hairs"] },
  { id: "mouths", nombre: "Bocas", que: "Boca", icono: "👄", partes: ["mouths"] },
  { id: "accesories", nombre: "Accesorios", que: "Accesorio", icono: "👓", partes: ["accesories", "accesories2"] },
  { id: "neck", nombre: "Cuello", que: "Cuello", icono: "🧣", partes: ["neck"] },
  { id: "cloth", nombre: "Torso", que: "Torso", icono: "👕", partes: ["cloth", "clothFront"] },
  { id: "arm", nombre: "Mangas", que: "Brazos", icono: "💪", partes: ["arm", "armFore", "armBack"] },
  { id: "clothBack", nombre: "Espalda", que: "Espalda", icono: "🎒", partes: ["clothBack"] },
  { id: "grip", nombre: "Mano", que: "Mano", icono: "✋", partes: ["grip", "gripFore", "gripBack", "glove", "gloveFore", "gloveBack"] },
  { id: "leg", nombre: "Piernas", que: "Piernas", icono: "👖", partes: ["leg"] },
  { id: "foot", nombre: "Pies", que: "Pies", icono: "👟", partes: ["foot"] },
  { id: "otros", nombre: "Otros", icono: "✨", partes: [] },
];
// Para qué usa el juego una Pieza que no viste al Gaturro (sin uso conocido: "Objeto").
const USOS = { transporte: "Transporte", accion: "Acción", casa: "Decoración", mascota: "Mascota" };
const POR_PAGINA = 15;
const PARTES_CON_CATEGORIA = new Set(CATEGORIAS.flatMap((c) => c.partes));

const inventario = {
  cargado: false,
  piezas: [], // [{ruta, clase, swf, partes}] de las fuentes
  categoria: "hats",
  pagina: 0,
};

// Las fuentes se recuerdan en esta computadora.
let fuentes = { todos: false, swfs: ["clothes1"] };
try {
  const guardadas = JSON.parse(localStorage.getItem("fuentesLooks") || "null");
  if (guardadas && Array.isArray(guardadas.swfs)) fuentes = { todos: Boolean(guardadas.todos), swfs: guardadas.swfs.filter((s) => typeof s === "string") };
} catch {}

function guardarFuentes() {
  try {
    localStorage.setItem("fuentesLooks", JSON.stringify(fuentes));
  } catch {}
}

// Lo que es una Pieza: los casilleros del Gaturro donde va, o para qué la usa el juego.
function queEs(pieza) {
  const casilleros = CATEGORIAS.filter((c) => c.que && pieza.partes.some((p) => c.partes.includes(p))).map((c) => c.que);
  if (casilleros.length) return { texto: casilleros.join(" · "), uso: "ropa" };
  if (pieza.partes.includes("transport")) return { texto: USOS.transporte, uso: "transporte" };
  return { texto: USOS[pieza.uso] ?? "Objeto", uso: pieza.uso ?? "objeto" };
}

const enCategoria = (pieza, categoria) =>
  categoria.id === "otros" ? !pieza.partes.some((p) => PARTES_CON_CATEGORIA.has(p)) : pieza.partes.some((p) => categoria.partes.includes(p));

async function cargarInventario() {
  const pedido = fuentes.todos ? null : fuentes.swfs;
  if (!fuentes.todos && !fuentes.swfs.length) {
    inventario.piezas = [];
  } else {
    const espera = fuentes.todos ? "Leyendo las Piezas de todos los SWF…" : `Leyendo las Piezas de ${fuentes.swfs.join(", ")}…`;
    const resultado = await mientras(espera, () => api().piezas_de_swfs(pedido));
    if (!resultado.ok) return avisarLista(resultado.error, "error");
    inventario.piezas = resultado.piezas;
    const errores = Object.entries(resultado.errores);
    avisarLista(errores.length ? `No se pudieron leer: ${errores.map(([s, e]) => `${s} (${e})`).join("; ")}` : "", "advertencia");
  }
  inventario.cargado = true;
  inventario.pagina = 0;
  mostrarLook();
}

function mostrarFuentes() {
  $("todas-las-fuentes").setAttribute("aria-pressed", String(fuentes.todos));
  $("lista-fuentes").replaceChildren(
    ...(fuentes.todos
      ? [etiqueta("todos los SWF del juego", "chip-fuente")]
      : fuentes.swfs.map((swf) => {
          const chip = etiqueta(swf, "chip-fuente");
          const quitar = Object.assign(document.createElement("button"), { className: "quitar", textContent: "✕", title: `Sacar ${swf} de las fuentes` });
          quitar.addEventListener("click", () => {
            fuentes.swfs = fuentes.swfs.filter((s) => s !== swf);
            guardarFuentes();
            cargarInventario();
          });
          chip.append(quitar);
          return chip;
        }))
  );
}

function mostrarInventario() {
  mostrarFuentes();
  const texto = $("filtro-piezas").value.trim().toLowerCase();
  const categoria = CATEGORIAS.find((c) => c.id === inventario.categoria);
  $("categorias").replaceChildren(
    ...CATEGORIAS.map((c) => {
      const cantidad = inventario.piezas.filter((p) => enCategoria(p, c)).length;
      const pestana = Object.assign(document.createElement("button"), { className: "categoria", title: `${c.nombre} (${cantidad})` });
      pestana.setAttribute("role", "tab");
      pestana.setAttribute("aria-selected", String(c === categoria));
      pestana.append(etiqueta(c.icono, "icono-categoria"), etiqueta(String(cantidad), "cantidad-categoria"), etiqueta(c.nombre, "nombre-categoria"));
      pestana.addEventListener("click", () => {
        inventario.categoria = c.id;
        inventario.pagina = 0;
        mostrarInventario();
      });
      return pestana;
    })
  );

  // Primero las que son solo de esta categoría, después las que suman una más, dos más… (como en «Agregar Items»).
  const piezas = ordenarPor(
    inventario.piezas.filter((p) => enCategoria(p, categoria) && p.clase.toLowerCase().includes(texto)),
    (p) => [CATEGORIAS.filter((c) => c.partes.length && p.partes.some((x) => c.partes.includes(x))).length]
  );
  const paginas = Math.max(1, Math.ceil(piezas.length / POR_PAGINA));
  inventario.pagina = Math.min(Math.max(inventario.pagina, 0), paginas - 1);
  const visibles = piezas.slice(inventario.pagina * POR_PAGINA, (inventario.pagina + 1) * POR_PAGINA);
  const destino = casilleroMarcado ?? (categoria.id === "otros" ? null : categoria.id);

  $("grilla-piezas").replaceChildren(
    ...visibles.map((pieza) => {
      const puesta = destino && lookActual.partes[destino] === pieza.ruta;
      const enUso = Object.values(lookActual.partes).includes(pieza.ruta);
      const boton = Object.assign(document.createElement("button"), { className: "pieza-grilla", title: `${pieza.clase} · ${pieza.swf}` });
      boton.setAttribute("aria-label", `${pieza.clase} de ${pieza.swf}`);
      boton.setAttribute("aria-pressed", String(Boolean(puesta)));
      boton.classList.toggle("en-uso", enUso && !puesta);
      boton.disabled = ocupado;
      boton.addEventListener("click", () => ponerPieza(pieza, destino));
      const que = queEs(pieza);
      const tipo = etiqueta(que.texto, "tipo-pieza");
      tipo.dataset.uso = que.uso;
      boton.title += ` · ${que.texto}`;
      boton.append(elementoIcono(pieza.ruta), tipo);
      if (pieza.pasaporte) marcarPasaporte(boton);
      const li = document.createElement("li");
      li.append(boton);
      return li;
    })
  );
  $("ayuda-grilla").textContent = !fuentes.todos && !fuentes.swfs.length
    ? "Agregá un SWF arriba (+ Agregar SWF) o tocá «Todos»."
    : !inventario.piezas.length
      ? ""
      : !piezas.length
        ? texto ? "Ninguna Pieza se llama así." : "No hay Piezas de esta categoría en estas fuentes."
        : !destino
          ? "Estas Piezas no tienen una Parte propia: tocá primero un casillero del Gaturro."
          : "";
  mostrarPaginas($("paginas"), piezas.length ? inventario.pagina : -1, paginas, irAPaginaDeLooks);
  $("pagina-anterior").disabled = $("diez-atras").disabled = inventario.pagina === 0;
  $("pagina-siguiente").disabled = $("diez-adelante").disabled = inventario.pagina >= paginas - 1;
  // Las imágenes de lo que se ve: se preparan por SWF a medida que hacen falta.
  cargarIconos(visibles.map((p) => p.ruta));
  for (const swf of new Set(visibles.map((p) => p.swf))) prepararIconosDe(swf);
}

function ponerPieza(pieza, destino) {
  if (!destino) {
    avisarLista("Tocá primero el casillero de la Parte donde va esta Pieza.", "advertencia");
    return;
  }
  if (lookActual.partes[destino] === pieza.ruta) delete lookActual.partes[destino];
  else lookActual.partes[destino] = pieza.ruta;
  mostrarLook();
}

$("filtro-piezas").addEventListener("input", () => {
  inventario.pagina = 0;
  mostrarInventario();
});
function irAPaginaDeLooks(pagina) {
  inventario.pagina = pagina;
  mostrarInventario();
}
$("diez-atras").addEventListener("click", () => irAPaginaDeLooks(Math.max(0, inventario.pagina - 10)));
$("diez-adelante").addEventListener("click", () => irAPaginaDeLooks(inventario.pagina + 10)); // se ajusta a la última
$("pagina-anterior").addEventListener("click", () => {
  inventario.pagina--;
  mostrarInventario();
});
$("pagina-siguiente").addEventListener("click", () => {
  inventario.pagina++;
  mostrarInventario();
});
$("todas-las-fuentes").addEventListener("click", () => {
  fuentes.todos = !fuentes.todos;
  guardarFuentes();
  cargarInventario();
});
crearDesplegable({
  campo: $("agregar-fuente"),
  lista: $("resultados-fuente"),
  consultar: async (t) => (await api().buscar_en_catalogo(t)).swfs.filter((s) => !fuentes.swfs.includes(s.swf)).slice(0, 80),
  fila: ({ swf, items }) => [etiqueta(swf, "nombre"), etiqueta(contarItems(items), "ayuda")],
  elegir: ({ swf }) => {
    fuentes = { todos: false, swfs: [...fuentes.swfs, swf] };
    guardarFuentes();
    $("agregar-fuente").value = "";
    cargarInventario();
  },
  vacio: "No hay SWF con ese nombre.",
});

// --- El Gaturro original del juego con las Piezas del Look ---

// Colores del Gaturro (como en el juego: cara, cuerpo, ojos). Cada Look tiene los suyos; los que no
// tiene, los de fábrica del juego.
let coloresDeFabrica = { color1: "#FFF200", color2: "#DDB42D", color3: "#FFFFFF" };
let tieneColorDeNariz = false;
const CLAVES_COLOR = ["color1", "color2", "color3"];
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

async function pedirGaturro(img, colores, partes = lookActual.partes) {
  const pedido = (pedidosGaturro.get(img) ?? 0) + 1;
  pedidosGaturro.set(img, pedido);
  const resultado = await api().gaturro({ ...partes }, colores);
  if (pedidosGaturro.get(img) !== pedido) return null;
  img.hidden = !resultado.ok; // sin el Gaturro original no se muestra ninguno
  if (resultado.ok) {
    svgsGaturro.set(img, resultado.svg);
    mostrarGaturroEn(img);
    coloresDeFabrica = resultado.colores_de_fabrica;
    tieneColorDeNariz = resultado.color_de_nariz;
  }
  return resultado;
}

async function dibujarGaturro() {
  const espera = setTimeout(() => ($("estado-gaturro").textContent = "Preparando las imágenes…"), 400);
  const resultado = await pedirGaturro($("imagen-gaturro"), coloresDe(lookActual));
  clearTimeout(espera);
  if (!resultado) return;
  if (!resultado.ok) {
    $("estado-gaturro").textContent = resultado.error;
    return;
  }
  const clases = (rutas) => rutas.map(claseDeRuta).join(", ");
  const avisos = resultado.aviso ? [resultado.aviso] : [];
  if (resultado.sin_lugar.length) avisos.push(`No se dibuja: ${clases(resultado.sin_lugar)}.`);
  if (resultado.sin_imagen.length) avisos.push(`Sin imagen: ${clases(resultado.sin_imagen)}.`);
  $("estado-gaturro").replaceChildren(...avisos.map((a) => etiqueta(a, "aviso-gaturro")));
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
    if (elemento.closest(".deshabilitado")) return;
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
    pedirGaturro($("gaturro-colores"), coloresEnEdicion);
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
  for (const [clave, selector] of Object.entries(selectoresColor)) {
    const habilitado = clave !== "color4" || tieneColorDeNariz;
    const contenedor = document.querySelector(`.selector-color[data-color="${clave}"]`);
    contenedor.classList.toggle("deshabilitado", !habilitado);
    contenedor.title = habilitado ? "" : "Este Gaturro (una versión anterior del juego) no tiene color de nariz.";
    selector.mostrar(coloresEnEdicion[clave] ?? "#F49AC1");
  }
}

$("colores-look").addEventListener("click", () => {
  coloresEnEdicion = coloresDe(lookActual);
  mostrarSelectoresColor();
  $("gaturro-colores").src = $("imagen-gaturro").src;
  $("dialogo-colores").showModal();
});
$("reiniciar-colores").addEventListener("click", () => {
  coloresEnEdicion = { ...coloresDeFabrica };
  mostrarSelectoresColor();
  pedirGaturro($("gaturro-colores"), coloresEnEdicion);
});
// GUARDAR: los colores pasan a ser del Look abierto (se guardan con ✓, como cualquier cambio del Look).
$("guardar-colores").addEventListener("click", () => {
  lookActual.colores = Object.fromEntries(CLAVES_COLOR.map((c) => [c, coloresEnEdicion[c]]));
  $("dialogo-colores").close();
  dibujarGaturro();
  avisarLista(lookActual.id ? "Colores cambiados: tocá ✓ para guardarlos en el Look." : "Colores cambiados.", "exito");
});
$("cerrar-colores").addEventListener("click", () => $("dialogo-colores").close());

// --- Dónde se guarda el Look (Item base): cualquier Prenda o Item de mochila de cualquier SWF ---

let basesDelSwf = []; // [{ruta, clase, tipo}]

// Qué Items se muestran: "ambos", "mochila" o "prenda" (guardarropa). Uno solo a la vez.
let tipoBase = "ambos";
const BOTONES_TIPO = ["tipo-ambos", "solo-mochila", "solo-guardarropa"];

function mostrarBases() {
  const texto = $("filtro-base").value.trim().toLowerCase();
  const porNombre = basesDelSwf.filter((b) => b.clase.toLowerCase().includes(texto));
  const deMochila = porNombre.filter((b) => b.tipo === "mochila").length;
  $("tipo-ambos").querySelector(".cantidad-tipo").textContent = `(${porNombre.length})`;
  $("solo-mochila").querySelector(".cantidad-tipo").textContent = `(${deMochila})`;
  $("solo-guardarropa").querySelector(".cantidad-tipo").textContent = `(${porNombre.length - deMochila})`;
  for (const id of BOTONES_TIPO) $(id).setAttribute("aria-checked", String($(id).dataset.tipo === tipoBase));
  const visibles = porNombre
    .filter((b) => tipoBase === "ambos" || (b.tipo === "mochila" ? "mochila" : "prenda") === tipoBase)
    .slice(0, 200);
  $("lista-bases").replaceChildren(
    ...visibles.map((b) => {
      const li = document.createElement("li");
      const boton = Object.assign(document.createElement("button"), { className: "fila-base", title: b.ruta });
      boton.setAttribute("aria-pressed", String(lookActual.base === b.ruta));
      boton.append(...filaDeBase(b));
      boton.addEventListener("click", () => {
        lookActual.base = b.ruta;
        $("dialogo-base").close();
        mostrarLook();
      });
      li.append(boton);
      return li;
    })
  );
  cargarIconos(visibles.map((b) => b.ruta));
}

// Si se elige otro SWF antes de que llegue la respuesta, la vieja se descarta.
let pedidoBases = 0;
async function usarBasesDe(swf) {
  const pedido = ++pedidoBases;
  $("swf-base").value = swf;
  basesDelSwf = [];
  mostrarBases();
  avisar($("mensaje-base"), `Leyendo los Items base de ${swf}… (la primera vez tarda unos segundos)`);
  const resultado = await api().items_base(swf);
  if (pedido !== pedidoBases) return;
  if (!resultado.ok) return avisar($("mensaje-base"), resultado.error, "error");
  basesDelSwf = resultado.items;
  avisar($("mensaje-base"), basesDelSwf.length ? "" : "Este SWF no tiene Prendas ni Items de mochila.", "advertencia");
  mostrarBases();
  prepararIconosDe(swf);
}

$("cambiar-base").addEventListener("click", () => {
  $("dialogo-base").showModal();
  $("filtro-base").value = "";
  const swf = lookActual.base ? swfDeRuta(lookActual.base) : fuentes.swfs[0];
  if (swf) usarBasesDe(swf);
  else $("swf-base").focus();
});
crearDesplegable({
  campo: $("swf-base"),
  lista: $("resultados-swf-base"),
  consultar: async (t) => (await api().buscar_en_catalogo(t)).swfs.slice(0, 80),
  fila: ({ swf, items }) => [etiqueta(swf, "nombre"), etiqueta(contarItems(items), "ayuda")],
  elegir: ({ swf }) => usarBasesDe(swf),
  vacio: "No hay SWF con ese nombre.",
});
$("filtro-base").addEventListener("input", mostrarBases);
for (const id of BOTONES_TIPO) {
  $(id).addEventListener("click", () => {
    tipoBase = $(id).dataset.tipo;
    mostrarBases();
  });
}
$("cerrar-base").addEventListener("click", () => $("dialogo-base").close());

// --- Guardar, descartar, borrar, duplicar ---

async function guardarLook() {
  const resultado = await api().guardar_look(lookActual);
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  lookActual = resultado.look;
  avisarLista(`Se guardó el Look «${lookActual.nombre}».`, "exito");
  await cargarLooks();
}

// Duplica el Look elegido en "Mis Looks" y elige la copia.
async function duplicarLook() {
  const resultado = await api().duplicar_look(lookElegido);
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  lookElegido = resultado.look.id;
  mostrandoPuesto = false;
  avisarLista(`Se creó «${resultado.look.nombre}».`, "exito");
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

// --- Aplicar y agregar al juego (barra de abajo) ---

function mostrarBarraLook() {
  const n = Object.keys(lookActual.partes).length;
  const listo = conectado && !ocupado;
  $("aplicar-look").disabled = !listo || !n;
  $("entregar-look").disabled = $("ver-encode").disabled = !listo || !$("encode").value;
  $("resumen-look").textContent = $("encode").value ? $("resumen").textContent : n ? "Tocá «Aplicar Look» para generar el Encode." : "Elegí las Piezas del Look.";
}

async function aplicarLook() {
  const resultado = await mientras("Aplicando el Look… (tarda unos segundos)", () => api().aplicar_look(lookActual));
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  mostrarEncode(resultado);
  avisarLista(
    (resultado.look.base_propuesta ? `Se usó ${resultado.look.base} como Item base. ` : "") + "Look aplicado: tocá «Agregar al juego» para recibirlo.",
    "exito"
  );
  mostrarBarraLook();
}

$("aplicar-look").addEventListener("click", aplicarLook);
$("entregar-look").addEventListener("click", entregar);
$("ver-encode").addEventListener("click", () => {
  $("resumen-ver-encode").textContent = $("resumen").textContent;
  $("texto-ver-encode").value = $("encode").value;
  $("dialogo-ver-encode").showModal();
});
$("copiar-look").addEventListener("click", copiar);
$("guardar-encode-look").addEventListener("click", guardar);
$("cerrar-ver-encode").addEventListener("click", () => $("dialogo-ver-encode").close());

$("nombre-look").addEventListener("input", () => {
  lookActual.nombre = $("nombre-look").value;
  mostrarEncode(null);
  mostrarBarraLook();
});

$("nuevo-look").addEventListener("click", () => {
  $("dialogo-mis-looks").close();
  lookActual = nuevoLook();
  casilleroMarcado = null;
  mostrarListaLooks();
  mostrarLook();
  $("nombre-look").focus();
});
$("guardar-look").addEventListener("click", guardarLook);
// ✗: vuelve a como estaba guardado (o vacío si el Look es nuevo).
$("descartar-look").addEventListener("click", () => {
  const guardado = looksGuardados.find((l) => l.id === lookActual.id);
  lookActual = guardado ? structuredClone(guardado) : nuevoLook();
  mostrarListaLooks();
  mostrarLook();
  avisarLista(guardado ? `Se descartaron los cambios de «${guardado.nombre}».` : "", "exito");
});
$("exportar-look").addEventListener("click", async () => {
  const look = looksGuardados.find((l) => l.id === lookElegido);
  if (!look) return;
  const resultado = await api().exportar_look(look);
  if (resultado.ok) avisarLista(`Look exportado en ${resultado.ruta}`, "exito");
  else if (!resultado.cancelado) avisarLista(resultado.error, "error");
});
// El Look importado queda elegido en "Mis Looks" (EQUIPAR lo abre).
$("importar-look").addEventListener("click", async () => {
  const resultado = await api().importar_look();
  if (resultado.cancelado) return;
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  lookElegido = resultado.look.id;
  mostrandoPuesto = false;
  await cargarLooks();
  avisarLista(`Se importó el Look «${resultado.look.nombre}». Tocá «Equipar» para abrirlo.`, "exito");
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
// --- Agregar Items: los Items de una o varias fuentes, por categoría, 5×3 por página ---

// Las Prendas van en la categoría de su casillero (las Mangas de una remera no cuentan aparte); las
// que ocupan varios, en Disfraces. Los demás tipos, cada uno en la suya.
const CATEGORIAS_ITEMS = [
  { id: "todos", nombre: "Todos", icono: "🔎" },
  ...CATEGORIAS.filter((c) => c.que),
  { id: "disfraces", nombre: "Disfraces", que: "Disfraz", icono: "🦸" },
  { id: "mochila", nombre: "Mochila", que: "Mochila", icono: "🧪" },
  { id: "transporte", nombre: "Transportes", que: "Transporte", icono: "🛹" },
  { id: "casa", nombre: "Decoración", que: "Decoración", icono: "🛋️" },
  { id: "mascota", nombre: "Mascotas", que: "Mascota", icono: "🐶" },
  { id: "ropa_mascota", nombre: "Ropa de mascota", que: "Ropa de mascota", icono: "🎀" },
  { id: "comida_mascota", nombre: "Comida y juguetes de mascota", que: "Comida de mascota", icono: "🦴", tipos: ["comida_mascota", "juguete_mascota"] },
  { id: "otros", nombre: "Otros", que: "Otro", icono: "✨" },
];

const buscador = {
  cargado: false,
  items: [], // [{ruta, clase, swf, tipo, partes}] de las fuentes
  categoria: "todos",
  pagina: 0,
};

let fuentesItems = { todos: false, swfs: [] };
try {
  const guardadas = JSON.parse(localStorage.getItem("fuentesAgregar") || "null");
  if (guardadas && Array.isArray(guardadas.swfs)) fuentesItems = { todos: Boolean(guardadas.todos), swfs: guardadas.swfs.filter((s) => typeof s === "string") };
} catch {}

function guardarFuentesItems() {
  try {
    localStorage.setItem("fuentesAgregar", JSON.stringify(fuentesItems));
  } catch {}
}

// Las categorías de un Item, con la misma regla que las Piezas en Looks: una Prenda está en cada
// categoría de las Partes que viste (una remera, en Torso y en Mangas; una capa con remera, en Torso
// y en Espalda), y además en Disfraces si ocupa varias (sin contar las Mangas de una remera). Los
// demás tipos, cada uno en la suya.
function categoriasDeItem(item) {
  if (item.tipo !== "prenda") return [CATEGORIAS_ITEMS.find((c) => (c.tipos ?? [c.id]).includes(item.tipo)) ?? CATEGORIAS_ITEMS.at(-1)];
  // Una Prenda rota (sin Piezas, o en una Parte que el Gaturro no tiene) va donde va su Pieza parecida.
  const partes = item.partes.some((p) => PARTES_CON_CATEGORIA.has(p)) ? item.partes : item.parecido ?? [];
  const casilleros = CATEGORIAS.filter((c) => c.que && partes.some((p) => c.partes.includes(p)));
  if (!casilleros.length) return [CATEGORIAS_ITEMS.find((c) => c.id === "otros")];
  const sinMangas = casilleros.length > 1 ? casilleros.filter((c) => c.id !== "arm") : casilleros;
  return sinMangas.length > 1 ? [...casilleros, CATEGORIAS_ITEMS.find((c) => c.id === "disfraces")] : casilleros;
}

// Lo que se lee debajo de un Item: sus casilleros (como en Looks) o su categoría y, si es para una
// mascota en especial, cuál.
function queEsItem(item) {
  if (item.tipo === "prenda") return categoriasDeItem(item).filter((c) => c.id !== "disfraces").map((c) => c.que).join(" · ");
  const que = item.tipo === "juguete_mascota" ? "Juguete de mascota" : categoriasDeItem(item)[0].que;
  return item.mascota ? `${que.replace(/ de mascota$/, "")} · ${item.mascota}` : que;
}

// Dónde llega cada Item al juego (lo calcula el núcleo con las reglas del cliente del juego).
const DESTINOS = {
  guardarropa: { nombre: "Guardarropa" },
  mochila: { nombre: "Mochila" },
  casa: { nombre: "Casa" },
  mascota: { nombre: "Mascota nueva" },
  pantalla_mascota: { nombre: "Solo en la mascota" },
  sesion: { nombre: "Se borra al salir" },
  oculto: { nombre: "No se ve" },
  descartado: { nombre: "No llega" },
};

const enCategoriaItems = (item, categoria) => categoria.id === "todos" || categoriasDeItem(item).includes(categoria);

// Los que coinciden con la categoría y con el nombre (varios, separados por coma): que empiece así o,
// si se eligió «Contiene», que lo tenga en cualquier lugar (pantalones con «ta»).
function itemsVisibles() {
  const categoria = CATEGORIAS_ITEMS.find((c) => c.id === buscador.categoria);
  const comienzos = $("filtro-items").value.split(",").map((t) => t.trim().toLowerCase()).filter(Boolean);
  const destino = $("destino-items").value;
  const contiene = $("modo-nombre-items").value === "contiene";
  let encontrados = buscador.items.filter(
    (i) => enCategoriaItems(i, categoria) && (!destino || i.destino === destino) &&
      (!comienzos.length || comienzos.some((t) => (contiene ? i.clase.toLowerCase().includes(t) : i.clase.toLowerCase().startsWith(t))))
  );
  const orden = $("orden-items").value;
  if (orden !== "exclusivos") {
    const signo = orden === "za" ? -1 : 1;
    encontrados = [...encontrados].sort((a, b) => signo * a.clase.localeCompare(b.clase, "es", { sensitivity: "base", numeric: true }));
    return ordenarPor(encontrados, (i) => [Boolean(i.motivo)]); // los rojos, al final igual
  }
  // Primero los que son solo de esta categoría, después los que suman una más, dos más…; al final, los
  // que no llegan bien al juego (en rojo). Dentro de cada grupo, el orden de siempre.
  return ordenarPor(encontrados, (i) => [Boolean(i.motivo), categoriasDeItem(i).filter((c) => c.id !== "disfraces").length]);
}

async function cargarItemsBuscados() {
  const pedido = fuentesItems.todos ? null : fuentesItems.swfs;
  if (!fuentesItems.todos && !fuentesItems.swfs.length) {
    buscador.items = [];
  } else {
    const espera = fuentesItems.todos ? "Leyendo los Items de todos los SWF…" : `Leyendo los Items de ${fuentesItems.swfs.join(", ")}…`;
    const resultado = await mientras(espera, () => api().items_de_swfs(pedido));
    if (!resultado.ok) return avisarLista(resultado.error, "error");
    buscador.items = resultado.items;
    const errores = Object.entries(resultado.errores);
    avisarLista(errores.length ? `No se pudieron leer: ${errores.map(([s, e]) => `${s} (${e})`).join("; ")}` : "", "advertencia");
  }
  buscador.cargado = true;
  buscador.pagina = 0;
  mostrarBuscador();
}

function mostrarFuentesItems() {
  $("todas-las-fuentes-items").setAttribute("aria-pressed", String(fuentesItems.todos));
  $("lista-fuentes-items").replaceChildren(
    ...(fuentesItems.todos
      ? [etiqueta("todos los SWF del juego", "chip-fuente")]
      : fuentesItems.swfs.map((swf) => {
          const chip = etiqueta(swf, "chip-fuente");
          const quitar = Object.assign(document.createElement("button"), { className: "quitar", textContent: "✕", title: `Sacar ${swf} de las fuentes` });
          quitar.addEventListener("click", () => {
            fuentesItems.swfs = fuentesItems.swfs.filter((s) => s !== swf);
            guardarFuentesItems();
            cargarItemsBuscados();
          });
          chip.append(quitar);
          return chip;
        }))
  );
}

function mostrarBuscador() {
  mostrarFuentesItems();
  const categoria = CATEGORIAS_ITEMS.find((c) => c.id === buscador.categoria);
  $("categorias-items").replaceChildren(
    ...CATEGORIAS_ITEMS.map((c) => {
      const cantidad = buscador.items.filter((i) => enCategoriaItems(i, c)).length;
      const pestana = Object.assign(document.createElement("button"), { className: "categoria", title: `${c.nombre} (${cantidad})` });
      pestana.setAttribute("role", "tab");
      pestana.setAttribute("aria-selected", String(c === categoria));
      pestana.append(etiqueta(c.icono, "icono-categoria"), etiqueta(String(cantidad), "cantidad-categoria"), etiqueta(c.nombre, "nombre-categoria"));
      pestana.addEventListener("click", () => {
        buscador.categoria = c.id;
        buscador.pagina = 0;
        mostrarBuscador();
      });
      return pestana;
    })
  );

  const visibles = itemsVisibles();
  const paginas = Math.max(1, Math.ceil(visibles.length / POR_PAGINA));
  buscador.pagina = Math.min(Math.max(buscador.pagina, 0), paginas - 1);
  const pagina = visibles.slice(buscador.pagina * POR_PAGINA, (buscador.pagina + 1) * POR_PAGINA);
  $("grilla-items").replaceChildren(
    ...pagina.map((item) => {
      const que = queEsItem(item);
      const destino = DESTINOS[item.destino] ?? DESTINOS.casa;
      const boton = Object.assign(document.createElement("button"), {
        className: "pieza-grilla item-grilla",
        title: `${item.clase} · ${item.swf} · ${que}\nLlega a: ${destino.nombre}` + (item.motivo ? ` (${item.motivo})` : ""),
      });
      boton.setAttribute("aria-label", `${item.clase} de ${item.swf}`);
      boton.setAttribute("aria-pressed", String(items.some((i) => i.ruta === item.ruta)));
      boton.classList.toggle("no-llega-bien", Boolean(item.motivo));
      boton.disabled = ocupado;
      boton.addEventListener("click", () => {
        if (items.some((i) => i.ruta === item.ruta)) return quitarItem(item.ruta);
        agregarItems([item.ruta]);
        if (item.motivo) avisarLista(`${item.clase}: ${destino.nombre.toLowerCase()}, ${item.motivo}.`, "advertencia");
      });
      const tipo = etiqueta(que, "tipo-pieza");
      tipo.dataset.uso = item.tipo === "prenda" ? "ropa" : item.tipo === "otro" ? "objeto" : item.tipo.endsWith("mascota") ? "mascota" : item.tipo;
      const llega = etiqueta(destino.nombre, "destino-item");
      llega.dataset.bien = String(!item.motivo);
      boton.append(elementoIcono(item.ruta), etiqueta(item.clase, "nombre-item"), tipo, llega);
      if (item.pasaporte) marcarPasaporte(boton);
      const li = document.createElement("li");
      li.append(boton);
      return li;
    })
  );
  $("ayuda-grilla-items").textContent = !fuentesItems.todos && !fuentesItems.swfs.length
    ? "Agregá un SWF arriba (+ Agregar SWF) o tocá «Todos»."
    : !buscador.items.length || visibles.length
      ? ""
      : $("filtro-items").value.trim()
        ? $("modo-nombre-items").value === "contiene" ? "Ningún Item tiene eso en el nombre." : "Ningún Item empieza así."
        : "No hay Items de esta categoría en estas fuentes.";
  $("numero-pagina-items").textContent = visibles.length ? contarItems(visibles.length) : "";
  mostrarPaginas($("paginas-items"), visibles.length ? buscador.pagina : -1, paginas, irAPaginaDeItems);
  $("pagina-anterior-items").disabled = $("diez-atras-items").disabled = buscador.pagina === 0;
  $("pagina-siguiente-items").disabled = $("diez-adelante-items").disabled = buscador.pagina >= paginas - 1;
  $("agregar-todos").disabled = !conectado || ocupado || !visibles.length;
  cargarIconos(pagina.map((i) => i.ruta));
  for (const swf of new Set(pagina.map((i) => i.swf))) prepararIconosDe(swf);
}

// Saltea los que el juego descarta (no llegarían a ningún lado).
function agregarTodos() {
  const visibles = itemsVisibles();
  const validos = visibles.filter((i) => i.destino !== "descartado");
  const agregados = agregarItems(validos.map((i) => i.ruta));
  const salteados = visibles.length - validos.length;
  avisarLista(
    `Se agregaron ${contarItems(agregados)}` + (agregados < validos.length ? " (los demás ya estaban)" : "") +
      (salteados ? `; se saltearon ${salteados} que el juego descarta.` : "."),
    salteados ? "advertencia" : "exito"
  );
}

async function abrirArchivoItems() {
  const resultado = await mientras("Abriendo SWF…", () => api().abrir_swf());
  mostrarSwfAbierto(resultado);
  if (!resultado.ok) return;
  fuentesItems = { todos: false, swfs: [...fuentesItems.swfs.filter((s) => s !== resultado.swf), resultado.swf] };
  guardarFuentesItems();
  cargarItemsBuscados();
}

crearDesplegable({
  campo: $("agregar-fuente-items"),
  lista: $("resultados-fuente-items"),
  consultar: async (t) => (await api().buscar_en_catalogo(t)).swfs.filter((s) => !fuentesItems.swfs.includes(s.swf)).slice(0, 80),
  fila: ({ swf, items }) => [etiqueta(swf, "nombre"), etiqueta(contarItems(items), "ayuda")],
  elegir: ({ swf }) => {
    fuentesItems = { todos: false, swfs: [...fuentesItems.swfs, swf] };
    guardarFuentesItems();
    $("agregar-fuente-items").value = "";
    cargarItemsBuscados();
  },
  vacio: "No hay SWF con ese nombre.",
});
$("todas-las-fuentes-items").addEventListener("click", () => {
  fuentesItems.todos = !fuentesItems.todos;
  guardarFuentesItems();
  cargarItemsBuscados();
});
$("abrir-archivo-items").addEventListener("click", abrirArchivoItems);
$("filtro-items").addEventListener("input", () => {
  buscador.pagina = 0;
  mostrarBuscador();
});
function irAPaginaDeItems(pagina) {
  buscador.pagina = pagina;
  mostrarBuscador();
}
$("diez-atras-items").addEventListener("click", () => irAPaginaDeItems(Math.max(0, buscador.pagina - 10)));
$("diez-adelante-items").addEventListener("click", () => irAPaginaDeItems(buscador.pagina + 10)); // se ajusta a la última
for (const filtro of ["orden-items", "destino-items", "modo-nombre-items"]) {
  $(filtro).addEventListener("change", () => irAPaginaDeItems(0));
}
$("pagina-anterior-items").addEventListener("click", () => {
  buscador.pagina--;
  mostrarBuscador();
});
$("pagina-siguiente-items").addEventListener("click", () => {
  buscador.pagina++;
  mostrarBuscador();
});
$("agregar-todos").addEventListener("click", agregarTodos);

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
  cargarParaLaVista();
});
mostrarLista();
