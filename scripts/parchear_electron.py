"""
Parcha el cliente de escritorio de Mundo Gaturro para que use los SWF modificados de MG Items
sin necesitar Fiddler abierto.

El código que se agrega al cliente (main.js dentro de app.asar), al arrancar el juego:
  1. Levanta un servidor HTTPS en 127.0.0.1 con un certificado autofirmado.
  2. Hace que el juego (y Flash) confíen en ese certificado, solo para 127.0.0.1.
  3. Redirige al servidor local los SWF del CDN que haya modificados en %LOCALAPPDATA%\\MGItems\\entregas\\swf:
       - acuarium.swf  (la pecera que muestra LATINcat)
       - computer.swf  (la computadora invisible de la pestaña Mapas)
     y sirve un crossdomain.xml permisivo: Flash lo pide al ver la redirección y sin él no carga el SWF.

El certificado se genera la primera vez (con openssl, que viene con Git) en %LOCALAPPDATA%\\MGItems\\cert.
Siempre parte de la copia original (app.asar.bak): correrlo de nuevo reemplaza el parche anterior.

    python scripts/parchear_electron.py

Para deshacer: copiar app.asar.bak sobre app.asar en %LOCALAPPDATA%\\Programs\\gaturro-desktop\\resources.
"""
import json
import os
import shutil
import struct
import subprocess
from pathlib import Path

LOCALAPPDATA = Path(os.environ["LOCALAPPDATA"])
ASAR_PATH = LOCALAPPDATA / "Programs" / "gaturro-desktop" / "resources" / "app.asar"
BACKUP_PATH = ASAR_PATH.with_suffix(".asar.bak")
CERT_DIR = LOCALAPPDATA / "MGItems" / "cert"
SWFS = ["acuarium", "computer"]


def openssl() -> str:
    encontrado = shutil.which("openssl")
    if encontrado:
        return encontrado
    git = shutil.which("git")
    if git:
        candidato = Path(git).resolve().parent.parent / "mingw64" / "bin" / "openssl.exe"
        if candidato.exists():
            return str(candidato)
    raise SystemExit("ERROR: no se encontró openssl (viene con Git for Windows).")


def generar_certificado() -> None:
    if (CERT_DIR / "cert.pem").exists() and (CERT_DIR / "key.pem").exists():
        return
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        openssl(), "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "36500",
        "-keyout", str(CERT_DIR / "key.pem"), "-out", str(CERT_DIR / "cert.pem"),
        "-subj", "/CN=127.0.0.1", "-addext", "subjectAltName=IP:127.0.0.1",
    ], check=True, capture_output=True)
    print(f"Certificado generado en: {CERT_DIR}")


