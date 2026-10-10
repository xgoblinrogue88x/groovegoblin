# Product requirements: Groove Goblin

## User goal

Build a straightforward, dark, Windows desktop application to organize a large music collection without hand-fixing each album. It must support multiple artists and albums in one session, correcting inaccurate release information online or manually, with a safe preview and undo.

## Product identity

- **App name:** Groove Goblin.
- **Branding:** Distinctive goblin holding vinyl/using headphones. Neon green and purple elements on a dark background. Bundled icon `.ico` and PNG wordmark. Preserve the branding but prioritize readability and accessibility. The wordmark is an image, not an installable font.
- **Platform:** Windows 10/11 desktop; must be comfortable through remote desktop at varying screen resolutions and DPI scaling. Do not mistake this for a native mobile app.
- **Cost:** Free tools/libraries preferred; no subscription or paid API required.

## Non-negotiable UX

1. Keep **one program window** alive throughout add folders -> scan -> matches -> manual lookup -> preview -> apply -> undo.
2. Dark by default; clearly labeled buttons, readable tables, resizable panels, scrollbars, keyboard shortcuts, status and progress, cancellation for long lookups.
3. Multiple root folders; recursively discover supported audio, avoid duplicate scans of overlapping roots.
4. Show one album group per music-containing directory, with artist, current album tag, proposed album/year, track count, match provenance/confidence, and enabled/disabled state.
5. Online lookup through MusicBrainz, including manual search and choice of specific release group. Keep unverified matches in review status and show the evidence behind a suggestion.
6. Allow manually setting artist, album, and original four-digit release year. Year 2015 on remastered collections should be corrected to the **original album** year where appropriate; compilations/live albums have their own release year.
7. Show per-file changes to tags, names and target directories in a dry-run preview. Export report to text. No changes until explicit approval and apply confirmation.
8. Rename album directory to `Artist - Album Title (Year)` with Windows-safe sanitization. Track filename naming `01 - Song Title.ext` is opt-in, initially OFF.
9. Include/skip individual albums; process the remaining approved albums in one operation. Refuse unsafe writes and explain what is blocking a batch.
10. Undo the most recent apply using snapshots of affected fields and name/path changes. Present clear warnings for conflicts or incomplete undo. Do not advertise this as a full file backup.

## Metadata and lookup

- Initial write formats: **FLAC/Vorbis comments** and **MP3/ID3** only. Keep OGG, M4A, WAV, WMA as future features unless added and tested.
- Do not re-encode audio or discard cover artwork, comment tags, ReplayGain, track numbers, or other unrelated fields.
- Read artist/album artist, title, album, date/year, track/disc index. Handle absent/poor tags with clear review states.
- Online: current MusicBrainz client uses standard library HTTPS, rate limiting, in-memory caching, release-group search, and approximate track-name matching. Strengthen incorrect-match defenses. Offline scanning remains available if networking fails.
- Special offline Van Halen maps are legacy support, not a substitute for general matching.
- **Acoustic fingerprint matching is NOT part of v1.0**. It is a possible future feature, subject to privacy/disclosure and additional dependencies.

## Acceptance criteria for the next stable version

- Existing automated tests still pass; new regression tests cover cases addressed by Codex.
- GUI can be used and all primary actions reached at 800x600 and 1024x768 (scrolling permitted), 1920x1080, and 125%/150% DPI on Windows. At least one actual Windows visual/manual test is documented.
- The main window stays open from scan through apply; UI remains responsive during long online searches.
- Mixed FLAC/MP3 batch containing >=2 different artists and multiple albums can be scanned, individually corrected, previewed, applied, and undone.
- Unapproved/missing-year/ambiguous albums don't get written. Conflicts are shown before apply.
- All planned filesystem moves are tested for Windows case-insensitive collisions and stale-scan changes. No overwrite of an existing destination, audio deletion, or accidental merge.
- After updating ALBUM and YEAR/DATE, unrelated tags and album art are preserved to the greatest extent supported by Mutagen; test ID3v2.3 and v2.4 explicitly.
- Undo handles applied file/folder names, selected original tag values, and recoverable partial interruptions without silently clobbering newer user changes.
- Missing network or MusicBrainz errors degrade gracefully; no UI freezes, and local manual editing still works.
- A reproducible Windows source launcher is retained, and any `.exe` generation uses a documented Windows build step. Do not claim tested EXE before a real Windows run.

## Existing limitations/risks for Codex to audit

- Current GUI is Tkinter with fixed-height top bars, basic fonts, and notebooks. `zoom()` only rebuilds styles and may not resize all widgets; long controls may clip at smaller resolutions.
- `GrooveGoblin.pyw` accesses a Tkinter variable (`auto_lookup.get()`) within a worker thread. Move all Tk access to the main thread and use immutable worker arguments/queue messages.
- `groove_core.py` treats each directory containing audio as exactly one album. A folder mixing unrelated releases must be separated or explicitly handled.
- Undo is a JSON journal, not a copy of the files. Partial writes and metadata edits made outside the app after apply need careful safeguards.
- Original album release date from MusicBrainz is not always definitive, particularly reissues, compilations, imports, and ambiguous shared titles.
- Windows launcher has not been verified on the user's PC as part of this handoff. Verify Python Install Manager aliases and the chosen GUI interpreter.
- No end-to-end tests of live MusicBrainz interaction or a compiled Windows app exist in the current source.

## Suggested roadmap

**P0 | Reliability:** Audit UI thread safety, race handling, folder/file collision preflight, ID3v2.3/v2.4 preservation, journaling/partial undo, responsive layout. Add tests.

**P1 | Usability:** Better per-album review controls, multi-selection, visible match evidence, clearer preview differences, progress/cancel support, robust display scaling, Windows drag-and-drop if appropriate.

**P2 | Distribution:** Provide reproducible PyInstaller build steps for a one-folder or one-file portable Windows EXE; verify bundled assets and licensing. Consider real installer only after the portable build is solid.

**P3 | Smarter matching:** Improve MusicBrainz release-selection logic, cache/persistent match choices, optional album art lookup. Consider opt-in AcoustID/Chromaprint identification later, without surprise audio-data transmission.
