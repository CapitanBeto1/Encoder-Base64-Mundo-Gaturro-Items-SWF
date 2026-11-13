package
{
   import com.qb9.flashlib.tasks.TaskRunner;
   import com.qb9.flashlib.utils.DisplayUtil;
   import com.qb9.gaturro.user.inventory.GaturroInventory;
   import com.qb9.gaturro.util.StubAttributeHolder;
   import com.qb9.gaturro.view.components.banner.clothCustom.ClothEditorModal;
   import com.qb9.gaturro.view.components.banner.clothCustom.utils.ClothCustomUtil;
   import com.qb9.gaturro.view.gui.base.modal.InstantiableGuiModal;
   import com.qb9.gaturro.view.world.avatars.Gaturro;
   import com.qb9.mambo.core.attributes.CustomAttributes;
   import com.qb9.mambo.net.library.Libraries;
   import com.qb9.mambo.net.manager.DefaultNetworkManager;
   import com.qb9.mambo.net.manager.NetworkManagerEvent;
   import com.qb9.mambo.world.avatars.AvatarBodyEnum;
   import com.qb9.mambo.world.avatars.UserAvatar;
   import com.qb9.mines.mobject.Mobject;
   import flash.display.MovieClip;
   import flash.display.StageAlign;
   import flash.display.StageScaleMode;
   import flash.events.Event;
   import flash.external.ExternalInterface;
   import flash.geom.Rectangle;
   import flash.media.SoundMixer;
   import flash.media.SoundTransform;
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
         this.acomodar();
         if(ExternalInterface.available)
         {
            ExternalInterface.addCallback("mgVestir",this.mgVestir);
            ExternalInterface.addCallback("mgRepetir",this.actuar);
            ExternalInterface.addCallback("mgCargado",this.mgCargado);
            ExternalInterface.addCallback("mgEditar",this.mgEditar);
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
            }
         };
         var yo:MMO = this;
         // Los inventarios que espera el editor al guardar: de un juego sin conexión (nadie llama a `connect`).
         var sinConexion:DefaultNetworkManager = new DefaultNetworkManager();
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
         this.piezasEnEdicion = datos.piezas;
         this.coloresGuardados = datos.colores || "";
         this.atributos.attributes.mergeObject(datos.atributos || {});
         api.userAvatar = new UserAvatar(this.atributos.attributes,null,null);
         this.gaturro.visible = false;
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
         addChild(this.editor);
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
         stage.addEventListener(Event.RESIZE,this.acomodarEditor);
         this.acomodarEditor();
         ExternalInterface.call("mgEditorAbierto",JSON.stringify(editadas));
      }

      /** El editor entero a la vista, centrado y del tamaño que entre. */
      private function acomodarEditor(e:Event = null) : void
      {
         if(!this.editor)
         {
            return;
         }
         this.editor.scaleX = this.editor.scaleY = 1;
         var caja:Rectangle = this.editor.getBounds(this.editor);
         var escala:Number = Math.min(stage.stageWidth / caja.width,stage.stageHeight / caja.height);
         this.editor.scaleX = this.editor.scaleY = escala;
         this.editor.x = (stage.stageWidth - caja.width * escala) / 2 - caja.x * escala;
         this.editor.y = (stage.stageHeight - caja.height * escala) / 2 - caja.y * escala;
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
         ExternalInterface.call("mgEditado",JSON.stringify(partes));
         // Estamos dentro del clic de «Guardar» del editor: se cierra en el cuadro siguiente.
         addEventListener(Event.ENTER_FRAME,this.cerrarAlCuadro);
      }

      private function alCancelarEditor(e:Event) : void
      {
         addEventListener(Event.ENTER_FRAME,this.cerrarAlCuadro);
         ExternalInterface.call("mgEditorCerrado");
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
         stage.removeEventListener(Event.RESIZE,this.acomodarEditor);
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
