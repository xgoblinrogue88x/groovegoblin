"""Bound each regression module and surface the last test in CI annotations."""
from pathlib import Path
import subprocess
import sys


def main():
    logs = Path('build/test-results'); logs.mkdir(parents=True, exist_ok=True)
    for module in sorted(Path('tests').glob('test_*.py')):
        log = logs / (module.stem + '.txt')
        print('Testing ' + module.name, flush=True)
        with log.open('w', encoding='utf-8') as stream:
            process = subprocess.Popen([sys.executable, '-u', '-m', 'unittest',
                'discover', '-s', 'tests', '-p', module.name, '-v'], stdout=stream,
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
