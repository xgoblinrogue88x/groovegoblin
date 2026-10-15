"""Real Tk selection -> STA drag loop -> other process -> real Shell move."""
import ctypes as C
from ctypes import wintypes as W
import faulthandler
import hashlib
import importlib.machinery
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
faulthandler.enable();faulthandler.dump_traceback_later(45)
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from test_groove import GrooveTests
from groove_manual import read_track
from groove_windows_drag import WindowsFileDrag

os.environ['GROOVE_GOBLIN_EDITION']=sys.argv[1].upper()
fixture=GrooveTests();fixture.setUp()
api=WindowsFileDrag();user=api.user
user.SetCursorPos.argtypes=[C.c_int,C.c_int];user.SetCursorPos.restype=W.BOOL
user.mouse_event.argtypes=[W.DWORD,W.DWORD,W.DWORD,W.DWORD,C.c_size_t]
user.SetForegroundWindow.argtypes=[W.HWND];user.SetForegroundWindow.restype=W.BOOL
app=None;receiver=None
try:
    source=[fixture.add_mp3('Source','One {Björk}.mp3','One'),fixture.add_flac('Source','Two 日本語.flac','Two')]
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source}
    destination=fixture.root/'Destination';destination.mkdir();report=fixture.root/'drop.json'
    receiver=subprocess.Popen([sys.executable,str(ROOT/'tests/windows_drag_receiver.py'),str(destination),str(report)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    deadline=time.monotonic()+10
    while not report.with_suffix('.ready').is_file() and time.monotonic()<deadline:
        if receiver.poll() is not None:raise RuntimeError(receiver.communicate())
        time.sleep(.05)
    target=json.loads(report.with_suffix('.ready').read_text())
    module=importlib.machinery.SourceFileLoader('drag_gui',str(ROOT/'GrooveGoblin.pyw')).load_module()
    app=module.GrooveGoblin();app.update();app.maxsize(4096,4096)
    app.geometry('800x600+0+0');app.update();app._responsive.apply();app.update()
    editor=app.track_editor;editor.records={str(p):read_track(p) for p in source};editor.refresh();app.tabs.select(editor);app.update()
    editor.tree.selection_set([str(p) for p in source]);editor.tree.see(str(source[0]));app.update()
    x,y,width,height=editor.tree.bbox(str(source[0]),'#1')
    start=(editor.tree.winfo_rootx()+x+18,editor.tree.winfo_rooty()+y+height//2)
    errors=[];app.report_callback_exception=lambda kind,value,trace:errors.append(str(value))
    def press():
        user.SetForegroundWindow(app.winfo_id());user.SetCursorPos(*start);user.mouse_event(2,0,0,0,0)
    def move_start():user.SetCursorPos(start[0]+22,start[1]+3)
    app.after(300,press);app.after(500,move_start)
    app.after(1500,lambda:user.SetCursorPos(target['x'],target['y']))
    app.after(2500,lambda:user.mouse_event(4,0,0,0,0))
    complete=[False]
    def check():
        if report.is_file() and not editor.file_drag.active and not app.worker_busy:
            complete[0]=True;app.quit()
        else:app.after(100,check)
    app.after(100,check);app.after(20000,app.quit);app.mainloop()
    if not complete[0]:
        editor.file_drag.close();raise RuntimeError('Native GUI drag timed out: '+app.status.get())
    assert not errors,errors
    result=json.loads(report.read_text());assert not result.get('error'),result
    assert {Path(p).resolve() for p in result['paths']}==set(source),result
    # Shell can return NONE after an optimized move. Verify the actual files
    # and followed editor paths below, rather than requiring a reported effect.
    assert result['effect'] in (0,2),result
    for p in source:
        new=destination/p.name
        assert new.is_file() and not p.exists(),(str(p),app.status.get())
        assert hashlib.sha256(new.read_bytes()).hexdigest()==before[str(p)]
        assert str(new) in editor.records and str(p) not in editor.records,app.status.get()
    assert len(editor.selected())==2,editor.selected()
    print('Native GUI multi-file drag and Shell move passed in '+sys.argv[1],flush=True)
finally:
    user.mouse_event(4,0,0,0,0)
    if app is not None:app.destroy()
    if receiver is not None:
        if receiver.poll() is None:receiver.terminate()
        output=receiver.communicate(timeout=10)
        if receiver.returncode not in (0,1):print(output,flush=True)
    fixture.tearDown()
