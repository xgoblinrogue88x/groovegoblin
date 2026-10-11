# Naming presets

Version 1.1.0 offers fixed presets in the Rename Options dropdowns. The default
filename is `## - Artist - Title`; the default folder is `Artist - Album (Year)`.
Filename renaming remains off until selected. Changes appear in the preview and
require Apply confirmation.

These presets use familiar music-library conventions: track-number ordering,
artist/title names, album/year names, and disc prefixes for multi-disc albums.
The [beets path-format documentation](https://github.com/beetbox/beets/blob/master/docs/reference/pathformat.rst)
provides examples of numbered titles, album artist/album organization, and
multi-disc naming. These are practical conventions, not a popularity ranking.

| Filename preset | Example |
| --- | --- |
| ## - Artist - Title | 01 - Artist - Song.mp3 |
| ## - Title | 01 - Song.mp3 |
| ## Title | 01 Song.mp3 |
| Artist - Title | Artist - Song.mp3 |
| Title | Song.mp3 |
| Disc-## - Title | 2-01 - Song.mp3 |
| Disc-## - Artist - Title | 2-01 - Artist - Song.mp3 |
| Artist - Album - ## - Title | Artist - Album - 01 - Song.mp3 |

| Folder preset | Example |
| --- | --- |
| Artist - Album (Year) | Artist - Album (1997) |
| Artist - Album | Artist - Album |
| Artist - Year - Album | Artist - 1997 - Album |
| Artist - (Year) Album | Artist - (1997) Album |
| Album (Year) | Album (1997) |
| Year - Album | 1997 - Album |
| Album | Album |

`##` uses the track-number tag, padded to at least two digits. `Disc` uses the
disc-number tag. Required missing fields block that rename with an explanation;
number-free presets can rename tracks without track numbers. Track artist falls
back to album artist, then the approved album artist. The Album component uses
the approved album name. Extensions stay unchanged and Windows-invalid
characters are sanitized. Duplicate destinations are blocked.

Folders are renamed in their existing parent directory; presets do not create
artist trees or move music to another library. Each music-containing directory
is one album. Existing destinations are never merged or overwritten.
