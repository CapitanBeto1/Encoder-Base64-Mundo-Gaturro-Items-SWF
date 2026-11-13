package
{
   import com.qb9.flashlib.tasks.TaskRunner;
   import com.qb9.flashlib.utils.DisplayUtil;
   import com.qb9.gaturro.user.inventory.GaturroInventory;
   import com.qb9.gaturro.user.inventory.InventoryUtil;
   import com.qb9.gaturro.util.StubAttributeHolder;
   import com.qb9.gaturro.view.components.banner.avatar.CustomLayerBanner;
   import com.qb9.gaturro.view.components.banner.clothCustom.ClothEditorModal;
   import com.qb9.gaturro.view.components.banner.clothCustom.utils.ClothCustomUtil;
   import com.qb9.gaturro.view.gui.base.modal.InstantiableGuiModal;
   import com.qb9.gaturro.view.world.avatars.Gaturro;
   import com.qb9.mambo.core.attributes.CustomAttributes;
   import com.qb9.mambo.net.library.Libraries;
   import com.qb9.mambo.user.inventory.InventorySceneObject;
   import com.qb9.mambo.net.manager.DefaultNetworkManager;
   import com.qb9.mambo.net.manager.NetworkManagerEvent;
   import com.qb9.mambo.world.avatars.AvatarBodyEnum;
   import com.qb9.mambo.world.avatars.UserAvatar;
   import com.qb9.mines.mobject.Mobject;
   import flash.display.Loader;
   import flash.display.LoaderInfo;
   import flash.display.MovieClip;
   import flash.display.Sprite;
   import flash.display.StageAlign;
   import flash.display.StageScaleMode;
   import flash.events.Event;
   import flash.events.IOErrorEvent;
   import flash.events.MouseEvent;
   import flash.external.ExternalInterface;
   import flash.media.SoundMixer;
   import flash.media.SoundTransform;
   import flash.net.URLRequest;
   import flash.system.Security;

   /**
    * El Gaturro en vivo de MG Items (docs/adr/0009): la clase principal del SWF, en lugar de la del juego.
    * Crea un `Gaturro` del juego (su clase, sin tocar) y le pasa los atributos que le manda la página con
    * `mgVestir`: los mismos que tiene un avatar en el juego (Partes del cuerpo, `transport`, `effect`,
    * `color1`…`color4`, `emote` y `action`). Vestirlo, pintarlo, montarlo y animarlo lo hace el código del juego.
    *
    * Con `mgEditar` abre el editor del juego para personalizar las Piezas («Customiza tu ropa»: `ClothEditorModal`,
    * con su arte del banner `CustomClothBanner`). Al guardar, el editor arma los `wear_<parte>` y se los pasa a
    * `net.sendAction`: acá `net` es un `DefaultNetworkManager` del juego que nunca se conecta (nadie llama a
    * `connect`, así que no tiene socket y no sale nada); se lee lo que iba a mandar y se le pasa a la página
    * (`mgEditado`).
    *
    * Con `mgPersonalizar` abre el menú del juego para personalizar (banner `AvatarConfig`): «Customiza tu ropa» abre
    * el editor, y «Configura tus accesorios» (`CustomLayerBanner`) deja poner hasta tres Piezas en Sombrero, Pelo,
    * Accesorio, Boca y Cuello, una arriba de la otra. Su grilla muestra las Piezas que manda la página, como si fueran
    * Items del guardarropa; al guardar, el juego las deja en el avatar (`hats2`, `hats3`…) y se le pasan a la página
    * (`mgCapas`).
    */
   [SWF(width="800", height="480", frameRate="24")]
   public class MMO extends MovieClip
   {

      private var gaturro:Gaturro;

      private var atributos:StubAttributeHolder;

      private var accion:String = "";

      // El editor de Piezas del juego y lo que necesita: el banner con su arte y un reloj de tareas.
      private var banner:InstantiableGuiModal;

      private var editor:ClothEditorModal;

      private var tareas:TaskRunner;

      private var piezasEnEdicion:Object;

      private var coloresGuardados:String = "";

      // El escenario del juego (800 × 480), donde van sus ventanas como las pone el juego (`Gui.addModal`, en su 0,0).
      private var escenario:Sprite;

      // El menú de personalizar del juego (y si se entró por él: al cerrar una ventana se vuelve al menú).
      private var menu:Sprite;

      private var menuDelJuego:MovieClip;

      private var conMenu:Boolean = false;

      private var paraPersonalizar:Object;

      // «Configura tus accesorios» y cómo estaban las capas al abrirlo (para saber si se guardó algo).
      private var capas:CustomLayerBanner;

      private var capasPorDesechar:CustomLayerBanner;

      private var capasAlAbrir:String;

      private var sinConexion:DefaultNetworkManager;

      // Las Partes con capas de «Configura tus accesorios» (`CustomLayerBanner.WEAR_TYPES`).
      private static const PARTES_CON_CAPAS:Array = ["hats","hairs","accesories","mouths","neck"];
      
      // A qué altura del escenario quedan los pies (la página agranda el zoom alrededor de ese punto).
      private static const PIES:Number = 0.8;

      public function MMO()
      {
         super();
         Security.allowDomain("*");
         Security.allowInsecureDomain("*");
         SoundMixer.soundTransform = new SoundTransform(0);
         if(stage)
         {
            this.iniciar();
         }
         else
         {
            addEventListener(Event.ADDED_TO_STAGE,this.iniciar);
         }
      }

      private function iniciar(e:Event = null) : void
      {
         removeEventListener(Event.ADDED_TO_STAGE,this.iniciar);
         while(numChildren > 0)
         {
            removeChildAt(0);
         }
         this.prepararElJuego();
         this.atributos = new StubAttributeHolder(new CustomAttributes());
         this.gaturro = new Gaturro(this.atributos,true,"");
         addChild(this.gaturro);
         stage.scaleMode = StageScaleMode.NO_SCALE;
         stage.align = StageAlign.TOP_LEFT;
         stage.addEventListener(Event.RESIZE,this.acomodar);
         stage.addEventListener(Event.RESIZE,this.acomodarVentanas);
         this.acomodar();
         if(ExternalInterface.available)
         {
            ExternalInterface.addCallback("mgVestir",this.mgVestir);
            ExternalInterface.addCallback("mgRepetir",this.actuar);
            ExternalInterface.addCallback("mgCargado",this.mgCargado);
            ExternalInterface.addCallback("mgEditar",this.mgEditar);
            ExternalInterface.addCallback("mgPersonalizar",this.mgPersonalizar);
         }
      }

      /**
       * El Gaturro parado en el medio, del tamaño que entra en el lugar que haya (el del marco de la página),
       * con espacio arriba para sombreros y vehículos que vuelan. Mide unos 62 × 78 sin nada puesto.
       */
      private function acomodar(e:Event = null) : void
      {
         var ancho:Number = stage.stageWidth;
         var alto:Number = stage.stageHeight;
         this.gaturro.scaleX = this.gaturro.scaleY = Math.min(0.5 * alto / 78,0.8 * ancho / 62);
         this.gaturro.x = ancho / 2;
         this.gaturro.y = alto * PIES;
      }
      
      /**
       * Lo que el `Gaturro` del juego espera encontrar alrededor: de dónde bajar las Piezas, y un juego sin
       * sala ni usuario ni restricciones del servidor (`api`, `user` y `settings` son los globales del juego).
       */
      private function prepararElJuego() : void
      {
         libs = new Libraries("/assets/",true);
         var yo:MMO = this;
         api = {
            "view":{"noTransport":false},
            "room":{"id":0},
            "roomView":{"isInViewArea":function(a:*):Boolean
            {
               return true;
            }},
            "userAvatar":{"username":""},
            "setAvatarAttribute":function(a:*, b:*):void
            {
            },
            "getAvatarAttribute":function(a:*):Object
            {
               return null;
            },
            "setSession":function(a:*, b:*):void
            {
            },
            "giveInstantCloth":function(a:*, b:*):void
            {
            },
            // Lo que piden las ventanas de personalizar: sin sala que congelar ni pantalla que oscurecer (eso lo hace
            // la página). «Configura tus accesorios» vuelve al menú al guardar o cerrar.
            "freeze":function():void
            {
            },
            "unfreeze":function():void
            {
            },
            "addShadowScreen":function(... a):void
            {
            },
            "removeShadowScreen":function(... a):void
            {
            },
            "showBannerModal":function(nombre:String):void
            {
               yo.alCerrarCapas();
            }
         };
         // Los inventarios que espera el editor al guardar: de un juego sin conexión (nadie llama a `connect`).
         var sinConexion:DefaultNetworkManager = new DefaultNetworkManager();
         this.sinConexion = sinConexion;
         user = {
            "username":"",
            "isCitizen":true,
            "sceneObjectId":0,
            "visualizer":new GaturroInventory(sinConexion),
            "bag":new GaturroInventory(sinConexion),
            "house":new GaturroInventory(sinConexion),
            "settings":{"getValue":function(a:*):Object
            {
               return true;
            }},
            "blocked":{"isBlocked":function(a:*):Boolean
            {
               return false;
            }},
            // Los colores que el jugador guarda en el editor («+»): los conserva la página.
            "getProfileAttribute":function(clave:*):Object
            {
               return clave == "custom/colors" ? yo.coloresGuardados : null;
            },
            "setProfileAttribute":function(clave:*, valor:*):void
            {
               if(clave == "custom/colors")
               {
                  yo.coloresGuardados = String(valor);
                  ExternalInterface.call("mgColoresGuardados",yo.coloresGuardados);
               }
            }
         };
         // Lo que manda el juego al servidor: acá nada sale (sin conexión); el editor entrega por acá lo que guarda.
         net = sinConexion;
         sinConexion.addEventListener(NetworkManagerEvent.ACTION_SENT,this.alGuardarEditor);
         region = {
            "setText":function(campo:*, texto:*):void
            {
               campo.text = texto;
            },
            "getText":function(texto:*):String
            {
               return texto;
            }
         };
         server = {"time":0};
         // Sin sonidos (las ventanas del juego suenan al abrirse).
         audio = {
            "addLazyPlay":function(... a):void
            {
            },
            "play":function(... a):void
            {
            },
            "stop":function(... a):void
            {
            }
         };
         // El editor busca su banner en `banners/`, que el servidor de MG Items saca del juego.
         settings.resources = {"banners":"/"};
         settings.troublesomeItems = {};
         settings.validItems = {
            "effect":{},
            "action":{}
         };
         settings.special_ph = {
            "items":{},
            "roomsId":[]
         };
         settings.tiles = {};
         settings.medals = {};
         settings.profile = {"verified":[]};
         settings.avatar = {"speed":100};
      }

      /**
       * Deja al Gaturro con esos atributos (JSON). La acción se hace al cambiar: en el juego es un atributo que
       * se dispara al usar el Item, no un estado.
       */
      private function mgVestir(json:String) : void
      {
         var nuevos:Object = JSON.parse(json);
         var accion:String = nuevos.action || "";
         delete nuevos.action;
         this.atributos.attributes.mergeObject(nuevos);
         if(accion != this.accion)
         {
            this.accion = accion;
            this.actuar();
         }
      }

      /** Si ya llegaron todas las Piezas que se le pidieron (para sacarle una foto entero). */
      private function mgCargado() : Boolean
      {
         return this.gaturro.loaded;
      }

      /**
       * Abre el editor del juego con esas Piezas (JSON: `{piezas: {parte: valor}, atributos, colores}`). `valor` es
       * el de la Pieza con su personalización (`pack.Clase_on,…//…`); `atributos`, los del Gaturro para «Visualizar»;
       * `colores`, los que el jugador guardó en el editor.
       */
      private function mgEditar(json:String) : void
      {
         var datos:Object = JSON.parse(json);
         this.cerrarTodo();
         this.conMenu = false;
         this.prepararAvatar(datos.atributos,datos.colores);
         this.editarPiezas(datos.piezas);
      }

      /**
       * Abre el menú de personalizar del juego (JSON: `{atributos, piezas, colores, capas}`): `piezas` son las que edita
       * «Customiza tu ropa» (como en `mgEditar`), y `capas` ([{ruta, parte}]), las que muestra la grilla de «Configura tus
       * accesorios», cada una en la pestaña de su Parte.
       */
      private function mgPersonalizar(json:String) : void
      {
         this.paraPersonalizar = JSON.parse(json);
         this.cerrarTodo();
         this.conMenu = true;
         this.prepararAvatar(this.paraPersonalizar.atributos,this.paraPersonalizar.colores);
         this.mostrarMenu();
      }

      /** El avatar que miran las ventanas del juego: el Gaturro con estos atributos (el de la sala, para las capas). */
      private function prepararAvatar(atributos:Object, colores:String) : void
      {
         this.coloresGuardados = colores || "";
         this.atributos.attributes.mergeObject(atributos || {});
         api.userAvatar = new UserAvatar(this.atributos.attributes,null,null);
         api.room.userAvatar = api.userAvatar;
         this.gaturro.visible = false;
      }

      private function editarPiezas(piezas:Object) : void
      {
         this.piezasEnEdicion = piezas;
         if(!this.banner)
         {
            this.banner = new InstantiableGuiModal("CustomClothBanner","PageInventoryMC");
            this.banner.visible = false;
            addChild(this.banner);
         }
         addEventListener(Event.ENTER_FRAME,this.esperarBanner);
      }

      private function esperarBanner(e:Event) : void
      {
         var listo:Boolean = false;
         try
         {
            listo = this.banner.getInstanceByName("LayerItemMC") != null;
         }
         catch(err:Error)
         {
         }
         if(!listo)
         {
            return;
         }
         removeEventListener(Event.ENTER_FRAME,this.esperarBanner);
         this.abrirEditor();
      }

      private function abrirEditor() : void
      {
         var parte:String = null;
         var valor:String = null;
         var primera:String = null;
         var editadas:Array = [];
         var partesDelCuerpo:Object = AvatarBodyEnum.getList();
         this.cerrarEditor();
         if(!this.tareas)
         {
            this.tareas = new TaskRunner(this);
            this.tareas.start();
         }
         // Como `ClothCustomBanner.openModal`: primero en pantalla, después las Piezas (las de un Item).
         this.editor = new ClothEditorModal(this.banner,this.tareas);
         this.editor.addEventListener(Event.CLOSE,this.alCancelarEditor);
         this.escenarioDelJuego().addChild(this.editor);
         // Las que el editor muestra (`ClothEditorModal.show`): Partes del cuerpo, sin las prohibidas.
         var item:Object = {};
         for(parte in this.piezasEnEdicion)
         {
            valor = String(this.piezasEnEdicion[parte]);
            if(!partesDelCuerpo[parte] || ClothCustomUtil.isProhibited(parte,valor))
            {
               continue;
            }
            item[parte] = valor;
            editadas.push(parte);
            primera = primera || valor.split(",")[0].split("//")[0];
         }
         item.id = "mgitems";
         item.itemName = primera;
         this.editor.show(item);
         this.acomodarVentanas();
         ExternalInterface.call("mgEditorAbierto",JSON.stringify(editadas));
      }

      /** El escenario del juego, encima de todo: sus ventanas quedan donde las pone el juego. */
      private function escenarioDelJuego() : Sprite
      {
         if(!this.escenario)
         {
            this.escenario = new Sprite();
            this.acomodarVentanas();
         }
         addChild(this.escenario);
         return this.escenario;
      }

      /** El escenario del juego entero a la vista: del tamaño que entre, centrado (como el juego en su página). */
      private function acomodarVentanas(e:Event = null) : void
      {
         if(!this.escenario)
         {
            return;
         }
         var escala:Number = Math.min(stage.stageWidth / 800,stage.stageHeight / 480);
         this.escenario.scaleX = this.escenario.scaleY = escala;
         this.escenario.x = (stage.stageWidth - 800 * escala) / 2;
         this.escenario.y = (stage.stageHeight - 480 * escala) / 2;
      }

      // --- El menú de personalizar (banner `AvatarConfig`) ---

      private function mostrarMenu() : void
      {
         var cargador:Loader = null;
         if(!this.menu)
         {
            // Los banners sueltos del juego se dibujan alrededor de su 0,0 (`acquireAPI` los corre a −400, −240).
            this.menu = new Sprite();
            this.menu.x = 400;
            this.menu.y = 240;
            this.escenarioDelJuego().addChild(this.menu);
            cargador = new Loader();
            cargador.contentLoaderInfo.addEventListener(Event.COMPLETE,this.alCargarMenu);
            cargador.contentLoaderInfo.addEventListener(IOErrorEvent.IO_ERROR,this.alFallarMenu);
            cargador.load(new URLRequest("/banners/AvatarConfig.swf"));
         }
         if(!this.menuDelJuego)
         {
            return;
         }
         this.menu.visible = true;
         this.escenarioDelJuego().addChild(this.menu);
         ExternalInterface.call("mgPersonalizarAbierto");
      }

      private function alCargarMenu(e:Event) : void
      {
         var yo:MMO = this;
         this.menuDelJuego = LoaderInfo(e.target).content as MovieClip;
         this.menu.addChild(this.menuDelJuego);
         // Lo que el menú le pide al juego: abrir una de sus dos ventanas (`AvatarConfig_fla.MainTimeline`).
         this.menuDelJuego.acquireAPI({
            "addShadowScreen":function(... a):void
            {
            },
            "removeShadowScreen":function(... a):void
            {
            },
            "instantiateBannerModal":function(nombre:String):void
            {
               yo.abrirDelMenu(nombre);
            }
         });
         var salir:MovieClip = this.menuDelJuego["close"] as MovieClip;
         salir.buttonMode = true;
         salir.addEventListener(MouseEvent.CLICK,this.alSalirDelMenu);
         this.mostrarMenu();
      }

      private function alFallarMenu(e:IOErrorEvent) : void
      {
         ExternalInterface.call("mgEditorError","no se pudo bajar el menú del juego");
      }

      private function abrirDelMenu(nombre:String) : void
      {
         var parte:String = null;
         var hayPiezas:Boolean = false;
         if(nombre == "ClothCustomModal")
         {
            for(parte in this.paraPersonalizar.piezas)
            {
               hayPiezas = true;
            }
            if(!hayPiezas)
            {
               ExternalInterface.call("mgSinPiezas");
               return;
            }
            this.menu.visible = false;
            this.editarPiezas(this.paraPersonalizar.piezas);
         }
         else if(nombre == "CustomLayerModal")
         {
            this.menu.visible = false;
            this.abrirCapas();
         }
      }

      private function alSalirDelMenu(e:MouseEvent) : void
      {
         this.menu.visible = false;
         this.conMenu = false;
         ExternalInterface.call("mgEditorCerrado");
      }

      /** Cierra lo que haya quedado abierto (la página cerró el diálogo sin pasar por el juego, con Escape). */
      private function cerrarTodo() : void
      {
         this.cerrarEditor();
         if(this.capas)
         {
            this.capasPorDesechar = this.capas;
            this.capas = null;
            this.desecharCapas();
         }
         if(this.menu)
         {
            this.menu.visible = false;
         }
      }

      // --- «Configura tus accesorios» (`CustomLayerBanner`) ---

      /**
       * Lo abre con las Piezas de la página en el guardarropa (`user.visualizer`): cada una es un Item de mentira que
       * viste esa Pieza en su Parte (`wear_<parte>`), hecho por el juego (`InventoryUtil`), con la Pieza de nombre (así
       * el juego dibuja la Pieza en el botón).
       */
      private function abrirCapas() : void
      {
         var pieza:Object = null;
         var datos:Object = null;
         var atributos:CustomAttributes = null;
         var item:InventorySceneObject = null;
         var delServidor:Mobject = null;
         var id:int = 1;
         var guardarropa:GaturroInventory = new GaturroInventory(this.sinConexion);
         var vacio:Mobject = new Mobject();
         vacio.setString("name","visualizer");
         vacio.setMobjectArray("sceneObjects",[]);
         guardarropa.buildFromMobject(vacio);
         for each(pieza in this.paraPersonalizar.capas)
         {
            datos = {};
            datos["wear_" + pieza.parte] = pieza.ruta;
            atributos = new CustomAttributes();
            atributos.mergeObject(datos);
            item = InventoryUtil.createInventoryObject(atributos);
            // El número y el nombre de un Item los trae lo que manda el servidor (`SceneObject.buildFromMobject`).
            delServidor = new Mobject();
            delServidor.setString("id",String(id++));
            delServidor.setString("name",pieza.ruta);
            delServidor.setIntegerArray("size",[1,1]);
            item.buildFromMobject(delServidor);
            guardarropa.sessionAdd(item);
         }
         user.visualizer = guardarropa;
         this.capasAlAbrir = this.capasDelAvatar();
         this.capas = new CustomLayerBanner();
         this.escenarioDelJuego().addChild(this.capas);
         this.capas.propertySetted();
         addEventListener(Event.ENTER_FRAME,this.esperarCapas);
      }

      private function esperarCapas(e:Event) : void
      {
         if(!this.capas || !this.capas.isReady)
         {
            return;
         }
         removeEventListener(Event.ENTER_FRAME,this.esperarCapas);
         // El ícono de error es un molde que el banner copia (`copyClip`), no algo que se ve: en el juego queda tapado.
         var molde:MovieClip = (this.capas.view as MovieClip)["iconError"] as MovieClip;
         if(molde)
         {
            molde.visible = false;
         }
      }

      /** Al guardar o cerrar «Configura tus accesorios» (`closeBanner`): si cambió algo, se lo pasa a la página. */
      private function alCerrarCapas() : void
      {
         if(!this.capas)
         {
            return;
         }
         removeEventListener(Event.ENTER_FRAME,this.esperarCapas);
         var ahora:String = this.capasDelAvatar();
         // Estamos dentro del clic del banner: se desecha en el cuadro siguiente.
         this.capasPorDesechar = this.capas;
         this.capas = null;
         addEventListener(Event.ENTER_FRAME,this.desecharCapas);
         if(ahora != this.capasAlAbrir)
         {
            this.conMenu = false;
            ExternalInterface.call("mgCapas",ahora);
         }
         else
         {
            this.mostrarMenu();
         }
      }

      private function desecharCapas(e:Event = null) : void
      {
         removeEventListener(Event.ENTER_FRAME,this.desecharCapas);
         if(!this.capasPorDesechar)
         {
            return;
         }
         try
         {
            this.capasPorDesechar.dispose();
         }
         catch(err:Error)
         {
         }
         if(this.capasPorDesechar.parent)
         {
            this.capasPorDesechar.parent.removeChild(this.capasPorDesechar);
         }
         this.capasPorDesechar = null;
      }

      /** Las capas del avatar (Parte de cada capa → valor de su Pieza, o ""), en JSON. */
      private function capasDelAvatar() : String
      {
         var parte:String = null;
         var numero:int = 0;
         var clave:String = null;
         var valor:* = undefined;
         var valores:Object = {};
         var atributos:CustomAttributes = UserAvatar(api.room.userAvatar).attributes;
         for each(parte in PARTES_CON_CAPAS)
         {
            for(numero = 1; numero <= 3; numero++)
            {
               clave = numero == 1 ? parte : parte + numero;
               valor = atributos[clave];
               valores[clave] = valor ? String(valor) : "";
            }
         }
         return JSON.stringify(valores);
      }

      /** Lo que el editor le iba a mandar al servidor al guardar: los `wear_<parte>` de las Piezas que quedaron. */
      private function alGuardarEditor(e:NetworkManagerEvent) : void
      {
         var pedido:Mobject = e.mobject;
         if(!pedido || pedido.getString("request") != "AcquireObjectActionRequest")
         {
            return;
         }
         var atributo:* = undefined;
         var clave:String = null;
         var valor:String = null;
         var partes:Object = {};
         var lista:Array = null;
         try
         {
            lista = pedido.getMobjectArray("customAttributes");
            if(!lista)
            {
               lista = [];
            }
            for each(atributo in lista)
            {
               clave = atributo.getString("type");
               valor = atributo.getString("data");
               if(clave && clave.indexOf("wear_") == 0)
               {
                  partes[clave.substr(5)] = valor.charAt(0) == "\"" ? valor.slice(1,-1) : valor;
               }
            }
         }
         catch(err:Error)
         {
            ExternalInterface.call("mgEditorError",String(err));
            return;
         }
         this.conMenu = false;
         ExternalInterface.call("mgEditado",JSON.stringify(partes));
         // Estamos dentro del clic de «Guardar» del editor: se cierra en el cuadro siguiente.
         addEventListener(Event.ENTER_FRAME,this.cerrarAlCuadro);
      }

      private function alCancelarEditor(e:Event) : void
      {
         addEventListener(Event.ENTER_FRAME,this.cerrarAlCuadro);
         if(this.conMenu)
         {
            addEventListener(Event.ENTER_FRAME,this.volverAlMenu);
         }
         else
         {
            ExternalInterface.call("mgEditorCerrado");
         }
      }

      private function volverAlMenu(e:Event) : void
      {
         removeEventListener(Event.ENTER_FRAME,this.volverAlMenu);
         this.mostrarMenu();
      }

      private function cerrarAlCuadro(e:Event) : void
      {
         removeEventListener(Event.ENTER_FRAME,this.cerrarAlCuadro);
         this.cerrarEditor();
      }

      private function cerrarEditor() : void
      {
         if(!this.editor)
         {
            return;
         }
         this.editor.removeEventListener(Event.CLOSE,this.alCancelarEditor);
         if(this.editor.parent)
         {
            this.editor.parent.removeChild(this.editor);
         }
         this.editor = null;
      }

      /** Hace la acción desde el principio, o vuelve a quedarse quieto si no hay ninguna. */
      private function actuar() : void
      {
         DisplayUtil.empty(this.gaturro.objects_ph);
         this.gaturro.stand();
         if(this.accion)
         {
            this.gaturro.doActionLocal(this.accion);
         }
      }
   }
}
