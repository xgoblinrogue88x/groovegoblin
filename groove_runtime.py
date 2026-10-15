"""Separate immutable bundled resources from persistent undo/startup records."""
import os
import sys
import hashlib
import json
from pathlib import Path


def resource_dir():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))


def data_dir():
    if not getattr(sys, 'frozen', False):
        return Path(__file__).resolve().parent
    executable_dir = Path(sys.executable).resolve().parent
    if (executable_dir / 'portable.flag').is_file():
        target = executable_dir / 'Data'
    else:
        base=Path(os.environ.get('LOCALAPPDATA', Path.home()))
        target=base/'GrooveGoblin'
        # Preserve existing mobile undo records when there is no full-app data.
        if not target.exists() and (base/'GrooveGoblinLite').is_dir():target=base/'GrooveGoblinLite'
    target.mkdir(parents=True, exist_ok=True)
    # Fail visibly if a portable folder is read-only; never silently relocate undo.
    import tempfile
    with tempfile.TemporaryFile(dir=target):
        pass
    return target


def configure_ffmpeg():
    if getattr(sys, 'frozen', False):
        binary = resource_dir() / 'ffmpeg' / 'ffmpeg.exe'
        if not binary.is_file():
            raise RuntimeError('Bundled FFmpeg is missing. Extract the complete portable ZIP or reinstall Groove Goblin.')
        os.environ['IMAGEIO_FFMPEG_EXE'] = str(binary)
        return binary
    import imageio_ffmpeg
    return Path(imageio_ffmpeg.get_ffmpeg_exe())


def verify_payload():
    if not getattr(sys, 'frozen', False):
        return
    root = Path(sys.executable).resolve().parent
    manifest = json.loads((root / 'runtime-manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest.items():
        path = root / name
        if not path.resolve().is_relative_to(root):
            raise RuntimeError('Invalid package manifest path.')
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        if digest.hexdigest() != expected:
            raise RuntimeError('A bundled component is damaged: ' + name +
                               '. Reinstall or extract a fresh complete portable ZIP.')
