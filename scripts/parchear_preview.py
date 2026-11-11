"""Le agrega al `preview.swf` del Gaturro en vivo lo que el programa necesita para vestirlo.

El `preview.swf` (de naw-trucador; lo baja `obtener_binarios.py`) trae el Gaturro de pantalla del juego y un
puente (`§+%§`) que lo viste desde la página. A ese puente se le agrega `mgVestir(json)`, que deja al Gaturro
como dice `{"partes": {parte: "swf.clase_on" o ""}, "colores": {"color1": entero, …}, "emote": "normal"}`:

- pone cada Pieza en su Parte del cuerpo (lo hace el archivo; `mgVestir` solo le pasa todas las Partes juntas);
- pinta enteros los clips de color del Gaturro y de las Piezas, como el juego (`ColorTransform.color`), en cada
  cuadro, porque las Piezas llegan después. La nariz de este Gaturro se llama `colorNose` (recibe `color4`);
  su ojo no trae clip de iris, así que `color3` solo pinta Piezas;
- lleva la cabeza a la emoción.
"""

import shutil
import tempfile
from pathlib import Path

from mgitems.ffdec import FFDec

PUENTE = "§+%§.as"

# (texto del puente decompilado, lo que se le agrega después)
AGREGADOS = [
    ("   import flash.display.DisplayObject;\n", "   import flash.display.DisplayObjectContainer;\n"),
    ("      private var §<&§:Boolean;\n", "      \n      private var mgColores:Object;\n"),
    ("         addChild(this.§,'§);\n", "         addEventListener(Event.ENTER_FRAME,this.mgCadaCuadro);\n"),
    ('         ExternalInterface.addCallback("changeAttr",this.changeAttr);\n',
     '         ExternalInterface.addCallback("mgVestir",this.mgVestir);\n'),
    ("      private function clearAsset() : void\n      {\n         §9$§.empty(this.§&%§.§<\"§);\n      }\n", '''
      private function mgVestir(param1:String) : void
      {
         var _loc2_:Object = null;
         var _loc3_:String = null;
         try
         {
            _loc2_ = JSON.parse(param1);
         }
         catch(err:Error)
         {
            return;
         }
         this.§<&§ = true;
         this.§&%§.visible = false;
         this.§,'§.visible = true;
         this.mgColores = {};
         for(_loc3_ in _loc2_.colores)
         {
            this.mgColores[_loc3_] = uint(_loc2_.colores[_loc3_]);
         }
         if("color4" in this.mgColores)
         {
            this.mgColores["colorNose"] = this.mgColores["color4"];
         }
         this.§,'§.attributes.§0$§(_loc2_.partes);
         this.§,'§.§2!§.gotoAndStop(_loc2_.emote);
      }

      private function mgCadaCuadro(param1:Event) : void
      {
         if(this.mgColores != null && this.§,'§ != null)
         {
            this.mgPintar(this.§,'§);
         }
      }

      private function mgPintar(param1:DisplayObjectContainer) : void
      {
         var _loc3_:DisplayObject = null;
         var _loc2_:int = 0;
         while(_loc2_ < param1.numChildren)
         {
            _loc3_ = param1.getChildAt(_loc2_);
            if(_loc3_ != null)
            {
               if(_loc3_.name in this.mgColores)
               {
                  §9$§.§+!§(_loc3_,this.mgColores[_loc3_.name]);
               }
               else if(_loc3_ is DisplayObjectContainer)
               {
                  this.mgPintar(_loc3_ as DisplayObjectContainer);
               }
            }
            _loc2_++;
         }
      }
'''),
]


def parchear(carpeta: Path) -> None:
    """Cambia `carpeta/preview.swf` por el mismo archivo con `mgVestir`. RuntimeError si no se pudo."""
    preview = carpeta / "preview.swf"
    ffdec = FFDec()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ffdec.ejecutar("-export", "script", str(tmp / "dec"), str(preview))
        fuente = (tmp / "dec" / "scripts" / PUENTE).read_text(encoding="utf-8")
        for ancla, agregado in AGREGADOS:
            if fuente.count(ancla) != 1:
                raise RuntimeError(f"El preview.swf no es el esperado: no se encuentra {ancla.strip()!r}")
            fuente = fuente.replace(ancla, ancla + agregado)
        (tmp / "scripts").mkdir()
        (tmp / "scripts" / PUENTE).write_text(fuente, encoding="utf-8", newline="\n")
        ffdec.ejecutar("-importScript", str(preview), str(tmp / "preview.swf"), str(tmp / "scripts"))
        ffdec.ejecutar("-export", "script", str(tmp / "ver"), str(tmp / "preview.swf"))
        if "mgPintar" not in (tmp / "ver" / "scripts" / PUENTE).read_text(encoding="utf-8"):
            raise RuntimeError("FFDec no pudo agregarle mgVestir al preview.swf")
        shutil.copyfile(tmp / "preview.swf", preview)
