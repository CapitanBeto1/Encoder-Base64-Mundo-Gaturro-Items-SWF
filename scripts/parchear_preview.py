"""PROTOTIPO: le agrega los colores del Gaturro al `preview.swf` de la vista previa con Ruffle.

El `preview.swf` (de terceros, en `vendor/ruffle/`, no se versiona) viste al Gaturro con `changeAttr`, pero no
pinta sus colores. Este script le agrega al puente (`§+%§`) lo que hace el juego: pintar enteros
(`ColorTransform.color`) los clips `color1`, `color2`… del Gaturro y de las Piezas, con los colores que llegan en
el mismo JSON de `changeAttr` como enteros. La nariz de este archivo se llama `colorNose` (recibe `color4`); el
ojo no trae clip de iris, así que `color3` solo pinta Piezas.

Uso: `.venv/Scripts/python scripts/parchear_preview.py` (guarda el original en `preview.original.swf`).
"""

import shutil
import sys
import tempfile
from pathlib import Path

from mgitems.ffdec import FFDec

RUFFLE = Path(__file__).resolve().parent.parent / "vendor" / "ruffle"
PUENTE = "§+%§.as"

# (texto del puente decompilado, lo que se le agrega después)
AGREGADOS = [
    ("   import flash.display.DisplayObject;\n", "   import flash.display.DisplayObjectContainer;\n"),
    ("      private var §<&§:Boolean;\n", "      \n      private var mgColores:Object;\n"),
    ("         addChild(this.§,'§);\n", "         addEventListener(Event.ENTER_FRAME,this.mgCadaCuadro);\n"),
    ("      private function changeAttr(param1:String) : void\n      {\n", "         this.mgGuardarColores(param1);\n"),
    ("      private function clearAsset() : void\n      {\n         §9$§.empty(this.§&%§.§<\"§);\n      }\n", '''
      private function mgGuardarColores(param1:String) : void
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
         this.mgColores = {};
         for each(_loc3_ in ["color1","color2","color3","color4"])
         {
            if(_loc2_ != null && _loc3_ in _loc2_)
            {
               this.mgColores[_loc3_] = uint(_loc2_[_loc3_]);
            }
         }
         if("color4" in this.mgColores)
         {
            this.mgColores["colorNose"] = this.mgColores["color4"];
         }
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


def main() -> int:
    preview, original = RUFFLE / "preview.swf", RUFFLE / "preview.original.swf"
    if not original.exists():
        if not preview.exists():
            print(f"Falta {preview}")
            return 1
        shutil.copyfile(preview, original)
    ffdec = FFDec()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ffdec.ejecutar("-export", "script", str(tmp / "dec"), str(original))
        fuente = (tmp / "dec" / "scripts" / PUENTE).read_text(encoding="utf-8")
        for ancla, agregado in AGREGADOS:
            if fuente.count(ancla) != 1:
                print(f"El preview.swf no es el esperado: no encuentro {ancla.strip()!r}")
                return 1
            fuente = fuente.replace(ancla, ancla + agregado)
        (tmp / "scripts").mkdir()
        (tmp / "scripts" / PUENTE).write_text(fuente, encoding="utf-8", newline="\n")
        ffdec.ejecutar("-importScript", str(original), str(tmp / "preview.swf"), str(tmp / "scripts"))
        ffdec.ejecutar("-export", "script", str(tmp / "ver"), str(tmp / "preview.swf"))
        if "mgPintar" not in (tmp / "ver" / "scripts" / PUENTE).read_text(encoding="utf-8"):
            print("FFDec no pudo meter el cambio en el preview.swf")
            return 1
        shutil.copyfile(tmp / "preview.swf", preview)
    print(f"Listo: {preview} ya pinta los colores del Gaturro.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
