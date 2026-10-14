Groove Goblin LITE 1.4.0 — portrait remote desktop support for Windows App on Android.

Open **GrooveGoblinPhone.exe** for the touch layout and a portrait window.
The installer adds a **Groove Goblin Phone** Start menu shortcut. The normal
GrooveGoblinLite.exe automatically adapts narrow or portrait windows, and
Settings > Layout lets you select Auto or Phone. Both EXEs share the bundled
runtime, music lists and persistent undo data.

- Touch navigation replaces the sidebar; scan actions use two rows.
- Albums appear as readable cards with Select Multiple.
- Albums, Match, Results and Options each have a full-width workspace.
- Track Editor has Tracks / Tags & Artwork tabs, Select All and a scrolling form.
- Matching forms, settings, Verify All and manual-save review fit phone widths.
- Auto restores the desktop layout when widened; minimum window is 360×540.

This is a Windows application used remotely, not an Android APK. Windows App
must display the app window or use portrait/dynamic session resolution; the
program cannot change the remote client's desktop resolution. Phone EXE also
works when the remote session reports a landscape display.

Python, Tcl/Tk, libraries and FFmpeg are bundled; no separate installations or
BAT launcher needed. Installer: run Setup.exe. Portable: extract the entire ZIP,
keep its files together, and open either EXE. Preserve portable Data when updating.
Installed data is in %LOCALAPPDATA%\GrooveGoblinLite and survives uninstall.

Scanning and searching are read-only. Applying changes still requires your
confirmation, matching validation and collision/stale-file checks. Independent
rename toggles and undo remain available. Format limits are documented in About.

Publication requires Windows regression tests, both frozen EXE smoke tests,
bundled decoder tests, silent installation, installed EXE launch and uninstall.
Device-specific Android remote touch gestures and physical S25 Ultra usability
still require hands-on verification. Audio checks use a dummy output.

Application: GPLv3. Dependency notices and matching source archives accompany
both packages. The full-logo Windows icon is preserved.
