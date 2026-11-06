// Agregar Items: los Items de una o varias fuentes, por categoría y por páginas.

// --- Agregar Items: los Items de una o varias fuentes, por categoría, 5×3 por página ---

// Las Prendas van en la categoría de su casillero (las Mangas de una remera no cuentan aparte); las
// que ocupan varios, en Disfraces. Los demás tipos, cada uno en la suya.
const CATEGORIAS_ITEMS = [
  { id: "todos", nombre: "Todos", icono: "magnifying-glass" },
  ...CATEGORIAS.filter((c) => c.que && c.id !== "transport"),
  { id: "disfraces", nombre: "Disfraces", que: "Disfraz", icono: "mask-happy" },
  { id: "mochila", nombre: "Mochila", que: "Mochila", icono: "flask" },
  { id: "transporte", nombre: "Transportes", que: "Transporte", icono: "scooter" },
  { id: "casa", nombre: "Decoración", que: "Decoración", icono: "couch" },
  { id: "mascota", nombre: "Mascotas", que: "Mascota", icono: "dog" },
  { id: "ropa_mascota", nombre: "Ropa de mascota", que: "Ropa de mascota", icono: "gift" },
  { id: "comida_mascota", nombre: "Comida, juguetes y cuidado de mascota", que: "Comida de mascota", icono: "bone",
    tipos: ["comida_mascota", "juguete_mascota", "cuidado_mascota"] },
  { id: "otros", nombre: "Otros", que: "Otro", icono: "sparkle" },
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
  const casilleros = CATEGORIAS.filter((c) => c.que && partes.some((p) => c.partes.includes(p)))
    .map((c) => (c.id === "transport" ? CATEGORIAS_ITEMS.find((i) => i.id === "transporte") : c));
  if (!casilleros.length) return [CATEGORIAS_ITEMS.find((c) => c.id === "otros")];
  const sinMangas = casilleros.length > 1 ? casilleros.filter((c) => c.id !== "arm") : casilleros;
  return sinMangas.length > 1 ? [...casilleros, CATEGORIAS_ITEMS.find((c) => c.id === "disfraces")] : casilleros;
}

// Lo que se lee debajo de un Item: sus casilleros (como en Looks) o su categoría y, si es para una
// mascota en especial, cuál.
function queEsItem(item) {
  if (item.tipo === "prenda") return categoriasDeItem(item).filter((c) => c.id !== "disfraces").map((c) => c.que).join(" · ");
  const que = { juguete_mascota: "Juguete de mascota", cuidado_mascota: "Cuidado de mascota" }[item.tipo] ?? categoriasDeItem(item)[0].que;
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
  const destino = $("destino-items").value;

  const coincide = buscarPorNombre($("filtro-items").value, $("modo-nombre-items").value);
  const encontrados = buscador.items.filter((i) => enCategoriaItems(i, categoria) && (!destino || i.destino === destino) && coincide(i.clase));
  const orden = $("orden-items").value;
  if (orden !== "exclusivos") return ordenarPor(ordenarPorNombre(encontrados, orden), (i) => [Boolean(i.motivo)]); // los rojos, al final igual
  // Primero los que son solo de esta categoría, después los que suman una más, dos más…; al final, los
  // que no llegan bien al juego (en rojo). Dentro de cada grupo, el orden de siempre.
  return ordenarPor(encontrados, (i) => [Boolean(i.motivo), categoriasDeItem(i).filter((c) => c.id !== "disfraces").length]);
}

async function cargarItemsBuscados() {
  const pedido = fuentesItems.todos ? null : fuentesItems.swfs;
  if (!fuentesItems.todos && !fuentesItems.swfs.length) {
    buscador.items = [];
  } else {
    const resultado = await cargando($("grilla-items"), "tarjetas", () => api().items_de_swfs(pedido));
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
          const quitar = Object.assign(document.createElement("button"), { className: "quitar", title: `Sacar ${swf} de las fuentes` });
        quitar.append(icono("x"));
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
      pestana.append(icono(c.icono, "icono-categoria"), etiqueta(String(cantidad), "cantidad-categoria"), etiqueta(c.nombre, "nombre-categoria"));
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
        title: `${item.clase} · ${item.swf} · ${que}\nLlega a: ${destino.nombre}` + (item.motivo ? ` (${item.motivo})` : "")
          + (item.dibujo ? "\nEs un dibujo del juego, no un Item hecho para el inventario: llega a la casa como un objeto" : ""),
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

// Los dibujos del juego para las ventanas que imitan las suyas: si no llegan, quedan los del programa.
async function ponerDibujosDelJuego() {
  const resultado = await api().dibujos_de_la_interfaz();
  if (!resultado.ok) return;
  for (const elemento of document.querySelectorAll("[data-dibujo]")) {
    const svg = resultado.dibujos[elemento.dataset.dibujo];
    if (!svg) continue;
    const url = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
    if (elemento.dataset.dibujoComo === "fondo") elemento.style.backgroundImage = `url("${url}")`;
    else elemento.replaceChildren(Object.assign(document.createElement("img"), { src: url, alt: "" }));
    elemento.classList.add("con-dibujo");
    elemento.hidden = false; // los adornos solo aparecen con su dibujo
  }
}
