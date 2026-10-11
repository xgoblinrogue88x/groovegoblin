import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import groove_runtime as runtime


class RuntimeTests(unittest.TestCase):
    def test_frozen_portable_undo_survives_resource_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); exe = root / 'GrooveGoblin.exe'
            (root / 'portable.flag').touch()
            with patch.object(runtime.sys, 'frozen', True, create=True), \
                 patch.object(runtime.sys, 'executable', str(exe)), \
                 patch.object(runtime.sys, '_MEIPASS', str(root / '_internal'), create=True):
                self.assertEqual(runtime.resource_dir(), root / '_internal')
                self.assertEqual(runtime.data_dir(), root / 'Data')
                journal = runtime.data_dir() / 'undo.json'; journal.write_text('keep')
                self.assertEqual(runtime.data_dir(), root / 'Data')
                self.assertEqual(journal.read_text(), 'keep')

    def test_installed_runtime_uses_local_appdata_and_bundled_decoder(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            binary = root / '_internal/ffmpeg/ffmpeg.exe'
            binary.parent.mkdir(parents=True); binary.write_bytes(b'test')
            with patch.object(runtime.sys, 'frozen', True, create=True), \
                 patch.object(runtime.sys, 'executable', str(root / 'GrooveGoblin.exe')), \
                 patch.object(runtime.sys, '_MEIPASS', str(root / '_internal'), create=True), \
                 patch.dict(os.environ, {'LOCALAPPDATA': str(root / 'user')}):
                self.assertEqual(runtime.data_dir(), root / 'user/GrooveGoblin')
                self.assertEqual(runtime.configure_ffmpeg(), binary)
                self.assertEqual(os.environ['IMAGEIO_FFMPEG_EXE'], str(binary))
                binary.unlink()
                with self.assertRaisesRegex(RuntimeError, 'FFmpeg is missing'):
                    runtime.configure_ffmpeg()

    def test_integrity_check_rejects_changed_missing_and_escaping_components(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); file = root / 'runtime.dll'; file.write_bytes(b'original')
            manifest = root / 'runtime-manifest.json'
            manifest.write_text(json.dumps({'runtime.dll': hashlib.sha256(b'original').hexdigest()}))
            with patch.object(runtime.sys, 'frozen', True, create=True), \
                 patch.object(runtime.sys, 'executable', str(root / 'GrooveGoblin.exe')):
                runtime.verify_payload()
                file.write_bytes(b'damaged')
                with self.assertRaisesRegex(RuntimeError, 'damaged'):
                    runtime.verify_payload()
                file.unlink()
                with self.assertRaises(FileNotFoundError):
                    runtime.verify_payload()
                manifest.write_text(json.dumps({'../elsewhere': 'hash'}))
                with self.assertRaisesRegex(RuntimeError, 'manifest path'):
                    runtime.verify_payload()
