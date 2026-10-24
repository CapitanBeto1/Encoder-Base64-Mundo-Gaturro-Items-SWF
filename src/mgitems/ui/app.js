// La interfaz no tiene lógica de dominio: todo pasa por window.pywebview.api (el núcleo).
// Solo guarda la lista de Items elegidos, que el jugador arma buscando o a mano.

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

function agregarItems(nuevos) {
  const antes = items.length;
  items = [...new Set([...items, ...nuevos])];
  mostrarLista();
  return items.length - antes;
}

function quitarItem(item) {
  items = items.filter((i) => i !== item);
  mostrarLista();
}

function mostrarLista() {
  const lista = $("lista");
  lista.replaceChildren(
    ...items.map((item) => {
      const fila = document.createElement("li");
      const nombre = document.createElement("span");
      nombre.textContent = item;
      const quitar = document.createElement("button");
      quitar.className = "quitar";
      quitar.textContent = "✕";
      quitar.title = `Quitar ${item}`;
      quitar.setAttribute("aria-label", `Quitar ${item}`);
      quitar.addEventListener("click", () => quitarItem(item));
      fila.append(nombre, quitar);
      return fila;
    })
  );
  $("cantidad").textContent = items.length ? `(${items.length})` : "";
  $("lista-vacia").hidden = items.length > 0;
  // El Encode mostrado deja de corresponder a la lista.
  mostrarEncode(null);
  actualizarControles();
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
  avisarLista(`SWF abierto. Escribí el comienzo de un nombre para buscar.`, "exito");
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

window.addEventListener("pywebviewready", () => {
  conectado = true;
  actualizarControles();
});
mostrarLista();
