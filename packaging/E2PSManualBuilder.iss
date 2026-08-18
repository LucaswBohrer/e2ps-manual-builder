; Inno Setup 6 script for E2PS Manual Builder.
; Compile after running packaging\build_windows.bat on a Windows computer.

#define AppName "E2PS Manual Builder"
#define AppVersion "1.0.0"
#define AppPublisher "E2PS"
#define AppExeName "E2PSManualBuilder.exe"
#define AppId "{{B84B343D-1902-4239-8C1F-51A4D37C6B74}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\E2PS Manual Builder
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\release
OutputBaseFilename=E2PS-Manual-Builder-Setup-{#AppVersion}
SetupIconFile=..\manual_builder\assets\e2ps.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
; Let Inno Setup close a running older E2PSManualBuilder.exe before replacing it.
CloseApplications=yes
CloseApplicationsFilter={#AppExeName}
RestartApplications=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos adicionais:"; Flags: unchecked

[Files]
Source: "..\dist\E2PS Manual Builder\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\.e2ps"; ValueType: string; ValueName: ""; ValueData: "E2PSManualBuilder.Project"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\E2PSManualBuilder.Project"; ValueType: string; ValueName: ""; ValueData: "Projeto E2PS Manual Builder"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\E2PSManualBuilder.Project\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"
Root: HKCU; Subkey: "Software\Classes\E2PSManualBuilder.Project\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Abrir o E2PS Manual Builder"; Flags: nowait postinstall skipifsilent
