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
    $("resumen").textContent = n === 1 ? "Encode con 1 Item." : `Encode con ${n} Items.`;
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
  $("abrir").disabled = !listo;
  $("prefijos").disabled = $("buscar").disabled = !listo || !swfAbierto;
  $("manual").disabled = $("agregar").disabled = !listo;
  $("quitar-todos").disabled = !listo || items.length === 0;
  $("importar").disabled = !listo;
  $("generar").disabled = !listo || items.length === 0;
  $("copiar").disabled = $("guardar").disabled = !listo || !$("encode").value;
}

async function abrirSwf() {
  const resultado = await mientras("Abriendo SWF…", () => api().abrir_swf());
  if (resultado.cancelado) return avisarLista("");
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  swfAbierto = true;
  actualizarControles();
  $("swf").textContent = `${resultado.swf}.swf · ${resultado.cantidad_items} Items`;
  avisarLista("SWF abierto. Escribí el comienzo de un nombre para buscar.", "exito");
  $("prefijos").focus();
}

async function buscar(evento) {
  evento.preventDefault();
  const resultado = await mientras("Buscando…", () => api().buscar_items($("prefijos").value));
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  if (!resultado.items.length) return avisarLista("No se encontraron Items con ese comienzo.", "error");
  const agregados = agregarItems(resultado.items);
  const encontrados = resultado.items.length;
  avisarLista(
    agregados === encontrados
      ? `Se agregaron ${encontrados} Items.`
      : `Se encontraron ${encontrados} Items (${agregados} nuevos en la lista).`,
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
  const avisos = [n === 1 ? "Encode importado: 1 Item." : `Encode importado: ${n} Items.`];
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

$("abrir").addEventListener("click", abrirSwf);
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

window.addEventListener("pywebviewready", () => {
  conectado = true;
  actualizarControles();
});
mostrarLista();
