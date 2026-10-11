GROOVE GOBLIN 1.1.0 - Music Tagger & Organizer

1. Extract the ENTIRE ZIP into a new writable folder. Do not run inside the ZIP.
2. Double-click START_GROOVE_GOBLIN.bat. Keep its console open for diagnostics.
   The launcher finds Python 3.10+ with Tk and installs missing dependencies:
   Mutagen, Pillow, pygame-ce. First installation needs internet.
3. Add Folders / Add Files, then Start Scan. Explorer drops auto-scan.
4. Review and approve album matches. Choose file/folder naming presets, inspect
   Preview Changes, then Apply Selected Changes and confirm.
5. Track Editor on the left allows individual and Ctrl/Shift batch tag edits,
   filename edits and local cover art. Stage Edits is read-only. Review & Save
   shows exact changes; Save Changes commits them with full-file undo backups.
6. Track Editor includes playback, pause, previous/next, stop, volume and seek.
7. Undo / Backups restores the last operation. Retain Logs and ManualBackups.

FLAC and MP3 only. Existing destinations are not overwritten. Organizer Undo
stores targeted tags/paths; manual Undo stores complete original files. Read
README.md for workflow, backup disk usage, controls and limits. This is Python
source with a Windows launcher, not a standalone EXE. About shows version 1.1.0.

Startup problems: see LAUNCH_HELP.txt. Send console error text for diagnostics.
