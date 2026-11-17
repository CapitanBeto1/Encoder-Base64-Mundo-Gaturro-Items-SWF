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
  const deTipo = (tipo) => porNombre.filter((b) => b.tipo === tipo).length;
  $("tipo-ambos").querySelector(".cantidad-tipo").textContent = `(${porNombre.length})`;
  $("solo-mochila").querySelector(".cantidad-tipo").textContent = `(${deTipo("mochila")})`;
  $("solo-guardarropa").querySelector(".cantidad-tipo").textContent = `(${deTipo("prenda")})`;
  for (const id of BOTONES_TIPO) $(id).setAttribute("aria-checked", String($(id).dataset.tipo === tipoBase));
  const visibles = porNombre
    .filter((b) => tipoBase === "ambos" || b.tipo === tipoBase)
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
  avisar($("mensaje-base"), "");
  const resultado = await conEsqueleto($("lista-bases"), "filas", () => api().items_de_swfs(null));
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
  avisar($("mensaje-base"), "");
  // En Acciones, Tiendas, Portales y Minijuegos sirve cualquier Item (del índice, sin los que el juego descarta).
  const resultado = await conEsqueleto($("lista-bases"), "filas", () => (cualquierItem() ? api().items_de_swfs([swf]) : api().items_base(swf)));
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

// La misma ventana en todas las pestañas, con los mismos filtros: solo cambia qué se recibe.
$("cambiar-base").addEventListener("click", () => {
  $("ayuda-base").textContent = dePestana().ayudaBase;
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

// Al lado de la lista, el Item grande: el que está debajo del mouse o, si no, el elegido.
function mostrarEnVistaBase(fila) {
  if (!fila) return $("vista-base").replaceChildren(etiqueta("Pasá el mouse por un Item para verlo grande.", "vacio"));
  $("vista-base").replaceChildren(...[fila.querySelector(".icono")?.cloneNode(true), etiqueta(fila.querySelector(".nombre")?.textContent ?? "", "nombre"),
    etiqueta(fila.title, "ruta"), fila.querySelector(".tipo-mochila, .tipo-prenda")?.cloneNode(true)].filter(Boolean));
}
$("lista-bases").addEventListener("pointerover", (e) => {
  const fila = e.target.closest(".fila-base");
  if (fila) mostrarEnVistaBase(fila);
});
$("lista-bases").addEventListener("pointerleave", () => mostrarEnVistaBase($("lista-bases").querySelector('.fila-base[aria-pressed="true"]')));
$("cambiar-base").addEventListener("click", () => mostrarEnVistaBase(null));

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
  // Lo que falta hacer lo dice la guía de arriba; acá, lo que trae el Encode.
  $("resumen-look").textContent = $("encode").value ? $("resumen").textContent : "";
  mostrarGuia();
}

// Como Look del juego (la casilla, marcada de entrada): un Look guardado del juego, con las Piezas, los colores y la
// emoción, sin trucar nada. Sin la casilla, la Prenda base trucada con las Piezas (los colores y la emoción no llegan).
async function aplicarLook() {
  const delJuego = $("check-look-del-juego").checked;
  const resultado = delJuego
    ? await mientras("Armando el Look del juego…", () => api().look_del_juego(lookActual))
    : await mientras("Aplicando el Look… (tarda unos segundos)", () => api().aplicar_look(lookActual));
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  mostrarEncode(resultado);
  const avisos = (resultado.avisos ?? []).map((a) => `${claseDeRuta(a.ruta)}: ${a.motivo}`);
  avisarLista(
    delJuego
      ? "Look listo: tocá «Agregar al juego» y, en el juego, elegilo en la ventana de Looks (guarda hasta 8; si ya tenés 8, borrá uno antes)."
        + (avisos.length ? ` No viaja: ${avisos.join("; ")}.` : "")
      : (resultado.look.base_propuesta ? `Se usó ${resultado.look.base} como Item base. ` : "") + "Look aplicado: tocá «Agregar al juego» para recibirlo.",
    avisos.length ? "advertencia" : "exito"
  );
  mostrarBarraLook();
}
$("check-look-del-juego").addEventListener("change", () => {
  mostrarEncode(null);
  mostrarBarraLook();
});

$("aplicar-look").addEventListener("click", () => dePestana().alAplicar());
$("entregar-look").addEventListener("click", () => entregar());
$("ver-encode").addEventListener("click", () => {
  $("titulo-ver-encode").textContent = `Encode ${guardados().el.replace(/^el /, "del ").replace(/^la /, "de la ")}`;
  $("resumen-ver-encode").textContent = $("resumen").textContent;
  $("texto-ver-encode").value = $("encode").value;
  $("dialogo-ver-encode").showModal();
});
$("copiar-look").addEventListener("click", () => copiar());
$("guardar-encode-look").addEventListener("click", () => guardar());
$("cerrar-ver-encode").addEventListener("click", () => $("dialogo-ver-encode").close());
