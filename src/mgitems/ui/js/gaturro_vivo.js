// El Gaturro en vivo: el Gaturro de pantalla del juego, corriendo en un marco (gaturro_vivo.html, ADR 0003).

// Un Gaturro en vivo en `marco` (un <iframe>). Su página se abre recién la primera vez que se lo viste.
function gaturroVivo(marco) {
  let abierto = null; // la página avisó que el Gaturro ya se puede vestir
  let pedido = 0; // si se lo viste varias veces seguidas, queda lo último
  let zoom = 1;
  const decir = (mensaje) => marco.contentWindow.postMessage(mensaje, "*");
  const abrir = () => abierto ??= (async () => {
    const pagina = await api().pagina_del_gaturro();
    if (!pagina.ok) throw new Error(pagina.error);
    await new Promise((listo, fallo) => {
      addEventListener("message", function oir(evento) {
        if (evento.source !== marco.contentWindow) return;
        removeEventListener("message", oir);
        if (evento.data?.listo) listo();
        else fallo(new Error(`No se pudo abrir el Gaturro: ${evento.data?.error ?? "no respondió"}.`));
      });
      marco.src = pagina.url;
    });
  })().catch((error) => {
    abierto = null; // la próxima vez se intenta de nuevo
    throw error;
  });

  return {
    // Lo deja con esas Piezas, colores y emoción. Devuelve lo de `Nucleo.gaturro_en_vivo` (con sus avisos),
    // {ok: false, error} si el Gaturro no se pudo abrir, o null si mientras tanto se pidió otra cosa.
    async vestir(partes, colores, emote = null) {
      const este = ++pedido;
      let resultado;
      try {
        [resultado] = await Promise.all([api().gaturro_en_vivo({ ...partes }, colores, emote), abrir()]);
      } catch (error) {
        resultado = { ok: false, error: error.message };
      }
      if (este !== pedido) return null;
      if (resultado.ok) decir({ vestir: resultado.vestir, zoom });
      return resultado;
    },
    // 1 es el tamaño de siempre; menos lo aleja y más lo acerca.
    zoom(valor) {
      zoom = valor;
      if (marco.src) decir({ zoom });
    },
  };
}
