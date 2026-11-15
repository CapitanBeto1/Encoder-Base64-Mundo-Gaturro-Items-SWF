// El Gaturro en vivo: el Gaturro del juego, corriendo en un marco (gaturro_vivo.html, ADR 0009).

// Lo que contesta la página de `marco` que cumple con `esLaRespuesta`.
function respuestaDe(marco, esLaRespuesta) {
  return new Promise((llego) => {
    addEventListener("message", function oir(evento) {
      if (evento.source !== marco.contentWindow || !esLaRespuesta(evento.data ?? {})) return;
      removeEventListener("message", oir);
      llego(evento.data);
    });
  });
}

// Mientras la ventana del programa no está activa (por ejemplo, mientras se juega), los Gaturros se quedan quietos, así
// no le sacan CPU al juego; al volver, siguen. El foco puede estar en un marco (el editor), y ahí la ventana sigue
// activa: `document.hasFocus()` lo cuenta. Se mira cada segundo, porque si el foco se va desde un marco la página no se
// entera.
let ventanaActiva = true;
const decirleLaPausa = (marco) => marco.contentWindow?.postMessage({ pausa: !ventanaActiva }, "*");
const alCambiarElFoco = []; // lo que se hace además, con `ventanaActiva`
function mirarElFoco() {
  if (document.hasFocus() === ventanaActiva) return;
  ventanaActiva = !ventanaActiva;
  document.querySelectorAll("iframe").forEach(decirleLaPausa);
  for (const hacer of alCambiarElFoco) hacer(ventanaActiva);
}
setInterval(mirarElFoco, 1000);
addEventListener("focus", mirarElFoco);

// Abre la página del Gaturro en `marco` (un <iframe>) y espera a que el Gaturro se pueda vestir.
async function abrirGaturroEn(marco, opciones = "") {
  const pagina = await api().pagina_del_gaturro();
  if (!pagina.ok) throw new Error(pagina.error);
  const respuesta = respuestaDe(marco, (r) => r.listo || r.error);
  marco.src = pagina.url + opciones;
  const { error } = await respuesta;
  if (error) throw new Error(`No se pudo abrir el Gaturro: ${error}.`);
  decirleLaPausa(marco);
}

// Un Gaturro en vivo en `marco` (un <iframe>). Su página se abre recién la primera vez que se lo viste.
// `tamano` achica o agranda al Gaturro dentro del marco (1: lo llena a lo alto).
function gaturroVivo(marco, tamano = 1) {
  let abierto = null; // la página avisó que el Gaturro ya se puede vestir
  let pedido = 0; // si se lo viste varias veces seguidas, queda lo último
  let zoom = 1;
  const decir = (mensaje) => marco.contentWindow.postMessage(mensaje, "*");
  const abrir = () => abierto ??= abrirGaturroEn(marco).catch((error) => {
    abierto = null; // la próxima vez se intenta de nuevo
    throw error;
  });

  return {
    // Lo deja con esas Piezas, colores y emoción, haciendo la acción `animacion` si la hay. Devuelve lo de
    // `Nucleo.gaturro_en_vivo` (con sus avisos), {ok: false, error} si el Gaturro no se pudo abrir, o null si
    // mientras tanto se pidió otra cosa.
    async vestir(partes, colores, emote = null, animacion = null, personalizacion = null) {
      const este = ++pedido;
      let resultado;
      try {
        [resultado] = await Promise.all([api().gaturro_en_vivo({ ...partes }, colores, emote, animacion, personalizacion), abrir()]);
      } catch (error) {
        resultado = { ok: false, error: error.message };
      }
      if (este !== pedido) return null;
      if (resultado.ok) decir({ vestir: resultado.atributos, zoom: zoom * tamano });
      return resultado;
    },
    // Hace la acción otra vez desde el principio.
    repetir() {
      if (marco.src) decir({ repetir: true });
    },
    // 1 es el tamaño de siempre; menos lo aleja y más lo acerca.
    zoom(valor) {
      zoom = valor;
      if (marco.src) decir({ zoom: zoom * tamano });
    },
    // Cierra su página y libera lo que ocupa. Se abre de nuevo la próxima vez que se lo viste.
    cerrar() {
      pedido++; // si se estaba vistiendo, no se le dice nada más
      abierto = null;
      marco.src = "about:blank";
    },
  };
}

// Lo que ocupaba un Gaturro cerrado el navegador lo devuelve recién al juntar la basura, y si la página no hace nada
// (mientras se juega) eso puede no pasar nunca. No hay cómo pedírselo directamente: reservar un bloque grande y soltarlo
// hace que la junte enseguida (medido: 430 → 278 MB). Si no alcanza la memoria para reservarlo, no pasa nada.
let limpieza = null;
function limpiarEnUnRato() {
  clearTimeout(limpieza);
  limpieza = setTimeout(() => {
    try {
      new Uint8Array(new ArrayBuffer(128 * 2 ** 20))[0] = 1;
    } catch {}
  }, 2000);
}

