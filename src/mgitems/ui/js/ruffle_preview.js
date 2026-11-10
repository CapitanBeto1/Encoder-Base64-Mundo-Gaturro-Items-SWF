// PROTOTIPO: vista previa del Gaturro con Ruffle (el modelo actual del juego, en vivo).
// Carga /preview.swf (el avatar real envuelto) en Ruffle y lo viste con changeAttr, usando los SWF que sirve
// el servidor local en /assets/<pack>.swf. El toggle «Viejo/Nuevo» alterna con la imagen armada en el programa.

// --- Pieza "swf.Clase" → valor que viste el juego ("swf.clase_on"), con las excepciones conocidas ---
// (portado de naw-trucador/app/frontend/src/look/slots.js)
const MAPEO_ESPECIAL_ON = {
  "costumes.peloMorti": "costumes.peloMorticia_on", "costumes.peloMorticia": "costumes.peloMorticia_on",
  "anime.Anime_kimono": "anime.Anime_Kimono_on", "anime.Kpop_CamisaCuadrille": "anime.Kpop_Camisacuadrille_on",
  "anime.Anime_UniformeH": "anime.Anime_uniformeH_on", "arcor.premio1": "arcor.premio11_on",
  "escuela.uniformeMujer": "escuela.uniformeMujerRojo_on", "escuela.uniformeVaron": "escuela.uniformeVaronRojo_brazo_on",
  "escuela.pelota2": "escuela.pelota_on", "escuelaNueva.pantalonGimnasia": "escuelaNueva.pantalonGimnasiaInvierno_on",
  "fashion2017.MusculosaBlancaA": "fashion2017.musculosaBlancaA_on", "fashion2017.MusculosaBlancaB": "fashion2017.musculosaBlancaB_on",
  "fashion2017.MusculosaNaranjaA": "fashion2017.musculosaNaranjaA_on", "fashion2017.MusculosaNaranjaB": "fashion2017.musculosaNaranjaB_on",
  "fashion2017.MusculosaRojaA": "fashion2017.musculosaRojaA_on", "fashion2017.MusculosaRojaB": "fashion2017.musculosaRojaB_on",
  "fashion2017.MusculosaVerdeA": "fashion2017.musculosaVerdeA_on", "fashion2017.MusculosaVerdeB": "fashion2017.musculosaVerdeB_on",
  "fashion2017.RemeraAmarillaA": "fashion2017.remeraAmarillaA_on", "fashion2017.RemeraAmarillaB": "fashion2017.remeraAmarillaB_on",
  "fashion2017.RemeraCelesteA": "fashion2017.remeraCelesteA_on", "fashion2017.RemeraCelesteB": "fashion2017.remeraCelesteB_on",
  "fashion2017.RemeraPurpuraA": "fashion2017.remeraPurpuraA_on", "fashion2017.RemeraPurpuraB": "fashion2017.remeraPurpuraB_on",
  "fashion2017.RemeraVerdeA": "fashion2017.remeraVerdeA_on", "fashion2017.RemeraVerdeB": "fashion2017.remeraVerdeB_on",
  "gigante.bota": "gigante.botaBrocoli_on", "hairs1.pelucaFrozen": "hairs1.pelucaFrozenHombre_on",
  "heartStop.mochila": "heartStop.mochila1_front_on", "islandClothes.pulseraFlores": "islandClothes.pulseraFlores_brazo_on",
  "mounstruos.remeraJardineroVerde": "mounstruos.remeraJardineroVerde_brazo_on",
  "mundial.pelota1": "mundial.pelota_on", "mundial.pelota2": "mundial.pelota_on",
  "mundialClothes.papelPicado2": "mundialClothes.papelPicado_on", "princeClothes.vestidoCenicienta2": "princeClothes.vestidoCenicienta_on",
  "serenito.remeraS": "serenito.remeraS_brazo_on", "serenito.tabletPremio": "serenito.tablet_on",
  "transport.caballoAzul2": "transport.caballoAzul_on", "transport.caballoRojo2": "transport.caballoRojo_on",
  "transport.caballoVioleta2": "transport.caballoVioleta_on", "transport.escoba1": "transport.escoba1Active_on",
  "trenFantasma.gorro": "trenFantasma.gorroFantasma_on",
};

function valorOn(ruta) {
  const limpio = String(ruta || "").replace(/\.swf$/i, "").trim();
  const punto = limpio.indexOf(".");
  if (punto < 0) return null;
  const pack = limpio.slice(0, punto);
  let leaf = limpio.slice(punto + 1);
  if (leaf.includes(".")) leaf = leaf.split(".").pop(); // clases en paquetes AS3
  const clave = `${pack}.${leaf}`;
  if (MAPEO_ESPECIAL_ON[clave]) return MAPEO_ESPECIAL_ON[clave];
  if (/^pelomorti/i.test(leaf)) return `${pack}.peloMorticia_on`;
  if (!/_on$/.test(leaf)) leaf += "_on";
  return `${pack}.${leaf}`;
}

