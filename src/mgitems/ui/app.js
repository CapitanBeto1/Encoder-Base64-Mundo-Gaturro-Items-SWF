// La interfaz no tiene lógica de dominio: todo pasa por window.pywebview.api (el núcleo).

const $ = (id) => document.getElementById(id);

const entrada = $("entrada");
const botonGenerar = $("generar");
const textoEncode = $("encode");
const botonCopiar = $("copiar");
const botonGuardar = $("guardar");
const resumen = $("resumen");
const mensaje = $("mensaje");

function mostrarMensaje(texto, tipo = "") {
  mensaje.textContent = texto;
  mensaje.className = "mensaje " + tipo;
}

function mostrarEncode(resultado) {
  textoEncode.value = resultado ? resultado.encode : "";
  botonCopiar.disabled = botonGuardar.disabled = !resultado;
  if (resultado) {
    const n = resultado.items.length;
    resumen.textContent = n === 1 ? "Encode con 1 Item." : `Encode con ${n} Items.`;
  } else {
    resumen.textContent = "Todavía no generaste ningún Encode.";
  }
}

async function generar() {
  const resultado = await window.pywebview.api.generar_encode(entrada.value);
  if (!resultado.ok) {
    mostrarEncode(null);
    mostrarMensaje(resultado.error, "error");
    return;
  }
  mostrarEncode(resultado);
  mostrarMensaje("Encode generado.", "exito");
}

async function copiar() {
  try {
    await navigator.clipboard.writeText(textoEncode.value);
  } catch {
    textoEncode.select();
    document.execCommand("copy");
  }
  mostrarMensaje("Encode copiado al portapapeles.", "exito");
}

async function guardar() {
  const resultado = await window.pywebview.api.guardar_encode(textoEncode.value);
  if (resultado.ok) {
    mostrarMensaje(`Encode guardado en ${resultado.ruta}`, "exito");
  } else if (!resultado.cancelado) {
    mostrarMensaje(resultado.error, "error");
  }
}

botonGenerar.addEventListener("click", generar);
botonCopiar.addEventListener("click", copiar);
botonGuardar.addEventListener("click", guardar);
entrada.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && e.ctrlKey && !botonGenerar.disabled) generar();
});

window.addEventListener("pywebviewready", () => {
  botonGenerar.disabled = false;
});
