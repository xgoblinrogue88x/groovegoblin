Groove Goblin 1.3.3 for Windows 10/11 x64, launched with **GrooveGoblin.exe** and
the Groove Goblin icon. Python, Tcl/Tk, tagging/image/audio libraries and FFmpeg
are bundled. No BAT launcher or separate Python/FFmpeg installation is required.

- **Setup.exe:** installs for your Windows account and creates a Start menu shortcut.
- **Portable.zip:** extract the complete ZIP into a writable folder and open GrooveGoblin.exe.
- **SHA256SUMS.txt:** checksums of both downloads.

Keep the portable `Data` folder when updating: it contains undo records and
backups. Installed app data is under `%LOCALAPPDATA%\GrooveGoblin` and survives
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
