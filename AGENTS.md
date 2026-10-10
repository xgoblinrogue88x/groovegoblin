# Codex instructions for Groove Goblin

## Context and priorities

You are maintaining **Groove Goblin**, a dark Windows music tagger/organizer written in Python with Tkinter, Mutagen, and MusicBrainz. Work from the existing source. Keep changes scoped and testable. Do not replace the GUI/framework or redesign the architecture unless you first justify why the existing implementation cannot meet a requirement.

Primary user requirements:

1. One all-in-one **Windows GUI** that stays open across scanning, online lookup, manual matching, previews, applying, and undo.
2. A truly usable dark layout when maximized, resized, scaled, and viewed over remote desktop at smaller resolutions.
3. Preserve existing **Groove Goblin** branding (musical goblin icon, logo/wordmark, accent colors).
4. Select and process multiple albums from multiple artists in one batch, with individual inclusion/exclusion and manual corrections.
5. Search MusicBrainz manually if the automatic album match is wrong. Never silently accept uncertain matches.
6. Rename album folders exactly as `Artist - Album Title (Year)` with Windows-safe filename handling.
7. Support both FLAC and MP3, preserving unrelated tags/art, without transcoding.
8. Keep read-only preview, clear confirmation, robust collision detection, and undo.

## Protect the user's music

- **Scanning, searching, and previewing are read-only.** Write only after an explicit user action and confirmation.
- Don't send music files, fingerprints, paths, or personally identifying data online without the user's explicit choice and clear explanation. Current MusicBrainz searches transmit artist/title lookup text, not the audio file.
- Do not modify TITLE, TRACKNUMBER, ARTIST, album artwork, ReplayGain, comments, or arbitrary other tags when changing album/year. File renaming is an independent opt-in setting (default OFF).
- Keep folder naming `Artist - Album Title (Year)` and prefer original album release year. Preserve legacy Van Halen mappings unless a test establishes a specific correction.
- Do not overwrite or merge into occupied destination folders. Detect case-insensitive collisions, nested folder conflicts, and changed files since scan. If in doubt, skip with a clear error.
- Preserve an auditable undo record before mutations. Handle partial failure/restart; be honest that undo is not a complete backup. Don't delete user media to resolve conflicts.
- When changing write/undo code, add tests using temporary files. Never run write tests on user libraries.
- Treat untrusted metadata and API responses as untrusted text. Sanitize Windows path components and avoid shell injection.

## Engineering guidance

- Source modules: `GrooveGoblin.pyw`, `groove_core.py`, `musicbrainz_client.py`, `legacy_collections.py`.
- Dependencies: Python 3.10+, Mutagen; Tkinter from standard Windows Python; `ffmpeg` is only used by the supplied tests.
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
