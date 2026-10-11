# Changelog

## 1.2.2

- Added multiple album-row selection with Ctrl-click, Shift-click and Ctrl+A.
- Added Remove Selected and Delete to remove albums from the current list without rescanning or changing files.
- Preserved remaining approvals, search results, selections and preview state after removal.
- Added consistent mouse-wheel scrolling over tables, headers and scrollbar gutters; Shift+wheel scrolls horizontally in Track Editor.
- Added a matching scrollbar and wheel support to Logs / Undo.

## 1.2.1

- Removed the branding caption and enlarged the sidebar logo.
- Gave the format-limits note a full-width footer to prevent clipping.
- Replaced the About message box with a styled window and clearer format/Undo sections.

## 1.2.0

- Added container-aware tagging/artwork for WAV, AIFF, ALAC/M4A, APE, WavPack,
  Ogg/Vorbis, WMA, Opus and DSF/DFF alongside existing FLAC/MP3.
- Expanded scans, file pickers, Explorer drops and cover previews to the shared
  format list, with aliases for common container extensions.
- Added filename-only editing/playback for raw AAC and PCM; PCM playback requires
  declared sample settings. CDA is recognized as a read-only CD track reference.
- Added cancellable background decoding to temporary listening copies for
  additional playback formats, leaving source files unchanged.
- Added container-specific organizer snapshots and retained full-file manual Undo.
- Documented codec/container distinctions, playback limits and validation scope.

## 1.1.1

- Matched Track Editor to the main app with rounded panels, icon toolbar cards,
  alternating track rows, green selection/staging accents and a framed player.
- Replaced raised scrollbars with slim rounded dark thumbs throughout the tables
  and manual review dialog; styled playback sliders with green handles.
- Kept controls visible at the 800×600 minimum size.

## 1.1.0

- Added eight filename and seven album-folder naming presets with live previews.
- Added Track Editor for individual and multi-selection edits to filename,
  title, artist, album artist, album, track, disc and year.
- Added local front-cover selection/removal while preserving other pictures.
- Added streamed FLAC/MP3 playback with pause, previous/next, stop, volume,
  seeking and elapsed/total time.
- Added detailed manual-save review, full-file backups and byte-for-byte Undo.
- Kept loaded editor paths synchronized with organizer renames and Undo.
- Fixed sidebar caption clipping and retained compact layouts down to 800×600.
- Added shared version information to the sidebar, window title and About.
- Retained queued native Explorer drops and automatic scanning on drop.
