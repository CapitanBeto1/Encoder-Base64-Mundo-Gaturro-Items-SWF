// Restricciones de ítems: gameplay.json (troublesomeItems).

let gameplayCargado = false;
let gameplaySeleccion = [];

const GRUPOS_GAMEPLAY = {
  transport: "Forzados al slot transporte",
  hats:      "Forzados al slot sombrero",
  cloth:     "Forzados al slot torso",
  "":        "Con comportamiento especial",
};

function renderizarGameplay(items) {
  const lista = $("gameplay-lista");
  lista.replaceChildren();

  const grupos = {};
  for (const item of items) {
    const g = GRUPOS_GAMEPLAY[item.attr] ?? "Otros";
    (grupos[g] ??= []).push(item);
  }

  for (const [nombre, grupo] of Object.entries(grupos)) {
    const titulo = document.createElement("h3");
    titulo.className = "terminator-grupo";
    titulo.textContent = nombre;
    lista.append(titulo);

    const ul = document.createElement("ul");
    ul.className = "terminator-items";
    for (const item of grupo) {
      const li = document.createElement("li");
      const label = document.createElement("label");
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = item.ruta;
      cb.addEventListener("change", actualizarSeleccionGameplay);
      label.append(cb, document.createTextNode(" " + item.ruta));
      li.append(label);
      ul.append(li);
    }
    lista.append(ul);
  }

  lista.hidden = false;
  gameplaySeleccion = [];
  $("gameplay-aplicar").disabled = true;
}

function actualizarSeleccionGameplay() {
  gameplaySeleccion = [...$("gameplay-lista").querySelectorAll("input[type=checkbox]:checked")].map((cb) => cb.value);
  $("gameplay-aplicar").disabled = gameplaySeleccion.length === 0;
  mostrarGuia();
}

async function cargarGameplay() {
  gameplayCargado = false;
  gameplaySeleccion = [];
  $("gameplay-lista").hidden = true;
  avisar($("gameplay-estado"), "Cargando desde el juego…", "progreso");
  $("gameplay-cargar").disabled = true;
  try {
    const r = await api().gameplay();
    if (!r.ok) return avisar($("gameplay-estado"), r.error, "error");
    gameplayCargado = true;
    avisar($("gameplay-estado"), "");
    renderizarGameplay(r.items_restringidos);
    mostrarGuia();
  } finally {
    $("gameplay-cargar").disabled = false;
  }
}

async function aplicarGameplay() {
  const abierto = await api().juego_abierto();
  const aviso = abierto
    ? "Para aplicar se van a cerrar Mundo Gaturro y Fiddler, y se van a volver a abrir. ¿Seguir?"
    : "Para aplicar se va a reiniciar Fiddler y se va a abrir Mundo Gaturro. ¿Seguir?";
  if (!confirm(aviso)) return;

  $("titulo-entrega").textContent = "Aplicando restricciones…";
  $("pasos-entrega").replaceChildren(
    Object.assign(document.createElement("li"), { className: "detalle", textContent: "Escribiendo la regla y abriendo el juego." })
  );
  $("resultado-entrega").hidden = true;
  $("cerrar-entrega").disabled = true;
  $("dialogo-entrega").showModal();

  let resultado;
  try {
    ocupado++;
    actualizarControles();
    resultado = await api().aplicar_gameplay(gameplaySeleccion);
  } finally {
    ocupado--;
    actualizarControles();
    $("cerrar-entrega").disabled = false;
  }

  if (resultado.ok) {
    $("titulo-entrega").textContent = "¡Restricciones quitadas!";
    mostrarPasos(resultado.pasos);
    mostrarResultadoEntrega("Qué hacer ahora", resultado.que_hacer, "");
  } else if (resultado.falta_configurar) {
    $("dialogo-entrega").close();
    avisar($("gameplay-estado"), resultado.error, "error");
    abrirEntorno();
  } else {
    $("titulo-entrega").textContent = "No se pudo aplicar";
    mostrarPasos(resultado.pasos || []);
    mostrarResultadoEntrega(resultado.error, resultado.que_hacer || "", "error");
  }
}

$("gameplay-cargar").addEventListener("click", cargarGameplay);
$("gameplay-aplicar").addEventListener("click", aplicarGameplay);
