Groove Goblin LITE 1.3.4 for Windows 10/11 x64, launched with **GrooveGoblinLite.exe** and
the Groove Goblin icon. Python, Tcl/Tk, tagging/image/audio libraries and FFmpeg
are bundled. No BAT launcher or separate Python/FFmpeg installation is required.

- **Setup.exe:** installs for your Windows account and creates a Start menu shortcut.
- **Portable.zip:** extract the complete ZIP into a writable folder and open GrooveGoblinLite.exe.
- **SHA256SUMS.txt:** checksums of both downloads.

Keep the portable `Data` folder when updating: it contains undo records and
backups. Installed app data is under `%LOCALAPPDATA%\GrooveGoblinLite` and survives
uninstall. Runtime integrity checks report missing or damaged components;
reinstall/extract a fresh complete package to repair them.

This build passes the Windows regression suite, frozen GUI/FLAC decoding smoke
test, silent installer check, installed EXE launch and uninstall check before
these assets are published. Automated playback uses a dummy audio output; audible
speaker output and 125%/150% display scaling still need hands-on verification.
Supported-format limits remain those documented in About, including raw PCM
configuration and CDA references.

Application license: GPLv3. Dependency notices and corresponding application,
Mutagen, pygame-ce, FFmpeg and other source archives accompany both packages.

LITE layout: six actions in one top row; expanded album and search lists;
Selected Album Details moves to the top of the right rail. Preview Changes,
Now Playing, Rename Options and Save Report are removed from the interface.
File and folder renaming, album/year tag replacement and undo journaling remain
on, with explicit confirmation and validation before writing music.
The original full 1.3.3 installer is preserved as a separate release.
