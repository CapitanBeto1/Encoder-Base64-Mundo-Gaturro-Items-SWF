// Las pestañas: lo que cambia de una a otra (PESTANA) y cómo se cambia de pestaña.

// --- Pestañas: Agregar Items / Trucar Prenda ---

let vista = "agregar";

// Looks, Acciones y Trucar Prenda usan la misma pantalla (el Gaturro, los casilleros y el inventario), cada una
// con su documento: lo que se está editando en una queda guardado mientras se está en otra.
const PESTANAS_DEL_EDITOR = ["looks", "acciones", "trucar", "tiendas", "portales", "minijuegos", "fondos"];
const PESTANAS = ["agregar", "trucar", "looks", "acciones", "tiendas", "portales", "minijuegos", "fondos", "terminator"];
// Tiendas, Portales y Minijuegos: cualquier Item que, puesto en la casa, hace lo mismo que un NPC del juego.
// Fondos: un objeto cuyo dibujo tiene varios cuadros, que muestra el elegido (comportamiento `painting`).
const PESTANAS_NPC = { tiendas: "tienda", portales: "portal", minijuegos: "minijuego", fondos: "fondo" };
const esFondos = () => vista === "fondos";

// Lo que cambia de una pestaña a otra: sus textos, cómo empieza un documento nuevo, qué hace «Aplicar» y sus
// guardados (Mis Looks, Mis acciones…: todos se guardan igual, con `api().guardados` y el tipo primero). Lo que una
// pestaña no dice, es como en Looks (`dePestana`).
// Los pasos de cada pestaña (la guía de arriba): [qué hacer, si ya está hecho].
const hayEncode = () => Boolean($("encode").value);
const conPiezas = () => Object.keys(lookActual.partes).length > 0;
const enLaLista = () => lookActual.lista.length > 0;
const pestanaNpc = ({ tipo, el, lo, nuevo, mis, titulo, sub, nombre, tocaUno, lista, tituloBase, sinBase = "elegí cualquier Item",
                      documentoNuevo = () => nuevoNpc(), elegirUno = "Elegí un Item", queHace = "Elegí qué hace",
                      hace = () => Boolean(lookActual.comportamiento) }) => ({
  generar: "Convertir todos", aplicar: "Convertir todos", seGuarda: "Se convierte:", alAplicar: () => convertirNpcs(),
  pasos: () => [[elegirUno, Boolean(lookActual.base)], [queHace, hace()], ["Sumalo a la lista", enLaLista()],
                ["Convertí todos", hayEncode()], ["Agregá al juego", false]],
  nombre, tocaUno, lista, tituloBase, sinBase, nuevo: documentoNuevo, guardados: { tipo, el, lo, nuevo, mis, titulo, sub },
});
const PESTANA = {
  agregar: {
    generar: "Generar Encode",
    pasos: () => [["Elegí los Items", items.length > 0], ["Agregá al juego", false]], // el Encode se genera al agregar
  },
  looks: {
    generar: "Aplicar Look", aplicar: "Aplicar Look", nombre: "NOMBRE DEL LOOK", seGuarda: "Se guarda en:", tocaUno: "un Look",
    pasos: () => [["Elegí las Piezas", conPiezas()], ["Aplicá el Look", hayEncode()], ["Agregá al juego", false]],
    sinBase: "se elige al aplicar", tituloBase: "¿Dónde se guarda el Look?", nuevo: () => nuevoLook(), alAplicar: () => aplicarLook(),
    guardados: { tipo: "look", el: "el Look", lo: "lo", nuevo: "Look nuevo", mis: "Mis Looks", titulo: "GUARDA TU LOOK", sub: "GUARDA TUS LOOKS FAVORITOS" },
  },
  acciones: {
    generar: "Aplicar acción", aplicar: "Aplicar acción",
    pasos: () => [["Elegí la animación", Boolean(lookActual.animacion)], ["Elegí el Item", Boolean(lookActual.base)],
                  ["Aplicá la acción", hayEncode()], ["Agregá al juego", false]], nombre: "NOMBRE DE LA ACCIÓN", tocaUno: "una acción", sinBase: "elegí cualquier Item",
    tituloBase: "¿Dónde se guarda la acción?", nuevo: () => nuevaAccion(), alAplicar: () => aplicarAccion(),
    guardados: { tipo: "accion", el: "la acción", lo: "la", nuevo: "Acción nueva", mis: "Mis acciones", titulo: "GUARDA TU ACCIÓN",
                 sub: "GUARDA TUS ACCIONES FAVORITAS" },
  },
  trucar: {
    generar: "Trucar Prenda", aplicar: "Trucar todas", nombre: "NOMBRE DE LA PRENDA TRUCADA", seGuarda: "Se trucará:",
    tocaUno: "una Prenda trucada", sinBase: "elegí el Item base", tituloBase: "¿Qué Item se truca?", nuevo: () => nuevaPrendaATrucar(),
    alAplicar: () => trucarPrenda(),
    pasos: () => [["Elegí el Item base", Boolean(lookActual.base)], ["Elegí la Pieza", conPiezas()], ["Sumala a la lista", enLaLista()],
                  ["Trucá todas", hayEncode()], ["Agregá al juego", false]],
    guardados: { tipo: "trucada", el: "la Prenda trucada", lo: "la", nuevo: "Prenda trucada nueva", mis: "Mis Prendas trucadas",
                 titulo: "GUARDA TU PRENDA TRUCADA", sub: "GUARDA TUS PRENDAS TRUCADAS FAVORITAS" },
  },
  tiendas: pestanaNpc({ tipo: "tienda", el: "la tienda", lo: "la", nuevo: "Tienda nueva", mis: "Mis tiendas", titulo: "GUARDA TU TIENDA",
                        sub: "GUARDA TUS TIENDAS FAVORITAS", nombre: "NOMBRE DE LA TIENDA", tocaUno: "una tienda", lista: "Tiendas",
                        tituloBase: "¿Qué Item se convierte en tienda?" }),
  portales: pestanaNpc({ tipo: "portal", el: "el portal", lo: "lo", nuevo: "Portal nuevo", mis: "Mis portales", titulo: "GUARDA TU PORTAL",
                         sub: "GUARDA TUS PORTALES FAVORITOS", nombre: "NOMBRE DEL PORTAL", tocaUno: "un portal", lista: "Portales",
                         tituloBase: "¿Qué Item se convierte en portal?" }),
  minijuegos: pestanaNpc({ tipo: "minijuego", el: "el minijuego", lo: "lo", nuevo: "Minijuego nuevo", mis: "Mis minijuegos",
                           titulo: "GUARDA TU MINIJUEGO", sub: "GUARDA TUS MINIJUEGOS FAVORITOS", nombre: "NOMBRE DEL MINIJUEGO",
                           tocaUno: "un minijuego", lista: "Minijuegos", tituloBase: "¿Qué Item se convierte en minijuego?" }),
  fondos: pestanaNpc({ tipo: "fondo", el: "el fondo", lo: "lo", nuevo: "Fondo nuevo", mis: "Mis fondos", titulo: "GUARDA TU FONDO",
                       sub: "GUARDA TUS FONDOS FAVORITOS", nombre: "NOMBRE DEL FONDO", tocaUno: "un fondo", lista: "Fondos",
                       tituloBase: "¿Qué objeto se convierte en fondo?", sinBase: "elegí un objeto de la derecha",
                       documentoNuevo: () => nuevoFondo(), elegirUno: "Elegí un objeto", queHace: "Elegí el fondo",
                       hace: () => lookActual.cuadro != null }),
  terminator: {
    pasos: () => [
      ["Cargá los objetos", terminatorCargado],
      ["Elegí qué desbloquear", terminatorSeleccion.length > 0],
      ["Aplicá al juego", false],
    ],
  },
};
const dePestana = (pestana = vista) => ({ ...PESTANA.looks, ...PESTANA[pestana] });
const esNpc = (pestana = vista) => pestana in PESTANAS_NPC;
// Dónde el Item base puede ser cualquier Item (se convierte en lo que hace falta: ADR 0007).
const cualquierItem = () => esNpc() || vista === "acciones";
const documentos = {};
let pestanaDelDocumento = "looks"; // de qué pestaña es `lookActual`

