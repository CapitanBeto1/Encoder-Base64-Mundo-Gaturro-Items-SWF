// Mapas: encodes para poner mapas interactivos en la casa.

let mapasCargados = false;

async function cargarMapas() {
  if (mapasCargados) return;
  const resultado = await api().mapas();
  if (!resultado.ok) return avisar($("mensaje-mapas"), resultado.error, "error");
  mapasCargados = true;
  $("mapas-lista").replaceChildren(...resultado.mapas.map((mapa) => {
    const btn = document.createElement("button");
    btn.className = "btn-mapa";
    btn.dataset.mapa = mapa.id;
    btn.append(etiqueta(mapa.nombre, "nombre-mapa"), etiqueta(mapa.descripcion, "descripcion-mapa"));
    btn.addEventListener("click", () => generarMapa(mapa.id));
    return btn;
  }));
}

async function generarMapa(mapa) {
  const resultado = await trabando(() => api().generar_encode_mapa(mapa));
  if (!resultado.ok) return avisar($("mensaje-mapas"), resultado.error, "error");
  for (const btn of $("mapas-lista").children) btn.classList.toggle("activo", btn.dataset.mapa === mapa);
  mostrarEncode(resultado);
  avisar($("mensaje-mapas"), "");
}
