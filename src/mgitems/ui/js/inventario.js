// El inventario de Piezas (Looks, Acciones, Trucar Prenda): fuentes, categorías y páginas.

// --- Inventario: Piezas de una o varias fuentes, por categoría, 5×3 por página ---

// Cada categoría junta las Piezas que el juego usa en esas Partes; tocar una la pone en `parte`.
// `que` es lo que se lee debajo de cada Pieza: el casillero del Gaturro donde va.
const CATEGORIAS = [
  { id: "hats", nombre: "Sombreros", que: "Sombrero", icono: "baseball-cap", partes: ["hats"] },
  { id: "hairs", nombre: "Pelos", que: "Pelo", icono: "hair-dryer", partes: ["hairs"] },
  { id: "mouths", nombre: "Bocas", que: "Boca", icono: "smiley", partes: ["mouths"] },
  { id: "accesories", nombre: "Accesorios", que: "Accesorio", icono: "eyeglasses", partes: ["accesories", "accesories2"] },
  { id: "neck", nombre: "Cuello", que: "Cuello", icono: "coat-hanger", partes: ["neck"] },
  { id: "cloth", nombre: "Torso", que: "Torso", icono: "t-shirt", partes: ["cloth", "clothFront"] },
  { id: "arm", nombre: "Mangas", que: "Brazos", icono: "hand-fist", partes: ["arm", "armFore", "armBack"] },
  { id: "clothBack", nombre: "Espalda", que: "Espalda", icono: "backpack", partes: ["clothBack"] },
  { id: "grip", nombre: "Mano", que: "Mano", icono: "hand", partes: ["grip", "gripFore", "gripBack", "glove", "gloveFore", "gloveBack"] },
  { id: "leg", nombre: "Piernas", que: "Piernas", icono: "pants", partes: ["leg"] },
  { id: "foot", nombre: "Pies", que: "Pies", icono: "sneaker", partes: ["foot"] },
  { id: "transport", nombre: "Transportes", que: "Transporte", icono: "scooter", partes: ["transport"] },
  { id: "otros", nombre: "Otros", icono: "sparkle", partes: [] },
  // Los objetos de la casa: solo los muestra una acción (no visten al Gaturro).
  { id: "decoracion", nombre: "Decoración", icono: "couch", partes: [], solo: "acciones" },
];
const categoriasDeLaVista = () => CATEGORIAS.filter((c) => !c.solo || c.solo === vista);
// Para qué usa el juego una Pieza que no viste al Gaturro (sin uso conocido: "Objeto").
const USOS = { transporte: "Transporte", accion: "Acción", casa: "Decoración", mascota: "Mascota" };
const POR_PAGINA = 15;
const PARTES_CON_CATEGORIA = new Set(CATEGORIAS.flatMap((c) => c.partes));