function cambiarVista(nueva) {
  if (PESTANAS_DEL_EDITOR.includes(nueva) && nueva !== pestanaDelDocumento) {
    documentos[pestanaDelDocumento] = lookActual;
    lookActual = documentos[nueva] ?? documentoNuevo(nueva);
    pestanaDelDocumento = nueva;
    casilleroMarcado = null;
    lookElegido = null;
    looksGuardados = [];
  }
  detenerAnimacion();
  vista = nueva;
  const pantalla = PESTANAS_DEL_EDITOR.includes(vista) ? "looks" : vista;
  for (const nombre of ["agregar", "looks", "terminator"]) $(`vista-${nombre}`).hidden = nombre !== pantalla;
  for (const nombre of PESTANAS) $(`pestana-${nombre}`).setAttribute("aria-selected", String(nombre === vista));
  document.querySelector("main").classList.toggle("modo-looks", pantalla === "looks");
  document.querySelector("main").classList.toggle("modo-acciones", vista === "acciones");
  document.querySelector("main").classList.toggle("modo-trucar", vista === "trucar");
  document.querySelector("main").classList.toggle("modo-npc", esNpc());
  document.querySelector("main").classList.toggle("modo-fondos", esFondos());
  document.querySelector("main").classList.toggle("modo-terminator", vista === "terminator");
  $("aplicar-look").textContent = dePestana().aplicar;
  $("texto-se-guarda").textContent = dePestana().seGuarda;
  $("nombre-look").placeholder = dePestana().nombre;
  document.querySelector("main").classList.toggle("modo-agregar", vista === "agregar");
  $("items-a-recibir").hidden = vista !== "agregar";
  $("generar").textContent = dePestana().generar;
  avisarLista("");
  mostrarEncode(null);
  return cargarParaLaVista();
}

for (const nombre of PESTANAS) $(`pestana-${nombre}`).addEventListener("click", () => cambiarVista(nombre));

// --- La ventana del Item base: cómo se ve cada uno ---

const filaConImagen = (o) => [elementoIcono(o.ruta), etiqueta(o.clase, "nombre")];
// Un Item base: dónde queda en el juego.
const filaDeBase = (o) => [
  ...filaConImagen(o),
  ...(basesDeTodos ? [etiqueta(swfDeRuta(o.ruta), "ayuda swf-base")] : []),
  conIcono({ mochila: "backpack", prenda: "t-shirt", casa: "house" }[o.tipo] ?? "package",
           { mochila: "mochila", prenda: "guardarropa", casa: "casa" }[o.tipo] ?? o.tipo,
           `ayuda tipo-${o.tipo === "mochila" ? "mochila" : "prenda"}`),
];
