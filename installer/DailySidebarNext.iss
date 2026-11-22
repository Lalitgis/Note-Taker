; Inno Setup script for Daily Sidebar Next.
; Build the app first (PyInstaller -> dist\DailySidebarNext), then compile this file,
; or just run build_installer.bat from the project folder.
;
; By default installs for all users into
;   C:\Program Files\Daily Sidebar Next   (Windows asks for admin permission once)
; The first page also offers "Install for me only", which needs no admin rights and
; installs into %LOCALAPPDATA%\Programs\Daily Sidebar Next instead.
; Adds a Start menu entry, an optional desktop icon, optional start-at-sign-in
; and an entry in Settings > Apps for uninstalling.
; Your tasks and notes live in %APPDATA%\DailySidebarNext and are never touched by
; installing, updating or uninstalling.

#define MyAppName "Daily Sidebar Next"
#ifndef MyAppVersion
  #define MyAppVersion "2.0.2"
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
PrivilegesRequired=admin
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
MinVersion=10.0
VersionInfoVersion={#MyAppVersion}
VersionInfoProductName={#MyAppName}
; The start-at-sign-in value is per user (HKCU) on purpose, like the app's own switch.
UsedUserAreasWarning=no

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
Filename: "{app}\{#MyAppExe}"; Description: "Open {#MyAppName} now"; Flags: nowait postinstall skipifsilent runasoriginaluser

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /IM {#MyAppExe} /F"; Flags: runhidden; RunOnceId: "StopApp"
