#define AppVersion "1.8"
[Setup]
AppId={{45092022-7647-4271-B6E0-FC30C3592945}
AppName=Groove Goblin
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\GrooveGoblin
DefaultGroupName=Groove Goblin
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=GrooveGoblin-1.8-Windows-x64-Setup
SetupIconFile=..\assets\GrooveGoblin.ico
UninstallDisplayIcon={app}\Launch Groove Goblin Suite.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "..\dist\GrooveGoblin\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "portable.flag"

[Icons]
Name: "{group}\Launch Groove Goblin Suite"; Filename: "{app}\Launch Groove Goblin Suite.exe"; WorkingDir: "{app}"
Name: "{group}\Groove Goblin Desktop Mode"; Filename: "{app}\Groove Goblin Desktop Mode.exe"; WorkingDir: "{app}"
Name: "{group}\Groove Goblin LITE Mode"; Filename: "{app}\Groove Goblin LITE Mode.exe"; WorkingDir: "{app}"
Name: "{group}\Groove Goblin Mobile Mode"; Filename: "{app}\Groove Goblin Mobile Mode.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Launch Groove Goblin Suite"; Filename: "{app}\Launch Groove Goblin Suite.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[InstallDelete]
Type: files; Name: "{app}\GrooveGoblin.exe"
Type: files; Name: "{app}\GrooveGoblinMobile.exe"
Type: files; Name: "{group}\Groove Goblin.lnk"
Type: files; Name: "{group}\Groove Goblin Mobile Remote Mode.lnk"
Type: files; Name: "{autodesktop}\Groove Goblin.lnk"

[Run]
Filename: "{app}\Launch Groove Goblin Suite.exe"; Description: "Open Groove Goblin Suite"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var ExitCode: Integer; Report: String;
begin
  if CurStep = ssPostInstall then begin
    Report := ExpandConstant('{tmp}\groove-runtime-check.json');
    if not Exec(ExpandConstant('{app}\Groove Goblin Desktop Mode.exe'), '--self-test "' + Report + '"',
      ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ExitCode) then
      RaiseException('Could not check the bundled runtime. Reinstall the complete package.');
    if (ExitCode <> 0) or not FileExists(Report) then
      RaiseException('Groove Goblin runtime check failed. See %LOCALAPPDATA%\GrooveGoblin\startup-error.log.');
  end;
end;
