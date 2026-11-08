// Desbloquear objetos del juego: terminator (settings.json).

let terminatorCargado = false;
let terminatorSeleccion = [];   // IDs de los objetos que el usuario quiere desbloquear

// Prefijos reconocidos → etiqueta para agrupar.
const GRUPOS_TERMINATOR = {
  "island.":          "Isla",
  "sky.":             "Cielo",
  "minigames.":       "Minijuegos",
  "angeles.":         "Ángeles",
  "extraterrestres.": "Extraterrestres",
  "buyStore.":        "Tienda",
  "arcor.":           "Promociones Arcor",
  "cards":            "Cartas coleccionables",
};

function grupoDeObjeto(id) {
  for (const [prefijo, nombre] of Object.entries(GRUPOS_TERMINATOR)) {
    if (id.startsWith(prefijo)) return nombre;
  }
  return "Otros";
}

function renderizarTerminator(objetos, atributos) {
  const lista = $("terminator-lista");
  lista.replaceChildren();

  // Agrupar objetos por categoría.
  const grupos = {};
  for (const id of objetos) {
    const g = grupoDeObjeto(id);
    (grupos[g] ??= []).push(id);
  }

  for (const [nombre, ids] of Object.entries(grupos)) {
    const titulo = document.createElement("h3");
    titulo.className = "terminator-grupo";
    titulo.textContent = nombre;
    lista.append(titulo);

    const arcor = nombre === "Promociones Arcor" || nombre === "Cartas coleccionables";
    if (arcor) {
      const nota = document.createElement("p");
      nota.className = "ayuda terminator-nota";
      nota.textContent = "Estos también están bloqueados del lado del servidor; desbloquearlos acá probablemente no sirva.";
      lista.append(nota);
    }

    const ul = document.createElement("ul");
    ul.className = "terminator-items";
    for (const id of ids) {
      const li = document.createElement("li");
      const label = document.createElement("label");
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = id;
      cb.addEventListener("change", actualizarSeleccion);
      label.append(cb, document.createTextNode(" " + id));
      li.append(label);
      ul.append(li);
    }
    lista.append(ul);
  }

  // Atributos: solo los mostramos como informativos (no hay checkbox porque casi siempre son server-side).
  if (atributos.length) {
    const titulo = document.createElement("h3");
    titulo.className = "terminator-grupo";
    titulo.textContent = "Atributos bloqueados";
    const nota = document.createElement("p");
    nota.className = "ayuda terminator-nota";
    nota.textContent = `${atributos.length} atributo(s) bloqueados por el servidor. No se pueden desbloquear desde acá.`;
    lista.append(titulo, nota);
  }

  lista.hidden = false;
  terminatorSeleccion = [];
  actualizarBoton();
}

function actualizarSeleccion() {
  terminatorSeleccion = [...$("terminator-lista").querySelectorAll("input[type=checkbox]:checked")].map((cb) => cb.value);
  actualizarBoton();
  mostrarGuia();
}

function actualizarBoton() {
  $("terminator-aplicar").disabled = terminatorSeleccion.length === 0;
}

async function cargarTerminator() {
  terminatorCargado = false;
  terminatorSeleccion = [];
  $("terminator-lista").hidden = true;
  avisar($("terminator-estado"), "Cargando desde el juego…", "progreso");
  $("terminator-cargar").disabled = true;
  try {
    const r = await api().terminator();
    if (!r.ok) return avisar($("terminator-estado"), r.error, "error");
    terminatorCargado = true;
    avisar($("terminator-estado"), "");
    renderizarTerminator(r.objetos, r.atributos);
    mostrarGuia();
  } finally {
    $("terminator-cargar").disabled = false;
  }
}

async function aplicarTerminator() {
  const abierto = await api().juego_abierto();
  const aviso = abierto
    ? "Para aplicar la config se van a cerrar Mundo Gaturro y Fiddler, y se van a volver a abrir. ¿Seguir?"
    : "Para aplicar la config se va a reiniciar Fiddler y se va a abrir Mundo Gaturro. ¿Seguir?";
  if (!confirm(aviso)) return;

  $("titulo-entrega").textContent = "Aplicando config…";
  $("pasos-entrega").replaceChildren(
    Object.assign(document.createElement("li"), { className: "detalle", textContent: "Escribiendo la regla y abriendo el juego. Puede tardar unos segundos." })
  );
  $("resultado-entrega").hidden = true;
  $("cerrar-entrega").disabled = true;
  $("dialogo-entrega").showModal();

  let resultado;
  try {
    ocupado++;
    actualizarControles();
    resultado = await api().aplicar_config(terminatorSeleccion);
  } finally {
    ocupado--;
    actualizarControles();
    $("cerrar-entrega").disabled = false;
  }

  if (resultado.ok) {
    $("titulo-entrega").textContent = "¡Config aplicada!";
    mostrarPasos(resultado.pasos);
    mostrarResultadoEntrega("Qué hacer ahora", resultado.que_hacer, "");
  } else if (resultado.falta_configurar) {
    $("dialogo-entrega").close();
    avisar($("terminator-estado"), resultado.error, "error");
    abrirEntorno();
  } else {
    $("titulo-entrega").textContent = "No se pudo aplicar la config";
    mostrarPasos(resultado.pasos || []);
    mostrarResultadoEntrega(resultado.error, resultado.que_hacer || "", "error");
  }
}

$("terminator-cargar").addEventListener("click", cargarTerminator);
$("terminator-aplicar").addEventListener("click", aplicarTerminator);
