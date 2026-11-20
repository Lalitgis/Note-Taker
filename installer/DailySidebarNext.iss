; Inno Setup script for Daily Sidebar Next.
; Build the app first (PyInstaller -> dist\DailySidebarNext), then compile this file,
; or just run build_installer.bat from the project folder.
;
; Installs for the current user only (no admin prompt) into
;   %LOCALAPPDATA%\Programs\Daily Sidebar Next
; and adds a Start menu entry, an optional desktop icon, optional start-at-sign-in
; and an entry in Settings > Apps for uninstalling.
; Your tasks and notes live in %APPDATA%\DailySidebarNext and are never touched by
; installing, updating or uninstalling.

#define MyAppName "Daily Sidebar Next"
#ifndef MyAppVersion
  #define MyAppVersion "2.0.1"
#endif
#define MyAppExe "DailySidebarNext.exe"

[Setup]
AppId={{8C3494D6-96C2-4221-AC9B-AE34B086E4B0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=Daily Sidebar
AppPublisherURL=https://github.com/Lalitgis/Note-Taker
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=DailySidebarNext-Setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExe}
UninstallDisplayName={#MyAppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
LicenseFile=..\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "startup"; Description: "Start {#MyAppName} when I sign in to Windows"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "..\dist\DailySidebarNext\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[Registry]
; Same value the app's own "Start with Windows" switch uses, so the two stay in sync.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "DailySidebarNext"; ValueData: """{app}\{#MyAppExe}"""; Tasks: startup; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "DailySidebarNext"; Flags: dontcreatekey uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Open {#MyAppName} now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /IM {#MyAppExe} /F"; Flags: runhidden; RunOnceId: "StopApp"
