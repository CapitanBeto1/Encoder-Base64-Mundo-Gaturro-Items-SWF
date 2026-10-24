// La interfaz no tiene lógica de dominio: todo pasa por window.pywebview.api (el núcleo).
// Solo guarda la lista de Items elegidos ({ruta, cantidad}), que el jugador arma
// buscando, a mano o importando un Encode.

const $ = (id) => document.getElementById(id);
const api = () => window.pywebview.api;

let items = [];
let ocupado = false;
let conectado = false; // true cuando pywebview expuso la API
let swfAbierto = false;

function avisar(elemento, texto, tipo = "") {
  elemento.textContent = texto;
  elemento.className = "mensaje " + tipo;
}

const contarItems = (n) => (n === 1 ? "1 Item" : `${n} Items`);

const avisarLista = (texto, tipo) => avisar($("mensaje"), texto, tipo);
const avisarEncode = (texto, tipo) => avisar($("mensaje-encode"), texto, tipo);

// Mientras el núcleo trabaja se bloquean los botones y se muestra qué está pasando.
async function mientras(texto, tarea) {
  ocupado = true;
  actualizarControles();
  avisarLista(texto, "progreso");
  try {
    return await tarea();
  } finally {
    ocupado = false;
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

  fila.append(nombre, campoCantidad, quitar);
  return fila;
}

function mostrarLista() {
  $("lista").replaceChildren(...items.map(filaDeItem));
  $("cantidad").textContent = items.length ? `(${items.length})` : "";
  $("lista-vacia").hidden = items.length > 0;
  // El Encode mostrado deja de corresponder a la lista.
  mostrarEncode(null);
}

function mostrarEncode(resultado) {
  $("encode").value = resultado ? resultado.encode : "";
  if (resultado) {
    const n = resultado.items.length;
    $("resumen").textContent = `Encode con ${contarItems(n)}.`;
  } else {
    $("resumen").textContent = items.length
      ? "Generá el Encode con los Items de la lista."
      : "Todavía no generaste ningún Encode.";
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
  $("generar").disabled = !listo || items.length === 0;
  $("copiar").disabled = $("guardar").disabled = $("entregar").disabled = !listo || !$("encode").value;
}

function mostrarSwfAbierto(resultado) {
  if (resultado.cancelado) return avisarLista("");
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  swfAbierto = true;
  actualizarControles();
  $("swf").textContent = `${resultado.swf}.swf · ${contarItems(resultado.cantidad_items)}`;
  if (resultado.aviso) avisarLista(resultado.aviso, "advertencia");
  else avisarLista("SWF abierto. Escribí el comienzo de un nombre para buscar.", "exito");
  $("prefijos").focus();
}

async function abrirArchivo() {
  mostrarSwfAbierto(await mientras("Abriendo SWF…", () => api().abrir_swf()));
}

// --- Elegir un SWF del catálogo ---

let resultadosSwf = [];
let activo = -1;

function cerrarResultadosSwf() {
  $("resultados-swf").hidden = true;
  $("buscar-swf").setAttribute("aria-expanded", "false");
  activo = -1;
}

function marcarActivo(indice) {
  const filas = $("resultados-swf").querySelectorAll("li[role=option]");
  filas.forEach((fila, i) => fila.classList.toggle("activo", i === indice));
  filas[indice]?.scrollIntoView({ block: "nearest" });
  activo = indice;
}

async function mostrarResultadosSwf() {
  const texto = $("buscar-swf").value;
  const { swfs } = await api().buscar_en_catalogo(texto);
  if (texto !== $("buscar-swf").value) return; // llegó tarde: el jugador siguió escribiendo
  resultadosSwf = swfs.slice(0, 80);
  const lista = $("resultados-swf");
  if (!resultadosSwf.length) {
    lista.replaceChildren(Object.assign(document.createElement("li"), { className: "vacio", textContent: "No hay SWF con ese nombre." }));
  } else {
    lista.replaceChildren(
      ...resultadosSwf.map(({ swf, items }) => {
        const fila = document.createElement("li");
        fila.setAttribute("role", "option");
        const nombre = Object.assign(document.createElement("span"), { textContent: swf });
        const cantidad = Object.assign(document.createElement("span"), { className: "ayuda", textContent: contarItems(items) });
        fila.append(nombre, cantidad);
        // mousedown en vez de click: se dispara antes de que el campo pierda el foco y cierre la lista.
        fila.addEventListener("mousedown", (e) => {
          e.preventDefault();
          abrirDelCatalogo(swf);
        });
        return fila;
      })
    );
  }
  lista.hidden = false;
  $("buscar-swf").setAttribute("aria-expanded", "true");
  activo = -1;
}

async function abrirDelCatalogo(nombre) {
  cerrarResultadosSwf();
  $("buscar-swf").value = nombre;
  mostrarSwfAbierto(await mientras(`Abriendo ${nombre} (se descarga del juego si hace falta)…`, () => api().abrir_swf_del_cdn(nombre)));
}

function teclaEnBuscarSwf(e) {
  const abierta = !$("resultados-swf").hidden;
  if (e.key === "ArrowDown") {
    e.preventDefault();
    if (!abierta) return mostrarResultadosSwf();
    marcarActivo(Math.min(activo + 1, resultadosSwf.length - 1));
  } else if (e.key === "ArrowUp" && abierta) {
    e.preventDefault();
    marcarActivo(Math.max(activo - 1, 0));
  } else if (e.key === "Enter") {
    e.preventDefault();
    const elegido = resultadosSwf[activo] ?? (resultadosSwf.length === 1 ? resultadosSwf[0] : null);
    if (abierta && elegido) abrirDelCatalogo(elegido.swf);
  } else if (e.key === "Escape") {
    cerrarResultadosSwf();
  }
}

$("buscar-swf").addEventListener("input", mostrarResultadosSwf);
$("buscar-swf").addEventListener("focus", mostrarResultadosSwf);
$("buscar-swf").addEventListener("blur", cerrarResultadosSwf);
$("buscar-swf").addEventListener("keydown", teclaEnBuscarSwf);

async function buscar(evento) {
  evento.preventDefault();
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
  if (resultado.ok) avisarEncode(`Encode guardado en ${resultado.ruta}`, "exito");
  else if (!resultado.cancelado) avisarEncode(resultado.error, "error");
}

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
    ocupado = true;
    actualizarControles();
    resultado = await api().entregar_encode(encode);
  } finally {
    ocupado = false;
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
