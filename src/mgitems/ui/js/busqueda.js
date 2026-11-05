// Buscar por imagen: qué Item es una captura del juego.

// --- Buscar por imagen: qué Item es una captura del juego (de una casa ajena, de otro Gaturro…) ---

// `se_parece` y `descartados`: lo que el jugador marcó para buscar de nuevo, mejor (se olvida con otra captura).
const busqueda = { imagen: null, recorte: null, listos: false, buscando: false, que: "", se_parece: [], descartados: [], resultados: [] };

function olvidarGuia() {
  busqueda.se_parece = [];
  busqueda.descartados = [];
}

$("buscar-por-imagen").addEventListener("click", async () => {
  $("dialogo-imagen").showModal();
  $("zona-imagen").focus();
  if (!partesConocidas.length) partesConocidas = (await api().partes_del_cuerpo()).partes_del_cuerpo; // para «Cortado: su …»
  const estado = await api().estado_busqueda();
  if (!estado.ok) return avisar($("mensaje-imagen"), estado.error, "error");
  busqueda.listos = estado.listos;
  $("tamano-datos").textContent = `${Math.round(estado.tamano / 1e6)} MB`;
  if ($("que-imagen").options.length === 1) {
    const opciones = await api().opciones_que_es();
    if (opciones.ok) {
      $("que-imagen").append(...opciones.opciones.map((o) => Object.assign(document.createElement("option"), { value: o.id, textContent: o.nombre })));
    }
  }
  mostrarBusqueda();
});
$("que-imagen").addEventListener("change", () => {
  busqueda.que = $("que-imagen").value;
  busqueda.descartados = []; // lo descartado era de otra cosa
  buscarCaptura();
});
$("ninguno-imagen").addEventListener("click", () => {
  busqueda.descartados = [...new Set([...busqueda.descartados, ...busqueda.resultados.map((r) => r.ruta)])];
  busqueda.se_parece = busqueda.se_parece.filter((r) => !busqueda.descartados.includes(r));
  buscarCaptura();
});
$("reiniciar-imagen").addEventListener("click", () => {
  olvidarGuia();
  buscarCaptura();
});
$("cerrar-imagen").addEventListener("click", () => $("dialogo-imagen").close());

function mostrarBusqueda() {
  $("bajar-datos").hidden = $("bajar-datos-busqueda").hidden = busqueda.listos;
  $("buscar-imagen").hidden = !busqueda.listos;
  $("buscar-imagen").disabled = !busqueda.imagen || busqueda.buscando;
  $("quitar-rectangulo").disabled = !busqueda.recorte;
  $("ninguno-imagen").disabled = !busqueda.resultados.length || busqueda.buscando;
  $("reiniciar-imagen").disabled = (!busqueda.se_parece.length && !busqueda.descartados.length) || busqueda.buscando;
  const guia = [busqueda.se_parece.length && `te guiás por ${busqueda.se_parece.map(claseDeRuta).join(", ")}`,
                busqueda.descartados.length && `${busqueda.descartados.length} descartados`].filter(Boolean);
  $("guia-imagen").textContent = guia.length ? `(${guia.join(" · ")})` : "";
  $("lienzo-imagen").hidden = !busqueda.imagen;
  $("ayuda-zona").hidden = Boolean(busqueda.imagen);
}

