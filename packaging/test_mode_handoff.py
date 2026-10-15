"""On Windows, launch each built EXE through the real mode-switch controller."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch
from itertools import permutations

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    folder=Path(sys.argv[1]).resolve();results=[]
    from groove_version import MODE_EXECUTABLES
    from groove_suite import SuiteLauncher
    routes=[*permutations(MODE_EXECUTABLES,2),*(('suite',target) for target in MODE_EXECUTABLES)]
    for parent_mode,target in routes:
        report=ROOT/'build'/f'handoff-{parent_mode}-{target}.json'
        report.unlink(missing_ok=True)
        with patch.dict(os.environ,{'GROOVE_GOBLIN_EDITION':parent_mode.upper()}),patch.object(sys,'argv',['handoff-test']):
            loader=importlib.machinery.SourceFileLoader('handoff_parent',str(ROOT/'GrooveGoblin.pyw'))
            module=importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name,loader));loader.exec_module(module)
            app=SuiteLauncher() if parent_mode=='suite' else module.GrooveGoblin();app.update()
            errors=[];app.report_callback_exception=lambda kind,value,trace:errors.append(str(value))
            def timeout():
                errors.append('Parent did not close after successful child startup.');app.destroy()
            timer=app.after(60000,timeout)
            command=[str(folder/MODE_EXECUTABLES[target]),'--self-test',str(report)]
            with patch('groove_modes.launch_command',return_value=command):
                app._mode_switch.start(target);app.mainloop()
            controller=app._mode_switch
            if errors or not controller.success:raise RuntimeError(f'{parent_mode} to {target}: {errors or "handoff failed"}')
            if controller.process.wait(timeout=90) or not report.is_file():raise RuntimeError('Child EXE smoke test failed.')
            result=json.loads(report.read_text(encoding='utf-8'))
            if not result['ok'] or result['mode']!=target:raise RuntimeError('Child opened the wrong mode.')
            if result.get('startup_window_state')!='zoomed':raise RuntimeError('Child mode did not open maximized.')
            results.append(result)
    if len({result['data'] for result in results})!=1:raise RuntimeError('Modes do not share their undo/data location.')
    (ROOT/'build/mode-handoff.json').write_text(json.dumps({'ok':True,'directions':results},indent=2),encoding='utf-8')
    print('All six mode switches and all three suite launch choices acknowledged real EXE startup before closing their parent windows.')


if __name__=='__main__':main()
