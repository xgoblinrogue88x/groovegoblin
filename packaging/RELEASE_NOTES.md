Groove Goblin 1.5.1 for Windows 10/11 x64

- GrooveGoblin.exe: the full desktop layout from 1.3.3 with current stability fixes.
- GrooveGoblinMobile.exe: launch Mobile Remote Mode directly for Android remote use.
- Full desktop includes Preview Changes, Now Playing, rename options and Save Report.
- Blue Switch to Mobile Remote Mode button directly below About in the desktop sidebar.
- Matching blue Switch to Desktop Mode button below Search All Albums Online in Mobile Remote Settings, with equal width and height.
- Button labels wrap to stay fully visible at narrow widths and native font sizes.

Switching launches the other EXE and closes the old window only after startup is
acknowledged. Active work blocks switching; unsaved Track Editor edits require
confirmation. Failed startup keeps the current window open. Switching starts a
fresh album/track list and never changes music. Both modes share undo/data.

The LITE product branding is retired. The complete goblin/logo Windows icon,
portrait workspaces, touch controls, scrolling, decoder, collision/stale-file
checks and undo improvements remain. Desktop defaults filename renaming off;
Mobile Remote retains independent rename checkboxes enabled by default.

Installer: run Setup.exe; both modes get Start menu shortcuts. Portable: extract
the entire ZIP and open either EXE. All Python/Tk, tagging/artwork/playback
libraries and FFmpeg are bundled. Keep the portable Data folder when updating.
Installed data is under %LOCALAPPDATA%\GrooveGoblin. An earlier mobile data folder
is reused when no desktop folder exists, without merging or overwriting records.
The installer upgrades the original full product; earlier mobile-only installs
remain separate and their data is preserved.

Publishing requires Windows regression tests, frozen runtime tests for both
modes, real cross-process handoff checks in both directions, silent install,
installed EXE launch and uninstall checks. Download SHA256 checksums are included.
Physical S25 Ultra touch gestures, audible output and 125%/150% native scaling
still need hands-on checks; automated playback uses a dummy output.

Application license: GPLv3. Notices and matching application/dependency sources
accompany both downloads. Supported-format limits remain documented in About.

The mobile workspace dropdown now uses an accented header, larger arrow, dark
popup and clear selection highlight. Its seven choices and navigation behavior
are unchanged. Sidebar sizing reserves room for the moved button and player.
