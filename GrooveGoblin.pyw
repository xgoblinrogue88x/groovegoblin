"""Groove Goblin - dark Windows GUI for multi-album FLAC/MP3 tagging.
Run with Python 3.10+ and the packages in requirements.txt. Uses built-in tkinter; no cloud account.
"""
import os, queue, sys, threading, traceback, json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from groove_drop import FolderDropMixin
from groove_version import __version__
from groove_naming import DEFAULT_FILE_FORMAT, DEFAULT_FOLDER_FORMAT
from groove_core import (scan_folders, plan_actions, apply_actions, undo_journal,
                         newest_journal, export_preview, backup_dir, year4)
from musicbrainz_client import MusicBrainz

BASE=Path(__file__).resolve().parent
BG='#0a1117'; PANEL='#131d27'; PANEL2='#1a2530'; INPUT='#202c38'; LINE='#31404e'
FG='#e9f2f4'; MUTED='#9eb0bd'; GREEN='#71f28b'; PURPLE='#cc75ff'; ORANGE='#ffc777'

class GrooveGoblin(FolderDropMixin, tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f'Groove Goblin {__version__} - Music Tagger & Organizer')
        self.geometry('1220x790');self.minsize(740,520)
        self.configure(bg=BG)
        try:self.iconphoto(True,tk.PhotoImage(file=str(BASE/'assets/groove_goblin_icon.png')))
        except Exception:pass
        self.matched=[];self.roots=[];self.album_map={};self.selected_id=None
        self.queue=queue.Queue();self.worker_busy=False;self.cancel=threading.Event()
        self.mb=MusicBrainz();self.actions=[];self.problems=[]
        self.auto_lookup=tk.BooleanVar(value=True)
        self.opt_tags=tk.BooleanVar(value=True)
        self.opt_folders=tk.BooleanVar(value=True)
        self.opt_filenames=tk.BooleanVar(value=False)
        self.file_format=tk.StringVar(value=DEFAULT_FILE_FORMAT)
        self.folder_format=tk.StringVar(value=DEFAULT_FOLDER_FORMAT)
        self.var_artist=tk.StringVar();self.var_album=tk.StringVar();self.var_year=tk.StringVar()
        self.var_search=tk.StringVar();self.var_enabled=tk.BooleanVar(value=True)
        self.status=tk.StringVar(value='Add one or more artist or album folders to begin.')
        self.count=tk.StringVar(value='0 albums · 0 files')
        self.font_size=10
        self.build_style();self.build_ui()
        self.update_roots()
        self.install_folder_drop()
        self.after(120,self.poll_queue)
        self.bind('<F11>',lambda e:self.toggle_fullscreen())
        self.bind('<Escape>',lambda e:self.attributes('-fullscreen',False))
        self.bind('<Control-plus>',lambda e:self.zoom(1))
        self.bind('<Control-equal>',lambda e:self.zoom(1))
        self.bind('<Control-minus>',lambda e:self.zoom(-1))
        self.protocol('WM_DELETE_WINDOW',self.confirm_close)

    def build_style(self):
        s=ttk.Style(self);s.theme_use('clam')
        s.configure('.',background=BG,foreground=FG,font=('Segoe UI',self.font_size))
        s.configure('TFrame',background=BG);s.configure('Panel.TFrame',background=PANEL)
        s.configure('TLabel',background=BG,foreground=FG)
        s.configure('Muted.TLabel',background=BG,foreground=MUTED)
        s.configure('Brand.TLabel',background=BG,foreground=GREEN,font=('Segoe UI Black',23,'bold'))
        s.configure('TLabelframe',background=BG,foreground=GREEN,bordercolor=LINE)
        s.configure('TLabelframe.Label',background=BG,foreground=GREEN,font=('Segoe UI',10,'bold'))
        s.configure('TCheckbutton',background=BG,foreground=FG,focuscolor=BG)
        s.map('TCheckbutton',background=[('active',BG)],foreground=[('disabled',MUTED)])
        s.configure('TButton',background=PANEL2,foreground=FG,padding=(11,8),borderwidth=1,bordercolor=LINE)
        s.map('TButton',background=[('active','#2c4051'),('disabled',PANEL)],foreground=[('disabled',MUTED)])
        s.configure('Go.TButton',background='#61228b',foreground='#ffffff',padding=(16,9),bordercolor='#ad45db')
        s.map('Go.TButton',background=[('active','#8229b2'),('disabled','#3d2a48')])
        s.configure('Apply.TButton',background='#1d7939',foreground='#ffffff',padding=(13,9),bordercolor=GREEN)
        s.map('Apply.TButton',background=[('active','#26934b'),('disabled','#223a2a')])
        s.configure('TNotebook',background=BG,borderwidth=0)
        s.configure('TNotebook.Tab',background=PANEL2,foreground=FG,padding=(14,10),font=('Segoe UI',10,'bold'))
        s.map('TNotebook.Tab',background=[('selected','#46205f'),('active','#273949')],foreground=[('selected','#ffffff')])
        s.configure('Treeview',background=PANEL,fieldbackground=PANEL,foreground=FG,rowheight=27,borderwidth=0)
        s.configure('Treeview.Heading',background=PANEL2,foreground=GREEN,relief='flat',font=('Segoe UI',10,'bold'),padding=5)
        s.map('Treeview',background=[('selected','#47315f')],foreground=[('selected','#ffffff')])
        s.configure('TEntry',fieldbackground=INPUT,foreground=FG,insertcolor=FG,bordercolor=LINE,padding=6)
        s.configure('TScrollbar',background=PANEL2,troughcolor=BG,arrowcolor=FG)

    def build_ui(self):
        head=ttk.Frame(self,padding=(14,9,14,4));head.pack(fill='x')
        try:
            logo=tk.PhotoImage(file=str(BASE/'assets/groove_goblin_logo.png'))
            # Pure Tk subsample, no Pillow dependency in installed app.
            self.logo=logo.subsample(3,3)
            ttk.Label(head,image=self.logo).pack(side='left',padx=(0,14))
        except Exception:pass
        htxt=ttk.Frame(head);htxt.pack(side='left',fill='x',expand=True)
        ttk.Label(htxt,text='GROOVE GOBLIN',style='Brand.TLabel').pack(anchor='w')
        ttk.Label(htxt,text='Batch music metadata · Online album lookup · Preview · Undo',style='Muted.TLabel').pack(anchor='w',pady=(3,5))
        ttk.Label(head,textvariable=self.count,style='Muted.TLabel').pack(side='right',padx=8)

        bar=ttk.Frame(self,padding=(14,4));bar.pack(fill='x')
        first=ttk.Frame(bar);first.pack(fill='x')
        second=ttk.Frame(bar);second.pack(fill='x',pady=(4,0))
        ttk.Button(first,text='+ Add folder',command=self.add_folder).pack(side='left',padx=(0,6))
        ttk.Button(first,text='Clear',command=self.clear).pack(side='left',padx=(0,6))
        self.btn_scan=ttk.Button(first,text='▶ Analyze',style='Go.TButton',command=self.scan)
        self.btn_scan.pack(side='left',padx=(0,6))
        self.btn_auto=ttk.Button(second,text='Search all online',command=self.lookup_all)
        self.btn_auto.pack(side='left',padx=(0,6))
        ttk.Button(second,text='Export preview',command=self.export).pack(side='left',padx=(0,6))
        ttk.Button(second,text='⛶ Fullscreen (F11)',command=self.toggle_fullscreen).pack(side='right')
        opts=ttk.Frame(self,padding=(15,7));opts.pack(fill='x')
        for index,(txt,v) in enumerate([('Auto-search online after scan',self.auto_lookup),('Update tags',self.opt_tags),
                      ('Rename album folders',self.opt_folders),('Rename filenames (optional)',self.opt_filenames)]):
            ttk.Checkbutton(opts,text=txt,variable=v,command=self.refresh_preview).grid(row=index//2,column=index%2,sticky='w',padx=(0,20),pady=2)
        rootline=ttk.Frame(self,padding=(16,0,16,5));rootline.pack(fill='x')
        ttk.Label(rootline,text='Folders:',style='Muted.TLabel').pack(side='left')
        self.root_text=ttk.Label(rootline,text='(none selected)',style='Muted.TLabel')
        self.root_text.pack(side='left',padx=7)

        self.tabs=ttk.Notebook(self);self.tabs.pack(fill='both',expand=True,padx=12,pady=(3,3))
        self.tab_albums=ttk.Frame(self.tabs,padding=9);self.tabs.add(self.tab_albums,text='Albums & Matches')
        self.tab_editor=ttk.Frame(self.tabs,padding=9);self.tabs.add(self.tab_editor,text='Manual Match / Online Lookup')
        self.tab_preview=ttk.Frame(self.tabs,padding=9);self.tabs.add(self.tab_preview,text='Preview Changes')
        self.tab_history=ttk.Frame(self.tabs,padding=9);self.tabs.add(self.tab_history,text='Logs & Undo')
        self.make_albums();self.make_editor();self.make_preview();self.make_history()

        bottom=ttk.Frame(self,padding=(13,5,13,12));bottom.pack(fill='x')
        ttk.Label(bottom,textvariable=self.status,style='Muted.TLabel').pack(side='left',fill='x',expand=True)
        self.btn_cancel=ttk.Button(bottom,text='Cancel search',command=self.cancel_search)
        self.btn_cancel.pack(side='right',padx=(6,0));self.btn_cancel.state(['disabled'])
        self.btn_apply=ttk.Button(bottom,text='✓ Apply Previewed Changes',style='Apply.TButton',command=self.apply)
        self.btn_apply.pack(side='right',padx=(6,0))
        self.btn_apply.state(['disabled'])
        # Reserve room for bottom actions BEFORE the expanding notebook claims space.
        bottom.pack_forget()
        bottom.pack(side='bottom',before=self.tabs,fill='x')

    def new_tree(self,parent,columns,widths,labels=None):
        wrap=ttk.Frame(parent);wrap.pack(fill='both',expand=True)
        t=ttk.Treeview(wrap,columns=columns,show='headings',selectmode='browse')
        for i,key in enumerate(columns):
            t.heading(key,text=(labels[i] if labels else key))
            t.column(key,width=widths[i],minwidth=75,stretch=(i in [0,1]))
        sy=ttk.Scrollbar(wrap,orient='vertical',command=t.yview)
        sx=ttk.Scrollbar(wrap,orient='horizontal',command=t.xview)
        t.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
        wrap.grid_rowconfigure(0,weight=1);wrap.grid_columnconfigure(0,weight=1)
        t.grid(row=0,column=0,sticky='nsew');sy.grid(row=0,column=1,sticky='ns');sx.grid(row=1,column=0,sticky='ew')
        t.tag_configure('ready',foreground=GREEN)
        t.tag_configure('review',foreground=ORANGE)
        t.tag_configure('disabled',foreground=MUTED)
        return t

    def make_albums(self):
        row=ttk.Frame(self.tab_albums);row.pack(fill='x',pady=(0,7))
        ttk.Label(row,text='One row per music-containing folder. Click an album to inspect it.').pack(side='left')
        ttk.Button(row,text='Match / edit selected',command=self.go_editor).pack(side='right',padx=(5,0))
        ttk.Button(row,text='Enable / Disable',command=self.toggle_selected).pack(side='right')
        self.albums_tree=self.new_tree(self.tab_albums,('Use','Artist','Current album','Proposed album','Year','Tracks','Status','Match'),[55,160,205,240,80,60,135,95])
        self.albums_tree.bind('<<TreeviewSelect>>',self.on_album_select)
        self.albums_tree.bind('<Double-1>',lambda e:self.go_editor())

    def make_editor(self):
        pane=ttk.Frame(self.tab_editor);pane.pack(fill='both',expand=True)
        ttk.Label(pane,text='Correct the selected album, or search MusicBrainz and choose a result.',style='Muted.TLabel').pack(anchor='w',pady=(0,8))
        self.current_label=ttk.Label(pane,text='Select an album from the first tab.',style='Muted.TLabel',wraplength=640)
        self.current_label.pack(fill='x',pady=(0,8))
        form=ttk.Frame(pane);form.pack(fill='x')
        for n,(txt,var) in enumerate([('Artist',self.var_artist),('Album',self.var_album),('Original release year',self.var_year)]):
            ttk.Label(form,text=txt).grid(row=n,column=0,sticky='w',padx=(0,8),pady=4)
            ttk.Entry(form,textvariable=var).grid(row=n,column=1,sticky='ew',pady=4)
        form.columnconfigure(1,weight=1)
        cmds=ttk.Frame(pane);cmds.pack(fill='x',pady=7)
        ttk.Button(cmds,text='✓ Save & approve match',style='Apply.TButton',command=self.save_match).pack(side='left',padx=(0,8))
        ttk.Button(cmds,text='Search online for this artist / album',command=self.lookup_selected).pack(side='left',padx=(0,8))
        ttk.Checkbutton(cmds,text='Include in batch',variable=self.var_enabled,command=self.set_enabled).pack(side='left')
        ttk.Label(pane,text='MusicBrainz search results (double-click to select):').pack(anchor='w',pady=(10,5))
        self.results_tree=self.new_tree(pane,('Album','Artist','Year','Type','Score'),[310,160,80,105,70])
        self.results_tree.bind('<Double-1>',lambda e:self.use_result())
        row=ttk.Frame(pane);row.pack(fill='x',pady=7)
        ttk.Button(row,text='Use highlighted result',command=self.use_result).pack(side='left')
        self.tracks_info=ttk.Label(row,text='',style='Muted.TLabel')
        self.tracks_info.pack(side='right')

    def make_preview(self):
        row=ttk.Frame(self.tab_preview);row.pack(fill='x',pady=(0,6))
        self.preview_summary=ttk.Label(row,text='Run a scan to generate a read-only preview.')
        self.preview_summary.pack(side='left')
        ttk.Button(row,text='Export .txt report',command=self.export).pack(side='right')
        self.preview_tree=self.new_tree(self.tab_preview,('Action','Existing','Proposed','Detail'),[120,360,400,250])
        warn=ttk.Frame(self.tab_preview);warn.pack(fill='x',pady=(6,0))
        ttk.Label(warn,text='Review / blocked:',style='Muted.TLabel').pack(anchor='w')
        self.preview_errors=tk.Text(warn,height=4,bg=PANEL,fg=ORANGE,insertbackground=FG,relief='flat',wrap='word',font=('Consolas',9))
        self.preview_errors.pack(fill='x')
        self.preview_errors.configure(state='disabled')

    def make_history(self):
        row=ttk.Frame(self.tab_history);row.pack(fill='x',pady=(0,8))
        ttk.Button(row,text='↶ Undo last apply',command=self.undo).pack(side='left',padx=(0,8))
        ttk.Button(row,text='Open backup/log folder',command=self.open_logs).pack(side='left',padx=(0,8))
        ttk.Button(row,text='View last journal',command=self.view_journal).pack(side='left')
        self.log_box=tk.Text(self.tab_history,bg=PANEL,fg=FG,insertbackground=GREEN,wrap='word',relief='flat',font=('Consolas',10))
        self.log_box.pack(fill='both',expand=True)
        self.log('Welcome to Groove Goblin. FLAC and MP3 supported. No files are changed by scanning.')

    def log(self,s):
        if not hasattr(self,'log_box'):return
        self.log_box.insert('end',s+'\n');self.log_box.see('end')

    def zoom(self,direction):
        self.font_size=max(8,min(16,self.font_size+direction))
        self.build_style()
        self.log('UI text size: '+str(self.font_size))

    def toggle_fullscreen(self): self.attributes('-fullscreen',not bool(self.attributes('-fullscreen')))
    def confirm_close(self):
        if self.worker_busy and not messagebox.askyesno('Work in progress','A file operation, scan or lookup is running. Close Groove Goblin anyway?'):return
        if hasattr(self,'track_editor') and (self.track_editor.pending or self.track_editor.inline or any(v.get() for v in self.track_editor.enabled.values())):
            if not messagebox.askyesno('Unsaved track edits','Discard unsaved Track Editor changes and close?'):return
        self.cancel.set();self.destroy()

    def is_busy(self):return self.worker_busy
    def run_background(self,work):
        if self.worker_busy:
            messagebox.showinfo('Please wait','Another scan, lookup, or file operation is already running.');return
        self.worker_busy=True;self.cancel.clear()
        self.btn_scan.state(['disabled']);self.btn_auto.state(['disabled']);self.btn_cancel.state(['!disabled']);self.btn_apply.state(['disabled'])
        def runner():
            try:work()
            except Exception as e:self.queue.put(('error',str(e)+'\n\n'+traceback.format_exc(limit=3)))
            finally:self.queue.put(('idle',))
        threading.Thread(target=runner,daemon=True).start()

    def poll_queue(self):
        try:
            while True:
                typ,*args=self.queue.get_nowait()
                if typ.startswith('manual_'):
                    self.track_editor.handle_event(typ,*args)
                elif typ=='status':self.status.set(args[0])
                elif typ=='log':self.log(args[0])
                elif typ=='scan_done':
                    self.matched=args[0];self.album_map={a.uid:a for a in self.matched}
                    self.populate_albums();self.refresh_preview()
                    self.status.set(f'Scanned {len(self.matched)} album folders; {sum(a.file_count for a in self.matched)} files.')
                    for x in args[1][:25]:self.log('SCAN SKIP: '+x)
                    if self._active_page=='tracks':self._import_tracks_after_scan=True
                elif typ=='suggest':
                    uid,suggestion,results=args
                    if uid in self.album_map:
                        a=self.album_map[uid];a.lookup_results=results
                        if suggestion and not a.approved:
                            a.album=suggestion['title'];a.year=suggestion['year'];a.mbid=suggestion['id']
                            a.match_source='MusicBrainz suggested (review)';a.confidence=suggestion.get('score',0)/100
                        self.populate_albums();self.refresh_preview()
                        if uid==self.selected_id:self.show_editor()
                elif typ=='results':
                    uid,results=args
                    if uid in self.album_map:
                        a=self.album_map[uid];a.lookup_results=results
                        if self.selected_id==uid:self.populate_results(a)
                elif typ=='apply_done':
                    self.log('APPLY COMPLETE. Undo journal: '+str(args[0]));self.status.set('Applied changes. Undo is available in Logs & Undo.')
                    self.matched=[];self.album_map={};self.populate_albums();self.refresh_preview();self.tabs.select(self.tab_history)
                    messagebox.showinfo('Groove Goblin','Changes applied successfully. Undo information has been saved.')
                elif typ=='undo_done':
                    err=args[0]
                    if err: messagebox.showwarning('Undo partially completed','\n'.join(err[:12]));self.log('UNDO WARNINGS:\n'+'\n'.join(err))
                    else:messagebox.showinfo('Undo complete','Original folder names, file names, and edited tags have been restored.');self.log('Undo completed.')
                    self.matched=[];self.album_map={};self.populate_albums();self.refresh_preview()
                elif typ=='error':
                    self.log('ERROR:\n'+args[0]);messagebox.showerror('Groove Goblin',args[0].split('\n\n')[0]);self.status.set('An error occurred. Details are in Logs & Undo.')
                elif typ=='idle':
                    self.worker_busy=False;self.btn_scan.state(['!disabled']);self.btn_auto.state(['!disabled']);self.btn_cancel.state(['disabled']);self.refresh_preview()
                    if getattr(self,'_import_tracks_after_scan',False):
                        self._import_tracks_after_scan=False;self.track_editor.import_scan()
        except queue.Empty:pass
        try:self.after(120,self.poll_queue)
        except tk.TclError:pass

    def add_folder(self):
        if self.worker_busy:return
        p=filedialog.askdirectory(title='Choose a folder containing music (subfolders included)',mustexist=True)
        if not p:return
        self.add_folder_paths([p])
    def clear(self):
        if self.worker_busy:return
        self.roots=[];self.matched=[];self.album_map={};self.selected_id=None
        self.update_roots();self.populate_albums();self.refresh_preview()
    def update_roots(self):
        self.root_text.configure(text=(f'{len(self.roots)} selected: '+', '.join(Path(x).name[:25] for x in self.roots[:2])+(' ...' if len(self.roots)>2 else '')) if self.roots else 'Add or drop folders / files here.')
    def scan(self):
        if not self.roots:messagebox.showinfo('Add folders first','Choose one or more music folders to scan.');return
        self.matched=[];self.album_map={};self.populate_albums();self.refresh_preview()
        roots=list(self.roots)
        auto_lookup=self.auto_lookup.get()
        recursive=self.scan_subfolders.get()
        def work():
            albums,errors=scan_folders(roots,lambda s:self.queue.put(('status',s)),self.cancel,recursive=recursive)
            self.queue.put(('scan_done',albums,errors))
            if auto_lookup and not self.cancel.is_set():self.worker_match_albums(albums)
        self.run_background(work)
    def worker_match_albums(self,albums):
        for i,a in enumerate(albums,1):
            if self.cancel.is_set():break
            if a.approved:continue
            if not a.artist:
                self.queue.put(('log','No artist for: '+a.folder));continue
            self.queue.put(('status',f'Online matching {i}/{len(albums)}: {a.artist} / {a.old_album or Path(a.folder).name}'))
            try:
                result,results=self.mb.suggest(a)
                self.queue.put(('suggest',a.uid,result,results))
            except Exception as e:self.queue.put(('log',f'Online lookup failed for {a.folder}: {e}'))
        self.queue.put(('status','Online lookup finished. Review and approve the proposed matches.'))
    def lookup_all(self):
        if not self.matched:messagebox.showinfo('Scan first','Scan music folders before searching online.');return
        albums=list(self.matched)
        self.run_background(lambda:self.worker_match_albums(albums))
    def cancel_search(self):
        self.cancel.set();self.status.set('Stopping after current file or online request...')

    def populate_albums(self):
        for id in self.albums_tree.get_children():self.albums_tree.delete(id)
        for a in self.matched:
            t='ready' if a.status=='READY' else ('disabled' if not a.enabled else 'review')
            self.albums_tree.insert('', 'end',iid=a.uid,values=('✓' if a.enabled else '−',a.artist,a.old_album,a.album,
                   a.year,a.file_count,a.status,f'{int(a.confidence*100)}%'),tags=(t,))
        self.count.set(f'{len(self.matched)} albums · {sum(a.file_count for a in self.matched)} files')
        if self.selected_id in self.album_map:self.albums_tree.selection_set(self.selected_id)

    def on_album_select(self,event=None):
        sel=self.albums_tree.selection()
        if sel:self.selected_id=sel[0];self.show_editor()
    def selected_album(self):return self.album_map.get(self.selected_id)
    def go_editor(self):
        if not self.selected_album():messagebox.showinfo('Choose an album','Select an album row first.');return
        self.tabs.select(self.tab_editor);self.show_editor()
    def show_editor(self):
        a=self.selected_album()
        if not a:return
        self.current_label.configure(text=f'Folder: {a.folder}\nCurrent tag: {a.old_album or "(missing)"}    |    Match: {a.match_source}')
        self.var_artist.set(a.artist);self.var_album.set(a.album);self.var_year.set(a.year);self.var_enabled.set(a.enabled)
        self.tracks_info.configure(text=f'{a.file_count} tracks; sample: '+', '.join(t.title for t in a.tracks[:3])[:54])
        self.populate_results(a)
    def populate_results(self,a):
        for k in self.results_tree.get_children():self.results_tree.delete(k)
        for i,r in enumerate(a.lookup_results):
            self.results_tree.insert('', 'end',iid=str(i),values=(r.get('title',''),r.get('artist',''),r.get('year',''),r.get('type',''),r.get('score','')))
    def save_match(self):
        a=self.selected_album()
        if not a:return
        artist=self.var_artist.get().strip();album=self.var_album.get().strip();year=year4(self.var_year.get())
        if not artist or not album or not year:
            messagebox.showwarning('Missing match information','Enter an artist, an album name, and a valid four-digit release year.');return
        a.artist=artist;a.album=album;a.year=year;a.enabled=self.var_enabled.get()
        a.approved=True;a.match_source='Manually approved';a.confidence=1.0
        self.populate_albums();self.refresh_preview();self.status.set('Album approved. Review the preview below before applying.')
    def set_enabled(self):
        a=self.selected_album()
        if a:a.enabled=self.var_enabled.get();self.populate_albums();self.refresh_preview()
    def toggle_selected(self):
        a=self.selected_album()
        if a:a.enabled=not a.enabled;self.populate_albums();self.refresh_preview()
    def lookup_selected(self):
        a=self.selected_album()
        if not a:return
        artist=self.var_artist.get().strip();album=self.var_album.get().strip()
        if not artist:messagebox.showwarning('Artist required','Enter an artist to search MusicBrainz.');return
        def work():
            self.queue.put(('status',f'Searching MusicBrainz for {artist} / {album or "all albums"}...'))
            hits=self.mb.search_albums(artist,album,limit=35)
            if not hits and album:hits=self.mb.search_albums(artist,'',limit=35)
            self.queue.put(('results',a.uid,hits))
            self.queue.put(('status',f'Found {len(hits)} possible release groups for {artist}.'))
        self.run_background(work)
    def use_result(self):
        a=self.selected_album();selection=self.results_tree.selection()
        if not a or not selection:return
        r=a.lookup_results[int(selection[0])]
        if not r.get('year'):messagebox.showwarning('No original release year','This database entry has no earliest release year. Enter a year manually.');return
        self.var_artist.set(r['artist'] or a.artist);self.var_album.set(r['title']);self.var_year.set(r['year'])
        self.save_match();a.match_source='MusicBrainz result chosen manually';a.mbid=r['id'];self.populate_albums()

    def option_dict(self):return {'tags':self.opt_tags.get(),'folders':self.opt_folders.get(),'filenames':self.opt_filenames.get(),
                                  'file_format':self.file_format.get(),'folder_format':self.folder_format.get()}
    def refresh_preview(self):
        if not hasattr(self,'preview_tree'):return
        self.actions,self.problems=plan_actions(self.matched,self.option_dict())
        tree=self.preview_tree
        for k in tree.get_children():tree.delete(k)
        tags=files=folders=0
        for a in self.actions:
            folder_changed=a['dest_folder']!=a['folder']
            if folder_changed:
                tree.insert('', 'end',values=('FOLDER',a['folder'],a['dest_folder'],f'{len(a["tracks"])} files'))
                folders+=1
            for t in a['tracks']:
                if t['needs_tags']:
                    tags+=1
                    tree.insert('', 'end',values=('TAGS',t['old_name'],f'{a["album"]} ({a["year"]})',a['artist']))
                if t['old_name']!=t['new_name']:
                    files+=1
                    tree.insert('', 'end',values=('FILENAME',t['old_name'],t['new_name'],Path(a['folder']).name))
        review=sum(a.enabled and a.status!='READY' for a in self.matched)
        self.preview_summary.configure(text=f'{folders} folders · {tags} tag updates · {files} filenames · {review} albums need review')
        self.preview_errors.configure(state='normal');self.preview_errors.delete('1.0','end')
        for p in (self.problems or ['No blocking issues in approved selections.']):self.preview_errors.insert('end',p+'\n')
        self.preview_errors.configure(state='disabled')
        if any(a['changed'] for a in self.actions) and not self.problems and not self.worker_busy:self.btn_apply.state(['!disabled'])
        else:self.btn_apply.state(['disabled'])

    def export(self):
        if not self.matched:messagebox.showinfo('Nothing to export','Scan music first.');return
        p=filedialog.asksaveasfilename(title='Save preview',defaultextension='.txt',filetypes=[('Text report','*.txt')],initialfile='Groove_Goblin_Preview.txt')
        if p:
            export_preview(self.actions,self.problems,p);self.status.set('Read-only preview saved to '+p)

    def apply(self):
        self.refresh_preview()
        tochange=[a for a in self.actions if a['changed']]
        if self.problems:
            self.tabs.select(self.tab_preview)
            messagebox.showwarning('Resolve review items','Some enabled albums have no approved match or conflict with existing folders. Review the Preview Changes tab, or disable those albums.');return
        if not tochange:messagebox.showinfo('Nothing to change','All selected albums already match your requested naming format.');return
        if not messagebox.askyesno('Apply changes?',f'Apply changes to {len(tochange)} album folders?\n\n'
                  'This will edit the enabled tag fields and possibly rename folders/files as previewed.\n'
                  'An undo journal will be stored in the application Logs folder.\n\nProceed?',icon='warning'):return
        self.track_editor.player.stop()
        actions=list(tochange);options=self.option_dict();loaded=list(self.track_editor.records)
        def work():
            path=apply_actions(actions,BASE,options,lambda x:self.queue.put(('status',x)))
            mappings={t['old_path']:str(Path(a['dest_folder'])/t['new_name']) for a in actions for t in a['tracks']}
            folders={a['folder']:a['dest_folder'] for a in actions}
            self.track_editor.relocate_worker(mappings,folders,loaded)
            self.queue.put(('apply_done',path))
        self.run_background(work)
    def undo(self):
        path=newest_journal(BASE)
        if not path:messagebox.showinfo('Nothing to undo','No previous apply journal has been found.');return
        if not messagebox.askyesno('Undo last apply?',f'Undo Groove Goblin changes recorded in:\n{path.name}\n\nThis will restore the saved tag values and names.'):return
        self.track_editor.player.stop()
        loaded=list(self.track_editor.records)
        def work():
            data=json.loads(Path(path).read_text())
            errors=undo_journal(path,lambda x:self.queue.put(('log',x)))
            if data.get('kind')=='manual_tracks':
                from groove_manual import read_track
                records={};mappings={}
                for track in data['tracks']:
                    mappings[track['destination']]=track['source']
                    for item in {track['source'],track['destination']}:
                        if Path(item).is_file():
                            record=read_track(item);records[record['path']]=record
                self.queue.put(('manual_undone',errors,mappings,records))
            else:
                mappings={};folders={}
                for album in data.get('albums',[]):
                    before=Path(album['folder_before']);after=Path(album['folder_after'])
                    current=after if album.get('folder_renamed') else before
                    if before.is_dir():folders[str(current)]=str(before)
                    names={t['new_name'] if t.get('file_renamed') else t['old_name']:t['old_name'] for t in album['tracks']}
                    for old in loaded:
                        if Path(old).parent==current:mappings[old]=str(before/names.get(Path(old).name,Path(old).name))
                self.track_editor.relocate_worker(mappings,folders,loaded)
            self.queue.put(('undo_done',errors))
        self.run_background(work)
    def open_logs(self):
        folder=backup_dir(BASE)
        try:os.startfile(str(folder))
        except AttributeError:messagebox.showinfo('Logs location',str(folder))
    def view_journal(self):
        p=newest_journal(BASE)
        if not p:messagebox.showinfo('No journal','No undo journal was found.');return
        self.log('Last journal: '+str(p))
        self.log(p.read_text(encoding='utf-8')[:18000])

from groove_layout import install_layout
install_layout(GrooveGoblin)

if __name__=='__main__':
    try:GrooveGoblin().mainloop()
    except Exception:
        from tkinter import messagebox
        messagebox.showerror('Groove Goblin startup error',traceback.format_exc())
        raise
