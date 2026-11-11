package
{
   import com.qb9.flashlib.utils.DisplayUtil;
   import com.qb9.gaturro.util.StubAttributeHolder;
   import com.qb9.gaturro.view.world.avatars.Gaturro;
   import com.qb9.mambo.core.attributes.CustomAttributes;
   import com.qb9.mambo.net.library.Libraries;
   import flash.display.MovieClip;
   import flash.display.StageAlign;
   import flash.display.StageScaleMode;
   import flash.events.Event;
   import flash.external.ExternalInterface;
   import flash.media.SoundMixer;
   import flash.media.SoundTransform;
   import flash.system.Security;

   /**
    * El Gaturro en vivo de MG Items (docs/adr/0009): la clase principal del SWF, en lugar de la del juego.
    * Crea un `Gaturro` del juego (su clase, sin tocar) y le pasa los atributos que le manda la página con
    * `mgVestir`: los mismos que tiene un avatar en el juego (Partes del cuerpo, `transport`, `effect`,
    * `color1`…`color4`, `emote` y `action`). Vestirlo, pintarlo, montarlo y animarlo lo hace el código del juego.
    */
   [SWF(width="800", height="480", frameRate="24")]
   public class MMO extends MovieClip
   {

      private var gaturro:Gaturro;

      private var atributos:StubAttributeHolder;

      private var accion:String = "";
      
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
         user = {
            "username":"",
            "isCitizen":true,
            "settings":{"getValue":function(a:*):Object
            {
               return true;
            }},
            "blocked":{"isBlocked":function(a:*):Boolean
            {
               return false;
            }}
         };
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
