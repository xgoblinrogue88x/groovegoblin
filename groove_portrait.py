"""Touch workspaces for a portrait remote desktop, using the existing controllers."""
import tkinter as tk
import sys
from pathlib import Path
from tkinter import ttk
from PIL import Image, ImageTk
from groove_widgets import BG, PANEL, FG, GREEN, MUTED, Button, Check, Scrollbar, bind_mousewheel
from groove_naming import FILE_FORMATS, FOLDER_FORMATS
from groove_version import __version__


class ScrollHost(tk.Frame):
    """Scroll only the active form; navigation and actions stay outside it."""
    def __init__(self, parent, widget, height):
        super().__init__(parent,bg=BG)
        self.widget=widget;self.height=height
        self.canvas=tk.Canvas(self,bg=BG,highlightthickness=0,yscrollincrement=32)
        self.bar=Scrollbar(self,orient='vertical',command=self.canvas.yview,style='Vertical.Goblin.TScrollbar')
        self.bar.pack(side='right',fill='y');self.canvas.pack(fill='both',expand=True)
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.window=None
        self.saved_bindings=[]
        self.canvas.bind('<Configure>',lambda event:self.fit())
        bind_mousewheel(self.canvas,targets=(self.bar,))

    def attach(self):
        self.widget.grid_forget()
        if self.window is None:
            self.window=self.canvas.create_window(0,0,window=self.widget,anchor='nw')
            def descendants(widget):
                return [widget,*[item for child in widget.winfo_children() for item in descendants(child)]]
            targets=tuple(descendants(self.widget))
            sequences=['<MouseWheel>','<Shift-MouseWheel>','<Button-4>','<Button-5>','<Shift-Button-4>','<Shift-Button-5>']
            if int(str(self.tk.call('package','provide','Tk')).split('.')[0])>=9:sequences+=['<TouchpadScroll>','<Shift-TouchpadScroll>']
            self.saved_bindings=[(target,sequence,target.bind(sequence)) for target in targets for sequence in sequences]
            bind_mousewheel(self.canvas,targets=targets)
        self.widget.tk.call('raise',self.widget._w)
        self.fit()

    def fit(self):
        if self.window is None:return
        width=max(1,self.canvas.winfo_width());height=max(self.canvas.winfo_height(),self.height())
        self.canvas.itemconfigure(self.window,width=width,height=height)
        self.canvas.configure(scrollregion=(0,0,width,height))

    def release(self):
        if self.window is not None:self.canvas.delete(self.window);self.window=None
        self.grid_remove()
        for target,sequence,script in self.saved_bindings:
            if target.winfo_exists():target.tk.call('bind',target._w,sequence,script or '')
        self.saved_bindings=[]


