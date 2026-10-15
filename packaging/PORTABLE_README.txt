Groove Goblin Suite 1.7 — Windows 10/11 x64

Desktop, LITE and Mobile open maximized on Windows, including when switching modes.
The suite launcher keeps its normal window size. Windows can still be restored and resized.

Extract the entire portable ZIP into a writable folder, then open:
  Launch Groove Goblin Suite.exe
The logo window offers Launch Desktop Mode, Launch LITE Mode and Launch Mobile Mode.

Or launch a mode directly:
  Groove Goblin Desktop Mode.exe — full layout, previews and Now Playing.
  Groove Goblin LITE Mode.exe — compact 1.3.7 layout with current stability fixes.
  Groove Goblin Mobile Mode.exe — portrait workspaces for Android remote use.

In every mode, Settings contains purple switches beneath Search All Albums Online.
Switching waits for the new window before closing the old one. Finish active work
first; unsaved Track Editor edits require confirmation before discarding. Lists
start fresh when switching; music is unchanged. All modes share undo/data.

Keep _internal, runtime-manifest.json and portable.flag beside the four EXEs.
Keep Data when updating: it contains your undo records and backups. Do not copy
only an EXE. Python, Tcl/Tk, tagging/artwork/playback libraries and FFmpeg are
bundled. No BAT file, system Python installation or administrator rights needed.

INSTALLER: Run Setup. Start menu shortcuts open the suite or each mode directly.
Installed undo/data records live under %LOCALAPPDATA%\GrooveGoblin, preserved
when uninstalling. Earlier mobile undo records are reused if no desktop data
folder exists. Existing system Python installations are untouched.

Missing/damaged runtime components produce a visible error and startup-error.log;
repair by rerunning Setup or extracting a complete fresh ZIP. Local editing works
offline; MusicBrainz and cover previews need internet. Remote phone use runs the
Windows application through Windows App, not an Android APK.

Application license: GPLv3 (LICENSE). ThirdParty holds dependency notices and
Sources holds matching application/dependency sources. The bundled LGPL FFmpeg
build excludes GPL/nonfree options and external codecs. Reproducible Windows
build instructions are in the application source archive's packaging/README.md.

TRACK EDITOR FILE DRAG: Sort by Disc number, select tracks with Ctrl/Shift and
start dragging from any selected row into Explorer. Ctrl copies; Shift moves;
Esc cancels. Save/discard selected unsaved edits first. Playback stops to release
locks. Explorer handles collisions and file-move undo. Same-volume paths update;
if a moved file cannot be followed, add its destination folder to reload it.