// La captura: pegada, arrastrada o elegida. Se busca enseguida (y otra vez al marcar el rectángulo).
function cargarCaptura(archivo) {
  if (!archivo || !archivo.type.startsWith("image/")) return avisar($("mensaje-imagen"), "Eso no es una imagen.", "advertencia");
  const lector = new FileReader();
  lector.onload = () => {
    busqueda.imagen = lector.result;
    busqueda.recorte = null;
    busqueda.resultados = [];
    olvidarGuia();
    $("imagen-captura").src = busqueda.imagen;
    $("rectangulo-imagen").hidden = true;
    $("resultados-imagen").replaceChildren();
    mostrarBusqueda();
    buscarCaptura();
  };
  lector.readAsDataURL(archivo);
}
document.addEventListener("paste", (evento) => {
  if (!$("dialogo-imagen").open) return;
  const archivo = [...(evento.clipboardData?.items ?? [])].find((i) => i.type.startsWith("image/"))?.getAsFile();
  if (archivo) {
    evento.preventDefault();
    cargarCaptura(archivo);
  } else {
    avisar($("mensaje-imagen"), "No hay una imagen copiada. Recortá con Win+Shift+S y pegá con Ctrl+V.", "advertencia");
  }
});
$("zona-imagen").addEventListener("dragover", (evento) => {
  evento.preventDefault();
  $("zona-imagen").classList.add("arrastrando");
});
$("zona-imagen").addEventListener("dragleave", () => $("zona-imagen").classList.remove("arrastrando"));
$("zona-imagen").addEventListener("drop", (evento) => {
  evento.preventDefault();
  $("zona-imagen").classList.remove("arrastrando");
  cargarCaptura(evento.dataTransfer.files[0]);
});
$("elegir-imagen").addEventListener("click", () => $("archivo-imagen").click());
$("archivo-imagen").addEventListener("change", () => {
  cargarCaptura($("archivo-imagen").files[0]);
  $("archivo-imagen").value = "";
});

// El rectángulo: se arrastra sobre la imagen. Se manda en píxeles de la imagen original.
let arrastre = null;
$("lienzo-imagen").addEventListener("pointerdown", (evento) => {
  const caja = $("imagen-captura").getBoundingClientRect();
  arrastre = { x: evento.clientX - caja.left, y: evento.clientY - caja.top, caja };
  try {
    $("lienzo-imagen").setPointerCapture(evento.pointerId); // así el arrastre sigue aunque se salga de la imagen
  } catch {}
});
$("lienzo-imagen").addEventListener("pointermove", (evento) => {
  if (!arrastre) return;
  const { caja } = arrastre;
  const x = Math.min(Math.max(evento.clientX - caja.left, 0), caja.width);
  const y = Math.min(Math.max(evento.clientY - caja.top, 0), caja.height);
  Object.assign($("rectangulo-imagen").style, {
    left: `${Math.min(x, arrastre.x)}px`, top: `${Math.min(y, arrastre.y)}px`,
    width: `${Math.abs(x - arrastre.x)}px`, height: `${Math.abs(y - arrastre.y)}px`,
  });
  arrastre.fin = { x, y };
  $("rectangulo-imagen").hidden = false;
});
$("lienzo-imagen").addEventListener("pointerup", () => {
  if (!arrastre) return;
  const { caja, fin } = arrastre;
  arrastre = null;
  if (!fin) return; // un toque sin arrastrar: queda como estaba
  const rect = $("rectangulo-imagen").getBoundingClientRect();
  if (rect.width < 6 || rect.height < 6) {
    $("rectangulo-imagen").hidden = true;
    return;
  }
  const escala = $("imagen-captura").naturalWidth / caja.width;
  const x0 = (rect.left - caja.left) * escala, y0 = (rect.top - caja.top) * escala;
  busqueda.recorte = [x0, y0, x0 + rect.width * escala, y0 + rect.height * escala].map(Math.round);
  olvidarGuia(); // es otra búsqueda
  mostrarBusqueda();
  buscarCaptura();
});
$("quitar-rectangulo").addEventListener("click", () => {
  busqueda.recorte = null;
  olvidarGuia();
  $("rectangulo-imagen").hidden = true;
  mostrarBusqueda();
  buscarCaptura();
});

async function buscarCaptura() {
  if (!busqueda.imagen || !busqueda.listos || busqueda.buscando) return;
  busqueda.buscando = true;
  mostrarBusqueda();
  avisar($("mensaje-imagen"), "Buscando…", "progreso");
  try {
    const resultado = await api().buscar_por_imagen(busqueda.imagen, busqueda.recorte, busqueda.que || null,
      busqueda.se_parece, busqueda.descartados);
    if (!resultado.ok) return avisar($("mensaje-imagen"), resultado.error, "error");
    busqueda.resultados = resultado.resultados;
    mostrarResultadosImagen(resultado.resultados);
    avisar($("mensaje-imagen"), !resultado.resultados.length
      ? "No quedan más con eso: probá «Empezar de nuevo» u otra opción en «¿Qué es?»."
      : !busqueda.recorte
        ? "Tocá el que es para sumarlo a «Items a recibir». Si no está, marcá el objeto con un rectángulo (si es ropa puesta, con un poco del Gaturro alrededor) o elegí «¿Qué es?»."
        : "Tocá el que es para sumarlo. Si no está: «Se parece» en uno cercano, o «No es ninguno de estos».", "exito");
  } finally {
    busqueda.buscando = false;
    mostrarBusqueda();
  }
}

