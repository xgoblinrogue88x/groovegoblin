from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH).parent
ffmpeg = root / 'build' / 'ffmpeg' / 'ffmpeg.exe'
if not ffmpeg.is_file():
    raise RuntimeError('Build bundled FFmpeg first; see packaging/README.md')
a = Analysis([str(root / 'packaging/windows_entry.py')], pathex=[str(root)],
    binaries=[(str(ffmpeg), 'ffmpeg')],
    datas=[(str(root / 'assets'), 'assets'), (str(root / 'GrooveGoblin.pyw'), '.')],
    hiddenimports=collect_submodules('mutagen') + ['groove_layout', 'groove_core',
        'groove_drop', 'groove_widgets', 'groove_version', 'groove_naming',
        'groove_track_editor', 'groove_track_drag', 'groove_windows_drag', 'groove_lite', 'groove_portrait', 'groove_modes', 'groove_settings', 'groove_suite', 'groove_album_lookup', 'groove_responsive',
        'groove_artwork', 'groove_manual', 'groove_formats', 'groove_decode',
        'groove_player', 'musicbrainz_client', 'legacy_collections', 'PIL.ImageTk'],
    hookspath=[], runtime_hooks=[], excludes=['tkinterdnd2'], noarchive=False)
# imageio's stock executable is deliberately replaced by our reproducible,
# LGPL FFmpeg build without external codecs. Keep only its Python wrapper.
a.datas = [item for item in a.datas if not item[0].replace('\\', '/').startswith('imageio_ffmpeg/binaries/')]
a.binaries = [item for item in a.binaries if not item[0].replace('\\', '/').startswith('imageio_ffmpeg/binaries/')]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='GrooveGoblin',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False,
    icon=str(root / 'assets/GrooveGoblin.ico'),
    version=str(root / 'packaging/version_info.txt'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='GrooveGoblin')
