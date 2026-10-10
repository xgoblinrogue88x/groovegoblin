GROOVE GOBLIN 1.0 - Music Metadata Tagger & Batch Organizer
============================================================

WINDOWS QUICK START
-------------------
1. Extract the ENTIRE ZIP into a normal, writable folder (for example, Desktop\Groove Goblin).
2. Double-click START_GROOVE_GOBLIN.bat. Do not run the program from inside the ZIP.
3. This version requires Python 3.10+, Tkinter, and the free Mutagen package.
   The launcher checks your actual runtime and installs Mutagen if missing.
   If startup fails, read LAUNCH_HELP.txt and copy the visible console error.
4. Click + Add folder to add your first artist or album root. Repeat for other roots.
5. Click Analyze. The scan is READ-ONLY. Folders are scanned recursively.
6. With "Auto-search online after scan" checked, the program will contact MusicBrainz
   to suggest artist/album/year. Large collections can take a while due to API rate limits.
7. Double-click an album row, review or correct the fields on Manual Match / Online Lookup,
   then click "Save & approve match". You may also search MusicBrainz and select a result.
   The special Van Halen The Collection I & II disc mappings are recognized offline.
8. Open Preview Changes. Check the album name, original year, and destination folder names.
9. Click "Apply Previewed Changes" and confirm. This is the first point where files are changed.
10. Logs & Undo can reverse the LAST available batch using the saved tag snapshots.

FEATURES
--------
- FLAC and MP3 files, batches from multiple artists/albums, nested folder traversal
- MusicBrainz release-group search and conservative track-title-based suggestions
- Individual manual edit/search/approval when an online guess is wrong
- Original release-group YEAR by default, not the date of the particular remaster
- Artist - Album Title (Year) folder naming (Windows-invalid characters sanitized)
- Optionally rename song files as "01 - Song Title.flac/mp3" (OFF by default)
- Update album and year tags while retaining unrelated tags/artwork
- Read-only preview; changes require explicit confirmation
- Undo journal saves ORIGINAL TARGETED METADATA VALUES and original folder/file names
- Dark-mode Tk GUI; resize/maximize; F11 fullscreen, Esc exit fullscreen, Ctrl +/- zoom text
- No account or MusicBrainz API key needed

IMPORTANT SAFETY / LIMITATIONS
------------------------------
* Not every album can be identified automatically. Most ambiguous matches require manual
  approval. Do not approve a wrong match. Album release-group dates can occasionally be
  missing or inaccurate in MusicBrainz; edit the year manually in that situation.
* MusicBrainz lookup requires internet and follows approx. one request/second.
* The original TITLE, TRACKNUMBER, ARTIST, album art and audio content are not intentionally
  changed by tag updates. Changing FLAC/MP3 tags changes the file bytes/size, not the audio.
* Undo journals are in the program's Logs folder. They store only the edited tag fields and
  file/folder paths, NOT full copies of audio files. Keep your own music backup for major edits.
* This is a WINDOWS desktop app (works with Windows Remote Desktop/remote-control software),
  NOT a web or phone app. For smaller screens use tabs, window resize and text zoom.
* Each music-containing directory is treated as ONE album. A directory containing different
  albums mixed together must first be separated or it will be considered one album.
* FLAC and MP3 only in this first release. It does not modify M4A, OGG, WAV, WMA, etc.
* Existing output folders are never merged/overwritten. Changed/missing files are rejected
  at apply time. Nested album-containing folders are blocked from being renamed together.
* If the app crashes mid-apply, open Logs & Undo to use the recorded partial journal.
* A metadata edit that occurs outside Groove Goblin after apply is NOT tracked. Restoring
  Groove Goblin's saved fields could overwrite later changes to those same fields.
* Keep this folder writable; Logs needs to be able to save undo records.
* The first version is shipped as source + Windows launcher, NOT a standalone .exe.

MUSICBRAINZ
-----------
Open music encyclopedia/data source: https://musicbrainz.org/
API documentation: https://musicbrainz.org/doc/MusicBrainz_API
MusicBrainz data is community maintained. Groove Goblin is not affiliated with MusicBrainz.

SUPPORT / DIAGNOSTICS
---------------------
If launch fails, open Command Prompt in this extracted folder:
    py -3 --version
    py -3 -m pip show mutagen
    py -3 GrooveGoblin.pyw
The last command shows a Python traceback in the console if the application cannot start.

VERSION 1.0
