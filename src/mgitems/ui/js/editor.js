// El editor que comparten Looks, Acciones, Trucar Prenda y las pestañas de NPC: el Item base, guardar, descartar, borrar, duplicar, y la barra de abajo (aplicar y agregar al juego).

// --- Dónde se guarda el Look (Item base): cualquier Prenda o Item de mochila de cualquier SWF ---

let basesDelSwf = []; // [{ruta, clase, tipo}]
let basesDeTodos = false; // true: los de todos los SWF del juego (del índice)

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
  const tipo = cualquierItem() ? "ambos" : tipoBase;
  const visibles = porNombre
    .filter((b) => tipo === "ambos" || (b.tipo === "mochila" ? "mochila" : "prenda") === tipo)
    .slice(0, 200);
  $("lista-bases").replaceChildren(
    ...visibles.map((b) => {
      const li = document.createElement("li");
      const boton = Object.assign(document.createElement("button"), { className: "fila-base", title: b.ruta });
      boton.setAttribute("aria-pressed", String(lookActual.base === b.ruta));
      boton.append(...filaDeBase(b));
      boton.addEventListener("click", () => {
        if (vista === "trucar" && lookActual.lista.some((t) => t.base === b.ruta)) {
          return avisar($("mensaje-base"), `${b.clase} ya está en la lista: cada uno necesita otro Item.`, "advertencia");
        }
        $("dialogo-base").close();
        lookActual.base = b.ruta;
        tiposDeItems.set(b.ruta, b.tipo);
        if (vista === "acciones" && b.tipo !== "mochila") {
          avisarLista(`${b.clase} no es de mochila: con la acción se convierte en uno y llega a la mochila.`, "advertencia");
        }
        mostrarLook();
      });
      li.append(boton);
      return li;
    })
  );
  cargarIconos(visibles.map((b) => b.ruta));
  if (basesDeTodos) for (const swf of new Set(visibles.map((b) => swfDeRuta(b.ruta)))) prepararIconosDe(swf);
}

// Los Items base de todos los SWF: las Prendas y los Items de mochila del índice (sin los que el juego
// descarta), sin analizar nada con FFDec.
async function usarBasesDeTodos() {
  const pedido = ++pedidoBases;
  basesDeTodos = true;
  $("bases-de-todos").setAttribute("aria-pressed", "true");
  $("swf-base").value = "";
  basesDelSwf = [];
  mostrarBases();
  avisar($("mensaje-base"), "Leyendo los Items base de todos los SWF…");
  const resultado = await api().items_de_swfs(null);
  if (pedido !== pedidoBases) return;
  if (!resultado.ok) return avisar($("mensaje-base"), resultado.error, "error");
  basesDelSwf = resultado.items.filter((i) => (cualquierItem() || i.tipo === "prenda" || i.tipo === "mochila") && i.destino !== "descartado" && !i.no_sirve_de_base);
  avisar($("mensaje-base"), "Escribí un nombre para encontrar el Item base (se muestran los primeros 200).");
  mostrarBases();
}

// Si se elige otro SWF antes de que llegue la respuesta, la vieja se descarta.
let pedidoBases = 0;
async function usarBasesDe(swf) {
  const pedido = ++pedidoBases;
  basesDeTodos = false;
  $("bases-de-todos").setAttribute("aria-pressed", "false");
  $("swf-base").value = swf;
  basesDelSwf = [];
  mostrarBases();
  avisar($("mensaje-base"), `Leyendo los Items base de ${swf}… (la primera vez tarda unos segundos)`);
  // En Acciones, Tiendas, Portales y Minijuegos sirve cualquier Item (del índice, sin los que el juego descarta).
  const resultado = cualquierItem() ? await api().items_de_swfs([swf]) : await api().items_base(swf);
  if (pedido !== pedidoBases) return;
  if (!resultado.ok) return avisar($("mensaje-base"), resultado.error, "error");
  if (cualquierItem() && resultado.errores?.[swf]) return avisar($("mensaje-base"), resultado.errores[swf], "error");
  basesDelSwf = cualquierItem() ? resultado.items.filter((i) => i.destino !== "descartado" && !i.no_sirve_de_base) : resultado.items;
  // En Acciones, los de mochila primero: son los que ya hacen acciones.
  if (vista === "acciones") basesDelSwf.sort((a, b) => (b.tipo === "mochila") - (a.tipo === "mochila"));
  avisar($("mensaje-base"), resultado.aviso ?? (basesDelSwf.length ? "" : "Este SWF no tiene Prendas ni Items de mochila."), "advertencia");
  mostrarBases();
  prepararIconosDe(swf);
}

