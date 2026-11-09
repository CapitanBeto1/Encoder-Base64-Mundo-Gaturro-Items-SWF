// Trucar Prenda: un Item base que muestra una sola Pieza en una Parte; varias juntas.

// --- Trucar Prenda: un Item base que muestra una sola Pieza (cualquiera) en una Parte (cualquiera); varias juntas ---

// La que se está armando (`base`, `parte` y en `partes` su única Pieza) y la lista de las que se reciben juntas.
function nuevaPrendaATrucar() {
  return { id: "", nombre: "", base: null, partes: {}, colores: {}, parte: "grip", lista: [] };
}

let trucarVisitada = false;
async function cargarTrucar() {
  if (!partesConocidas.length) partesConocidas = (await api().partes_del_cuerpo()).partes_del_cuerpo;
  // Todas las Partes donde puede ir la Pieza: las del cuerpo y las que usan algunas Prendas.
  const partes = [...partesConocidas.map((p) => p.id), ...Object.keys(NOMBRES_DE_OTRAS_PARTES).filter((p) => p !== "action")];
  $("parte-trucar").replaceChildren(
    ...partes.map((p) => Object.assign(document.createElement("option"), { value: p, textContent: `${nombreDeParte(p)} (${p})` }))
  );
  if (!trucarVisitada) {
    trucarVisitada = true;
    inventario.categoria = "otros"; // lo que se truca suele ser un «Otro» (si las fuentes no tienen, la primera con Piezas)
    inventario.categoriaAMano = false;
    inventario.pagina = 0;
  }
  await cargarLooks(); // las Prendas trucadas guardadas, el editor y el inventario
}

const piezaATrucar = () => Object.values(lookActual.partes)[0] ?? null;

function mostrarArmadoTrucar() {
  const pieza = piezaATrucar();
  $("pieza-trucar").replaceChildren(
    ...(pieza ? [elementoIcono(pieza), etiqueta(`${claseDeRuta(pieza)} (${swfDeRuta(pieza)})`, "nombre")] : [etiqueta("tocá una Pieza de la grilla", "ayuda")])
  );
  $("parte-trucar").value = lookActual.parte;
  $("agregar-trucada").disabled = !conectado || ocupado || !pieza || !lookActual.base;
  $("titulo-lista-trucadas").textContent = "Prendas trucadas";
  $("cantidad-trucadas").textContent = `(${lookActual.lista.length})`;
  $("lista-trucadas").replaceChildren(
    ...lookActual.lista.map((t, i) => {
      const li = document.createElement("li");
      li.title = `${t.pieza} en ${nombreDeParte(t.parte)}, en el Item ${t.base}`;
      const quitar = Object.assign(document.createElement("button"), { className: "quitar", title: "Sacar de la lista" });
      quitar.append(icono("x"));
      quitar.addEventListener("click", () => {
        lookActual.lista.splice(i, 1);
        mostrarEncode(null);
        mostrarLook();
      });
      const texto = `${claseDeRuta(t.pieza)} en ${nombreDeParte(t.parte)} · ${claseDeRuta(t.base)}`;
      li.append(elementoIcono(t.pieza), etiqueta(t.nombre ? `${t.nombre}: ${texto}` : texto, "nombre"), quitar);
      return li;
    })
  );
  cargarIconos(lookActual.lista.map((t) => t.pieza));
}

$("parte-trucar").addEventListener("change", () => {
  const pieza = piezaATrucar();
  lookActual.parte = $("parte-trucar").value;
  lookActual.partes = pieza ? { [lookActual.parte]: pieza } : {};
  mostrarLook();
});

$("agregar-trucada").addEventListener("click", () => {
  const pieza = piezaATrucar();
  if (!pieza || !lookActual.base) return;
  if (lookActual.lista.some((t) => t.base === lookActual.base)) {
    return avisarLista(`${claseDeRuta(lookActual.base)} ya está en la lista: cada Prenda trucada necesita otro Item base.`, "advertencia");
  }
  lookActual.lista.push({ base: lookActual.base, parte: lookActual.parte, pieza, nombre: lookActual.nombre.trim() });
  avisarLista(`Se agregó ${claseDeRuta(pieza)} en ${nombreDeParte(lookActual.parte)} (${claseDeRuta(lookActual.base)}). Armá otra o tocá «Trucar todas».`, "exito");
  Object.assign(lookActual, { id: "", nombre: "", base: null, partes: {} });
  mostrarEncode(null);
  mostrarListaLooks();
  mostrarLook();
});

async function trucarPrenda() {
  const lista = lookActual.lista;
  const colores = Object.keys(lookActual.colores ?? {}).length ? lookActual.colores : null;
  const persistir = $("check-persistir-trucado").checked;
  const llamada = persistir
    ? () => api().trucar_varias_via_encode(lista, colores)
    : () => api().trucar_varias(lista, colores);
  const msg = persistir ? `Trucando ${lista.length === 1 ? "la Prenda" : `${lista.length} Prendas`}…`
                        : `Trucando ${lista.length === 1 ? "la Prenda" : `${lista.length} Prendas`}… (tarda unos segundos)`;
  const resultado = await mientras(msg, llamada);
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  mostrarEncode(resultado);
  avisarLista(`${lista.length === 1 ? "Prenda trucada" : "Prendas trucadas"}: tocá «Agregar al juego» para recibirlas.`, "exito");
  mostrarBarraLook();
}
