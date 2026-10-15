"""Launch the other mode, keeping the current window until startup is confirmed."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import tkinter as tk
from tkinter import messagebox
from groove_runtime import resource_dir
from groove_widgets import BG, Button
from groove_version import MODE_LABELS, MODE_EXECUTABLES


def launch_command(target):
    if target not in MODE_LABELS:raise ValueError('Unknown application mode')
    if getattr(sys,'frozen',False):
        filename=MODE_EXECUTABLES[target]
        executable=Path(sys.executable).resolve().parent/filename
        if not executable.is_file():raise FileNotFoundError(f'{filename} is missing. Reinstall or extract the complete package.')
        return [str(executable)]
    return [sys.executable,str(resource_dir()/'GrooveGoblin.pyw'),'--'+target]


class ModeSwitcher:
    def __init__(self,app):
        self.app=app;self.active=False;self.success=False;self.process=None;self.temporary=None;self.buttons=[];self.overlay=None

    def start(self,target):
        a=self.app
        if self.active:return
        if a.worker_busy:
            messagebox.showinfo('Finish current work','Wait for the current scan, search or file operation to finish before switching modes.',parent=a);return
        editor=getattr(a,'track_editor',None)
        if editor is not None and (editor.pending or editor.inline or any(v.get() for v in editor.enabled.values())):
            if not messagebox.askyesno('Unsaved track edits','Switching modes closes this window. Discard unsaved Track Editor edits and continue?',parent=a):return
        try:
            command=launch_command(target)
            self.temporary=tempfile.TemporaryDirectory(prefix='groove-mode-')
            self.ready=Path(self.temporary.name)/'ready.json';self.target=target
            environment=dict(os.environ);environment.pop('GROOVE_GOBLIN_EDITION',None)
            self.process=subprocess.Popen([*command,'--handoff-ready',str(self.ready)],
                cwd=str(resource_dir()),env=environment,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except Exception as error:
            self.fail(error);return
        self.active=True;self.success=False;self.deadline=time.monotonic()+45
        # Freeze editing during the handoff so no new edits/writes can begin
        # between the unsaved-edit check and the target's readiness message.
        self.overlay=tk.Frame(a,bg=BG,takefocus=True)
        self.overlay.place(x=0,y=0,relwidth=1,relheight=1)
        tk.Label(self.overlay,text='Opening '+MODE_LABELS[target]+'…',
                 bg=BG,fg='#ffffff',font=(a.ui_font,13),wraplength=max(260,a.winfo_width()-40)).place(relx=.5,rely=.5,anchor='center')
        self.overlay.lift();self.overlay.bind('<Key>',lambda event:'break');self.overlay.focus_set()
        for button in self.buttons:
            if button.winfo_exists():button.state(['disabled'])
        a.status.set('Opening '+MODE_LABELS[target]+'…')
        a.after(100,self.poll)

    def poll(self):
        if not self.active:return
        try:
            if self.ready.is_file():
                ready=json.loads(self.ready.read_text(encoding='utf-8'))
                if ready.get('pid')==self.process.pid and ready.get('mode')==self.target:
                    self.success=True;self.active=False;self.cleanup()
                    for callback in self.app.tk.call('after','info'):
                        script,_=self.app.tk.call('after','info',callback)
                        if script.split()[0] in (self.app._tclCommands or []):self.app.after_cancel(callback)
                    self.app.destroy();return
        except (OSError,ValueError):pass
        if self.process.poll() is not None:
            self.fail(RuntimeError('The other mode exited before its window was ready. The current window has been kept open.'));return
        if time.monotonic()>=self.deadline:
            try:self.process.terminate();self.process.wait(timeout=2)
            except (OSError,subprocess.TimeoutExpired):pass
            self.fail(RuntimeError('The other mode did not finish starting. The current window has been kept open.'));return
        self.app.after(100,self.poll)

    def cleanup(self):
        if self.overlay is not None:
            self.overlay.destroy();self.overlay=None
        if self.temporary is not None:
            self.temporary.cleanup();self.temporary=None

    def fail(self,error):
        self.active=False;self.cleanup()
        for button in self.buttons:
            if button.winfo_exists():button.state(['!disabled'])
        self.app.status.set('Could not switch modes. The current window is still open.')
        self.app.log('Mode switch failed: '+str(error))
        messagebox.showerror('Could not switch modes',str(error),parent=self.app)


def switch_button(app,parent,target,verb='Switch to'):
    text=verb+' '+MODE_LABELS[target]
    button=Button(parent,text,lambda:app._mode_switch.start(target),width=300,height=48,
                  wrap_label=True,primary=True,font=(app.ui_font,11,'bold'))
    app._mode_switch.buttons.append(button)
    return button


def install_mode_switch(app):
    app._mode_switch=ModeSwitcher(app)


def register_ready(app):
    app._handoff_ready=False
    if '--handoff-ready' not in sys.argv:return
    index=sys.argv.index('--handoff-ready')
    path=Path(sys.argv[index+1])
    def notify():
        if not app.winfo_viewable():app.after(100,notify);return
        temporary=path.with_suffix('.pending')
        temporary.write_text(json.dumps({'pid':os.getpid(),'mode':app.app_mode}),encoding='utf-8')
        temporary.replace(path)
        app._handoff_ready=True
    app.after(250,notify)
