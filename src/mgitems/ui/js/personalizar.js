// Personalizar las Piezas del documento con el editor del juego («Customiza tu ropa»: `ClothEditorModal`, con su arte),
// corriendo en vivo como el Gaturro (ADR 0009). MG Items le pasa las Piezas y, al guardar, recibe lo que el juego habría
// guardado (`wear_<parte>`): el núcleo lo convierte en la personalización del documento (`lookActual.personalizacion`:
// Parte → {colores, ajuste}), que viaja con él a la vista previa, a la entrega y a los guardados.

let reglasPersonalizar = null; // {sin_personalizar, rotables, ajuste_defecto}
async function cargarReglasPersonalizar() {
  if (!reglasPersonalizar) reglasPersonalizar = await api().reglas_de_personalizar();
}

const esPersonalizable = (parte) => !!reglasPersonalizar && !reglasPersonalizar.sin_personalizar.includes(parte);
const esAjustable = (parte) => !!reglasPersonalizar && reglasPersonalizar.rotables.some((c) => parte === c || parte.startsWith(c));
const hayParaPersonalizar = () => Object.keys(lookActual.partes).some(esPersonalizable);

// Si una Parte tiene algo personalizado (para marcar su casillero).
function tienePersonalizacion(parte) {
  const p = lookActual.personalizacion?.[parte];
  if (!p || !lookActual.partes[parte] || !esPersonalizable(parte)) return false;
  const defecto = reglasPersonalizar.ajuste_defecto;
  const colorTocado = (p.colores ?? []).some((c) => c.quitar || c.color != null);
  const ajustado = esAjustable(parte) && !!p.ajuste && Object.keys(defecto).some((k) => (p.ajuste[k] ?? defecto[k]) !== defecto[k]);
  return colorTocado || ajustado;
}

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

const marcoEditor = () => $("editor-piezas");
let editorListo = null; // la página del editor, abierta (se abre la primera vez y queda para las siguientes)
let partesEnElEditor = []; // las que el editor mostró (las que no vuelven al guardar, se cortaron con la tijera)
let documentoEnElEditor = null; // el que se está editando (si se cambia de pestaña, el resultado no se pierde)

const mostrarCargaEditor = (cargando) => $("dialogo-editor-piezas").classList.toggle("cargando", cargando);

async function abrirEditorDePiezas() {
  await cargarReglasPersonalizar();
  if (!hayParaPersonalizar()) return;
  const preparado = await api().para_el_editor({ ...lookActual.partes }, coloresDe(lookActual), lookActual.emote ?? null,
    lookActual.personalizacion ?? null);
  if (!preparado.ok) return avisarLista(preparado.error, "error");
  documentoEnElEditor = lookActual;
  mostrarCargaEditor(true);
  $("dialogo-editor-piezas").showModal();
  try {
    await (editorListo ??= abrirGaturroEn(marcoEditor()).catch((error) => {
      editorListo = null; // la próxima vez se intenta de nuevo
      throw error;
    }));
  } catch (error) {
    $("dialogo-editor-piezas").close();
    return avisarLista(error.message, "error");
  }
  marcoEditor().contentWindow.postMessage({ editar: { piezas: preparado.piezas, atributos: preparado.atributos, colores: coloresDelEditor() } }, "*");
}

async function alGuardarEnElEditor(piezas) {
  const documento = documentoEnElEditor;
  $("dialogo-editor-piezas").close();
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
  const { editor, partes, piezas, error, coloresGuardados } = evento.data ?? {};
  if (coloresGuardados !== undefined) {
    try {
      localStorage.setItem(CLAVE_COLORES_EDITOR, coloresGuardados);
    } catch {}
  }
  if (editor === "abierto") {
    partesEnElEditor = partes ?? [];
    mostrarCargaEditor(false);
    marcoEditor().focus();
  } else if (editor === "guardado") {
    alGuardarEnElEditor(piezas ?? {});
  } else if (editor === "cancelado") {
    $("dialogo-editor-piezas").close();
  } else if (editor === "error") {
    $("dialogo-editor-piezas").close();
    avisarLista(`El editor del juego no pudo guardar: ${error}`, "error");
  }
});

$("editar-piezas").addEventListener("click", () => abrirEditorDePiezas());
