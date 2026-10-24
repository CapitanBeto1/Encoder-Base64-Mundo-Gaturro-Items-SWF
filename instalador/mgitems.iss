; Instalador de MG Items (Inno Setup 6).
; Lo compila scripts/armar_instalador.py, que pasa /DVersion y /DPrograma (carpeta armada por PyInstaller).

#ifndef Version
  #define Version "0.0.0"
#endif
#ifndef Programa
  #define Programa "..\dist\MGItems"
#endif

[Setup]
AppId={{6C1F6E8A-4B7D-4E3B-9F55-2A6D1C0B9E41}
AppName=MG Items
AppVersion={#Version}
AppVerName=MG Items {#Version}
AppPublisher=MG Items
DefaultDirName={autopf}\MGItems
DefaultGroupName=MG Items
DisableProgramGroupPage=yes
; Instalación para el usuario actual: no pide permisos de administrador.
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=MGItems-Setup-{#Version}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\MGItems.exe
CloseApplications=yes

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "{#Programa}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\MG Items"; Filename: "{app}\MGItems.exe"
Name: "{autodesktop}\MG Items"; Filename: "{app}\MGItems.exe"; Tasks: escritorio

[Run]
Filename: "{app}\MGItems.exe"; Description: "Abrir MG Items"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Lo que el programa descargó o generó (SWF del juego, imágenes). La configuración en %APPDATA% se conserva.
Type: filesandordirs; Name: "{localappdata}\MGItems"
