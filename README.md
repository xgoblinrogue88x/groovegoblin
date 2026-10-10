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

1. Add Folders or Add Files, or drag folders or FLAC/MP3 files from Windows Explorer
   onto the main window. A drop that adds new items automatically scans the selected list. Duplicate-only
   and unsupported drops do not restart scanning; busy operations reject drops.
   Scan subfolders controls folder recursion, and Search online after scan
   controls MusicBrainz lookup. Add Folders / Add Files still wait for Start Scan.
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
- Track filename renaming defaults off and uses `## - Artist - Title`
  (for example, `01 - Van Halen - Jump.mp3`). Turn on Rename files and open
  the File Names preview before applying. Numbers come from track-number tags,
  padded to at least two digits; extensions are preserved. Each track uses its
  own artist, falling back to album artist or the approved album artist. Missing
  track numbers block renaming for that album and appear under Skipped.
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

27 tests passed on Linux/Python 3.12 with a virtual Tk display. They cover the
existing scan/apply/undo engine, FLAC/MP3 batches, collisions and stale files,
GUI scanning/approval/filtering, row and bulk inclusion, result selection,
window resizing from 800x600 through 1920x1080, launcher quote removal, explicit-file scope,
recursion, embedded artwork preservation through apply/undo, and mocked HTTPS
cover lookup/redirect checks, read-only folder drops, and native message
dispatch/handle cleanup with a simulated Windows API. Native callback checks
verify that drops, failed drops and peeked messages never invoke Tk; the Tk timer
processes queued paths later. Drop scanning checks cover one scan per new batch,
duplicate/unsupported/busy drops, recursion and lookup settings, and unchanged
music bytes. Filename checks cover
FLAC/MP3 rename-and-undo with folder moves, byte preservation, artist fallbacks,
missing track numbers, duplicate names, removed source folders and destinations
created after preview.

The Windows PowerShell launcher and native Windows message-loop subprocess
tests are skipped on Linux. The latter posts a real drop with temporary paths
and checks that the Tk main loop survives and adds files/folders and requests a scan from the Tk event loop. Actual Windows
launcher, Explorer drag-and-drop, Python 3.14/3.15 behavior and 125%/150% DPI appearance remain unverified.
The previous window-procedure-based drop implementation caused a fatal thread-state
error on the user’s Python 3.15 and has been removed. Actual Windows execution
of the native replacement remains unverified in this Linux environment; the
user confirmed Explorer drops work on their Python 3.15 installation before
the automatic-scan change.

No live MusicBrainz requests or real user media are used in these tests.

## Source

- `GrooveGoblin.pyw`: existing controller and background-task queue.
- `groove_layout.py`: reference layout and preview display.
- `groove_drop.py`: read-only folder adding and drop feedback.
- `groove_windows_drop.py`: queued native Windows drops; no window-procedure replacement
  or Tk calls inside native callbacks, and no extra dependency.
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
