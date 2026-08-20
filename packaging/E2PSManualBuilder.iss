; Inno Setup 6 script for E2PS Manual Builder V2.
; The V2 installer uses a separate application identity and directory so it
; never tries to overwrite or delete an executable from the legacy install.

#define AppName "E2PS Manual Builder V2"
#define AppVersion "2.0.0"
#define AppPublisher "E2PS"
#define AppExeName "E2PSManualBuilder.exe"
#define AppId "{{8F8D1D24-8E5A-4E4E-9B3E-6D7A2B0C4F91}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\E2PS Manual Builder V2
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\release
OutputBaseFilename=E2PS-Manual-Builder-V2-Setup-{#AppVersion}
SetupIconFile=..\manual_builder\assets\e2ps.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
CloseApplications=yes
CloseApplicationsFilter={#AppExeName}
RestartApplications=yes
ChangesAssociations=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\E2PS Manual Builder\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\.e2ps"; ValueType: string; ValueName: ""; ValueData: "E2PSManualBuilder.Project"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\E2PSManualBuilder.Project"; ValueType: string; ValueName: ""; ValueData: "E2PS Manual Builder Project"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\E2PSManualBuilder.Project\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"
Root: HKCU; Subkey: "Software\Classes\E2PSManualBuilder.Project\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch E2PS Manual Builder V2"; Flags: nowait postinstall skipifsilent