function mostrarResultadosImagen(resultados) {
  $("resultados-imagen").replaceChildren(
    ...resultados.map((item, i) => {
      // Una Pieza suelta: se ve puesta (en otros Gaturros, armada con Trucar Prenda o Looks), pero ningún Item la trae.
      const destino = item.suelta ? { nombre: "Pieza sola" } : DESTINOS[item.destino] ?? DESTINOS.casa;
      const que = item.suelta ? nombreDeParte(item.partes[0]) : queEsItem(item);
      const boton = Object.assign(document.createElement("button"), {
        type: "button", className: "resultado-imagen",
        title: item.suelta
          ? `${item.clase} · ${item.swf} · ${que}\nEs una Pieza que ningún Item del juego trae: tocala para ponerla en una Prenda trucada.`
          : `${item.clase} · ${item.swf} · ${que}\nLlega a: ${destino.nombre}` + (item.motivo ? ` (${item.motivo})` : "")
            + (item.por_pieza ? `\nSe parece a lo que se ve puesto (${claseDeRuta(item.por_pieza)})` : ""),
      });
      boton.setAttribute("aria-pressed", String(items.some((x) => x.ruta === item.ruta)));
      const llega = etiqueta(destino.nombre, "destino-item");
      llega.dataset.bien = String(!item.motivo && !item.suelta);
      // Cortado: lo que se parece es una sola parte del Item (el pantalón de un traje, las mangas de una remera).
      const parte = item.cortado?.partes[0];
      const cortado = item.suelta ? [etiqueta("Ningún Item la trae", "cortado-resultado")]
        : item.cortado ? [etiqueta(`✂ Solo ${nombreDeParte(parte).toLowerCase()}`, "cortado-resultado")] : [];
      if (item.cortado && !item.suelta) boton.title += `\nSe parece a una sola parte: ${claseDeRuta(item.cortado.pieza)} (${nombreDeParte(parte)})`;
      // Si está cortado, se ve la parte que se parece (el pantalón), y el Item entero (el traje) chiquito en una esquina.
      // (La parte se dibuja puesta en un Gaturro, como en Looks: suelta no se reconoce, un pantalón es un pedazo de cadera.)
      const imagen = item.cortado ? Object.assign(document.createElement("img"), { className: "gaturro-resultado", alt: "" }) : elementoIcono(item.ruta);
      if (item.cortado) {
        imagen.dataset.zoom = "1";
        // Acercado a donde va la parte (arriba la cabeza, abajo los pies).
        imagen.style.transformOrigin = `50% ${ALTURA_DE_PARTE[parte] ?? 55}%`;
        pedirGaturro(imagen, coloresDe(null), { [parte]: item.cortado.pieza });
      }
      const entero = item.cortado && !item.suelta ? [Object.assign(elementoIcono(item.ruta), { title: `${item.clase}: lo que vas a recibir (entero)` })] : [];
      entero.forEach((e) => e.classList.add("icono-entero"));
      const marco = item.cortado ? Object.assign(document.createElement("span"), { className: "marco-gaturro" }) : imagen;
      if (item.cortado) marco.append(imagen);
      boton.append(marco, ...entero, etiqueta(item.clase, "nombre-item"), etiqueta(item.swf, "swf-resultado"), llega,
        ...cortado, etiqueta(`${i + 1}`, "puesto-resultado"));
      if (item.pasaporte) marcarPasaporte(boton);
      boton.addEventListener("click", () => {
        if (item.suelta) return trucarSoloEstaParte(item.ruta, parte); // no hay Item que recibir
        if (items.some((x) => x.ruta === item.ruta)) {
          quitarItem(item.ruta);
          avisar($("mensaje-imagen"), `Se sacó ${item.clase} de «Items a recibir».`, "exito");
        } else {
          agregarItems([item.ruta]);
          avisar($("mensaje-imagen"), `Se sumó ${item.clase} (${item.swf}) a «Items a recibir».` + (item.motivo ? ` Ojo: ${item.motivo}.` : ""),
            item.motivo ? "advertencia" : "exito");
        }
        boton.setAttribute("aria-pressed", String(items.some((x) => x.ruta === item.ruta)));
      });
      // «Se parece»: buscar de nuevo, más cerca de este (cuando aparece algo parecido pero no el exacto).
      const parecido = Object.assign(document.createElement("button"), {
        type: "button", className: "se-parece", textContent: "≈ Se parece", title: "Buscar de nuevo, más parecidos a este",
      });
      parecido.setAttribute("aria-pressed", String(busqueda.se_parece.includes(item.ruta)));
      parecido.addEventListener("click", (evento) => {
        evento.stopPropagation();
        busqueda.se_parece = busqueda.se_parece.includes(item.ruta)
          ? busqueda.se_parece.filter((r) => r !== item.ruta)
          : [...busqueda.se_parece, item.ruta];
        buscarCaptura();
      });
      const li = document.createElement("li");
      li.style.position = "relative";
      li.append(boton, parecido);
      if (item.cortado) {
        // Recibir solo esa parte: Trucar Prenda con esa Pieza ya elegida (falta el Item base).
        const trucar = Object.assign(document.createElement("button"), {
          type: "button", className: "trucar-parte", textContent: "✂ Trucar solo esta parte",
          title: `Abrir Trucar Prenda con ${claseDeRuta(item.cortado.pieza)} en ${nombreDeParte(parte)}`,
        });
        trucar.addEventListener("click", (evento) => {
          evento.stopPropagation();
          trucarSoloEstaParte(item.cortado.pieza, parte);
        });
        li.append(trucar);
      }
      return li;
    })
  );
  cargarIconos([...resultados.map((r) => r.ruta), ...resultados.filter((r) => r.cortado).map((r) => r.cortado.pieza)]);
  for (const swf of new Set(resultados.flatMap((r) => [r.swf, ...(r.cortado ? [swfDeRuta(r.cortado.pieza)] : [])]))) prepararIconosDe(swf);
}

