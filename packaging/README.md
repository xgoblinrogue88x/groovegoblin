# Groove Goblin 1.5 Windows packaging

The Windows workflow builds **GrooveGoblin.exe**, **GrooveGoblinMobile.exe**, a portable ZIP and a per-user
Inno Setup installer. CPython 3.12.10, Tcl/Tk, Pillow, Mutagen, pygame-ce/SDL and
FFmpeg travel with the application. It never runs pip on a user's PC or chooses
their system Python. PyInstaller's directory layout permits replacement of
dynamic SDL libraries. The application and packaged distribution use GPLv3;
dependency licenses retain their own terms.

## Reproduce the build

On Windows x64, install CPython 3.12.10 including Tcl/Tk, Inno Setup 6, and MSYS2
UCRT64 with GCC, make, curl, tar and diffutils. From a clean repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r packaging/requirements-build.txt
```

In a UCRT64 shell in that same root run `bash packaging/build_ffmpeg.sh`.
FFmpeg n8.0 is downloaded with a pinned SHA256 and built statically without
external libraries, network protocols, GPL or nonfree options. Its source and
configuration accompany the package; Python's imageio-ffmpeg wrapper uses this
binary, and the wheel's unrelated stock FFmpeg is excluded.

Back in PowerShell:

```powershell
$env:PATH = "$pwd\build\ffmpeg;$env:PATH"
$env:SDL_AUDIODRIVER = 'dummy'
$env:GROOVE_GOBLIN_TEST_AUDIO = '1'
python -m unittest discover -s tests -v
python packaging/build_windows.py
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" packaging/installer.iss
```

`dist` contains the installer and portable ZIP. The workflow also tests silent
installation, the installed EXE and uninstall before publishing build artifacts.
Successful runs also publish both downloads to GitHub Releases, with a tag
containing the source commit. An unsuccessful run provides no installer release.

## Runtime and data

`portable.flag` selects persistent `Data` beside the EXE; installed builds use
`%LOCALAPPDATA%\GrooveGoblin`. Neither uses PyInstaller's internal resource
directory for undo. Updating/uninstalling must preserve data and user media.
Both package types check the bundled files against `runtime-manifest.json` and
exercise Tk plus FFmpeg. Corruption requires reinstalling/extracting the package;
repair does not download arbitrary binaries or alter global Python.

`--self-test REPORT.json` launches the actual frozen Tk window, resizes it and
visits Scan, Track Editor, Album Lookup and Logs. Automated audio tests use SDL's
dummy driver. They establish decoding/playback control behavior, **not audible
output**. Listen on a real Windows output and check 125%/150% display scaling
before declaring the release fully validated. Native drop tests are included.

## Release review

Do not commit binaries. Preserve `ThirdParty`, `Sources` and all licenses when
redistributing. The package collects wheel license/notice files, exact PyPI
source distributions, CPython/Tcl/Tk notices and matching FFmpeg source. Review
the pygame wheel's bundled SDL/codec notices when updating dependencies. The
pinned wheel was audited against its upstream development packages: FreeType
2.11.1 and PortMidi DLLs match the pinned fallback package, libpng identifies
1.6.58, and the corresponding license texts and FreeType attribution are
collected explicitly. Repeat that audit when changing the pinned wheel.
Builds are unsigned unless a separate signing
process is configured. No signing identity or completed Windows test is implied
by the existence of these scripts.

Both modes share data. If no desktop data folder exists but an earlier mobile
installation has data, that location is reused without copying or overwriting.
The build tests both real EXEs through the readiness handshake in both directions
using packaging/test_mode_handoff.py, then installs/launches/uninstalls the package.
