// La personalización de las Piezas del documento (`lookActual.personalizacion`: Parte → {colores, ajuste}, ya
// validada por el núcleo, ver `mgitems.personalizar`): viaja con él a la vista previa, a la entrega y a los guardados.
// Se edita con las ventanas del juego, corriendo en vivo como el Gaturro (ADR 0009). En Looks, el pincel abre su menú:
// «Customiza tu ropa» (`ClothEditorModal`: MG Items le pasa las Piezas y, al guardar, recibe lo que el juego habría
// guardado, `wear_<parte>`, que el núcleo convierte en la personalización) y «Configura tus accesorios»
// (`CustomLayerBanner`: hasta tres Piezas en Sombrero, Pelo, Accesorio, Boca y Cuello, una arriba de la otra, elegidas
// entre las de las fuentes del inventario). En Trucar Prenda, el pincel abre directo el editor (`PESTANA[…].capas`).

// Si la Pieza de una Parte está personalizada (para marcar su casillero).
const tienePersonalizacion = (parte) => !!lookActual.partes[parte] && !!lookActual.personalizacion?.[parte];

// Lo que se olvida al cambiar la Pieza de una Parte: los colores por capa eran de la Pieza anterior.
function olvidarPersonalizacion(parte) {
  if (lookActual.personalizacion) delete lookActual.personalizacion[parte];
}

// --- El editor ---

// Los colores que el jugador guarda en el editor («+»), como en su perfil del juego: quedan en esta computadora.
const CLAVE_COLORES_EDITOR = "coloresEditorPiezas";
function coloresDelEditor() {
  try {
    return localStorage.getItem(CLAVE_COLORES_EDITOR) ?? "";
  } catch {
    return "";
  }
}

const dialogoEditor = () => $("dialogo-editor-piezas");
const marcoEditor = () => $("editor-piezas");
let editorListo = null; // la página del editor, abierta (se abre la primera vez y queda para las siguientes)
let partesEnElEditor = []; // las que el editor mostró (las que no vuelven al guardar, se cortaron con la tijera)
let documentoEnElEditor = null; // el que se está editando (si se cambia de pestaña, el resultado no se pierde)

const mostrarCargaEditor = (cargando) => dialogoEditor().classList.toggle("cargando", cargando);

async function abrirEditorDePiezas() {
  const conCapas = dePestana().capas;
  const documento = [{ ...lookActual.partes }, coloresDe(lookActual), lookActual.emote ?? null, lookActual.personalizacion ?? null];
  const preparado = conCapas
    ? await api().para_personalizar(...documento, fuentes.todos ? null : fuentes.swfs)
    : await api().para_el_editor(...documento);
  if (!preparado.ok) return avisarLista(preparado.error, "advertencia");
  documentoEnElEditor = lookActual;
  mostrarCargaEditor(true);
  dialogoEditor().showModal();
  try {
    await (editorListo ??= abrirGaturroEn(marcoEditor()).catch((error) => {
      editorListo = null; // la próxima vez se intenta de nuevo
      throw error;
    }));
  } catch (error) {
    dialogoEditor().close();
    return avisarLista(error.message, "error");
  }
  const datos = { piezas: preparado.piezas, atributos: preparado.atributos, colores: coloresDelEditor() };
  marcoEditor().contentWindow.postMessage(conCapas ? { personalizar: { ...datos, capas: preparado.capas } } : { editar: datos }, "*");
}

// Lo que guardó «Configura tus accesorios»: las Piezas de cada capa (las de arriba no tienen casillero).
async function alGuardarCapas(valores) {
  const documento = documentoEnElEditor;
  dialogoEditor().close();
  const resultado = await api().capas_configuradas({ ...documento.partes }, documento.personalizacion ?? null, valores);
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  documento.partes = resultado.partes;
  documento.personalizacion = resultado.personalizacion;
  if (documento !== lookActual) return;
  mostrarEncode(null); // el Encode que había era sin estos cambios
  mostrarLook();
}

async function alGuardarEnElEditor(piezas) {
  const documento = documentoEnElEditor;
  dialogoEditor().close();
  const resultado = await api().personalizacion_del_editor({ ...documento.partes }, piezas, partesEnElEditor);
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  documento.personalizacion = resultado.personalizacion;
  for (const parte of resultado.quitadas) delete documento.partes[parte];
  if (documento !== lookActual) return;
  mostrarEncode(null); // el Encode que había era sin estos cambios
  mostrarLook();
  if (resultado.quitadas.length) {
    avisarLista(`Se sacó del Look: ${resultado.quitadas.map(nombreDeParte).join(", ")} (cortado en el editor).`, "advertencia");
  }
}

addEventListener("message", (evento) => {
  if (evento.source !== marcoEditor().contentWindow) return;
  const { editor, partes, piezas, error, coloresGuardados, personalizar, capas } = evento.data ?? {};
  if (coloresGuardados !== undefined) {
    try {
      localStorage.setItem(CLAVE_COLORES_EDITOR, coloresGuardados);
    } catch {}
  }
  if (personalizar === "abierto") {
    mostrarCargaEditor(false);
    marcoEditor().focus();
  } else if (capas) {
    alGuardarCapas(capas);
  } else if (editor === "sin piezas") {
    dialogoEditor().close();
    avisarLista("Para «Customiza tu ropa», poné primero una Pieza en el Gaturro.", "advertencia");
  } else if (editor === "abierto") {
    partesEnElEditor = partes ?? [];
    mostrarCargaEditor(false);
    marcoEditor().focus();
  } else if (editor === "guardado") {
    alGuardarEnElEditor(piezas ?? {});
  } else if (editor === "cancelado") {
    dialogoEditor().close();
  } else if (editor === "error") {
    dialogoEditor().close();
    avisarLista(`El editor del juego no pudo guardar: ${error}`, "error");
  }
});

$("editar-piezas").addEventListener("click", () => abrirEditorDePiezas());