const inventario = {
  cargado: false,
  piezas: [], // [{ruta, clase, swf, partes}] de las fuentes
  decoracion: [], // los objetos de la casa de las fuentes, con la forma de las Piezas (solo para las acciones)
  categoria: "hats",
  // Mientras la categoría la elige el programa, si queda vacía pasa a la primera con Piezas; la que elige el usuario
  // se respeta aunque esté vacía.
  categoriaAMano: false,
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

// Los vehículos (los que el juego solo muestra en Transporte) van en Transportes aunque ningún Item los use ahí.
const partesDePieza = (pieza) => (pieza.solo_en === "transport" ? [...pieza.partes, "transport"] : pieza.partes);
const enCategoria = (pieza, categoria) =>
  categoria.id === "decoracion" || pieza.decoracion
    ? categoria.id === "decoracion" && Boolean(pieza.decoracion)
    : categoria.id === "otros"
    ? !partesDePieza(pieza).some((p) => PARTES_CON_CATEGORIA.has(p))
    : partesDePieza(pieza).some((p) => categoria.partes.includes(p));

// Por qué el juego no mostraría esta Pieza en la Parte `parte` del Gaturro (null si la mostraría), con
// las reglas del cliente que trae el núcleo: `no_se_ve` (en ninguna) y `solo_en` (solo en esa Parte).
function motivoNoSeVe(pieza, parte) {
  // Lo que muestra una acción no pasa por las Partes del Gaturro: solo cuenta lo que dice el núcleo.
  if (parte === "action") return pieza.sin_accion ?? null;
  if (pieza.decoracion) return "un objeto de la casa solo se ve en la acción";
  if (pieza.no_se_ve) return pieza.no_se_ve;
  if (!parte) return null;
  // El efecto de cabeza: cualquier Pieza (también un vehículo), salvo las de la lista del juego con otra
  // Parte que el sombrero y las de 150 o más.
  if (parte === "effect") {
    if (pieza.lista && pieza.solo_en !== "hats") return "el juego no la deja en la cabeza";
    if (pieza.grande) return "el efecto de cabeza no dibuja lo de 150×150 o más";
    return null;
  }
  if (pieza.solo_en && pieza.solo_en !== parte && pieza.solo_en !== "transport") return `solo se ve en ${nombreDeParte(pieza.solo_en)}`;
  if (parte === "transport" && pieza.solo_en !== "transport" && !pieza.vehiculo) return "en Transporte solo se ven los vehículos";
  return null;
}

async function cargarInventario() {
  const pedido = fuentes.todos ? null : fuentes.swfs;
  if (!fuentes.todos && !fuentes.swfs.length) {
    inventario.piezas = inventario.decoracion = [];
  } else {
    const resultado = await cargando($("grilla-piezas"), "tarjetas", () => api().piezas_de_swfs(pedido));
    if (!resultado.ok) return avisarLista(resultado.error, "error");
    inventario.piezas = resultado.piezas;
    // Del mismo índice que las Piezas: ya está leído, no tarda.
    const decoracion = await api().decoracion_de_swfs(pedido);
    inventario.decoracion = decoracion.ok ? decoracion.decoracion : [];
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
          const quitar = Object.assign(document.createElement("button"), { className: "quitar", title: `Sacar ${swf} de las fuentes` });
          quitar.append(icono("x"));
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
  const texto = $("filtro-piezas").value.trim();
  const categorias = categoriasDeLaVista();
  const todas = vista === "acciones" ? [...inventario.piezas, ...inventario.decoracion] : inventario.piezas;
  const conPiezas = (c) => todas.some((p) => enCategoria(p, c));
  if (!categorias.some((c) => c.id === inventario.categoria)) inventario.categoria = categorias[0].id;
  if (!inventario.categoriaAMano && todas.length && !conPiezas(categorias.find((c) => c.id === inventario.categoria))) {
    inventario.categoria = (categorias.find(conPiezas) ?? categorias[0]).id;
  }
  const categoria = categorias.find((c) => c.id === inventario.categoria);
  $("categorias").replaceChildren(
    ...categorias.map((c) => {
      const cantidad = todas.filter((p) => enCategoria(p, c)).length;
      const pestana = Object.assign(document.createElement("button"), { className: "categoria", title: `${c.nombre} (${cantidad})` });
      pestana.setAttribute("role", "tab");
      pestana.setAttribute("aria-selected", String(c === categoria));
      pestana.append(icono(c.icono, "icono-categoria"), etiqueta(String(cantidad), "cantidad-categoria"), etiqueta(c.nombre, "nombre-categoria"));
      pestana.addEventListener("click", () => {
        inventario.categoria = c.id;
        inventario.categoriaAMano = true;
        inventario.pagina = 0;
        mostrarInventario();
      });
      return pestana;
    })
  );

  // El tipo (transporte, acción…) solo filtra en «Otros», donde están las Piezas que no visten.
  $("uso-piezas").hidden = categoria.id !== "otros";
  const uso = categoria.id === "otros" ? $("uso-piezas").value : "";
  const coincide = buscarPorNombre(texto, $("modo-nombre-piezas").value);
  const encontradas = todas.filter((p) => enCategoria(p, categoria) && coincide(p.clase) && (!uso || queEs(p).uso === uso));
  // Recomendado: primero las que son solo de esta categoría, después las que suman una más, dos más… (como en «Agregar Items»).
  const destino = vista === "acciones" ? casilleroMarcado ?? "action"
    : vista === "trucar" ? lookActual.parte
    : casilleroMarcado ?? (categoria.id === "otros" ? null : categoria.id);
  // Lo que el juego no mostraría donde va (en rojo), siempre al final, como en «Agregar Items».
  const rojo = (p) => Boolean(motivoNoSeVe(p, destino));
  const piezas = $("orden-piezas").value === "recomendado"
    ? ordenarPor(encontradas, (p) => [rojo(p), CATEGORIAS.filter((c) => c.partes.length && partesDePieza(p).some((x) => c.partes.includes(x))).length])
    : ordenarPor(ordenarPorNombre(encontradas, $("orden-piezas").value), (p) => [rojo(p)]);
  const paginas = Math.max(1, Math.ceil(piezas.length / POR_PAGINA));
  inventario.pagina = Math.min(Math.max(inventario.pagina, 0), paginas - 1);
  const visibles = piezas.slice(inventario.pagina * POR_PAGINA, (inventario.pagina + 1) * POR_PAGINA);

  $("grilla-piezas").replaceChildren(
    ...visibles.map((pieza) => {
      const puesta = destino && lookActual.partes[destino] === pieza.ruta;
      const enUso = Object.values(lookActual.partes).includes(pieza.ruta);
      const boton = Object.assign(document.createElement("button"), { className: "pieza-grilla", title: `${pieza.clase} · ${pieza.swf}` });
      boton.setAttribute("aria-label", `${pieza.clase} de ${pieza.swf}`);
      boton.setAttribute("aria-pressed", String(Boolean(puesta)));
      boton.classList.toggle("en-uso", enUso && !puesta);
      boton.disabled = ocupado;
      const motivo = motivoNoSeVe(pieza, destino);
      boton.classList.toggle("no-llega-bien", Boolean(motivo));
      boton.addEventListener("click", () => {
        ponerPieza(pieza, destino);
        if (motivo && destino && lookActual.partes[destino] === pieza.ruta) avisarLista(`${pieza.clase}: no se ve en el juego, ${motivo}.`, "advertencia");
      });
      const que = queEs(pieza);
      const tipo = etiqueta(que.texto, "tipo-pieza");
      tipo.dataset.uso = que.uso;
      boton.title += ` · ${que.texto}`;
      boton.classList.add("item-grilla");
      boton.append(elementoIcono(pieza.ruta), etiqueta(nombreConCortes(pieza.clase), "nombre-item"), tipo);
      if (motivo) {
        const noSeVe = etiqueta("No se ve", "destino-item");
        noSeVe.dataset.bien = "false";
        boton.append(noSeVe);
        boton.title += ` · No se ve en el juego: ${motivo}`;
      }
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
        ? texto ? "Ninguna Pieza se llama así." : uso ? "No hay Piezas de ese tipo en estas fuentes." : "No hay Piezas de esta categoría en estas fuentes."
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
  if (lookActual.partes[destino] !== pieza.ruta || vista === "trucar") olvidarPersonalizacion(destino); // era de la otra Pieza
  if (vista === "trucar") lookActual.partes = lookActual.partes[destino] === pieza.ruta ? {} : { [destino]: pieza.ruta };
  else if (lookActual.partes[destino] === pieza.ruta) delete lookActual.partes[destino];
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
for (const filtro of ["modo-nombre-piezas", "orden-piezas", "uso-piezas"]) {
  $(filtro).addEventListener("change", () => irAPaginaDeLooks(0));
}
$("abrir-archivo-looks").addEventListener("click", async () => {
  const resultado = await mientras("Abriendo SWF…", () => api().abrir_swf());
  mostrarSwfAbierto(resultado);
  if (!resultado.ok) return;
  fuentes = { todos: false, swfs: [...fuentes.swfs.filter((s) => s !== resultado.swf), resultado.swf] };
  guardarFuentes();
  cargarInventario();
});
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
