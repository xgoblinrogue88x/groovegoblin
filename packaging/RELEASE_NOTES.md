Groove Goblin 1.8.3: fill and update embedded title, album, year, track, artist
and album artist in every mode. Blank numbered Artist - Title files can provide
reviewable hints. Tag writes are read back before renames/success reporting;
failures stop with an undo journal. Tag writing OFF explicitly means rename-only.
Existing audio, artwork and unrelated tags remain intact. Raw AAC/PCM/CDA retain
their documented limitations.

Groove Goblin 1.8.2 updates accepted album tags, year-only dates (YYYY),
verified song titles and track numbers in Desktop, LITE and Mobile. Unique song
titles can identify missing/incorrect numbers; verified positions remain the
fallback. Matching editions must agree. Preview and confirmation include number
changes, naming presets use corrected numbers, and Undo restores previous
numbering, full dates, titles and album names. Unrelated tags/art/audio remain
intact. Verification alone stays read-only; approve and Apply to write.

Groove Goblin Suite 1.8.2 for Windows 10/11 x64

Desktop, LITE and Mobile open maximized on Windows, including when switching modes.
The suite launcher keeps its normal window size. Windows can still be restored and resized.

New in 1.8: verified song titles update embedded Title tags in Desktop, LITE and
Mobile. Verify with MusicBrainz or choose an album result, approve and apply.
Numbered tracks/discs and release track counts must fit. Matching editions must
agree, or existing titles must identify one tracklist. Ambiguous/missing
numbering and lookup failures keep titles unchanged, with an apply warning.
Desktop previews old/new titles; every mode confirms the update count. Naming
presets use corrected titles. Undo restores original, missing and multi-value
titles. Artist/track/disc tags, artwork, comments, ReplayGain and audio stay intact.

New in 1.7: drag selected tracks from Track Editor into Windows Explorer in all
three modes. Disc/track numbers sort numerically; disc sorting also orders the
tracks within each disc. Multi-selection stays intact when starting a drag.
Ctrl copies, Shift moves and Esc cancels. Explorer owns transfers, collision
dialogs and undo; selected unsaved edits must be saved/discarded first.

Playback stops for the transfer. Same-volume moves update editor paths while
preserving other tracks/staged edits and sort order. Files that cannot be
followed (such as moves to another drive) are removed from the editor; add their
destination to reload. Scan results for affected albums are invalidated so a
stale organizer plan cannot be applied. Existing tag/rename undo stays unchanged.
The new OLE work runs on an STA worker; no native drag callback calls Tk.

Four EXEs share one complete runtime:
- Launch Groove Goblin Suite.exe: full logo above three stacked purple launch buttons.
- Groove Goblin Desktop Mode.exe: full desktop layout with previews and Now Playing.
- Groove Goblin LITE Mode.exe: restored 1.3.7 compact layout with current fixes.
- Groove Goblin Mobile Mode.exe: portrait workspaces for Android remote use.

All mode switches are in Settings, below Search All Albums Online. Buttons are
purple with white text and show their full labels. Desktop offers Mobile then
LITE; Mobile offers Desktop then LITE; LITE offers Mobile then Desktop. There
are no switches on the main screens. Mobile Mode replaces Mobile Remote Mode.
Settings can scroll in short windows; the launcher and buttons resize.

All modes use the current scanning, playback, file-format, scrolling,
collision/stale-file protection, confirmation and undo code. Desktop defaults
file renaming off; LITE and Mobile retain independent rename checkboxes on by
default. Scanning/searching remain read-only. Only approved album/year and matched song-title fields are changed.

Switches and launcher choices close the old window only after the new EXE
acknowledges startup. Failed startup keeps the current window open. Active work
blocks switching; discarding unsaved Track Editor edits requires confirmation.
Switching starts fresh lists without changing music. All modes share undo/data.

Installer and portable ZIP include Python/Tk, tagging/artwork/playback libraries,
FFmpeg, complete logo icons, GPLv3 license, notices and matching sources. Extract
the entire portable ZIP and keep its Data folder when updating. Installed data
remains under %LOCALAPPDATA%\GrooveGoblin (or the preserved legacy mobile folder).
The installer upgrades the existing full product and refreshes its shortcuts.

Publishing requires Windows regression tests, four frozen EXE launch tests,
six real mode-switch routes and three suite-launch routes, installed EXE tests,
and uninstall checks. SHA256 download checksums accompany the packages.
Physical phone touch gestures, audible output and native 125%/150% scaling still
need hands-on checks; automated playback uses a dummy output.
