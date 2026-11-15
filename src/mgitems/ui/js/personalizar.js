// La personalización de las Piezas del documento (`lookActual.personalizacion`: Parte → {colores, ajuste}, ya
// validada por el núcleo, ver `mgitems.personalizar`): viaja con él a la vista previa, a la entrega y a los guardados.
// Se edita con las ventanas del juego, con su arte, corriendo en vivo como el Gaturro (ADR 0009). En Looks, el pincel abre
// su menú para personalizar (`PESTANA[…].capas`), con sus dos ventanas: «Customiza tu ropa» (`ClothEditorModal`: MG Items
// le pasa las Piezas y, al guardar, recibe lo que el juego habría guardado, `wear_<parte>`, que el núcleo convierte en la
// personalización) y «Configura tus accesorios» (`CustomLayerBanner`: hasta tres Piezas en Sombrero, Pelo, Accesorio,
// Boca y Cuello, una arriba de la otra, elegidas entre las de las fuentes del inventario). En Trucar Prenda, que lleva una
// sola Pieza, el pincel abre directo el editor.

// Si la Pieza de una Parte está personalizada (para marcar su casillero).
const tienePersonalizacion = (parte) => !!lookActual.partes[parte] && !!lookActual.personalizacion?.[parte];

// Lo que se olvida al cambiar la Pieza de una Parte: los colores por capa eran de la Pieza anterior.
function olvidarPersonalizacion(parte) {
  if (lookActual.personalizacion) delete lookActual.personalizacion[parte];
}

// --- Las ventanas del juego ---

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
let editorListo = null; // la página de las ventanas, abierta (queda para las siguientes, hasta un rato después de cerrarlas)
let partesEnElEditor = []; // las que el editor mostró (las que no vuelven al guardar, se cortaron con la tijera)
let documentoEnElEditor = null; // el que se está editando (si se cambia de pestaña, el resultado no se pierde)
let sinPiezasParaElEditor = null; // por qué «Customiza tu ropa» no tiene Piezas que mostrar (lo dice el núcleo)

const mostrarCargaEditor = (cargando) => dialogoEditor().classList.toggle("cargando", cargando);

async function abrirPersonalizar() {
  const conCapas = dePestana().capas;
  const documento = [{ ...lookActual.partes }, coloresDe(lookActual), lookActual.emote ?? null, lookActual.personalizacion ?? null];
  const preparado = conCapas
    ? await api().para_personalizar(...documento, fuentes.todos ? null : fuentes.swfs)
    : await api().para_el_editor(...documento);
  if (!preparado.ok) return avisarLista(preparado.error, "advertencia");
  documentoEnElEditor = lookActual;
  sinPiezasParaElEditor = preparado.sin_piezas ?? null;
  dialogoEditor().classList.toggle("solo-editor", !conCapas); // para la forma de la carga
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

// Después de guardar en una ventana del juego: el documento cambió, y su Encode también.
function alCambiarElDocumento(documento) {
  if (documento !== lookActual) return;
  mostrarEncode(null);
  mostrarLook();
}

async function alGuardarEnElEditor(piezas) {
  const documento = documentoEnElEditor;
  dialogoEditor().close();
  const resultado = await api().personalizacion_del_editor({ ...documento.partes }, piezas, partesEnElEditor);
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  documento.personalizacion = resultado.personalizacion;
  for (const parte of resultado.quitadas) delete documento.partes[parte];
  alCambiarElDocumento(documento);
  if (documento === lookActual && resultado.quitadas.length) {
    avisarLista(`Se sacó del Look: ${resultado.quitadas.map(nombreDeParte).join(", ")} (cortado en el editor).`, "advertencia");
  }
}

// Lo que guardó «Configura tus accesorios»: la Pieza de cada capa (las de arriba no tienen casillero).
async function alGuardarCapas(valores) {
  const documento = documentoEnElEditor;
  dialogoEditor().close();
  const resultado = await api().capas_configuradas({ ...documento.partes }, documento.personalizacion ?? null, valores);
  if (!resultado.ok) return avisarLista(resultado.error, "error");
  documento.partes = resultado.partes;
  documento.personalizacion = resultado.personalizacion;
  alCambiarElDocumento(documento);
}

addEventListener("message", (evento) => {
  if (evento.source !== marcoEditor().contentWindow) return;
  const { editor, personalizar, capas, partes, piezas, error, coloresGuardados } = evento.data ?? {};
  if (coloresGuardados !== undefined) {
    try {
      localStorage.setItem(CLAVE_COLORES_EDITOR, coloresGuardados);
    } catch {}
  }
  if (personalizar === "abierto") {
    mostrarCargaEditor(false);
    marcoEditor().focus();
  } else if (personalizar === "error") {
    dialogoEditor().close();
    avisarLista(`No se pudo abrir la ventana del juego: ${error}`, "error");
  } else if (capas) {
    alGuardarCapas(capas);
  } else if (editor === "sin piezas") {
    dialogoEditor().close();
    avisarLista(sinPiezasParaElEditor, "advertencia");
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

$("editar-piezas").addEventListener("click", () => abrirPersonalizar());
cerrarAlRatoDeCerrarse(dialogoEditor(), () => {
  editorListo = null;
  marcoEditor().src = "about:blank";
});
