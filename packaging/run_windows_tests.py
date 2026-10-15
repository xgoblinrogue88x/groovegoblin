"""Bound each regression module and surface the last test in CI annotations."""
from pathlib import Path
import subprocess
import sys
import os


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    os.environ['PYTHONIOENCODING']='utf-8'
    logs = Path('build/test-results'); logs.mkdir(parents=True, exist_ok=True)
    pattern = sys.argv[1] if len(sys.argv) > 1 else 'test_*.py'
    for module in sorted(Path('tests').glob(pattern), key=lambda p:(p.name!='test_windows_drag.py',p.name)):
        log = logs / (module.stem + '.txt')
        print('Testing ' + module.name, flush=True)
        with log.open('w', encoding='utf-8') as stream:
            probe = ('import faulthandler,unittest; '
                     'faulthandler.dump_traceback_later(120); '
                     'unittest.main(module=None)')
            process = subprocess.Popen([sys.executable, '-u', '-c', probe,
                'discover', '-s', 'tests', '-p', module.name, '-v', '-f'], stdout=stream,
                stderr=subprocess.STDOUT, text=True)
            try:
                code = process.wait(timeout=180)
            except subprocess.TimeoutExpired:
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               capture_output=True, timeout=20)
                code = 124
        if code:
            tail = log.read_text(encoding='utf-8', errors='replace')[-6000:]
            message = (module.name + f' exited {code}: ' + tail).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
            print('::error::' + message, flush=True)
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
