; installer.iss — Inno Setup script for StreamFlow
; Generates a standard Windows installer: Next → Next → Finish
;
; Requirements:
;   Inno Setup 6 — https://jrsoftware.org/isinfo.php
;   PyInstaller output at dist\StreamFlow\  (run build_installer.bat first)

#define MyAppName      "StreamFlow"
#define MyAppVersion   "1.0"
#define MyAppPublisher "Flow Cytometry Lab"
#define MyAppExeName   "StreamFlow.exe"
#define MyAppURL       ""

[Setup]
AppId={{B4F2A1C3-7D9E-4A3B-8C5F-1234567890AB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
; Install into Program Files by default; user can change
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Allow unprivileged users to install to their own AppData if no admin rights
PrivilegesRequiredOverridesAllowed=commandline dialog
AllowNoIcons=yes
; Output
OutputDir=output
OutputBaseFilename=StreamFlow_Setup_v{#MyAppVersion}
; Compression
Compression=lzma2/ultra64
SolidCompression=yes
; Appearance
WizardStyle=modern
WizardSmallImageFile=
; Minimum Windows version: Windows 10 (6.2 = Windows 8)
MinVersion=6.2
; 64-bit installer
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon";    Description: "{cm:CreateDesktopIcon}";    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startmenuicon";  Description: "Create a Start Menu entry";  GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; Main application bundle — everything PyInstaller put in dist\StreamFlow\
Source: "dist\StreamFlow\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

; Create the db\ directory so the app can find it on first launch
; (the launcher will create inventory.db inside it automatically)
Source: "db_placeholder\keep"; DestDir: "{app}\db"; Flags: ignoreversion

[Dirs]
; Make sure db\ exists in the installation directory
Name: "{app}\db"

[Icons]
; Start Menu shortcut
Name: "{group}\{#MyAppName}";        Filename: "{app}\{#MyAppExeName}"; \
    Comment: "Open StreamFlow - Flow Cytometry Manager"
; Start Menu — uninstall entry
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
; Desktop shortcut (optional, user selects in tasks)
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
    Tasks: desktopicon; Comment: "Open StreamFlow - Flow Cytometry Manager"

[Run]
; Offer to launch immediately after installation
Filename: "{app}\{#MyAppExeName}"; \
    Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove the database directory when uninstalling
; WARNING: this deletes all lab data — comment this out to keep data on uninstall
; Type: filesandordirs; Name: "{app}\db"

[Code]
// Custom page: show a friendly message explaining what is being installed
procedure InitializeWizard();
begin
  WizardForm.WelcomeLabel2.Caption :=
    'This will install StreamFlow – Flow Cytometry Laboratory Manager on your computer.' + #13#10 +
    #13#10 +
    'StreamFlow opens in your web browser (no internet connection required).' + #13#10 +
    'All your data is stored locally on this PC.' + #13#10 +
    #13#10 +
    'Click Next to continue.';
end;
