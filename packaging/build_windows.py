"""Build from the repository root on Windows, after building FFmpeg with MSYS2."""
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import traceback
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def fetch_checked(url, destination, digest):
    with urllib.request.urlopen(url, timeout=120) as response:
        content = response.read()
    if hashlib.sha256(content).hexdigest() != digest:
        raise RuntimeError('Source archive checksum mismatch: ' + destination.name)
    destination.write_bytes(content)


def main():
    if sys.platform != 'win32' or sys.version_info[:2] != (3, 12):
        raise SystemExit('Build with 64-bit CPython 3.12 on Windows.')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm',
                    'packaging/GrooveGoblin.spec'], cwd=ROOT, check=True)
    app = ROOT / 'dist/GrooveGoblinLite'
    # The same frozen runtime selects its initial phone workspace by EXE name.
    # Keeping both beside _internal also makes the phone launcher portable.
    shutil.copy2(app / 'GrooveGoblinLite.exe', app / 'GrooveGoblinPhone.exe')
    bundled_decoders = [file.relative_to(app).as_posix() for file in app.rglob('*.exe')
                        if 'ffmpeg' in file.name.lower()]
    if bundled_decoders != ['_internal/ffmpeg/ffmpeg.exe']:
        raise RuntimeError('Unexpected FFmpeg payload; exclude the wheel binary before distribution: '
                           + repr(bundled_decoders))
    sources = app / 'Sources'; sources.mkdir()
    notices = app / 'ThirdParty'; notices.mkdir()
    shutil.copy2(ROOT / 'LICENSE', app / 'LICENSE')
    shutil.copy2(ROOT / 'LICENSE_NOTES.txt', app / 'LICENSE_NOTES.txt')
    shutil.copy2(ROOT / 'packaging/PORTABLE_README.txt', app / 'README.txt')
    subprocess.run(['git', 'archive', '--format=zip', '-o', str(sources / 'GrooveGoblin-source.zip'), 'HEAD'],
                   cwd=ROOT, check=True)
    shutil.copy2(ROOT / 'build/sources/ffmpeg-n8.0.tar.gz', sources)
    shutil.copytree(ROOT / 'build/ffmpeg', notices / 'FFmpeg', ignore=shutil.ignore_patterns('*.exe'))
    # Retain each installed wheel's notices and exact published sdist, with PyPI's SHA256.
    for name in ('mutagen', 'Pillow', 'pygame-ce', 'imageio-ffmpeg', 'pyinstaller'):
        dist = metadata.distribution(name)
        directory = notices / name; directory.mkdir()
        found = []
        for file in dist.files or ():
            if any(word in str(file).lower() for word in ('license', 'copying', 'notice', 'lgpl')):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    target = directory / str(file).replace('..', '_')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target); found.append(str(file))
        if not found:
            raise RuntimeError('Missing license notices: ' + name)
        with urllib.request.urlopen(f'https://pypi.org/pypi/{name}/{dist.version}/json', timeout=60) as response:
            info = json.load(response)
        archive = next(item for item in info['urls'] if item['packagetype'] == 'sdist')
        fetch_checked(archive['url'], sources / archive['filename'], archive['digests']['sha256'])
    # pygame's wheel has its LGPL text but omits the development packages'
    # codec notices. Preserve those upstream notices using pygame's own pinned
    # package URLs/checksums; never run code fetched from that source archive.
    pygame_source = next(sources.glob('pygame_ce-*.tar.gz'))
    import ast
    with tarfile.open(pygame_source) as archive:
        member = next(item for item in archive.getmembers()
                      if item.name.endswith('buildconfig/download_win_prebuilt.py'))
        script = archive.extractfile(member).read().decode('utf-8')
    tree = ast.parse(script)
    pairs = []
    for node in ast.walk(tree):
        if isinstance(node, ast.List) and len(node.elts) == 2:
            try:
                values = ast.literal_eval(node)
            except (ValueError, TypeError):
                continue
            if all(isinstance(value, str) for value in values) and values[0].startswith('https://'):
                pairs.append(values)
    # Only the SDL2 libraries and x64 fallback are used by this pinned wheel.
    selected = [(url, checksum) for url, checksum in pairs
                if '/SDL2' in url or '/prebuilt-x64-' in url]
    if len(selected) != 5:
        raise RuntimeError('pygame dependency manifest changed; audit its notices before packaging.')
    for url, checksum in selected:
        with urllib.request.urlopen(url, timeout=120) as response:
            content = response.read()
        if hashlib.sha1(content).hexdigest() != checksum:
            raise RuntimeError('pygame upstream development package checksum mismatch.')
        import io
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            for member in archive.infolist():
                if not member.is_dir() and any(word in member.filename.lower()
                    for word in ('license', 'copying', 'notice', 'readme', 'copyright', 'portmidi.h')):
                    relative = Path(member.filename)
                    if relative.is_absolute() or '..' in relative.parts:
                        raise RuntimeError('Unsafe upstream notice path.')
                    target = notices / 'pygame-dependencies' / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(member))
    # Wheel audit: FreeType and PortMidi DLLs match the pinned x64 fallback.
    # FreeType's header identifies 2.11.1; libpng's DLL identifies 1.6.58.
    # The fallback omits the FreeType license, so retain the verified source
    # license explicitly. PortMidi's complete MIT license is in its header.
    supplemental = [
        ('freetype-2.11.1.tar.gz',
         'https://codeload.github.com/freetype/freetype/tar.gz/refs/tags/VER-2-11-1',
         '754d60f086158ad374419d32c94d4b2ced6d3f22d4ed26896f62deee977da892'),
        ('libpng-1.6.58.tar.gz',
         'https://codeload.github.com/pnggroup/libpng/tar.gz/refs/tags/v1.6.58',
         'a9d4df463d36a6e5f9c29bd6f4967312d17e996c1854f3511f833924eb1993cf')]
    for filename, url, checksum in supplemental:
        archive_path = sources / filename
        fetch_checked(url, archive_path, checksum)
        with tarfile.open(archive_path) as archive:
            for member in archive.getmembers():
                if member.isfile() and member.name.rsplit('/', 1)[-1].lower() in (
                    'license', 'copying', 'ftl.txt'):
                    target = notices / filename.removesuffix('.tar.gz') / member.name.rsplit('/', 1)[-1]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.extractfile(member).read())
    (notices / 'FreeType-attribution.txt').write_text(
        'Portions of this software are copyright (c) 2021 The FreeType Project '
        '(www.freetype.org). All rights reserved. Used under the FreeType License (FTL).\n',
        encoding='utf-8')
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    shutil.copy2(python_license, notices / 'Python-LICENSE.txt')
    # Tcl/Tk notices alongside the interpreter's Tcl library.
    for file in (Path(sys.base_prefix) / 'tcl').rglob('*'):
        if file.is_file() and file.name.lower() in ('license.terms', 'license.txt', 'license'):
            target = notices / 'TclTk' / file.relative_to(Path(sys.base_prefix) / 'tcl')
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(file, target)
    manifest = {file.relative_to(app).as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()
                for file in sorted(app.rglob('*')) if file.is_file() and
                (file.suffix.lower() in ('.exe', '.dll', '.pyd', '.pyw', '.png', '.tcl', '.zip') or
                 file.name == 'base_library.zip') and 'Sources' not in file.parts}
    (app / 'runtime-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (app / 'portable.flag').write_text('Portable data belongs in Data next to the executable.\n')
    report = ROOT / 'build/frozen-smoke.json'
    result = subprocess.run([str(app / 'GrooveGoblinLite.exe'), '--self-test', str(report)], timeout=90)
    if result.returncode or not report.is_file() or not json.loads(report.read_text())['ok']:
        detail = report.read_text() if report.is_file() else 'No startup report was produced.'
        raise RuntimeError('Frozen application smoke test failed; no installer published.\n' + detail)
    phone_report=ROOT / 'build/frozen-phone-smoke.json'
    result=subprocess.run([str(app / 'GrooveGoblinPhone.exe'),'--self-test',str(phone_report)],timeout=90)
    if result.returncode or not phone_report.is_file() or not json.loads(phone_report.read_text())['ok']:
        raise RuntimeError('Frozen phone launcher smoke test failed; no installer published.')
    # Never include test-generated undo/data in the portable ZIP.
    shutil.rmtree(app / 'Data', ignore_errors=True)
    shutil.make_archive(str(ROOT / 'dist/GrooveGoblin-LITE-1.4.0-Windows-x64-Portable'), 'zip',
                        root_dir=ROOT / 'dist', base_dir='GrooveGoblinLite')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        detail=traceback.format_exc()[-8000:]
        print('::error::'+detail.replace('%','%25').replace('\r','%0D').replace('\n','%0A'),flush=True)
        raise