// A qué altura del Gaturro (en % desde arriba) está cada Parte, para acercar el dibujo de un resultado cortado.
const ALTURA_DE_PARTE = {
  hats: 8, hairs: 12, mouths: 30, accesories: 25, accesories2: 25, neck: 45, effect: 5,
  cloth: 62, arm: 62, clothFront: 62, clothBack: 58, grip: 70, gripFore: 70, gripBack: 70, glove: 70,
  leg: 84, foot: 95, transport: 90,
};

async function trucarSoloEstaParte(pieza, parte) {
  $("dialogo-imagen").close();
  await cambiarVista("trucar"); // que termine de cargar, así el aviso no se borra
  Object.assign(lookActual, { parte, partes: { [parte]: pieza } });
  mostrarLook();
  prepararIconosDe(swfDeRuta(pieza));
  avisarLista(`Se eligió ${claseDeRuta(pieza)} en ${nombreDeParte(parte)}: elegí el Item base con «Cambiar…» y tocá «Agregar a la lista».`, "exito");
}

// La primera vez: bajar el modelo y las huellas, mostrando cuánto va.
$("bajar-datos-busqueda").addEventListener("click", async () => {
  $("bajar-datos-busqueda").disabled = true;
  $("progreso-datos").hidden = false;
  avisar($("mensaje-imagen"), "Bajando los datos de la búsqueda… (unos minutos)", "progreso");
  const avance = setInterval(async () => {
    const p = await api().progreso_busqueda();
    if (p.total) $("progreso-datos").value = p.hechos / p.total;
  }, 500);
  try {
    const resultado = await api().preparar_busqueda();
    if (!resultado.ok) return avisar($("mensaje-imagen"), resultado.error, "error");
    busqueda.listos = true;
    avisar($("mensaje-imagen"), "Listo: ya se puede buscar.", "exito");
    mostrarBusqueda();
    buscarCaptura();
  } finally {
    clearInterval(avance);
    $("bajar-datos-busqueda").disabled = false;
  }
});
$("buscar-imagen").addEventListener("click", buscarCaptura);
