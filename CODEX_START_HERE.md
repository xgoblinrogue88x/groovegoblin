# Paste this prompt into Codex

Continue development of the **existing** Groove Goblin Windows music tagger in this repository. Read `AGENTS.md`, `PROJECT_REQUIREMENTS.md`, and `README.md`, then inspect the Python files and the five existing tests before changing anything. Preserve the musical goblin branding and the core workflow.

## First task: turn the v1 prototype into a safer, more usable v1.1

1. **Establish a baseline:** install requirements; run `python -m unittest discover -s tests -v` (ffmpeg is needed to generate temporary test audio); briefly report the result and key architecture findings.
2. **Fix correctness first:** audit Tkinter main-thread safety and background-worker state. In particular, do not access `tk.BooleanVar` from a worker thread. Audit/prevent destructive path collisions and scan-to-apply races; improve partial-failure undo and preserve FLAC/MP3 unrelated tags/artwork. Write regression tests for each fixed issue.
3. **Improve the UI:** dark GUI should show all critical controls and permit scrolling at 800x600, 1024x768, and 1920x1080, including Windows DPI scaling and remote desktop; provide status/progress and cancel behavior. Keep the app open during Analyze -> Preview -> Apply -> Undo.
4. **Keep user requirements:** multiple root folders, multiple artists/albums per batch, MusicBrainz suggestions and manual album search, explicit per-album approval, read-only preview/export, FLAC+MP3 editing, folder naming `Artist - Album Title (Year)`, optional `01 - Song Title.ext` renaming default OFF, and undo history.
5. **Improve Windows distribution:** retain the Python launcher and add documented, reproducible Windows-only PyInstaller build scripts/config for a portable EXE including the logo/icon. If you cannot actually build/test on Windows, clearly mark that as unverified instead of claiming an EXE exists.
6. **Validate:** rerun automated tests plus new ones. Do not edit real user music or require live online tests. Provide changed-file summary, how to run, test results, and any Windows tests still needed.

## Important design constraints

- The existing code works and should be extended rather than discarded.
- Never change any audio/tags during scanning, matching or preview; require a separate apply confirmation.
- Do not overwrite or merge occupied folders and do not silently change uncertain albums.
- Preserve cover art, track titles, track numbers, artist, ReplayGain and other unrelated metadata. Keep original release years by default.
- No paid API or subscription dependency. Treat MusicBrainz data as suggestions, not guaranteed truth.
- No native phone app is required; this is a Windows desktop app accessed remotely as needed.
- A JSON undo journal is **not** an audio backup. Be explicit about this limitation.

After completing v1.1, recommend a short, prioritized next-iteration plan, but implement and test the task above first.