OLD = "whenReadyApp(){this.createEvents(),this.createWindow()}"
# `c` es el módulo electron en el main.js minificado del cliente.
NEW = (
    "whenReadyApp(){"
    "this.createEvents();"
    "try{"
    'const _F=require("fs"),_Pa=require("path"),_B=_Pa.join(process.env.LOCALAPPDATA,"MGItems");'
    'const _S=' + json.dumps(SWFS) + ';const _D={};'
    '_S.forEach(function(n){const p=_Pa.join(_B,"entregas","swf",n+".swf");if(_F.existsSync(p))_D[n]=_F.readFileSync(p);});'
    'const _C=_Pa.join(_B,"cert");'
    'if(Object.keys(_D).length&&_F.existsSync(_Pa.join(_C,"cert.pem"))){'
    'const _XML=\'<?xml version="1.0"?><!DOCTYPE cross-domain-policy SYSTEM "http://www.macromedia.com/xml/dtds/cross-domain-policy.dtd">'
    '<cross-domain-policy><allow-access-from domain="*" secure="false"/>'
    '<allow-http-request-headers-from domain="*" headers="*" secure="false"/></cross-domain-policy>\';'
    'const _sv=require("https").createServer({cert:_F.readFileSync(_Pa.join(_C,"cert.pem")),key:_F.readFileSync(_Pa.join(_C,"key.pem"))},function(q,r){'
    'const u=q.url||"";'
    'if(u.indexOf("crossdomain")>=0){r.writeHead(200,{"Content-Type":"text/xml","Access-Control-Allow-Origin":"*"});r.end(_XML);return;}'
    'const n=Object.keys(_D).find(function(k){return u.indexOf("/"+k+".swf")===0;});'
    'if(!n){r.writeHead(404);r.end();return;}'
    'r.writeHead(200,{"Content-Type":"application/x-shockwave-flash","Access-Control-Allow-Origin":"*"});r.end(_D[n]);'
    '});'
    '_sv.listen(0,"127.0.0.1",function(){'
    "const _s=c.session&&c.session.defaultSession;if(!_s)return;"
    '_s.setCertificateVerifyProc(function(q,cb){cb(q.hostname==="127.0.0.1"?0:-3);});'
    '_s.webRequest.onBeforeRequest('
    '{urls:Object.keys(_D).map(function(n){return "https://cdn-ar.mundogaturro.com/juego/assets/"+n+".swf*";})},'
    'function(d,cb){const n=Object.keys(_D).find(function(k){return d.url.indexOf("/assets/"+k+".swf")>=0;});'
    'cb({redirectURL:"https://127.0.0.1:"+_sv.address().port+"/"+n+".swf"});}'
    ");"
    "});"
    "}"
    "}catch(e){}"
    "this.createWindow()}"
)


def leer_asar(datos: bytes):
    _, p2, _, header_size = struct.unpack_from("<4I", datos, 0)
    # data_offset = 8 (pickle exterior) + p2 (pickle del header, que ya incluye el padding a 4 bytes).
    return json.loads(datos[16:16 + header_size].decode("utf-8")), 8 + p2


def correr_offsets(nodo, despues_de, delta):
    if "files" in nodo:
        for hijo in nodo["files"].values():
            correr_offsets(hijo, despues_de, delta)
    elif "offset" in nodo and int(nodo["offset"]) > despues_de:
        nodo["offset"] = str(int(nodo["offset"]) + delta)


def main() -> None:
    if not ASAR_PATH.exists():
        raise SystemExit(f"ERROR: no se encontró el cliente de Mundo Gaturro en {ASAR_PATH}")
    if not BACKUP_PATH.exists():
        shutil.copy2(ASAR_PATH, BACKUP_PATH)
        print(f"Copia original guardada en: {BACKUP_PATH}")
    generar_certificado()

    asar = BACKUP_PATH.read_bytes()
    header, data_offset = leer_asar(asar)
    main_node = header["files"]["dist"]["files"]["main.js"]
    main_offset, main_size = int(main_node["offset"]), main_node["size"]
    main_js = asar[data_offset + main_offset:data_offset + main_offset + main_size].decode("utf-8")
    if OLD not in main_js:
        raise SystemExit("ERROR: no se encontró el punto a parchear en main.js. El cliente puede haberse actualizado.")

    nuevo_js = main_js.replace(OLD, NEW, 1).encode("utf-8")
    correr_offsets(header, main_offset, len(nuevo_js) - main_size)
    main_node["size"] = len(nuevo_js)
    datos = bytearray(asar[data_offset:])
    datos[main_offset:main_offset + main_size] = nuevo_js

    header_json = json.dumps(header, separators=(",", ":")).encode("utf-8")
    alineado = (len(header_json) + 3) & ~3
    bloque = struct.pack("<4I", 4, alineado + 8, alineado + 4, len(header_json))
    bloque += header_json + b"\x00" * (alineado - len(header_json))
    ASAR_PATH.write_bytes(bloque + bytes(datos))
    print(f"app.asar parcheado ({len(bloque) + len(datos)} bytes). Reiniciá Mundo Gaturro para que lo tome.")


if __name__ == "__main__":
    main()
