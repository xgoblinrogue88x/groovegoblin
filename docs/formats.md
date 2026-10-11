# Audio formats in Groove Goblin 1.2.4

Add Files, folder scans, Explorer drops, Track Editor and cover previews share
one format list. A filename extension is checked against the actual container;
renaming an unrelated file to `.wav` does not make it a WAV file.

| Format | Tags and front artwork | File/folder naming | Playback |
| --- | --- | --- | --- |
| WAV (`.wav`, `.wave`) | ID3 in the WAV container | Yes | Yes |
| AIFF (`.aiff`, `.aif`, `.aifc`) | ID3 in the AIFF container | Yes | Yes |
| FLAC (`.flac`) | Vorbis comments / FLAC pictures | Yes | Yes |
| ALAC (`.alac`, normally `.m4a`) | MP4 tags and covers | Yes | Yes |
| Monkey's Audio (`.ape`) | APEv2 tags and cover art | Yes | Yes, when FFmpeg can decode the stream |
| WavPack (`.wv`) | APEv2 tags and cover art | Yes | Yes |
| MP3 (`.mp3`) | ID3 tags and pictures | Yes | Yes |
| M4A / audio MP4 (`.m4a`, `.mp4`) | MP4 tags and covers; AAC or ALAC audio | Yes | Yes |
| Ogg (`.ogg`, `.oga`) | Vorbis or Opus comments and pictures | Yes | Yes |
| WMA (`.wma`) | ASF attributes and pictures | Yes | Yes, for decodable, unencrypted audio |
| Opus (`.opus`) | Opus comments and pictures | Yes | Yes |
| DSD (`.dsf`, `.dff`, `.dsd`) | ID3 in DSF / DFF containers | Yes | Yes, when FFmpeg can decode the stream |
| Raw AAC (`.aac`) | Embedded tag editing unavailable | Filename/folder renaming only | Yes |
| Raw PCM (`.pcm`) | No standard embedded tag container | Filename/folder renaming only | Yes, with explicit sample settings |
| CD track reference (`.cda`) | Read-only reference; not an audio stream | No | Rip the CD to an audio file first |

DSD is a codec family: the supported files contain a DSF or DFF header, including
files named `.dsd`. Headerless DSD payloads are not imported as though they were
DSF. ALAC is also a codec: files named `.alac` must contain a valid MP4/M4A
container. Arbitrary codec data cannot acquire tags just by changing an extension.

Raw AAC and PCM are listed in Track Editor with a limitation notice. Tag and
artwork controls are disabled for those rows; filename editing stays available.
In Scan & Rename, turn off Replace album / year tags before renaming a folder that
contains raw AAC/PCM. Numbered filename presets still require track-number tags;
number-free formats can use the filename-derived title and approved artist.
CDA rows explain that CD ripping is needed and cannot be edited or played as
ordinary audio files. No CD ripping feature is included.

PCM playback asks for sample format, sample rate and channel count in one dialog.
The defaults are suggestions that must be confirmed; the program does not infer
raw recording settings. Settings apply to the selected PCM tracks for the current
session. A subsequent unconfigured PCM track requires its own settings.

MP4 cover arrays have no standardized front/back picture types. Groove Goblin
replaces or removes the first cover and preserves subsequent covers. The other
tag containers preserve explicitly typed non-front pictures and unrelated tags.
Organizer operations update only album/year; manual edits update only selected
fields. Neither converts the user's library. Filename extensions are retained.

## Playback

Compatibility playback is enabled by default on Windows. It streams a temporary
48 kHz stereo 16-bit WAV listening copy, bypassing the direct compressed-file
decoder. With compatibility off, MP3/FLAC stream directly; other formats use
temporary FLAC copies. These copies are decoded by the separately installed
imageio-ffmpeg package in a background worker. The player
shows Buffering while preparing a temporary stereo 48 kHz listening copy, then
provides pause, seeking, previous/next, stop and volume. DSD is decoded to PCM for
listening; the original DSD file is unchanged. This playback path is not a
bit-perfect DSD output mode. Audio Output provides device selection, reconnect
and a short test tone. If the tone is silent, check the chosen device and the
Python/Groove Goblin volume in Windows Volume mixer.

Listening copies use temporary disk space; at most four are cached and they are
removed when the player closes. Stop cancels preparation, and a canceled job
cannot start audio later. The source files are never replaced with these copies.
Unsupported, corrupt or encrypted codecs report an error without editing music.
FFmpeg's supported decoders vary by platform build. No music is uploaded.

## Validation and limits

Tests generate WAV, AIFF, AAC, ALAC, Ogg/Vorbis, Opus, WMA and WavPack using ffmpeg,
plus synthetic silent DSF/DFF streams. They check tags, covers, unrelated metadata,
renaming, organizer Undo, full-byte manual Undo and decoded-audio preservation.
Playback tests use SDL's dummy audio device and verify that original bytes stay
unchanged. Raw PCM uses declared sample settings; CDA fixtures test read-only
handling. APE tests use a synthetic container header to validate APEv2 operations;
an actual encoded Monkey's Audio playback file has not been tested here.

Actual Windows audio devices, Python 3.15 playback, DSD variants, encrypted WMA
and 125%/150% Windows DPI behavior remain unverified in this Linux workspace.
Container support does not guarantee that every codec variant can be decoded.

References: [Mutagen format support](https://mutagen.readthedocs.io/en/latest/),
[FFmpeg formats](https://ffmpeg.org/ffmpeg-formats.html),
[FFmpeg codecs](https://ffmpeg.org/ffmpeg-codecs.html), and
[imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg).