$("cambiar-base").addEventListener("click", () => {
  const enAcciones = vista === "acciones";
  $("dialogo-base").classList.toggle("sin-tipos", cualquierItem());
  $("titulo-base").textContent = dePestana().tituloBase;
  $("ayuda-base").textContent = enAcciones
    ? "Cualquier Item de cualquier SWF: es lo que vas a recibir, y hace la acción cada vez que lo usás. Llega a la mochila, aunque sea una Prenda o de la casa."
    : esNpc()
    ? "Cualquier Item de cualquier SWF (de la casa, una Prenda, uno de mochila): llega a la casa con su dibujo y su nombre, y al tocarlo hace lo que elegiste."
    : vista === "trucar"
      ? "Es lo que vas a recibir: una Prenda (guardarropa) o un Item de mochila de cualquier SWF, que en vez de lo suyo muestra la Pieza elegida."
      : "El Item base es lo que vas a recibir: una Prenda (guardarropa) o un Item de mochila. Puede ser de cualquier SWF.";
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
$("bases-de-todos").addEventListener("click", usarBasesDeTodos);
for (const id of BOTONES_TIPO) {
  $(id).addEventListener("click", () => {
    tipoBase = $(id).dataset.tipo;
    mostrarBases();
  });
}
$("cerrar-base").addEventListener("click", () => $("dialogo-base").close());

// --- Guardar, descartar, borrar, duplicar ---

async function guardarLook() {
  const resultado = await llamarGuardados("guardar", lookActual);
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  lookActual = enElEditor(guardadoDe(resultado));
  avisarLista(`Se guardó ${guardados().el} «${lookActual.nombre}».`, "exito");
  await cargarLooks();
}

// Duplica el Look elegido en "Mis Looks" y elige la copia.
async function duplicarLook() {
  const resultado = await llamarGuardados("duplicar", lookElegido);
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  lookElegido = guardadoDe(resultado).id;
  mostrandoPuesto = false;
  avisarLista(`Se creó «${guardadoDe(resultado).nombre}».`, "exito");
  await cargarLooks();
}

async function borrarLook() {
  if (!confirm(`¿Borrar ${guardados().el} «${lookActual.nombre}»?`)) return;
  const resultado = await llamarGuardados("borrar", lookActual.id);
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  avisarLista(`Se borró «${lookActual.nombre}».`, "exito");
  lookActual = enElEditor(documentoNuevo());
  await cargarLooks();
}

// --- Aplicar y agregar al juego (barra de abajo) ---

function mostrarBarraLook() {
  const n = vista === "acciones" ? Number(Boolean(lookActual.animacion && lookActual.base))
    : vista === "trucar" || esNpc() ? lookActual.lista.length
    : Object.keys(lookActual.partes).length;
  const listo = conectado && !ocupado;
  $("aplicar-look").disabled = !listo || !n;
  $("entregar-look").disabled = $("ver-encode").disabled = !listo || !$("encode").value;
  $("resumen-look").textContent = $("encode").value
    ? $("resumen").textContent
    : vista === "acciones"
      ? n ? "Tocá «Aplicar acción» para generar el Encode." : "Elegí la animación y el Item donde se guarda."
      : esFondos()
      ? n ? "Tocá «Convertir todos» para generar el Encode." : "Elegí un objeto y su fondo, y agregalo a la lista."
      : esNpc()
      ? n ? "Tocá «Convertir todos» para generar el Encode." : "Elegí un Item y qué hace, y agregalo a la lista."
      : vista === "trucar"
      ? n ? "Tocá «Trucar todas» para generar el Encode." : "Armá una Prenda trucada y agregala a la lista."
      : n ? "Tocá «Aplicar Look» para generar el Encode." : "Elegí las Piezas del Look.";
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

$("aplicar-look").addEventListener("click", () => dePestana().alAplicar());
$("entregar-look").addEventListener("click", () => entregar());
$("ver-encode").addEventListener("click", () => {
  $("resumen-ver-encode").textContent = $("resumen").textContent;
  $("texto-ver-encode").value = $("encode").value;
  $("dialogo-ver-encode").showModal();
});
$("copiar-look").addEventListener("click", () => copiar());
$("guardar-encode-look").addEventListener("click", () => guardar());
$("cerrar-ver-encode").addEventListener("click", () => $("dialogo-ver-encode").close());
