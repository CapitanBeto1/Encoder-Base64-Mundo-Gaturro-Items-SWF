// Lo de toda la interfaz: el estado general, «Items a recibir», el Encode, los controles, las imágenes de los Items, el desplegable de sugerencias, las páginas y los nombres.

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
  if (resultado?.trucadas) {
    const n = resultado.trucadas.length;
    $("resumen").textContent = `${n === 1 ? "1 Prenda trucada" : `${n} Prendas trucadas`}: ${resultado.trucadas.map((t) => claseDeRuta(t.ruta)).join(", ")}.`;
  } else if (resultado?.accion) {
    $("resumen").textContent = `Acción «${resultado.accion.nombre}» en ${resultado.prenda.ruta}: está en la mochila, usala para hacerla.`;
  } else if (resultado?.look) {
    const n = Object.keys(resultado.prenda.partes).length;
    $("resumen").textContent = `Look «${resultado.look.nombre}»: ${resultado.prenda.ruta} con ${n === 1 ? "1 Pieza" : `${n} Piezas`}.` + (resultado.prenda.tipo === "mochila" ? " Está en la mochila: usalo para vestirte." : "");
  } else if (resultado && esNpc()) {
    const n = resultado.items.length;
    $("resumen").textContent = `${n === 1 ? `1 ${PESTANAS_NPC[vista]}` : `${n} ${vista}`}: ${resultado.items.map((i) => claseDeRuta(i.ruta)).join(", ")}. ${n === 1 ? "Llega" : "Llegan"} a la casa.`;
  } else if (resultado?.prenda) {
    const n = Object.keys(resultado.prenda.partes).length;
    $("resumen").textContent = `Prenda trucada: ${resultado.prenda.ruta} con ${n === 1 ? "1 Pieza" : `${n} Piezas`}.` + (resultado.prenda.tipo === "mochila" ? " Está en la mochila: usalo para vestirte." : "");
  } else if (resultado) {
    $("resumen").textContent = `Encode con ${contarItems(resultado.items.length)}.`;
  } else {
    $("resumen").textContent =
      esNpc()
        ? lookActual.lista.length ? "Tocá «Convertir todos» para generar el Encode." : "Armá uno y agregalo a la lista."
        : vista === "trucar"
        ? lookActual.lista.length ? "Tocá «Trucar todas» para generar el Encode." : "Agregá Prendas trucadas a la lista."
        : vista === "acciones"
          ? lookActual.animacion ? "Tocá «Aplicar acción» para generar el Encode." : "Elegí la animación."
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
  const puedeGenerar = vista === "agregar" ? items.length > 0 : vista === "trucar" || esNpc() ? lookActual.lista.length > 0 : Object.keys(lookActual.partes).length > 0;
  $("generar").disabled = !listo || !puedeGenerar;
  $("guardar-look").disabled = $("descartar-look").disabled = $("nuevo-look").disabled = $("importar-look").disabled = !listo;
  $("abrir-mis-looks").disabled = !listo;
  $("borrar-look").disabled = !listo || !lookActual.id;
  $("nombre-look").disabled = $("cambiar-base").disabled = $("agregar-fuente").disabled = $("todas-las-fuentes").disabled = $("abrir-archivo-looks").disabled = !listo;
  mostrarBarraLook();
  for (const nombre of PESTANAS) $(`pestana-${nombre}`).disabled = !conectado || ocupado;
  $("usar-comportamiento").disabled = $("comportamiento-a-mano").disabled = !listo;
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
  prepararIconos(resultado.swf);
  cargarParaLaVista();
}

// Lo que necesita la pestaña elegida, en orden (las cargas no se pisan entre sí).
async function cargarParaLaVista() {
  if (vista === "trucar") await cargarTrucar();
  if (vista === "looks") await cargarLooks();
  if (vista === "acciones") await cargarAcciones();
  if (esNpc()) await cargarNpcs();
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

// Si un nombre coincide con lo buscado: varios separados por coma; «empieza» (que empiece así) o
// «contiene» (que lo tenga en cualquier lugar: «ta» encuentra pantalones). Sin mayúsculas.
function buscarPorNombre(texto, modo) {
  const buscados = texto.split(",").map((t) => t.trim().toLowerCase()).filter(Boolean);
  if (!buscados.length) return () => true;
  return (nombre) => buscados.some((t) => (modo === "contiene" ? nombre.toLowerCase().includes(t) : nombre.toLowerCase().startsWith(t)));
}

// Por nombre, «az» o «za» (los números en orden: remera2 antes que remera10).
function ordenarPorNombre(lista, orden) {
  const signo = orden === "za" ? -1 : 1;
  return [...lista].sort((a, b) => signo * a.clase.localeCompare(b.clase, "es", { sensitivity: "base", numeric: true }));
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
  if (vista === "trucar") return trucarPrenda();
  if (vista === "looks") return aplicarLook();
  if (vista === "acciones") return aplicarAccion();
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
