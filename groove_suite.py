"""Small standalone launcher for the bundled Desktop, LITE and Mobile modes."""
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image, ImageTk
from groove_modes import ModeSwitcher, switch_button
from groove_runtime import resource_dir
from groove_version import __version__
from groove_widgets import BG, MUTED


class SuiteLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.app_mode='suite';self.worker_busy=False;self.messages=[]
        self.ui_font='Segoe UI' if 'Segoe UI' in tkfont.families(self) else 'Helvetica'
        self.title('Groove Goblin Suite '+__version__);self.configure(bg=BG)
        self.minsize(320,460)
        width=min(440,max(320,self.winfo_screenwidth()-40))
        height=min(650,max(460,self.winfo_screenheight()-80))
        self.geometry(f'{width}x{height}+{max(0,(self.winfo_screenwidth()-width)//2)}+{max(0,(self.winfo_screenheight()-height)//2)}')
        self.iconphoto(True,tk.PhotoImage(file=str(resource_dir()/'assets/groove_goblin_app_icon.png')))
        self.status=tk.StringVar(value='Choose your Groove Goblin mode')
        self._mode_switch=ModeSwitcher(self)
        controls=tk.Frame(self,bg=BG);controls.pack(side='bottom',fill='x',padx=24,pady=(8,20))
        self.launch_buttons={}
        for mode in ('desktop','lite','mobile'):
            button=switch_button(self,controls,mode,verb='Launch')
            button.pack(fill='x',pady=(0,10));self.launch_buttons[mode]=button
        tk.Label(controls,textvariable=self.status,bg=BG,fg=MUTED,font=(self.ui_font,9),wraplength=280).pack(fill='x',pady=(2,0))
        with Image.open(resource_dir()/'assets/groove_goblin_logo.png') as source:self.logo_source=source.convert('RGBA')
        self.logo_label=tk.Label(self,bg=BG,bd=0);self.logo_label.pack(fill='both',expand=True,padx=20,pady=(16,0))
        self.logo_size=None
        self.logo_label.bind('<Configure>',self.fit_logo)
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.after_idle(self.launch_buttons['desktop'].focus_set)

    def fit_logo(self,event):
        bounds=(max(1,min(300,event.width-8)),max(1,event.height-8))
        if bounds==self.logo_size:return
        image=self.logo_source.copy();image.thumbnail(bounds,Image.Resampling.LANCZOS)
        self.logo=ImageTk.PhotoImage(image,master=self);self.logo_label.configure(image=self.logo)
        self.logo_size=bounds

    def log(self,message):self.messages.append(str(message))

    def close(self):
        if not self._mode_switch.active:self.destroy()


if __name__=='__main__':SuiteLauncher().mainloop()
