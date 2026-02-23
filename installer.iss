; installer.iss — Inno Setup 6 script for StreamFlow
; Generates a standard Windows installer: Next -> Next -> Finish

[Setup]
AppId={{B4F2A1C3-7D9E-4A3B-8C5F-1234567890AB}
AppName=StreamFlow
AppVersion=1.0
AppPublisher=Flow Cytometry Lab
AppPublisherURL=
AppSupportURL=
AppUpdatesURL=
DefaultDirName={autopf}\StreamFlow
DefaultGroupName=StreamFlow
PrivilegesRequiredOverridesAllowed=commandline dialog
AllowNoIcons=yes
OutputDir=output
OutputBaseFilename=StreamFlow_Setup_v1.0
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
MinVersion=6.2
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main application bundle — everything PyInstaller put in dist\StreamFlow\
Source: "dist\StreamFlow\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Placeholder so the db\ directory is created during install
Source: "db_placeholder\keep"; DestDir: "{app}\db"; Flags: ignoreversion

[Dirs]
Name: "{app}\db"

[Icons]
Name: "{group}\StreamFlow"; Filename: "{app}\StreamFlow.exe"; Comment: "Open StreamFlow - Flow Cytometry Manager"
Name: "{group}\Uninstall StreamFlow"; Filename: "{uninstallexe}"
Name: "{commondesktop}\StreamFlow"; Filename: "{app}\StreamFlow.exe"; Tasks: desktopicon; Comment: "Open StreamFlow - Flow Cytometry Manager"

[Run]
Filename: "{app}\StreamFlow.exe"; Description: "{cm:LaunchProgram,StreamFlow}"; Flags: nowait postinstall skipifsilent
