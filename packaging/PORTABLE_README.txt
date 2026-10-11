Groove Goblin LITE 1.3.5 — Windows 10/11 x64

PORTABLE: Extract the entire ZIP into a writable folder. Open GrooveGoblinLite.exe
(the goblin icon). Keep _internal, runtime-manifest.json and portable.flag
alongside it. No Python, pip, FFmpeg installation, BAT file or admin rights
are needed. Keep Data when updating: it contains your undo records/backups.

INSTALLER: Run the Setup EXE. It installs for your Windows account and creates
a Start menu shortcut to GrooveGoblinLite.exe. Installed app data/undo records are
under %LOCALAPPDATA%\GrooveGoblinLite, preserved when uninstalling.

The bundled runtime is checked at startup. Missing or damaged components
produce a visible error and startup-error.log; repair by rerunning Setup or
extracting a fresh complete ZIP. Do not copy only the EXE. Existing system
Python installations are untouched. Local editing works offline; online album
lookup and cover searches need internet. Device/audio drivers remain Windows'
responsibility. Test playback before applying changes to your library.

Application license: GPLv3 (LICENSE). Dependency notices: ThirdParty.
Matching application/dependency source archives: Sources. FFmpeg is compiled
without GPL/nonfree options or external codec libraries; its configuration and
LGPL license accompany its matching source. Build instructions are in the
application source archive's packaging/README.md.