class PortraitLayout:
    def __init__(self,app):
        self.a=app;self.w=app._responsive.w;self.active=False;self.busy=False;self.view='Albums';self.track_view='Tracks'
        self.mode=tk.StringVar(value='Auto')
        app.minsize(360,540)
        self.header=tk.Frame(app._desktop,bg=PANEL)
        self.header.columnconfigure(1,weight=1)
        image=app._responsive.logo_source.copy()
        image.thumbnail((40,48),Image.Resampling.LANCZOS)
        self.logo=ImageTk.PhotoImage(image,master=app)
        tk.Label(self.header,image=self.logo,bg=PANEL).grid(row=0,column=0,padx=(8,4),pady=4)
        self.nav=ttk.Combobox(self.header,state='readonly',width=20,font=(app.ui_font,12),
            values=[b.text for b in app.nav_buttons.values()])
        self.nav.grid(row=0,column=1,sticky='ew',padx=8,pady=8)
        self.nav.bind('<<ComboboxSelected>>',self.navigate)
        self.strip=tk.Frame(app.dashboard,bg=BG)
        self.strip_buttons=[]
        for col,title in enumerate(('Albums','Match','Results','Options')):
            self.strip.columnconfigure(col,weight=1,uniform='phone')
            button=Button(self.strip,title,lambda name=title:self.select(name),width=20,height=44,font=(app.ui_font,10),green_active=True)
            button.grid(row=0,column=col,sticky='ew',padx=(0,3 if col<3 else 0));self.strip_buttons.append(button)
        self.right=ScrollHost(app.dashboard,app.tab_editor,self.right_height)
        self.options=tk.Frame(app.dashboard,bg=PANEL)
        self.options_host=ScrollHost(app.dashboard,self.options,lambda:self.options.winfo_reqheight())
        self.rename_controls=[]
        for text,var,presets in (('Rename tracks',app.opt_filenames,FILE_FORMATS),('Rename album folders',app.opt_folders,FOLDER_FORMATS)):
            Check(self.options,text,var,self.options_changed,width=20,font=(app.ui_font,12)).pack(fill='x',padx=8,pady=(10,2))
            value=app.file_format if presets is FILE_FORMATS else app.folder_format
            combo=ttk.Combobox(self.options,textvariable=value,values=list(presets),state='readonly',width=20,font=(app.ui_font,12),style='Phone.TCombobox')
            combo.pack(fill='x',padx=8,pady=(0,8));combo.bind('<<ComboboxSelected>>',lambda event:app.refresh_preview())
            self.rename_controls.append((combo,var))
        for text,var,command in (('Scan subfolders',app.scan_subfolders,None),('Search online after scan',app.auto_lookup,None),('Show only problems',app.show_problems,app.populate_albums)):
            check=Check(self.options,text,var,command,width=20,font=(app.ui_font,12));check.configure(height=44);check.pack(fill='x',padx=8)
        tk.Label(self.options,text='Album grouping, album/year tag replacement and undo journaling stay on. Scanning never changes music.',bg=PANEL,fg=MUTED,font=(app.ui_font,11),wraplength=300,justify='left').pack(fill='x',padx=12,pady=12)
        self.cancel=Button(self.options,'Cancel Current Search',app.cancel_search,width=20,height=44,font=(app.ui_font,11))
        self.cancel.pack(fill='x',padx=8,pady=8)
        self.multi=Button(app.tab_albums,'Select Multiple',self.toggle_multi,width=140,height=40,font=(app.ui_font,10),green_active=True)
        self.multi_mode=False
        editor=app.track_editor
        self.track_strip=tk.Frame(editor,bg=BG)
        self.track_tabs=[]
        for column,title in enumerate(('Tracks','Tags & Artwork')):
            self.track_strip.columnconfigure(column,weight=1,uniform='tracks')
            button=Button(self.track_strip,title,lambda name=title:self.select_tracks(name),width=20,height=44,font=(app.ui_font,11),green_active=True)
            button.grid(row=0,column=column,sticky='ew',padx=(0,4 if column==0 else 0));self.track_tabs.append(button)
        self.tags_host=ScrollHost(editor.body,editor.side_panel,lambda:editor.side.winfo_reqheight()+20)
        self.select_tracks_button=Button(editor.clear_list_button.master,'Select All',editor.select_all,width=90,height=40,font=(app.ui_font,10))
        ttk.Style(app).configure('Phone.TCombobox',padding=7)
        ttk.Style(app).configure('Phone.TEntry',padding=6)
        if '--phone' in sys.argv or (getattr(sys,'frozen',False) and Path(sys.executable).stem=='GrooveGoblinPhone'):
            app.after_idle(self.open_phone)
        elif app.winfo_screenheight()>app.winfo_screenwidth()*1.15:
            app.geometry(f'{max(360,app.winfo_screenwidth()-32)}x{max(540,app.winfo_screenheight()-80)}')

    def open_phone(self):
        self.mode.set('Phone')
        self.a.geometry(f'{max(360,min(480,self.a.winfo_screenwidth()-32))}x{max(540,min(1040,self.a.winfo_screenheight()-80))}')
        self.a._responsive.schedule()

    def wants(self):
        a=self.a
        return self.mode.get()=='Phone' or a._desktop.winfo_width()<800 or a._desktop.winfo_height()>a._desktop.winfo_width()*1.15

    def navigate(self,event=None):
        index=self.nav.current()
        if index>=0:list(self.a.nav_buttons.values())[index].invoke()
        self.a._responsive.schedule()

    def select(self,name):
        self.view=name;self.right.canvas.yview_moveto(0);self.apply()

    def select_tracks(self,name):
        self.track_view=name;self.tags_host.canvas.yview_moveto(0);self.resize_tracks()

    def toggle_multi(self):
        self.multi_mode=not self.multi_mode;self.multi.active=self.multi_mode;self.multi.draw()
        self.a.albums_tree.touch_multi=self.multi_mode

    def options_changed(self):
        for combo,var in self.rename_controls:combo.configure(state='readonly' if var.get() else 'disabled')
        self.a.lite_file_format_box.configure(state='readonly' if self.a.opt_filenames.get() else 'disabled')
        self.a.lite_folder_format_box.configure(state='readonly' if self.a.opt_folders.get() else 'disabled')
        self.a.refresh_preview()

    def right_height(self):
        panel=self.w['details'] if self.view=='Match' else self.w['results']
        return panel.body.winfo_reqheight()+24 if self.view=='Match' else 100

    def apply(self):
        if self.busy:return
        self.busy=True
        try:
            self.active=True;a=self.a;w=self.w
            self.unit=max(1,min(2.4,a._desktop.winfo_width()/480,a._desktop.winfo_height()/900))
            px=lambda value:round(value*self.unit)
            self.nav.configure(font=(a.ui_font,px(12)))
            for child in self.options.winfo_children():
                if isinstance(child,Check):child.font=(a.ui_font,px(12));child.configure(height=px(44));child.draw()
                elif isinstance(child,tk.Label):child.configure(font=(a.ui_font,px(11)),wraplength=max(280,a.winfo_width()-56))
            for combo,var in self.rename_controls:combo.configure(font=(a.ui_font,px(12)),state='readonly' if var.get() else 'disabled')
            a._responsive_mode='portrait'
            w['sidebar'].grid_remove()
            a._desktop.columnconfigure(0,minsize=0,weight=1);a._desktop.columnconfigure(1,minsize=0,weight=0)
            a._desktop.rowconfigure(0,weight=0);a._desktop.rowconfigure(1,weight=1)
            self.header.grid(row=0,column=0,columnspan=2,sticky='ew')
            a.content.grid_configure(row=1,column=0,columnspan=2,padx=6,pady=(4,0))
            current={'scan':0,'lookup':1,'tracks':2,'logs':5}.get(a._active_page,0)
            self.nav.current(current)
            a.dashboard.columnconfigure(0,weight=1,minsize=0);a.dashboard.columnconfigure(1,weight=0,minsize=0)
            for row in (0,1,2):a.dashboard.rowconfigure(row,weight=1 if row==2 else 0)
            a.lite_toolbar.grid_configure(row=0,column=0,columnspan=1)
            for col in range(6):a.lite_toolbar.columnconfigure(col,weight=1 if col<3 else 0,minsize=0,uniform='phoneactions' if col<3 else '')
            for i,button in enumerate(a.lite_buttons):
                button.text=button.lite_short;button.symbol=None;button.font=(a.ui_font,px(12))
                button.configure(width=20,height=px(46));button.grid_configure(row=i//3,column=i%3,padx=(0,4 if i%3<2 else 0),pady=(0,4));button.draw()
            self.strip.grid(row=1,column=0,sticky='ew',pady=(0,5))
            for b in self.strip_buttons:
                b.active=b.text==self.view;b.font=(a.ui_font,px(10));b.configure(height=px(44));b.draw()
            for key in ('toolbar','preview','opts','player','checkrow'):w[key].grid_remove()
            a.lite_formats.pack_forget()
            w['center'].grid_remove();self.right.grid_remove();self.options_host.grid_remove()
            if self.right.window is None:a.tab_editor.grid_remove()
            for row in (0,1,3):w['center'].rowconfigure(row,weight=0,minsize=0)
            w['center'].rowconfigure(2,weight=1,minsize=0)
            w['albums'].padding=8;w['albums'].grid_configure(pady=0)
            a.albums_heading.pack_configure(side='top',anchor='w',before=a.remove_albums_button)
            for b,width in ((a.btn_verify,126),(a.remove_albums_button,166)):
                b.configure(width=px(width),height=px(42));b.font=(a.ui_font,px(10));b.draw()
            self.multi.pack(fill='x',before=a.albums_tree,pady=(4,6))
            self.multi.font=(a.ui_font,px(10));self.multi.configure(height=px(40));self.multi.draw()
            a.albums_heading.configure(font=(a.ui_font,px(11),'bold'))
            a.albums_tree.touch_multi=self.multi_mode
            a.albums_tree.touch_edge=px(40)
            a.albums_tree.phone=True;a.albums_tree.rowheight=px(100);a.albums_tree.font=(a.ui_font,px(12));a.albums_tree.head.pack_forget();a.albums_tree.schedule()
            if self.view=='Albums':w['center'].grid(row=2,column=0,sticky='nsew')
            elif self.view=='Options':
                self.options_host.grid(row=2,column=0,sticky='nsew');self.options_host.attach()
                self.cancel.state(['!disabled'] if a.worker_busy else ['disabled'])
            else:
                w['details'].grid_remove();w['results'].grid_remove()
                a.tab_editor.columnconfigure(0,weight=1)
                for row in range(3):a.tab_editor.rowconfigure(row,weight=0)
                if self.view=='Match':
                    self.details();w['details'].grid(row=0,column=0,sticky='nsew',pady=0)
                else:
                    a.tab_editor.rowconfigure(0,weight=1);w['results'].grid(row=0,column=0,sticky='nsew')
                self.right.grid(row=2,column=0,sticky='nsew');self.right.attach()
                a.results_tree.rowheight=px(82);a.results_tree.font=(a.ui_font,px(12));a.results_tree.schedule()
            a._footer_controls.pack_forget();w['footer_spacer'].pack_forget()
            a.status_label.configure(font=(a.ui_font,px(10)),height=2,wraplength=max(300,a.winfo_width()-24))
            a._footer.pack_configure(padx=6,pady=4)
            history_row=a.log_box.master.winfo_children()[1]
            for child in history_row.winfo_children():
                if isinstance(child,ttk.Button):child.pack_configure(side='top',fill='x',padx=0,pady=3)
            self.resize_tracks();a.lookup_page.resize()
            a.update_idletasks();self.right.fit();self.options_host.fit();self.tags_host.fit()
        finally:self.busy=False

    def details(self):
        a=self.a;w=self.w
        px=lambda value:round(value*self.unit)
        w['details'].padding=8
        for entry in (a.artist_entry,a.album_entry,*[child for child in w['yearrow'].winfo_children() if isinstance(child,ttk.Entry)]):entry.configure(font=(a.ui_font,px(12)),style='Phone.TEntry',width=7 if entry.master is w['yearrow'] else 1)
        for label in w['form'].winfo_children():
            if isinstance(label,tk.Label):label.configure(font=(a.ui_font,px(11)))
        a.current_label.configure(font=(a.ui_font,px(11)),height=0,wraplength=max(260,a.content.winfo_width()-48))
        a.cover_size=px(80);a.cover_box.configure(width=a.cover_size,height=px(96));a.update_cover()
        album=a.selected_album()
        if album:a.old_album_label.configure(text=album.old_album or '(missing)')
        a.old_album_label.configure(wraplength=max(120,a.content.winfo_width()-a.cover_size-60),justify='left')
        for i,button in enumerate(w['actions'].winfo_children()):
            if i==1:button.command=lambda:self.select('Results')
            button.vertical=False;button.symbol=None;button.font=(a.ui_font,px(12))
            button.configure(width=20,height=px(44));button.grid_configure(row=i,column=0,columnspan=3,padx=0,pady=(3,0))
        a.update_idletasks()
        w['details'].configure(height=w['details'].body.winfo_reqheight()+20)

    def resize_tracks(self):
        if not self.active:return
        e=self.a.track_editor
        px=lambda value:round(value*self.unit)
        toolbar=e.top_buttons[0].master
        for child in toolbar.winfo_children():
            if isinstance(child,tk.Label):child.pack_forget()
        for b in e.top_buttons:
            if b.winfo_manager()=='pack':b.pack_forget()
        for i,b in enumerate(e.top_buttons):
            b.symbol=None;b.subtitle='';b.text=('Add Files','Add Folder','Scan List')[i];b.font=(self.a.ui_font,px(11))
            b.configure(width=20,height=px(44));toolbar.columnconfigure(i,weight=1,uniform='phone');b.grid(row=0,column=i,sticky='ew',padx=(0,4 if i<2 else 0));b.draw()
        e.rowconfigure(1,weight=0);e.rowconfigure(2,weight=1)
        self.track_strip.grid(row=1,column=0,sticky='ew',pady=(0,5));e.body.grid_configure(row=2)
        e.body.columnconfigure(0,weight=1);e.body.columnconfigure(1,minsize=0,weight=0)
        for b in self.track_tabs:b.active=(b.text==self.track_view);b.font=(self.a.ui_font,px(11));b.configure(height=px(44));b.draw()
        e.list_panel.grid_remove();self.tags_host.grid_remove()
        if self.track_view=='Tracks':e.list_panel.grid(row=0,column=0,sticky='nsew',padx=0)
        else:self.tags_host.grid(row=0,column=0,sticky='nsew');self.tags_host.attach()
        for button in (e.clear_selected_button,e.clear_list_button,self.select_tracks_button):
            button.symbol=None;button.font=(self.a.ui_font,px(10));button.configure(width=px(108 if button is e.clear_selected_button else 92),height=px(40));button.draw()
        self.select_tracks_button.pack(side='left',padx=(4,0))
        e.track_hint.pack_forget()
        ttk.Style(self.a).configure('Editor.Treeview',rowheight=px(44),font=(self.a.ui_font,px(11)))
        for field in e.entries:
            e.checks[field].font=(self.a.ui_font,px(11));e.checks[field].configure(width=px(122),height=px(44));e.checks[field].draw()
            e.entries[field].configure(font=(self.a.ui_font,px(12)),style='Phone.TEntry',width=1)
        e.side_panel.configure(height=e.side.winfo_reqheight()+20)
        for b in (*e.art_buttons,e.stage_button,e.discard_button,e.save_button,e.undo_button):
            b.font=(self.a.ui_font,px(10));b.configure(height=px(42));b.draw()
        e.summary.configure(wraplength=max(280,e.winfo_width()-48))
        e.help.configure(wraplength=max(280,e.winfo_width()-48),font=(self.a.ui_font,px(10)))
        self.tags_host.fit()

    def restore(self):
        if not self.active:return
        self.active=False;a=self.a;w=self.w
        self.right.release();self.options_host.release();self.tags_host.release()
        self.header.grid_remove();self.strip.grid_remove();self.track_strip.grid_remove();self.multi.pack_forget()
        self.select_tracks_button.pack_forget();a.albums_tree.phone=False;a.albums_tree.touch_multi=False
        a.albums_tree.head.pack(fill='x',before=a.albums_tree.body)
        a._desktop.columnconfigure(0,weight=0);a._desktop.columnconfigure(1,weight=1)
        a._desktop.rowconfigure(0,weight=1);a._desktop.rowconfigure(1,weight=0)
        w['sidebar'].grid();a.content.grid_configure(row=0,column=1,columnspan=1)
        a.dashboard.rowconfigure(2,weight=0)
        a.lite_toolbar.grid_configure(columnspan=2)
        for col in range(6):a.lite_toolbar.columnconfigure(col,weight=1,uniform='actions')
        for i,b in enumerate(a.lite_buttons):
            b.symbol=('folder','music','cross','play','check','undo')[i];b.grid_configure(row=0,column=i,pady=0)
        a.tab_editor.grid(row=1,column=1,sticky='nsew')
        w['center'].grid(row=1,column=0,sticky='nsew');w['checkrow'].grid()
        a.lite_formats.pack(fill='x',before=self.multi if self.multi.winfo_manager() else a.albums_tree,pady=(0,7))
        for i,b in enumerate(w['actions'].winfo_children()):
            if i==1:b.command=a.choose_result
            b.vertical=True;b.symbol=('search','list','edit')[i];b.grid_configure(row=0,column=i,columnspan=1,padx=(0,4 if i<2 else 0),pady=0)
        for entry in (a.artist_entry,a.album_entry,*[child for child in w['yearrow'].winfo_children() if isinstance(child,ttk.Entry)]):entry.configure(style='TEntry')
        a.old_album_label.configure(wraplength=0)
        e=a.track_editor;e.body.grid_configure(row=1);e.rowconfigure(1,weight=1);e.rowconfigure(2,weight=0)
        e.list_panel.grid(row=0,column=0,sticky='nsew',padx=(0,8));e.side_panel.grid(row=0,column=1,sticky='nsew')
        for b in e.top_buttons:b.grid_forget()
        for i,b in enumerate(e.top_buttons):
            b.text=('Add Files','Add Folder','Use Scan List')[i];b.symbol=('music','folder','list')[i];b.pack(side='left',padx=(0,5))
        title=e.top_buttons[0].master.winfo_children()[0];title.pack(side='left',padx=(0,12),before=e.top_buttons[0])
        e.track_hint.pack(side='left',padx=12,before=e.track_count)
        for field in e.entries:e.entries[field].configure(style='Manual.TEntry',width=17)
        ttk.Style(a).configure('Editor.Treeview',font=(a.ui_font,a.font_size))
        history_row=a.log_box.master.winfo_children()[1]
        for child in history_row.winfo_children():
            if isinstance(child,ttk.Button):child.pack_configure(side='left',fill='none',padx=(0,8),pady=0)
        self.options_changed();e.resize()

    def fit_dialog(self,window,height=440):
        """Keep application-owned confirmation/settings windows on the remote viewport."""
        # Leave room for native Windows borders and the dialog title bar too.
        width=max(300,min(520,self.a.winfo_width()-40));height=min(height,self.a.winfo_height()-80)
        window.minsize(300,260);window.resizable(True,True)
        window.geometry(f'{width}x{height}+{self.a.winfo_rootx()+8}+{self.a.winfo_rooty()+12}')
        def walk(parent):
            for child in parent.winfo_children():
                if isinstance(child,tk.Label):child.configure(wraplength=width-44,justify='left')
                if isinstance(child,Button):child.configure(width=min(int(child.cget('width')),width-40),height=44)
                if isinstance(child,Check):child.configure(width=width-40,height=44)
                walk(child)
        walk(window)

    def about(self):
        a=self.a;window=tk.Toplevel(a,bg=BG);window.title('About Groove Goblin LITE');window.transient(a)
        window.geometry(f'{min(480,a.winfo_width()-40)}x{min(650,a.winfo_height()-80)}+{a.winfo_rootx()+8}+{a.winfo_rooty()+12}')
        Button(window,'Close',window.destroy,width=20,height=44,primary=True).pack(side='bottom',fill='x',padx=8,pady=8)
        text=tk.Text(window,bg=PANEL,fg=FG,wrap='word',relief='flat',font=(a.ui_font,12),padx=14,pady=14)
        scroll=Scrollbar(window,orient='vertical',command=text.yview,style='Vertical.Goblin.TScrollbar');scroll.pack(side='right',fill='y')
        text.configure(yscrollcommand=scroll.set);text.pack(fill='both',expand=True)
        text.insert('end',f'GROOVE GOBLIN LITE\nVersion {__version__}\n\nPortrait remote layout\nUse the menu at the top to change sections. Albums, Match, Results and Options have separate touch workspaces. Wider windows automatically restore the desktop layout.\n\nAudio formats\nWAV, AIFF, FLAC, ALAC/M4A, APE, WavPack, MP3, Ogg/Vorbis, WMA, Opus, DSF/DFF.\n\nAAC and raw PCM: filename editing only; PCM needs playback settings. CDA files reference CD tracks; rip the CD first. Container support depends on its codec.\n\nChanges & undo\nScanning and searching never change music. Apply requires your confirmation. Track Editor keeps full-file backups. Organizer Undo restores edited tags and names. Keep your own music backups.\n\nLicense: GPLv3. Dependency notices and sources accompany the Windows package.')
        text.configure(state='disabled');bind_mousewheel(text,targets=(scroll,));a._about_window=window