// Las Partes del cuerpo que la vista de Ruffle sabe vestir (los efectos de cabeza son aparte; se omiten por ahora).
const PARTES_RUFFLE = ["hats", "hairs", "accesories", "accesories2", "mouths", "neck", "cloth", "arm", "clothBack", "grip", "gripFore", "leg", "foot", "transport"];

function atributosDelLook(partes) {
  const attrs = {};
  for (const parte of PARTES_RUFFLE) {
    const ruta = partes?.[parte];
    if (!ruta) continue;
    const valor = valorOn(ruta);
    if (!valor) continue;
    attrs[`wear_${parte}`] = valor;
    attrs[parte] = valor;
  }
  return attrs;
}

// --- Ruffle ---
let rufflePromesa = null;
let rufflePlayer = null;
let ruffleListo = false;
let modeloNuevo = false;
const packsCargados = new Set();

function cargarRuffle() {
  if (rufflePromesa) return rufflePromesa;
  window.RufflePlayer = window.RufflePlayer || {};
  window.RufflePlayer.config = {
    publicPath: "/ruffle/", polyfills: false, wmode: "transparent", allowScriptAccess: true,
    allowNetworking: "all", contextMenu: "off", splashScreen: false, logLevel: "warn", unmuteOverlay: "hidden",
  };
  rufflePromesa = new Promise((res, rej) => {
    const s = document.createElement("script");
    s.src = "/ruffle/ruffle.js";
    s.onload = () => res();
    s.onerror = () => rej(new Error("no cargó ruffle.js"));
    document.head.appendChild(s);
  });
  return rufflePromesa;
}

function msgRuffle(texto) {
  const el = $("estado-ruffle");
  el.textContent = texto || "";
  el.hidden = !texto;
}

async function iniciarPlayer() {
  if (ruffleListo) return true;
  msgRuffle("Cargando el Gaturro…");
  await cargarRuffle();
  if (!window.RufflePlayer?.newest) throw new Error("Ruffle no quedó disponible");
  const host = $("gaturro-ruffle");
  host.innerHTML = "";
  const player = window.RufflePlayer.newest().createPlayer();
  player.style.width = "100%";
  player.style.height = "100%";
  host.appendChild(player);
  rufflePlayer = player;
  await player.load({ url: "/preview.swf", allowScriptAccess: true, autoplay: "on", unmuteOverlay: "hidden", splashScreen: false, letterbox: "on", wmode: "transparent" });
  for (let i = 0; i < 120 && typeof player.changeAttr !== "function"; i++) await new Promise((r) => setTimeout(r, 80));
  ruffleListo = typeof player.changeAttr === "function";
  if (!ruffleListo) throw new Error("el preview no expuso changeAttr");
  return true;
}

let generacionVestir = 0;
async function vestirRuffle() {
  if (!modeloNuevo) return;
  const gen = ++generacionVestir;
  try {
    await iniciarPlayer();
    if (gen !== generacionVestir) return;
    const attrs = atributosDelLook(lookActual.partes);
    const packs = new Set(Object.values(attrs).map((v) => v.split(".")[0]));
    let sembroAlguno = false;
    for (const p of packs) {
      if (!packsCargados.has(p)) {
        packsCargados.add(p);
        sembroAlguno = true;
        try { rufflePlayer.searchAssets(p); } catch {}
      }
    }
    if (sembroAlguno) {
      await new Promise((r) => setTimeout(r, 800));
      if (gen !== generacionVestir) return;
    }
    try { rufflePlayer.clearAsset?.(); } catch {}
    rufflePlayer.changeAttr(JSON.stringify(attrs));
    msgRuffle(Object.keys(attrs).length ? "" : "Agregá una Pieza para verla puesta.");
  } catch (e) {
    msgRuffle("No se pudo abrir la vista nueva.");
    console.warn("ruffle:", e);
  }
}

function mostrarModelo(nuevo) {
  modeloNuevo = nuevo;
  $("modelo-viejo").classList.toggle("activo", !nuevo);
  $("modelo-nuevo").classList.toggle("activo", nuevo);
  $("imagen-gaturro").hidden = nuevo;
  $("gaturro-ruffle").hidden = !nuevo;
  $("estado-gaturro").style.display = nuevo ? "none" : ""; // los avisos son del preview viejo
  if (nuevo) vestirRuffle();
  else msgRuffle("");
}

$("modelo-viejo").addEventListener("click", () => mostrarModelo(false));
$("modelo-nuevo").addEventListener("click", () => mostrarModelo(true));

// Engancha a cada redibujo del Gaturro para vestir también la vista nueva.
const _dibujarGaturro = dibujarGaturro;
dibujarGaturro = function () {
  const r = _dibujarGaturro.apply(this, arguments);
  if (modeloNuevo) vestirRuffle();
  return r;
};
