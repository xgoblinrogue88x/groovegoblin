"""Windowed executable entry and noninteractive frozen-runtime smoke test."""
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import traceback

from groove_runtime import configure_ffmpeg, data_dir, resource_dir, verify_payload


def check_runtime():
    verify_payload()
    import tkinter
    import mutagen
    from PIL import Image, ImageTk
    import pygame
    binary = configure_ffmpeg()
    result = subprocess.run([str(binary), '-version'], capture_output=True, text=True,
                            timeout=20, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError('Bundled FFmpeg failed its startup check. Reinstall or re-extract the complete download.')
    with Image.open(resource_dir() / 'assets/groove_goblin_logo.png') as logo:
        logo.verify()
    data_dir()


def main():
    try:
        if getattr(sys,'frozen',False):
            mobile=Path(sys.executable).stem=='GrooveGoblinMobile' or '--mobile' in sys.argv
            os.environ['GROOVE_GOBLIN_EDITION']='MOBILE' if mobile else 'FULL'
        check_runtime()
        module = runpy.run_path(str(resource_dir() / 'GrooveGoblin.pyw'), run_name='groove_frozen_app')
        app = module['GrooveGoblin']()
        if '--self-test' in sys.argv:
            # Exercises real Tcl/Tk, Pillow image widgets, every page and the player.
            app.update()
            if '--handoff-ready' in sys.argv:
                import time
                deadline=time.monotonic()+5
                while not app._handoff_ready and time.monotonic()<deadline:app.update();time.sleep(.02)
                if not app._handoff_ready:raise RuntimeError('Mode handoff did not acknowledge its ready window.')
            if app.is_lite and app._phone.mode.get()!='Phone':
                raise RuntimeError('Mobile EXE did not select its portrait workspace.')
            if app.is_lite:app._phone.mode.set('Auto')
            app.maxsize(4096,4096)
            dimensions_to_test=('800x600','412x915','1440x3120','1024x768','1920x1080') if app.is_lite else ('800x600','1024x768','1920x1080')
            for dimensions in dimensions_to_test:
                app.geometry(dimensions)
                app.update()
                app._responsive.apply();app.update()
            if app.is_lite:
                app.geometry('412x915');app.update();app._responsive.apply();app.update()
                for name in ('Albums','Match','Results','Options'):
                    app._phone.select(name);app.update()
            for page in (app.dashboard, app.track_editor, app.lookup_page, app.tab_history):
                app.tabs.select(page)
                app.update()
            if app.is_lite:app._phone.select_tracks('Tags & Artwork');app.update()
            # Exercise the frozen decoder and SDL too, using disposable audio.
            import tempfile
            import time
            from groove_player import MusicPlayer
            with tempfile.TemporaryDirectory() as temporary:
                media = Path(temporary) / 'smoke.flac'
                subprocess.run([str(configure_ffmpeg()), '-hide_banner', '-loglevel', 'error',
                                '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
                                '-c:a', 'flac', str(media)], check=True, timeout=20,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                os.environ['SDL_AUDIODRIVER'] = 'dummy'
                player = MusicPlayer(compatibility=True, allow_test_output=True)
                try:
                    player.play([{'path': str(media), 'duration': 1}])
                    deadline = time.monotonic() + 20
                    while player.state == 'buffering' and time.monotonic() < deadline:
                        player.pump(); time.sleep(.02)
                    if player.state != 'playing':
                        raise RuntimeError('Frozen FLAC decode/playback smoke test failed.')
                    player.toggle(); player.stop()
                finally:
                    player.close()
            app.destroy()
            output = Path(sys.argv[sys.argv.index('--self-test') + 1])
            output.write_text(json.dumps({'ok': True, 'python': sys.version,
                                          'data': str(data_dir()),'mode':'mobile' if app.is_lite else 'desktop'}), encoding='utf-8')
        else:
            app.mainloop()
        return 0
    except Exception:
        detail = traceback.format_exc()
        if '--self-test' in sys.argv:
            try:
                Path(sys.argv[sys.argv.index('--self-test') + 1]).write_text(
                    json.dumps({'ok': False, 'error': detail}), encoding='utf-8')
            except Exception:
                pass
        try:
            log = data_dir() / 'startup-error.log'
            log.write_text(detail, encoding='utf-8')
            detail += '\nStartup log: ' + str(log)
        except Exception:
            pass
        if '--self-test' not in sys.argv:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, detail, 'Groove Goblin could not start', 0x10)
        return 1


if __name__ == '__main__':
    sys.exit(main())