// Un Gaturro abierto ocupa unos 100 MB aunque no se vea. Cuando deja de verse, se cierra un rato después: si antes se lo
// vuelve a ver, sigue el mismo, sin esperar a que se abra. Devuelve con qué avisar que dejó de verse; `cerrar` se llama
// si para entonces `sigueSinVerse()`.
const ESPERA_PARA_CERRAR_EL_GATURRO = 60000;
function cierreAlRato(cerrar, sigueSinVerse) {
  let cierre = null;
  return () => {
    clearTimeout(cierre);
    cierre = setTimeout(() => {
      if (!sigueSinVerse()) return;
      cerrar();
      limpiarEnUnRato();
    }, ESPERA_PARA_CERRAR_EL_GATURRO);
  };
}

// El de una ventana (<dialog>), al rato de cerrarla.
const cerrarAlRatoDeCerrarse = (dialogo, cerrar) => dialogo.addEventListener("close", cierreAlRato(cerrar, () => !dialogo.open));

// --- Fotos del Gaturro en vivo: para donde hay muchos a la vez (las miniaturas de los guardados) ---

// Un Gaturro que no se ve: se viste, se le saca la foto y pasa al siguiente. Cada foto se saca una sola vez, y se
// guarda para la próxima vez que se abra el programa (`Nucleo.foto_guardada`: sacarlas cuesta tiempo y memoria). Cuando
// no quedan fotos por sacar, se cierra: abierto, se sigue dibujando aunque no se vea, y gasta CPU y memoria.
const fotosDelGaturro = new Map(); // atributos (JSON) → la imagen, o la promesa de la imagen
const FORMATO_DE_FOTO = "webgl-240-1.6"; // cómo se saca (dibujador, tamaño, zoom): si cambia, las guardadas no sirven
let fotografo = null; // la promesa del marco, ya abierto
let turnoDeFoto = Promise.resolve(); // de a una
let fotosPedidas = 0;
let fotosPorSacar = 0;
let cierreDelFotografo = null;
const ESPERA_ANTES_DE_CERRAR_EL_FOTOGRAFO = 3000; // si enseguida se piden más (otro guardado), las saca el mismo

function abrirFotografo() {
  const marco = Object.assign(document.createElement("iframe"), { className: "fotografo-del-gaturro", tabIndex: -1 });
  marco.setAttribute("aria-hidden", "true");
  document.body.append(marco);
  return abrirGaturroEn(marco, "?fotos").then(() => marco, (error) => {
    marco.remove();
    throw error;
  });
}

function cerrarFotografo() {
  fotografo?.then((marco) => marco.remove(), () => {});
  fotografo = null;
  limpiarEnUnRato();
}

// La imagen (data:image/png…) del Gaturro quieto con esas Piezas, colores, emoción y personalización, o null si no
// se pudo sacar.
async function fotoDelGaturro(partes, colores, emote = null, personalizacion = null) {
  const resultado = await api().gaturro_en_vivo({ ...partes }, colores, emote, null, personalizacion);
  if (!resultado.ok) return null;
  const clave = JSON.stringify(resultado.atributos);
  if (!fotosDelGaturro.has(clave)) fotosDelGaturro.set(clave, guardadaOSacada(clave, resultado.atributos));
  return fotosDelGaturro.get(clave);
}

async function guardadaOSacada(clave, atributos) {
  const guardada = await api().foto_guardada(atributos, FORMATO_DE_FOTO);
  if (guardada.ok && guardada.imagen) return guardada.imagen;
  const imagen = await sacarFoto(atributos);
  if (imagen) api().guardar_foto(atributos, FORMATO_DE_FOTO, imagen);
  else fotosDelGaturro.delete(clave); // la próxima vez se intenta de nuevo
  return imagen;
}

// La foto que le saca el fotógrafo cuando le toca (de a una), o null si no se pudo.
function sacarFoto(atributos) {
  fotosPorSacar++;
  clearTimeout(cierreDelFotografo);
  const foto = turnoDeFoto.then(async () => {
    const marco = await (fotografo ??= abrirFotografo());
    const numero = ++fotosPedidas;
    const respuesta = respuestaDe(marco, (r) => r.foto === numero);
    marco.contentWindow.postMessage({ foto: numero, vestir: atributos, zoom: 1.6 }, "*");
    return (await respuesta).imagen;
  }).catch(() => {
    cerrarFotografo(); // la próxima foto lo abre de nuevo
    return null;
  }).finally(() => {
    if (--fotosPorSacar === 0) cierreDelFotografo = setTimeout(cerrarFotografo, ESPERA_ANTES_DE_CERRAR_EL_FOTOGRAFO);
  });
  turnoDeFoto = foto;
  return foto;
}
