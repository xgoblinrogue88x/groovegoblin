# Codex instructions for Groove Goblin

## Context and priorities

You are maintaining **Groove Goblin**, a dark Windows music tagger/organizer written in Python with Tkinter, Mutagen, and MusicBrainz. Work from the existing source. Keep changes scoped and testable. Do not replace the GUI/framework or redesign the architecture unless you first justify why the existing implementation cannot meet a requirement.

Primary user requirements:

1. One all-in-one **Windows GUI** that stays open across scanning, online lookup, manual matching, previews, applying, and undo.
2. A truly usable dark layout when maximized, resized, scaled, and viewed over remote desktop at smaller resolutions.
3. Preserve existing **Groove Goblin** branding (musical goblin icon, logo/wordmark, accent colors).
4. Select and process multiple albums from multiple artists in one batch, with individual inclusion/exclusion and manual corrections.
5. Search MusicBrainz manually if the automatic album match is wrong. Never silently accept uncertain matches.
6. Keep `Artist - Album Title (Year)` as the default album-folder preset, with selectable file/folder presets and Windows-safe naming.
7. Support the formats documented in docs/formats.md, preserving unrelated tags/art and source audio without transcoding the library. Raw AAC/PCM have limited operations; CDA is a CD reference.
8. Keep read-only preview, clear confirmation, robust collision detection, and undo.

## Protect the user's music

- **Scanning, searching, and previewing are read-only.** Write only after an explicit user action and confirmation.
- Don't send music files, fingerprints, paths, or personally identifying data online without the user's explicit choice and clear explanation. Current MusicBrainz searches transmit artist/title lookup text, not the audio file.
- The user explicitly requested verified song-title updates in all three modes. Organizer apply may update TITLE only from a matching MusicBrainz tracklist after approval and apply confirmation; preserve title preview and targeted undo. The user also authorized verified TRACKNUMBER updates, accepted album names and year-only dates in 1.8.2, with preview and targeted undo. The user authorized artist and album-artist updates and filling all six blank metadata fields in 1.8.3, including approved filename-derived values. Preserve per-track artists on compilations and read back writes before reporting success. Do not modify album artwork, ReplayGain, comments, or arbitrary other tags when changing album/year. FULL defaults file renaming OFF. The user explicitly requested Mobile Remote Mode with file/folder renaming ON by default (independently switchable) and album/year replacement ON; preserve its apply confirmation and undo journal.
- Keep the default folder naming `Artist - Album Title (Year)` and prefer original album release year; explicit user-selected presets may change the layout. Preserve legacy Van Halen mappings unless a test establishes a specific correction.
- Do not overwrite or merge into occupied destination folders. Detect case-insensitive collisions, nested folder conflicts, and changed files since scan. If in doubt, skip with a clear error.
- Manual Track Editor edits may change explicitly selected title/artist/track/disc/album/year fields, filenames and front artwork after review and confirmation. Preserve all other tags/pictures and support multi-selection.
- Manual saves make full-file undo backups; organizer operations retain targeted metadata journals. Keep playback stopped/unloaded during writes.
- Preserve an auditable undo record before mutations. Handle partial failure/restart; be honest that undo is not a complete backup. Don't delete user media to resolve conflicts.
- When changing write/undo code, add tests using temporary files. Never run write tests on user libraries.
- Treat untrusted metadata and API responses as untrusted text. Sanitize Windows path components and avoid shell injection.

## Engineering guidance

- Source modules: `GrooveGoblin.pyw`, `groove_core.py`, `musicbrainz_client.py`, `legacy_collections.py`.
- Dependencies: Python 3.10+, Tkinter, Mutagen, Pillow, pygame-ce, imageio-ffmpeg; Tkinter from standard Windows Python. FFmpeg decodes temporary listening copies in a worker, never replaces source audio. System ffmpeg is also used to generate disposable test files.
- Keep GUI work responsive. Tkinter widgets/variables must only be manipulated by the UI thread; communicate from background workers using the existing queue or a safer equivalent.
- MusicBrainz has a public rate limit. Retain timeouts, caching, appropriate User-Agent, and conservative lookup. Missing internet must not block local scanning/manual tagging.
- Maintain keyboard accessibility and horizontal/vertical scrolling where content exceeds a small screen. Test at 800x600, 1024x768, and 1920x1080, including Windows 125%/150% scaling; avoid obscuring the Apply/Undo controls.
- Keep error messages actionable and log full tracebacks without silently closing.
- Standalone Windows packaging is a future goal. Add reproducible packaging scripts and clear instructions. Do not claim a compiled EXE works until built/tested on Windows.

## Validation and delivery

- Before edits, run: `python -m unittest discover -s tests -v` with Mutagen and ffmpeg installed.
- After each change, rerun tests. Add coverage for any identified bug or new feature. Use mocked MusicBrainz responses for deterministic tests.
- Validate scan -> approve/adjust -> preview -> apply -> undo on both FLAC and MP3, using temporary files.
- Test no-write behavior in scans/previews; existing-folder conflicts; case-insensitive path conflicts; canceled work; stale scan; partial failures; unknown/missing original years; multi-artist batches; and preserving cover art/unrelated metadata.
- Explain any untested Windows-specific behavior. Do not label mockups as real GUI screenshots.
- Summarize modifications and remaining risks; include commands for validation and reproducible Windows run/build steps.

## Constraints

- Keep dependencies minimal; do not add a paid API, subscription, or online account requirement.
- Do not commit any real music/audio assets, API secrets, logs, user paths, `__pycache__`, or generated binaries.
- Logo/art assets in `assets/` are intended to remain in the app; these are raster graphics, **not a distributable font file**.
- Review `LICENSE_NOTES.txt` and dependency licensing before any public release; don't invent licensing claims.

## Groove Goblin Suite 1.6 modes

The suite launcher offers Desktop, LITE (the 1.3.7 compact layout), and Mobile
(the portrait layout formerly called Mobile Remote Mode). Each has a separately
named EXE. The full Desktop layout remains the source default. All mode switches
belong only in Settings under Search All Albums Online, purple with white text.
Keep the readiness handshake so failed startup preserves the current window;
block mode changes during active work and confirm before discarding unsaved
edits. All modes share undo/data and current stability fixes. Internal is_lite
means either compact mode; only Mobile installs the portrait controller.
