#define AppVersion "1.3.3"
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
OutputBaseFilename=GrooveGoblin-1.3.3-Windows-x64-Setup
SetupIconFile=..\assets\GrooveGoblin.ico
UninstallDisplayIcon={app}\GrooveGoblin.exe
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
Name: "{group}\Groove Goblin"; Filename: "{app}\GrooveGoblin.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Groove Goblin"; Filename: "{app}\GrooveGoblin.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\GrooveGoblin.exe"; Description: "Open Groove Goblin"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var ExitCode: Integer; Report: String;
begin
  if CurStep = ssPostInstall then begin
    Report := ExpandConstant('{tmp}\groove-runtime-check.json');
    if not Exec(ExpandConstant('{app}\GrooveGoblin.exe'), '--self-test "' + Report + '"',
      ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ExitCode) then
      RaiseException('Could not check the bundled runtime. Reinstall the complete package.');
    if (ExitCode <> 0) or not FileExists(Report) then
      RaiseException('Groove Goblin runtime check failed. See %LOCALAPPDATA%\GrooveGoblin\startup-error.log.');
  end;
end;
