"""Groove Goblin desktop layout, implemented against the user's visual reference."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font as tkfont
from PIL import Image, ImageTk, ImageDraw
from groove_artwork import CoverCache
from groove_widgets import BG, PANEL, LINE, FG, MUTED, GREEN, Button, Check, Radio, Panel, Table, icon
from groove_core import plan_actions
from groove_version import __version__
from groove_naming import FILE_FORMATS, FOLDER_FORMATS
from groove_formats import FILE_PATTERN


class PageNavigation:
    def __init__(self, app):self.app=app
    def select(self, page):
        a=self.app
        tracks=hasattr(a,'track_editor') and page is a.track_editor
        history=page is a.tab_history
        target=a.track_editor if tracks else (a.tab_history if history else a.dashboard)
        for frame in (a.dashboard,a.tab_history,getattr(a,'track_editor',a.dashboard)):
            frame.grid_remove()
        target.grid(row=0,column=0,sticky='nsew')
        a._active_page='tracks' if tracks else ('logs' if history else 'scan')
        for name,button in a.nav_buttons.items():
            button.active=name==a._active_page;button.draw()
        from types import SimpleNamespace
        a._footer_resize(SimpleNamespace(width=a._footer.winfo_width()))
        if tracks and not a.track_editor.records and a.matched and not a.worker_busy:a.track_editor.import_scan()
        if page is a.tab_editor:a.album_entry.focus_set()


def install_layout(cls):
    old_style=cls.build_style
    old_clear=cls.clear
    old_show=cls.show_editor

    def show_about(self):
        existing=getattr(self,'_about_window',None)
        if existing is not None and existing.winfo_exists():
            existing.lift();existing.focus_set();return
        window=tk.Toplevel(self,bg=BG)
        self._about_window=window
        window.title('About Groove Goblin');window.transient(self)
        window.geometry('620x540');window.minsize(560,520)
        body=tk.Frame(window,bg=BG);body.pack(fill='both',expand=True,padx=16,pady=14)
        Button(body,'Close',window.destroy,width=110,height=36,primary=True,font=(self.ui_font,10)).pack(side='bottom',anchor='e',pady=(4,0))
        heading=tk.Frame(body,bg=BG);heading.pack(fill='x',pady=(0,8))
        tk.Label(heading,text='GROOVE GOBLIN',bg=BG,fg=GREEN,font=(self.ui_font,18,'bold')).pack(anchor='w')
        tk.Label(heading,text=f'Version {__version__}',bg=BG,fg=MUTED,font=(self.ui_font,9)).pack(anchor='w',pady=(2,4))
        description=tk.Label(heading,text='Match albums, edit tags and artwork, organize files and folders,\nand listen to your music.',bg=BG,fg=FG,font=(self.ui_font,9),justify='left',anchor='w')
        description.pack(fill='x')
        wrapped=[description]
        def section(title,height):
            panel=Panel(body,height=height,padding=12)
            panel.pack(fill='x',pady=(0,10))
            tk.Label(panel.body,text=title,bg=PANEL,fg=GREEN,font=(self.ui_font,11,'bold')).pack(anchor='w',pady=(0,6))
            return panel.body
        def paragraph(parent,text,color=FG):
            label=tk.Label(parent,text=text,bg=PANEL,fg=color,font=(self.ui_font,9),justify='left',anchor='w')
            label.pack(fill='x',pady=(0,3));wrapped.append(label)
            return label
        formats=section('Audio formats',190)
        paragraph(formats,'Tag editing, artwork and playback',GREEN)
        paragraph(formats,'WAV, AIFF, FLAC, ALAC/M4A, APE, WavPack, MP3, Ogg/Vorbis,\nWMA, Opus and DSD (DSF/DFF).')
        paragraph(formats,'AAC / PCM — Filename editing and playback only. Raw PCM needs its sample settings.',MUTED)
        paragraph(formats,'CDA — A reference to a track on an audio CD. Rip the CD to an audio file before editing or playback.',MUTED)
        saving=section('Changes & undo',134)
        paragraph(saving,'Scanning and previews leave your music unchanged.')
        paragraph(saving,'Track Editor saves keep full-file backups for Undo.',MUTED)
        paragraph(saving,'Organizer Undo restores the edited tags and file/folder names. Keep your own music backup too.',MUTED)
        def resize(event):
            if event.widget is window:
                for label in wrapped:label.configure(wraplength=max(420,event.width-64))
        window.bind('<Configure>',resize,add='+')
        window.bind('<Escape>',lambda event:window.destroy())

    def build_style(self):
        old_style(self)
        self.ui_font='Segoe UI' if 'Segoe UI' in tkfont.families(self) else 'Helvetica'
        s=ttk.Style(self)
        s.configure('.',background=BG,foreground=FG,font=(self.ui_font,self.font_size))
        s.configure('TFrame',background=BG)
        s.configure('TLabel',background=BG,foreground=FG)
        s.configure('Muted.TLabel',background=BG,foreground=MUTED)
        s.configure('TEntry',fieldbackground='#182129',foreground=FG,insertcolor=FG,bordercolor='#546673',padding=4)
        s.configure('TCombobox',fieldbackground='#172128',background='#172128',foreground=FG,arrowcolor=MUTED,bordercolor=LINE)
        s.map('TCombobox',fieldbackground=[('readonly','#172128')],foreground=[('readonly',FG)],selectbackground=[('readonly','#172128')],selectforeground=[('readonly',FG)])
        s.map('TEntry',bordercolor=[('focus','#748997'),('!focus','#485b68')],lightcolor=[('focus','#748997'),('!focus','#485b68')],darkcolor=[('focus','#748997'),('!focus','#485b68')])
        s.configure('Manual.TEntry',padding=1)
        s.configure('TScrollbar',background='#27363f',troughcolor=PANEL,bordercolor=PANEL,arrowcolor=MUTED,arrowsize=10)
        s.map('TScrollbar',background=[('active','#43565f')])
        # Image elements prevent platform themes from adding bevels or grips.
        if not hasattr(self,'_theme_images'):self._theme_images=[]
        def pill(size,color):
            image=Image.new('RGBA',(size[0]*3,size[1]*3))
            ImageDraw.Draw(image).rounded_rectangle((0,0,size[0]*3-1,size[1]*3-1),radius=12,fill=color)
            photo=ImageTk.PhotoImage(image.resize(size,Image.Resampling.LANCZOS),master=self)
            self._theme_images.append(photo);return photo
        for direction,sticky,size in [('Vertical','ns',(10,28)),('Horizontal','ew',(28,10))]:
            element='Goblin.'+direction+'.Scrollbar.thumb'
            if element not in s.element_names():
                s.element_create(element,'image',pill(size,'#344753'),
                                 ('disabled',pill(size,PANEL)),('pressed',pill(size,GREEN)),('active',pill(size,'#608090')),
                                 border=4,sticky='nsew')
            name=direction+'.Goblin.TScrollbar'
            s.layout(name,[(direction+'.Scrollbar.trough',{'sticky':sticky,'children':[
                (element,{'expand':True,'sticky':'nsew'})]})])
            s.configure(name,troughcolor=PANEL,bordercolor=PANEL,
                        lightcolor=PANEL,darkcolor=PANEL,borderwidth=0,arrowsize=10)
        s.configure('Editor.Treeview',background=PANEL,fieldbackground=PANEL,foreground=FG,
                    borderwidth=0,relief='flat',rowheight=32)
        s.layout('Editor.Treeview',[('Treeview.treearea',{'sticky':'nsew'})])
        s.configure('Editor.Treeview.Heading',background='#1a252e',foreground=FG,
                    relief='flat',font=(self.ui_font,9,'bold'),padding=(8,7))
        s.map('Editor.Treeview',background=[('selected','#193b30')],foreground=[('selected','#b6ffcb')])
        s.map('Editor.Treeview.Heading',background=[('active','#243641')])
        element='Goblin.Horizontal.Scale.slider'
        if element not in s.element_names():
            s.element_create(element,'image',pill((14,14),GREEN),
                             ('active',pill((14,14),'#b6ffcb')),sticky='')
        s.layout('Player.Horizontal.TScale',[('Horizontal.Scale.trough',{'sticky':'we','children':[
            (element,{'side':'left','sticky':''})]})])
        s.configure('Player.Horizontal.TScale',background=PANEL,troughcolor='#172832',
                    bordercolor=LINE,lightcolor=LINE,darkcolor=LINE,borderwidth=0)
        s.map('Manual.TEntry',bordercolor=[('focus',GREEN),('!focus','#485b68')])

    def build_ui(self):
        self.configure(bg=BG)
        self.geometry(f'{min(1536,self.winfo_screenwidth()-40)}x{min(1000,self.winfo_screenheight()-80)}')
        self.minsize(800,600)
        self.preview_filter=tk.StringVar(value='Folders')
        self.preview_view=tk.StringVar(value='All')
        self.show_problems=tk.BooleanVar(value=False)
        self.scan_subfolders=tk.BooleanVar(value=True)
        self.always_group=tk.BooleanVar(value=True)
        self.journal_required=tk.BooleanVar(value=True)
        self.future_option=tk.BooleanVar(value=False)
        self.nav_buttons={}
        self._active_page='scan'
        self._cover_photo=None
        self._art=CoverCache(self)
        self.button_font=(self.ui_font,10)

        # Footer remains reachable even when the workspace needs scrolling.
        footer=tk.Frame(self,bg=BG)
        self._footer=footer
        footer.pack(side='bottom',fill='x',padx=(0,12),pady=(6,10))
        footer_spacer=tk.Frame(footer,bg=BG,width=272)
        footer_spacer.pack(side='left',fill='y')
        controls=tk.Frame(footer,bg=BG)
        controls.pack(side='right')
        self.btn_apply=Button(controls,'Apply Selected Changes',self.apply,width=244,height=50,symbol='check',primary=True,font=(self.ui_font,9))
        self.btn_apply.pack(side='right',padx=(8,0));self.btn_apply.state(['disabled'])
        Button(controls,'Undo Last Apply',self.undo,width=165,height=50,symbol='undo',font=self.button_font).pack(side='right',padx=(8,0))
        Button(controls,'Save Report',self.export,width=142,height=50,symbol='save',font=self.button_font).pack(side='right',padx=(8,0))
        self.btn_cancel=Button(controls,'Cancel',self.cancel_search,width=86,height=50,font=self.button_font)
        self.btn_cancel.on_state=lambda:self.btn_cancel.pack_forget() if self.btn_cancel.disabled else self.btn_cancel.pack(side='right')
        self.btn_cancel.state(['disabled'])
        self.status_label=tk.Label(footer,textvariable=self.status,bg=BG,fg=GREEN,font=(self.ui_font,9),anchor='w',justify='left',wraplength=420)
        self.status_label.pack(side='left',fill='x',expand=True,padx=(0,8))
        def footer_resize(event):
            if self._active_page=='tracks':
                controls.pack_forget();footer_spacer.pack_forget()
                self.status_label.pack_configure(side='top',fill='x',expand=False)
                self.status_label.configure(height=1,wraplength=max(300,event.width-20))
                return
            if event.width<1100:
                controls.pack(side='bottom',anchor='e')
                footer_spacer.pack_forget()
                controls.pack_configure(side='bottom',anchor='e')
                self.status_label.pack_configure(side='top',fill='x',expand=False)
                self.status_label.configure(wraplength=max(300,event.width-20))
            else:
                controls.pack(side='right',anchor='e')
                footer_spacer.pack(side='left',fill='y',before=controls)
                controls.pack_configure(side='right',anchor='e')
                self.status_label.pack_configure(side='left',fill='x',expand=True)
                self.status_label.configure(wraplength=max(200,event.width-controls.winfo_reqwidth()-footer_spacer.winfo_reqwidth()-12))
        self._footer_resize=footer_resize
        footer.bind('<Configure>',footer_resize)
        self._footer_controls=controls

        viewport=tk.Frame(self,bg=BG)
        viewport.pack(fill='both',expand=True)
        desktop=tk.Frame(viewport,bg=BG)
        desktop.pack(fill='both',expand=True)
        desktop.grid_propagate(False)
        self._desktop=desktop
        desktop.rowconfigure(0,weight=1);desktop.columnconfigure(1,weight=1)

        # Full-height branded sidebar.
        sidebar=Panel(desktop,width=260,padding=12)
        sidebar.grid(row=0,column=0,sticky='nsew')
        side=sidebar.body
        side.columnconfigure(0,weight=1);side.rowconfigure(2,weight=1)
        brand=tk.Frame(side,bg=PANEL)
        brand.grid(row=0,column=0,sticky='ew')
        with Image.open(Path(__file__).parent/'assets/groove_goblin_logo.png') as source:
            im=source.convert('RGBA');im.thumbnail((238,316),Image.Resampling.LANCZOS)
            self.logo=ImageTk.PhotoImage(im,master=self)
        self._logo_label=tk.Label(brand,image=self.logo,bg=PANEL,bd=0,padx=0,pady=0)
        self._logo_label.pack(pady=(0,8))
        nav=tk.Frame(side,bg=PANEL)
        nav.grid(row=1,column=0,sticky='ew')
        for name,label,symbol,action in [
            ('scan','Scan & Rename','search',lambda:self.tabs.select(self.tab_albums)),
            ('lookup','Album Lookup','disc',self.go_editor),
            ('tracks','Track Editor','music',lambda:self.tabs.select(self.track_editor)),
            ('settings','Settings','gear',self.show_settings),
            ('undo','Undo / Backups','undo',lambda:self.tabs.select(self.tab_history)),
            ('logs','View Logs','files',lambda:self.tabs.select(self.tab_history)),
            ('about','About','info',self.show_about),
        ]:
            b=Button(nav,label,action,width=234,height=49,symbol=symbol,navigation=True,font=(self.ui_font,11))
            b.active=name=='scan';b.pack(fill='x',pady=1);self.nav_buttons[name]=b
        self.sidebar_player_panel=Panel(side,height=252,padding=8)
        self.sidebar_player_panel.grid(row=3,column=0,sticky='ew',pady=(4,4))
        tk.Label(side,text=f'Groove Goblin v{__version__}',bg=PANEL,fg=MUTED,font=(self.ui_font,9)).grid(row=4,column=0,sticky='w',pady=(4,8))

        # Main center + compact right rail.
        self.content=tk.Frame(desktop,bg=BG)
        self.content.grid(row=0,column=1,sticky='nsew',padx=(12,10),pady=(10,0))
        self.content.rowconfigure(0,weight=1);self.content.columnconfigure(0,weight=1)
        self.dashboard=tk.Frame(self.content,bg=BG)
        self.dashboard.grid(row=0,column=0,sticky='nsew')
        self.dashboard.columnconfigure(0,weight=1);self.dashboard.columnconfigure(1,minsize=342)
        self.dashboard.rowconfigure(0,weight=1)
        self.tab_history=tk.Frame(self.content,bg=BG)
        self.tabs=PageNavigation(self)
        center=tk.Frame(self.dashboard,bg=BG)
        center.grid(row=0,column=0,sticky='nsew',padx=(0,10))
        center.columnconfigure(0,weight=1);center.rowconfigure(2,weight=3,minsize=420);center.rowconfigure(3,weight=2,minsize=220)

        toolbar=tk.Frame(center,bg=BG)
        toolbar.grid(row=0,column=0,sticky='ew',pady=(5,10))
        toolbar.columnconfigure(3,weight=1)
        Button(toolbar,'Add Folders',self.add_folder,width=174,height=66,symbol='folder',accent='#ffd443',subtitle='Select or drop music folders',font=self.button_font).grid(row=0,column=0,sticky='ew',padx=(0,12))
        Button(toolbar,'Add Files',self.add_files,width=174,height=66,symbol='music',accent='#b52bf4',subtitle='Select specific music files',font=self.button_font).grid(row=0,column=1,sticky='ew',padx=(0,12))
        Button(toolbar,'Clear List',self.clear,width=158,height=66,symbol='cross',accent='#ff464e',subtitle='Remove all items',font=self.button_font).grid(row=0,column=2,sticky='ew',padx=(0,25))
        self.btn_scan=Button(toolbar,'Start Scan',self.scan,width=200,height=66,symbol='play',primary=True,subtitle='Analyze and find metadata',font=self.button_font)
        self.btn_scan.grid(row=0,column=3,sticky='ew')
        checkrow=tk.Frame(center,bg=BG)
        checkrow.grid(row=1,column=0,sticky='ew',pady=(0,10))
        for col,(text,var,width,command,disabled) in enumerate([
            ('Scan subfolders',self.scan_subfolders,140,None,False),
            ('Group by album',self.always_group,140,None,True),
            ('Show only problems',self.show_problems,160,self.populate_albums,False),
            ('Search online after scan',self.auto_lookup,194,None,False),
        ]):
            Check(checkrow,text,var,command,width=width,disabled=disabled,font=(self.ui_font,9)).grid(row=0,column=col,sticky='w',padx=(0,5))
        self.root_text=tk.Label(checkrow,text='',bg=BG,fg=MUTED,font=(self.ui_font,8),anchor='w')
        self.root_text.grid(row=1,column=0,columnspan=4,sticky='ew')

        albums=Panel(center,padding=11)
        albums.grid(row=2,column=0,sticky='nsew',pady=(0,9))
        self.tab_albums=albums.body
        album_header=tk.Frame(albums.body,bg=PANEL);album_header.pack(fill='x',pady=(0,8))
        self.remove_albums_button=Button(album_header,'Remove Selected',self.remove_selected_albums,width=170,height=27,symbol='cross',accent='#ff5264',font=(self.ui_font,9))
        self.remove_albums_button.pack(side='right')
        self.albums_heading=tk.Label(album_header,text='Albums Found   (0)',bg=PANEL,fg=FG,font=(self.ui_font,10,'bold'))
        self.albums_heading.pack(side='left')
        self.albums_tree=Table(albums.body,mode='albums',font=(self.ui_font,10),on_toggle=self.toggle_album_id)
        self.albums_tree.on_toggle_all=self.toggle_all_albums
        self.albums_tree.cover_provider=lambda uid,size:self._art.request(uid,size)
        self.albums_tree.pack(fill='both',expand=True)
        self.albums_tree.bind('<<TreeviewSelect>>',self.on_album_select)
        self.albums_tree.bind('<Double-1>',lambda e:self.go_editor())
        self.albums_tree.body.bind('<Delete>',self.remove_selected_albums)

        preview=Panel(center,padding=11)
        preview.grid(row=3,column=0,sticky='nsew')
        self.tab_preview=preview.body
        tk.Label(preview.body,text='Preview Changes',bg=PANEL,fg=FG,font=(self.ui_font,10,'bold')).pack(anchor='w',pady=(0,7))
        filters=tk.Frame(preview.body,bg=PANEL)
        filters.pack(fill='x',pady=(0,7))
        self.preview_tabs={}
        for name,label,width in [('Folders','Folders (0)',104),('Tags','File Tags (0)',110),('Filenames','File Names (0)',112),('Skipped','Skipped (0)',100)]:
            b=Button(filters,label,lambda value=name:self.set_preview_filter(value),width=width,height=34,font=(self.ui_font,9),green_active=True)
            b.active=name=='Folders';b.pack(side='left',padx=(0,4));self.preview_tabs[name]=b
        views=tk.Frame(preview.body,bg=PANEL)
        views.pack(fill='x',pady=(0,5))
        self.preview_summary=tk.Label(views,text='',bg=PANEL,fg=MUTED,font=(self.ui_font,8),anchor='w')
        self.preview_summary.pack(side='left',fill='x',expand=True)
        Radio(views,'All',self.preview_view,'All',self.refresh_preview,width=65,font=(self.ui_font,9)).pack(side='right')
        Radio(views,'Selected Only',self.preview_view,'Selected',self.refresh_preview,width=118,font=(self.ui_font,9)).pack(side='right')
        self.preview_tree=Table(preview.body,mode='preview',font=(self.ui_font,9),on_toggle=self.toggle_preview_id)
        self.preview_tree.on_toggle_all=self.toggle_all_preview
        self.preview_tree.pack(fill='both',expand=True)
        self.preview_errors=tk.Text(preview.body,height=1,bg=PANEL,fg='#ffcc53',relief='flat',wrap='word',font=(self.ui_font,8),takefocus=False)
        self.preview_errors.pack(fill='x',pady=(4,0));self.preview_errors.configure(state='disabled')
        self.preview_errors.bind('<Button-1>',lambda e:messagebox.showwarning('Review before applying','\n'.join(self.problems[:30])) if self.problems else None)

        self.tab_editor=tk.Frame(self.dashboard,bg=BG,width=342)
        self.tab_editor.grid(row=0,column=1,sticky='nsew')
        self.tab_editor.grid_propagate(False)
        self.tab_editor.columnconfigure(0,weight=1);self.tab_editor.rowconfigure(2,weight=1)
        opts=tk.Frame(self.tab_editor,bg=BG)
        opts.grid(row=0,column=0,sticky='ew',pady=(8,9))
        tk.Label(opts,text='Rename Options',bg=BG,fg=GREEN,font=(self.ui_font,10,'bold')).pack(anchor='w',pady=(0,5))
        self.filename_check=Check(opts,'Rename music files',self.opt_filenames,self.refresh_preview,width=320,font=(self.ui_font,9))
        self.filename_check.pack(anchor='w')
        self.file_format_box=ttk.Combobox(opts,textvariable=self.file_format,values=list(FILE_FORMATS),state='readonly',font=(self.ui_font,9))
        self.file_format_box.pack(fill='x',padx=(27,0),pady=(0,3))
        self.file_format_box.bind('<<ComboboxSelected>>',lambda e:self.refresh_preview())
        Check(opts,'Rename album folders',self.opt_folders,self.refresh_preview,width=320,font=(self.ui_font,9)).pack(anchor='w')
        self.folder_format_box=ttk.Combobox(opts,textvariable=self.folder_format,values=list(FOLDER_FORMATS),state='readonly',font=(self.ui_font,9))
        self.folder_format_box.pack(fill='x',padx=(27,0),pady=(0,3))
        self.folder_format_box.bind('<<ComboboxSelected>>',lambda e:self.refresh_preview())
        Check(opts,'Replace album / year tags',self.opt_tags,self.refresh_preview,width=320,font=(self.ui_font,9)).pack(anchor='w')
        Check(opts,'Keep an undo journal (always on)',self.journal_required,width=320,disabled=True,font=(self.ui_font,9)).pack(anchor='w')

        details=Panel(self.tab_editor,height=322,padding=11)
        details.grid(row=1,column=0,sticky='ew',pady=(0,9))
        body=details.body
        tk.Label(body,text='Selected Album Details',bg=PANEL,fg=FG,font=(self.ui_font,10,'bold')).pack(anchor='w',pady=(0,10))
        form=tk.Frame(body,bg=PANEL);form.pack(fill='x')
        self.cover_box=tk.Canvas(form,width=142,height=146,bg='#060a0d',highlightthickness=1,highlightbackground='#435766')
        self.cover_box.grid(row=0,column=0,rowspan=6,sticky='n',padx=(0,10))
        self.cover_box.create_text(71,67,text='No artwork',fill=MUTED,font=(self.ui_font,9))
        form.columnconfigure(1,weight=1)
        tk.Label(form,text='Artist:',bg=PANEL,fg=MUTED,font=(self.ui_font,9)).grid(row=0,column=1,sticky='w')
        self.artist_entry=ttk.Entry(form,textvariable=self.var_artist,width=19,font=(self.ui_font,9))
        self.artist_entry.grid(row=1,column=1,sticky='ew',pady=(1,6))
        tk.Label(form,text='Album (current):',bg=PANEL,fg=MUTED,font=(self.ui_font,9)).grid(row=2,column=1,sticky='w')
        self.old_album_label=tk.Label(form,text='-',bg=PANEL,fg=FG,font=(self.ui_font,9),anchor='w')
        self.old_album_label.grid(row=3,column=1,sticky='ew',pady=(0,4))
        tk.Label(form,text='Album (new):',bg=PANEL,fg=MUTED,font=(self.ui_font,9)).grid(row=4,column=1,sticky='w')
        self.album_entry=ttk.Entry(form,textvariable=self.var_album,width=19,font=(self.ui_font,9))
        self.album_entry.grid(row=5,column=1,sticky='ew',pady=(1,5))
        yearrow=tk.Frame(body,bg=PANEL);yearrow.pack(fill='x',pady=(4,0))
        self.tracks_info=tk.Label(yearrow,text='Tracks: -',bg=PANEL,fg=MUTED,font=(self.ui_font,9));self.tracks_info.pack(side='left')
        ttk.Entry(yearrow,textvariable=self.var_year,width=7,font=(self.ui_font,9)).pack(side='right')
        tk.Label(yearrow,text='Year:',bg=PANEL,fg=MUTED,font=(self.ui_font,9)).pack(side='right',padx=(0,9))
        self.current_label=tk.Label(body,text='Select an album to inspect its match.',bg=PANEL,fg=MUTED,font=(self.ui_font,8),anchor='w',wraplength=310)
        self.current_label.pack(fill='x',pady=(4,4))
        actions=tk.Frame(body,bg=PANEL);actions.pack(fill='x')
        for col,(text,symbol,fn) in enumerate([('Search Online','search',self.lookup_selected),('Choose Result','list',self.choose_result),('Approve Edit','edit',self.save_match)]):
            actions.columnconfigure(col,weight=1)
            Button(actions,text,fn,width=97,height=58,symbol=symbol,vertical=True,font=(self.ui_font,9)).grid(row=0,column=col,sticky='ew',padx=(0,4 if col<2 else 0))

        results=Panel(self.tab_editor,padding=9)
        results.grid(row=2,column=0,sticky='nsew')
        tk.Label(results.body,text='Search Results (MusicBrainz)',bg=PANEL,fg=FG,font=(self.ui_font,10,'bold')).pack(anchor='w',pady=(0,7))
        self.results_tree=Table(results.body,mode='results',font=(self.ui_font,9),on_choose=self.use_result)
        self.results_tree.cover_provider=self.result_cover
        self.results_tree.pack(fill='both',expand=True)
        self.results_tree.bind('<Double-1>',lambda e:self.use_result())
        self.btn_auto=Button(self.tab_history,'Search All Online',self.lookup_all,width=190,font=self.button_font)
        self.btn_auto.pack(anchor='w',pady=(0,8))
        self.make_history()
        self.refresh_preview()
        from groove_track_editor import TrackEditor
        self.track_editor=TrackEditor(self)
        from groove_responsive import ResponsiveLayout
        self._responsive=ResponsiveLayout(self,dict(sidebar=sidebar,side=side,brand=brand,nav=nav,player=self.sidebar_player_panel,
            center=center,toolbar=toolbar,checkrow=checkrow,albums=albums,preview=preview,filters=filters,views=views,
            opts=opts,details=details,results=results,form=form,yearrow=yearrow,actions=actions,
            footer=footer,footer_spacer=footer_spacer,controls=controls))

    def update_cover(self):
        if not hasattr(self,'cover_box'):return
        self.cover_box.delete('all')
        self._cover_photo=self._art.request(self.selected_id,getattr(self,'cover_size',142)) if self.selected_id else None
        width=int(self.cover_box.cget('width'));height=int(self.cover_box.cget('height'))
        if self._cover_photo:self.cover_box.create_image(width/2,height/2,image=self._cover_photo)
        else:
            size=min(60,width-12)
            icon(self.cover_box,'disc',(width-size)/2,max(4,(height-size)/2-10),size,'#5b7181')
            self.cover_box.create_text(width/2,height-15,text='No artwork' if width<100 else 'No local artwork',fill=MUTED,font=(self.ui_font,8))

    def show_editor(self):
        old_show(self)
        album=self.selected_album()
        if album:
            self.old_album_label.configure(text=album.old_album[:27] or '(missing)')
            self.tracks_info.configure(text=f'Tracks: {album.file_count}')
            self.current_label.configure(text=album.match_source+' | '+('approved' if album.approved else 'needs your approval'))
        self.update_cover()
        if self.preview_view.get()=='Selected':self.refresh_preview()

    def result_cover(self,row,size):
        album=self.selected_album()
        if not album:return None
        index=int(row)
        if index>=len(album.lookup_results):return None
        return self._art.request_result(album.lookup_results[index].get('id'),size)

    def choose_result(self):
        if self.results_tree.selection():self.use_result()
        else:self.results_tree.body.focus_set();self.status.set('Select an online result, then click its Select button.')

    def show_settings(self):
        self.tabs.select(self.tab_albums)
        window=tk.Toplevel(self);window.title('Groove Goblin - Settings');window.configure(bg=BG);window.geometry('460x260')
        Check(window,'Search MusicBrainz after scan',self.auto_lookup,width=390,font=(self.ui_font,10)).pack(anchor='w',padx=20,pady=(20,5))
        tk.Label(window,text='Online searches send artist / album lookup text,\nnot audio files. Results can load public cover previews.\nTurn online scanning off to work offline.\n\nUndo journals save changed fields and paths.\nKeep separate music backups.',bg=BG,fg=MUTED,font=(self.ui_font,10),justify='left').pack(anchor='w',padx=20,pady=10)
        Button(window,'Search All Albums Online',self.lookup_all,width=260,font=self.button_font).pack(anchor='w',padx=20)

    def add_files(self):
        if self.worker_busy:return
        files=filedialog.askopenfilenames(title='Select music files',filetypes=[('Supported music',FILE_PATTERN),('All files','*.*')])
        self.add_paths(files)

    def populate_albums(self):
        if not hasattr(self,'albums_tree'):return
        tree=self.albums_tree
        selection=tree.selection()
        tree.delete(*tree.get_children())
        for a in self.matched:
            if self.show_problems.get() and a.status=='READY' and a.enabled:continue
            tag='ready' if a.status=='READY' else ('disabled' if not a.enabled else 'review')
            tree.insert('','end',iid=a.uid,values=('✓' if a.enabled else '−',a.artist,a.old_album,a.album,a.year,a.file_count,a.status,f'{int(a.confidence*100)}%'),tags=(tag,))
        self.count.set(f'{len(self.matched)} albums | {sum(a.file_count for a in self.matched)} files')
        self.albums_heading.configure(text=f'Albums Found   ({len(tree.get_children())})')
        selection=[uid for uid in selection if uid in tree.data]
        if selection:tree.selection_set(selection)
        elif self.selected_id in tree.data:tree.selection_set(self.selected_id)

    def remove_selected_albums(self,event=None):
        if self.worker_busy:
            self.status.set('Wait for the current operation to finish before removing albums.')
            return 'break'
        removed=set(self.albums_tree.selection())
        if not removed:
            self.status.set('Select album rows to remove. Use Ctrl-click or Shift-click for multiple albums.')
            return 'break'
        self.matched=[album for album in self.matched if album.uid not in removed]
        self.album_map={album.uid:album for album in self.matched}
        if self.selected_id in removed:
            self.selected_id=None
            self.results_tree.delete(*self.results_tree.get_children())
            for var in (self.var_artist,self.var_album,self.var_year):var.set('')
            self.current_label.configure(text='Select an album to inspect its match.')
            self.old_album_label.configure(text='-');self.tracks_info.configure(text='Tracks: -')
            self.update_cover()
        self.populate_albums();self.refresh_preview()
        self.status.set(f'Removed {len(removed)} album(s) from the list. Music files are unchanged.')
        return 'break'

    def toggle_album_id(self,uid):
        if self.worker_busy:return
        album=self.album_map.get(uid)
        if album:
            self.selected_id=uid
            album.enabled=not album.enabled;self.var_enabled.set(album.enabled);self.populate_albums();self.refresh_preview()

    def toggle_all_albums(self):
        if self.worker_busy:return
        albums=[self.album_map[uid] for uid in self.albums_tree.get_children()]
        enable=not all(a.enabled for a in albums)
        for album in albums:album.enabled=enable
        self.populate_albums();self.refresh_preview()
        if self.selected_album():self.show_editor()

    def toggle_preview_id(self,row):
        if row in self.preview_tree.data:
            self.toggle_album_id(self.preview_tree.item(row).get('album_uid'))

    def toggle_all_preview(self):
        if self.worker_busy:return
        ids={row.get('album_uid') for row in self.preview_tree.data.values()}
        albums=[self.album_map[uid] for uid in ids if uid in self.album_map]
        if not albums:return
        enable=not all(a.enabled for a in albums)
        for album in albums:album.enabled=enable
        self.populate_albums();self.refresh_preview()
        if self.selected_album():self.show_editor()

    def set_preview_filter(self,value):self.preview_filter.set(value);self.refresh_preview()

    def refresh_preview(self):
        if not hasattr(self,'preview_tree'):return
        self.actions,self.problems=plan_actions(self.matched,self.option_dict())
        self.preview_tree.delete(*self.preview_tree.get_children())
        rows=[];folders=tags=filenames=0
        for action in self.actions:
            common={'album_uid':action['album_uid'],'files':len(action['tracks'])}
            if action['folder']!=action['dest_folder']:
                folders+=1;rows.append(('FOLDER',action['folder'],action['dest_folder'],str(len(action['tracks'])),common))
            for track in action['tracks']:
                if track['needs_tags']:
                    tags+=1;rows.append(('TAGS',track['old_path'],f'{action["album"]} ({action["year"]})',action['artist'],{**common,'files':1}))
                if track['old_name']!=track['new_name']:
                    filenames+=1;rows.append(('FILENAME',track['old_path'],track['new_name'],action['artist'],{**common,'files':1}))
        planned={action['album_uid'] for action in self.actions}
        skipped=[a for a in self.matched if not a.enabled or a.uid not in planned]
        chosen={'Folders':'FOLDER','Tags':'TAGS','Filenames':'FILENAME'}.get(self.preview_filter.get())
        if self.preview_filter.get()=='Skipped':
            for album in skipped:
                if self.preview_view.get()=='Selected' and album.uid!=self.selected_id:continue
                self.preview_tree.insert('','end',values=('SKIP',album.folder,'Skipped' if not album.enabled else ('Awaiting approval' if album.status!='READY' else 'Review naming / metadata'),album.match_source),album_uid=album.uid,files=album.file_count,enabled=album.enabled)
        else:
            for kind,old,new,detail,extra in rows:
                if chosen and kind!=chosen:continue
                if self.preview_view.get()=='Selected' and extra['album_uid']!=self.selected_id:continue
                self.preview_tree.insert('','end',values=(kind,old,new,detail),**extra)
        counts={'Folders':folders,'Tags':tags,'Filenames':filenames,'Skipped':len(skipped)}
        labels={'Folders':'Folders','Tags':'File Tags','Filenames':'File Names','Skipped':'Skipped'}
        for name,b in self.preview_tabs.items():
            b.text=f'{labels[name]} ({counts[name]})';b.active=self.preview_filter.get()==name;b.draw()
        self.preview_summary.configure(text=f'{folders} folders | {tags} tags | {len(skipped)} skipped / review')
        self.preview_errors.configure(state='normal');self.preview_errors.delete('1.0','end')
        for issue in self.problems:self.preview_errors.insert('end',issue.rsplit(': ',1)[-1]+'\n')
        self.preview_errors.configure(state='disabled')
        changes=sum(a['changed'] for a in self.actions)
        self.btn_apply.configure(text=f'Apply Selected Changes ({changes})')
        self.btn_apply.state(['!disabled'] if changes and not self.problems and not self.worker_busy else ['disabled'])

    def clear(self):
        if self.worker_busy:return
        old_clear(self)
        self.current_label.configure(text='Select an album to inspect its match.')
        self.old_album_label.configure(text='-');self.tracks_info.configure(text='Tracks: -')
        for var in (self.var_artist,self.var_album,self.var_year):var.set('')
        self.results_tree.delete(*self.results_tree.get_children())
        self.update_cover()

    def zoom(self,direction):
        self.font_size=max(8,min(14,self.font_size+direction))
        self.build_style()
        for table in (self.albums_tree,self.preview_tree,self.results_tree):
            table.font=(self.ui_font,self.font_size);table.rowheight=max(32,self.font_size*3) if table.mode!='results' else max(66,self.font_size*6);table.schedule()
        self._responsive.apply()
        self.status.set('Table text size: '+str(self.font_size))

    cls.build_style=build_style;cls.build_ui=build_ui
    cls.refresh_preview=refresh_preview;cls.clear=clear;cls.show_editor=show_editor
    cls.populate_albums=populate_albums;cls.update_cover=update_cover;cls.result_cover=result_cover;cls.choose_result=choose_result
    cls.show_settings=show_settings;cls.show_about=show_about;cls.add_files=add_files
    cls.remove_selected_albums=remove_selected_albums
    cls.toggle_all_preview=toggle_all_preview
    cls.toggle_all_albums=toggle_all_albums
    cls.toggle_album_id=toggle_album_id;cls.toggle_preview_id=toggle_preview_id
    cls.set_preview_filter=set_preview_filter;cls.zoom=zoom
