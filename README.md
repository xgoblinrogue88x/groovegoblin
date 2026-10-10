# Groove Goblin

Windows desktop music tagger and organizer, using Python 3.10+, Tkinter, Mutagen
and Pillow. The supplied design reference guides the layout and styling:
large branded sidebar, icon toolbar, albums and preview together, and a compact
right rail for options, cover artwork, album details and online results.

![Running application with generated test music and mocked lookup results](docs/interface-linux.png)

This screenshot shows the actual application on a Linux virtual display, using
12 disposable test files, generated test covers and mocked MusicBrainz results.
It is not a mockup or a screenshot of the user's music. Windows fonts and DPI
rendering still need to be checked on Windows.

## Run on Windows

Extract the whole project into a new writable folder. Double-click
`START_GROOVE_GOBLIN.bat`. The launcher finds an installed Python, checks whether
it can open a Tk window, installs Mutagen and Pillow if needed, and runs the app
with the same exact interpreter. Leave its console open for error messages.

If Python detection fails, drag your installed `python.exe` onto the launcher.
See `LAUNCH_HELP.txt` for diagnostics. In Command Prompt inside the app folder:

```bat
"C:\path\to\python.exe" -m pip install --user -r requirements.txt
"C:\path\to\python.exe" GrooveGoblin.pyw
```

## Workflow

1. Add Folders or Add Files, or drag one or more folders from Windows Explorer
   onto the main window. Drops add folders without starting a scan; duplicates
   are ignored. Click Start Scan when ready. Scan subfolders controls folder recursion.
2. Start Scan. Local scanning and preview are read-only.
3. Select an album to see its local artwork and editable artist, album and year.
4. Search Online for MusicBrainz suggestions, then use a result's Select button,
   or edit the fields and click Approve Edit. Suggestions require approval.
5. Use row checkboxes to include or skip albums; the album header checkbox
   changes the visible albums together. Show only problems filters the table.
6. Inspect Folders, File Tags, File Names and Skipped preview tabs. Selected Only
   narrows the preview to the album currently being inspected.
7. Apply Selected Changes requires confirmation. Save Report exports the preview.
   Undo Last Apply uses the saved undo journal; View Logs shows that journal.

The settings page controls online search after scanning and provides batch
online lookup. MusicBrainz searches send artist/album lookup text, never audio.
Artwork is read from embedded FLAC/MP3 pictures or local cover/folder images,
loaded in background workers. Visible online results can load public Cover Art Archive previews over HTTPS,
using release IDs only. Artwork is held in memory; it is not written into music.
Missing artwork or internet access leaves a disc placeholder.

## Music safety and current limits

- FLAC and MP3 editing only. Other formats from the reference image are planned.
- Album folder names use `Artist - Album Title (Year)`.
- Track filename renaming defaults off and uses `01 - Song Title.ext`.
- Add Files processes only selected tracks. If a selection omits other audio in
  its folder, folder renaming is blocked; disable that option or scan the whole
  folder. This prevents moving unselected music as part of a folder rename.
- Grouping is always by music-containing directory. Mixed-album directories
  still need separation; the grouping control is read-only.
- Create artist folders and Move to new folders are disabled and marked planned.
- The checked undo-journal option is always on. It records targeted metadata and
  paths, not complete audio-file backups. Keep separate music backups.
- Existing destinations are not merged or overwritten. Unapproved albums block
  Apply until approved or excluded. Review MusicBrainz suggestions yourself.
- This is Python source, not a compiled EXE. Test on a copy of a small music
  folder before applying changes to important music.

## Small screens and keyboard

The whole program fits the window without an outer scrollbar, down to the
800×600 minimum window size. [See the compact view](docs/interface-compact-linux.png)
(captured on Linux with generated test music). Resizing adjusts panel sizes, artwork and spacing;
small windows use sidebar icons with hover labels and wrap the toolbar controls.
Album, preview and search lists scroll internally when they contain more rows
than fit. Apply, Undo and Report stay visible. Tab moves between controls, Space
activates checkboxes, arrow keys select table rows, and Enter opens the selected
album or chooses the selected online result. Ctrl +/- adjusts table text; F11
enters fullscreen and Esc exits it.

## Validation

Install requirements and have ffmpeg on PATH; tests generate disposable audio:

```bat
"C:\path\to\python.exe" -m unittest discover -s tests -v
```

18 tests passed on Linux/Python 3.12 with a virtual Tk display. They cover the
existing scan/apply/undo engine, FLAC/MP3 batches, collisions and stale files,
GUI scanning/approval/filtering, row and bulk inclusion, result selection,
window resizing from 800x600 through 1920x1080, launcher quote removal, explicit-file scope,
recursion, embedded artwork preservation through apply/undo, and mocked HTTPS
cover lookup/redirect checks, read-only folder drops, and native message
dispatch/handle cleanup with a simulated Windows API.

The real Windows PowerShell launcher test is skipped on Linux. Actual Windows
launcher, Explorer drag-and-drop, Python 3.14/3.15 behavior and 125%/150% DPI appearance remain unverified.
No live MusicBrainz requests or real user media are used in these tests.

## Source

- `GrooveGoblin.pyw`: existing controller and background-task queue.
- `groove_layout.py`: reference layout and preview display.
- `groove_drop.py`: read-only folder adding and drop feedback.
- `groove_windows_drop.py`: native Windows folder drops; no extra dependency.
- `groove_responsive.py`: live window sizing and compact layouts.
- `groove_widgets.py`: small Tk canvas widgets, vector icons and virtual tables.
- `groove_artwork.py`: background local and public cover-preview loading.
- `groove_core.py`: scanning, preview, tag edits, moves and undo engine.
- `musicbrainz_client.py`: MusicBrainz lookup and rate limiting.
- `legacy_collections.py`: existing Van Halen collection mappings.
- `Launch-GrooveGoblin.ps1`: exact-interpreter Windows startup and diagnostics.
- `assets/`: original branding.

`GUI_Preview.png` is the original mockup; the image above is the running app.
The handoff documents describe a broader roadmap, not completed features.
Read `LICENSE_NOTES.txt` before public redistribution.
