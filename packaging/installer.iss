#define AppVersion "1.3.6"
[Setup]
AppId={{B87264A7-5236-4EA0-A416-EB0F8DE72468}
AppName=Groove Goblin LITE
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\GrooveGoblinLite
DefaultGroupName=Groove Goblin LITE
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=GrooveGoblin-LITE-1.3.6-Windows-x64-Setup
SetupIconFile=..\assets\GrooveGoblin.ico
UninstallDisplayIcon={app}\GrooveGoblinLite.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "..\dist\GrooveGoblinLite\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "portable.flag"

[Icons]
Name: "{group}\Groove Goblin LITE"; Filename: "{app}\GrooveGoblinLite.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Groove Goblin LITE"; Filename: "{app}\GrooveGoblinLite.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\GrooveGoblinLite.exe"; Description: "Open Groove Goblin"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var ExitCode: Integer; Report: String;
begin
  if CurStep = ssPostInstall then begin
    Report := ExpandConstant('{tmp}\groove-runtime-check.json');
    if not Exec(ExpandConstant('{app}\GrooveGoblinLite.exe'), '--self-test "' + Report + '"',
      ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ExitCode) then
      RaiseException('Could not check the bundled runtime. Reinstall the complete package.');
    if (ExitCode <> 0) or not FileExists(Report) then
      RaiseException('Groove Goblin runtime check failed. See %LOCALAPPDATA%\GrooveGoblinLite\startup-error.log.');
  end;
end;
