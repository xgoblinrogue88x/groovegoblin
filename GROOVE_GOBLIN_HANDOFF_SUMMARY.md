# Groove Goblin: one-page Codex handoff

**What it is:** Dark Windows GUI utility to fix music album metadata and organize album folders. Originated as an offline Van Halen *The Collection* / *The Collection II* FLAC tag fixer. Current v1.0 handles both FLAC and MP3 and searches MusicBrainz for general albums.

**Primary workflow:** Add multiple roots (multiple artists and albums) -> Analyze local tags -> optionally search MusicBrainz -> manually verify or change a match -> inspect read-only file/tag/folder preview -> explicitly Apply -> undo from JSON journal when necessary. The app stays open for the whole session.

**Naming convention:** Album folders: `Artist - Album Title (Year)`. Song names: `01 - Song Title.ext` only if explicitly enabled. Use original album release year by default, not a remaster/box-set year.

**Identity:** Groove Goblin, dark theme, headphone/vinyl goblin logo, neon green/purple branding. Assets are in `assets/`, including a Windows icon; the lettering is raster artwork, not a font package.

**Stack:** Python 3.10+, Tkinter/ttk, Mutagen, MusicBrainz HTTPS using Python standard library. Windows `.bat` launcher. Existing automated tests need ffmpeg. Main files: `GrooveGoblin.pyw`, `groove_core.py`, `musicbrainz_client.py`, `legacy_collections.py`.

**What exists:** FLAC/MP3 tag read/write, MusicBrainz suggestion/manual lookup, multi-root recursive scan, per-album approval, preview/export, folder renaming, optional filename renaming, write-ahead JSON undo, basic UI scaling/fullscreen, legacy Van Halen offline mappings.

**What is *not* there yet:** Standalone EXE, acoustic fingerprint identification, fully fluid responsive design, general mixed-album-folder splitting, support for other audio formats, verified Windows automated packaging, or full-file backups. Online results can be wrong or unavailable.

**Safety rules:** Scans/previews are read-only; confirmation before writes; preserve unrelated tags and album art; no overwrites or folder merges; account for changes since scan; never silently auto-apply uncertain matches; undo journal is not a replacement for backups.

**Recommended first Codex pass:** Run baseline tests, fix thread-safety and transaction/undo risks, test multi-artist FLAC+MP3 batches and metadata preservation, improve small-screen/remote layout, add reproducible Windows EXE build instructions. Then consider fingerprinting as an opt-in future enhancement.

**Current test status:** Five tests in `tests/test_groove.py` passed in a Linux/Python 3.13.5 environment with Mutagen + ffmpeg. That is not a Windows GUI/EXE certification.

**Next file:** `CODEX_START_HERE.md` contains the ready-to-paste Codex prompt. `AGENTS.md` supplies repository instructions.
