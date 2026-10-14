"""Mp3tag-style staged editing, multi-selection, cover editing and playback."""
from io import BytesIO
import json
import os
import queue
import threading
from pathlib import Path
from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from groove_widgets import BG,PANEL,LINE,FG,MUTED,GREEN,PURPLE,Button,Check,Panel,Scrollbar,bind_mousewheel
from groove_manual import FIELDS,read_track,load_artwork,validate_changes,plan_manual,apply_manual
from groove_core import scan_folders,newest_journal,undo_journal,EXTENSIONS
from groove_player import MusicPlayer
from groove_formats import FILE_PATTERN, can_tag, can_rename, format_note
from groove_decode import PCM_FORMATS
from groove_runtime import data_dir

LABELS={'filename':'Filename','title':'Track title','artist':'Artist','albumartist':'Album artist',
        'album':'Album','track':'Track','disc':'Disc number','year':'Year'}


class TrackEditor(tk.Frame):
    def __init__(self,app):
        super().__init__(app.content,bg=BG)
        self.app=app;self.storage_base=data_dir();self.records={};self.pending={};self.loading=False;self.photo=None;self.cover_cache={};self.list_cleared=False
        self.player=MusicPlayer();self.seeking=False;self.timer=None;self.inline=None
        self.columnconfigure(0,weight=1);self.rowconfigure(1,weight=1)
        toolbar=tk.Frame(self,bg=BG);toolbar.grid(row=0,column=0,sticky='ew',pady=(0,6))
        tk.Label(toolbar,text='Track Editor',bg=BG,fg=GREEN,font=(app.ui_font,12,'bold')).pack(side='left',padx=(0,12))
        self.top_buttons=[]
        for text,command,symbol,accent,subtitle in [('Add Files',self.add_files,'music',PURPLE,'Select tracks to edit'),('Add Folder',self.add_folder,'folder','#ffd24c','Add a music folder'),('Use Scan List',self.import_scan,'list',GREEN,'Import scanned tracks')]:
            button=Button(toolbar,text,command,width=180,height=58,symbol=symbol,accent=accent,subtitle=subtitle,font=(app.ui_font,10))
            button.pack(side='left',padx=(0,5));self.top_buttons.append(button)
        self.body=tk.Frame(self,bg=BG);self.body.grid(row=1,column=0,sticky='nsew')
        self.body.columnconfigure(0,weight=1);self.body.columnconfigure(1,minsize=320);self.body.rowconfigure(0,weight=1)
        self.list_panel=Panel(self.body,padding=8);self.list_panel.grid(row=0,column=0,sticky='nsew',padx=(0,8))
        listing=self.list_panel.body
        listing.rowconfigure(1,weight=1);listing.columnconfigure(0,weight=1)
        header=tk.Frame(listing,bg=PANEL);header.grid(row=0,column=0,columnspan=2,sticky='ew',pady=(0,7))
        title_row=tk.Frame(header,bg=PANEL);title_row.pack(fill='x')
        tk.Label(title_row,text='Tracks',bg=PANEL,fg=FG,font=(app.ui_font,11,'bold')).pack(side='left')
        self.track_hint=tk.Label(title_row,text='Double-click to edit',bg=PANEL,fg=MUTED,font=(app.ui_font,8))
        self.track_hint.pack(side='left',padx=12)
        self.track_count=tk.Label(title_row,text='0 tracks',bg=PANEL,fg=GREEN,font=(app.ui_font,9));self.track_count.pack(side='right')
        clear_row=tk.Frame(header,bg=PANEL);clear_row.pack(fill='x',pady=(4,0))
        self.clear_selected_button=Button(clear_row,'Clear Selected',self.clear_selected,width=142,height=30,symbol='cross',accent='#ff6068',font=(app.ui_font,9))
        self.clear_selected_button.pack(side='left',padx=(0,5))
        self.clear_list_button=Button(clear_row,'Clear List',self.clear_list,width=110,height=30,symbol='cross',accent='#ff6068',font=(app.ui_font,9))
        self.clear_list_button.pack(side='left')
        self.clear_selected_button.state(['disabled']);self.clear_list_button.state(['disabled'])
        self.tree=ttk.Treeview(listing,columns=FIELDS,show='headings',selectmode='extended',style='Editor.Treeview')
        for field in FIELDS:
            self.tree.heading(field,text=LABELS[field],command=lambda f=field:self.sort(f))
            self.tree.column(field,width=210 if field=='filename' else (60 if field in ('track','disc','year') else 145),minwidth=45,stretch=False)
        self.tree.tag_configure('even',background='#0e181f')
        self.tree.tag_configure('odd',background=PANEL)
        self.tree.tag_configure('staged',foreground=GREEN)
        self.tree.grid(row=1,column=0,sticky='nsew')
        vertical=Scrollbar(listing,orient='vertical',command=self.tree.yview,style='Vertical.Goblin.TScrollbar')
        vertical.grid(row=1,column=1,sticky='ns')
        self.tree.configure(yscrollcommand=vertical.set)
        horizontal=Scrollbar(listing,orient='horizontal',command=self.tree.xview,style='Horizontal.Goblin.TScrollbar')
        horizontal.grid(row=2,column=0,sticky='ew');self.tree.configure(xscrollcommand=horizontal.set)
        bind_mousewheel(self.tree,targets=(vertical,horizontal))
        self.tree.bind('<<TreeviewSelect>>',self.selection_changed)
        self.tree.bind('<Double-1>',self.begin_inline)
        self.tree.bind('<Control-a>',self.select_all)
        self.side_panel=Panel(self.body,padding=8,width=320)
        self.side_panel.grid(row=0,column=1,sticky='nsew')
        self.side=self.side_panel.body;self.side.columnconfigure(0,weight=1)
        self.selection_label=tk.Label(self.side,text='Track Tags',bg=PANEL,fg=GREEN,font=(app.ui_font,10,'bold'),anchor='w')
        self.selection_label.grid(row=0,column=0,sticky='ew',padx=8,pady=(6,2))
        self.help=tk.Label(self.side,text='Checked fields apply to selected tracks.\nBlank checked fields clear that tag.',bg=PANEL,fg=MUTED,font=(app.ui_font,8),justify='left')
        self.help.grid(row=1,column=0,sticky='w',padx=8,pady=(0,4))
        self.form=tk.Frame(self.side,bg=PANEL);self.form.grid(row=2,column=0,sticky='ew',padx=6)
        self.form.columnconfigure(1,weight=1)
        self.vars={};self.enabled={};self.entries={};self.checks={}
        for row,field in enumerate(FIELDS):
            variable=tk.StringVar();enabled=tk.BooleanVar(value=False)
            check=Check(self.form,LABELS[field],enabled,width=100,font=(app.ui_font,9))
            check.grid(row=row,column=0,sticky='w')
            entry=ttk.Entry(self.form,textvariable=variable,width=17,font=(app.ui_font,9),style='Manual.TEntry')
            entry.grid(row=row,column=1,sticky='ew',pady=1)
            variable.trace_add('write',lambda *args,f=field:self.mark_field(f))
            self.vars[field]=variable;self.enabled[field]=enabled;self.entries[field]=entry;self.checks[field]=check
        self.art_frame=tk.Frame(self.side,bg=PANEL);self.art_frame.grid(row=3,column=0,sticky='ew',padx=8,pady=5)
        self.cover=tk.Label(self.art_frame,bg='#080e12',width=10,height=4,text='No artwork',fg=MUTED,highlightthickness=1,highlightbackground=LINE)
        self.cover.pack(side='left',padx=(0,7))
        art_buttons=tk.Frame(self.art_frame,bg=PANEL);art_buttons.pack(side='left',fill='x',expand=True)
        self.art_buttons=[]
        for text,command,symbol in [('Choose Artwork',self.choose_artwork,'disc'),('Remove Front',self.remove_artwork,'cross')]:
            button=Button(art_buttons,text,command,width=145,height=30,symbol=symbol,font=(app.ui_font,8))
            button.pack(fill='x',pady=1);self.art_buttons.append(button)
        actions=tk.Frame(self.side,bg=PANEL);actions.grid(row=4,column=0,sticky='ew',padx=8,pady=3)
        actions.columnconfigure(0,weight=1);actions.columnconfigure(1,weight=1)
        self.stage_button=Button(actions,'Stage Edits',self.stage_fields,width=140,height=32,font=(app.ui_font,9),green_active=True,accent=GREEN)
        self.stage_button.grid(row=0,column=0,sticky='ew',padx=(0,4))
        self.discard_button=Button(actions,'Discard Selected',self.discard_selected,width=140,height=32,font=(app.ui_font,8))
        self.discard_button.grid(row=0,column=1,sticky='ew')
        save_row=tk.Frame(self.side,bg=PANEL);save_row.grid(row=5,column=0,sticky='ew',padx=8,pady=3)
        save_row.columnconfigure(0,weight=1);save_row.columnconfigure(1,weight=1)
        self.save_button=Button(save_row,'Review & Save',self.save,width=145,height=32,primary=True,font=(app.ui_font,9))
        self.save_button.grid(row=0,column=0,sticky='ew',padx=(0,4))
        self.undo_button=Button(save_row,'Undo Last Save',self.undo,width=145,height=32,font=(app.ui_font,9))
        self.undo_button.grid(row=0,column=1,sticky='ew')
        self.summary=tk.Label(self.side,text='No staged changes',bg=PANEL,fg=MUTED,font=(app.ui_font,8),anchor='w',wraplength=280)
        self.summary.grid(row=7,column=0,sticky='ew',padx=8,pady=2)
        self.build_player()
        self.bind('<Configure>',self.resize)
        self.bind('<Destroy>',self.close,add='+')
        self.timer=app.after(150,self.tick)

    def resize(self,event=None):
        if getattr(getattr(self.app,'_phone',None),'active',False):
            self.app._phone.resize_tracks();return
        compact=self.winfo_width()<1000 or self.winfo_height()<650
        width=268 if compact else 320
        self.body.columnconfigure(1,minsize=width)
        self.side_panel.configure(width=width)
        for panel in (self.list_panel,self.side_panel):
            panel.padding=6 if compact else 10
            panel.resize(SimpleNamespace(width=panel.winfo_width(),height=panel.winfo_height()))
        for index,button in enumerate(self.top_buttons):
            button.configure(width=130 if compact else 180,height=42 if compact else 58)
            button.subtitle='' if compact else ['Select tracks to edit','Add a music folder','Import scanned tracks'][index]
            button.font=(self.app.ui_font,8 if compact else 10);button.draw()
        for button in (self.clear_selected_button,self.clear_list_button):
            button.font=(self.app.ui_font,8 if compact else 9)
            button.configure(height=28 if compact else 30);button.draw()
        ttk.Style(self).configure('Editor.Treeview',rowheight=28 if compact else 34)
        for field in FIELDS:
            self.checks[field].configure(width=93 if compact else 105,height=20 if compact else 24)
            self.checks[field].font=(self.app.ui_font,8 if compact else 9);self.checks[field].draw()
            self.entries[field].configure(font=(self.app.ui_font,8 if compact else 9))
        self.track_hint.configure(text='Double-click to edit' if compact else 'Ctrl / Shift selects tracks · Double-click to edit · * staged')
        self.summary.configure(wraplength=width-16)
        self.help.configure(text='Check fields to set; blank clears a tag.' if compact else 'Checked fields apply to selected tracks.\nBlank checked fields clear that tag.')
        for button in (self.stage_button,self.discard_button):button.configure(height=28 if compact else 32)
        for button in self.art_buttons:button.configure(height=25 if compact else 30)
        self.art_size=56 if compact else 96
        self.show_cover()

    def mark_field(self,field):
        if not self.loading:self.enabled[field].set(True)

    def selected(self):return list(self.tree.selection())

    def values(self,path):
        data=dict(self.records[path]);data.update(self.pending.get(path,{}));return data

    def select_all(self,event=None):
        self.tree.selection_set(self.tree.get_children());return 'break'

    def sort(self,field):
        for index,path in enumerate(sorted(self.tree.get_children(),key=lambda p:self.values(p).get(field,'').casefold())):
            self.tree.move(path,'',index)

    def refresh(self):
        selected=self.selected()
        for item in self.tree.get_children():self.tree.delete(item)
        for index,path in enumerate(self.records):
            data=self.values(path)
            values=[data.get(field,'') for field in FIELDS]
            if path in self.pending:values[0]='* '+values[0]
            self.tree.insert('','end',iid=path,values=values,tags=(('even' if index%2==0 else 'odd'),)+(('staged',) if path in self.pending else ()))
        self.tree.selection_set([p for p in selected if p in self.records])
        self.track_count.configure(text=f'{len(self.records)} tracks · {len(self.pending)} staged')
        self.summary.configure(text=f'{len(self.pending)} tracks have unsaved changes' if self.pending else 'No staged changes')
        self.selection_changed()

    def selection_changed(self,event=None):
        selected=self.selected()
        self.clear_selected_button.state(['!disabled'] if selected else ['disabled'])
        self.clear_list_button.state(['!disabled'] if self.records else ['disabled'])
        self.selection_label.configure(text=f'Track Tags · {len(selected)} selected' if selected else 'Track Tags')
        self.loading=True
        try:
            for field in FIELDS:
                values={self.values(p).get(field,'') for p in selected}
                self.vars[field].set(next(iter(values)) if len(values)==1 else '')
                self.enabled[field].set(False)
        finally:self.loading=False
        editable=bool(selected) and all(can_tag(p) for p in selected)
        renameable=bool(selected) and all(can_rename(p) for p in selected)
        for field in FIELDS:
            self.checks[field].disabled=not (renameable if field=='filename' else editable)
            self.checks[field].draw()
            self.entries[field].state(['!disabled'] if (renameable if field=='filename' else editable) else ['disabled'])
        for button in self.art_buttons:button.state(['!disabled'] if editable else ['disabled'])
        notes=[format_note(p) for p in selected if format_note(p)]
        self.summary.configure(text=(notes[0] if notes else (f'{len(self.pending)} tracks have unsaved changes' if self.pending else 'No staged changes')))
        self.show_cover()

    def show_cover(self):
        selected=self.selected();art=None
        if selected:
            path=selected[0]
            if 'artwork' in self.pending.get(path,{}):
                proposed=self.pending[path]['artwork'];art=proposed['data'] if proposed else None
            else:
                try:
                    key=(path,tuple(self.records[path]['signature']))
                    if key not in self.cover_cache:
                        if len(self.cover_cache)>=8:self.cover_cache.pop(next(iter(self.cover_cache)))
                        self.cover_cache[key]=read_track(path,include_artwork=True).get('artwork')
                    art=self.cover_cache[key]
                except (OSError,ValueError):pass
        if art:
            try:
                with Image.open(BytesIO(art)) as image:
                    image.thumbnail((getattr(self,'art_size',96),getattr(self,'art_size',96)))
                    self.photo=ImageTk.PhotoImage(image.copy(),master=self.app)
                self.cover.configure(image=self.photo,text='',width=getattr(self,'art_size',96),height=getattr(self,'art_size',96))
                return
            except (OSError,ValueError):pass
        self.photo=None;self.cover.configure(image='',text='No artwork',width=8,height=3 if getattr(self,'art_size',96)<80 else 4)

    def check_idle(self):
        if self.app.worker_busy:
            messagebox.showinfo('Please wait','Wait for the current operation to finish.');return False
        return True

    def stage_fields(self):
        if not self.check_idle():return
        selected=self.selected()
        if not selected:return
        changes={field:self.vars[field].get() for field in FIELDS if self.enabled[field].get()}
        try:
            prepared={path:validate_changes(self.records[path],changes) for path in selected}
        except ValueError as error:messagebox.showwarning('Check edits',str(error));return
        for path,values in prepared.items():
            if values:self.pending.setdefault(path,{}).update(values)
        self.refresh()

    def begin_inline(self,event):
        if self.app.worker_busy:return
        path=self.tree.identify_row(event.y);column=self.tree.identify_column(event.x)
        if not path or not column:return
        field=FIELDS[int(column[1:])-1];bounds=self.tree.bbox(path,column)
        if not bounds:return
        if self.inline:self.inline.destroy()
        variable=tk.StringVar(value=self.values(path).get(field,''))
        entry=ttk.Entry(self.tree,textvariable=variable);self.inline=entry
        entry.place(x=bounds[0],y=bounds[1],width=bounds[2],height=bounds[3]);entry.focus_set();entry.selection_range(0,'end')
        def commit(event=None):
            try:changes=validate_changes(self.records[path],{field:variable.get()})
            except ValueError as error:messagebox.showwarning('Check edit',str(error));return
            self.pending.setdefault(path,{}).update(changes);entry.destroy();self.inline=None;self.refresh()
        entry.bind('<Return>',commit)
        entry.bind('<Escape>',lambda e:(entry.destroy(),setattr(self,'inline',None)))

    def choose_artwork(self):
        if not self.check_idle() or not self.selected():return
        path=filedialog.askopenfilename(title='Choose front-cover image',filetypes=[('Images','*.jpg *.jpeg *.png *.webp *.bmp'),('All files','*.*')])
        if not path:return
        try:art=load_artwork(path)
        except Exception as error:messagebox.showwarning('Artwork',str(error));return
        for selected in self.selected():self.pending.setdefault(selected,{})['artwork']=art
        self.refresh()

    def remove_artwork(self):
        if not self.check_idle():return
        for path in self.selected():self.pending.setdefault(path,{})['artwork']=None
        self.refresh()

    def discard_selected(self):
        if not self.check_idle():return
        for path in self.selected():self.pending.pop(path,None)
        self.refresh()

    def clear_selected(self):
        self.remove_tracks(self.selected())

    def clear_list(self):
        self.remove_tracks(list(self.records),clear_all=True)

    def remove_tracks(self,paths,*,clear_all=False):
        """Remove editor rows only; source files and the organizer stay intact."""
        if not self.check_idle():return
        removed=set(paths)&self.records.keys()
        if not removed:return
        if any(path in self.pending for path in removed) or self.inline:
            prompt=f'Remove {len(removed)} tracks from the editor and discard their staged edits?'
            if self.inline:prompt+=' Any open unsaved cell edit will also be discarded.'
            prompt+=' Your music files will stay unchanged.'
            if not messagebox.askyesno('Clear tracks',prompt,parent=self.app):return
        if self.inline:self.inline.destroy();self.inline=None
        current=self.player.current
        stop=clear_all or (current is not None and current['path'] in removed)
        if stop:self.player.stop()
        self.player.playlist=[] if clear_all else [record for record in self.player.playlist if record['path'] not in removed]
        self.player.index=next((i for i,record in enumerate(self.player.playlist) if record is current),-1) if not stop else -1
        for path in removed:self.records.pop(path,None);self.pending.pop(path,None)
        self.cover_cache={key:art for key,art in self.cover_cache.items() if key[0] not in removed}
        if not self.records:self.list_cleared=True
        self.refresh();self.update_player_details();self.update_player_art()
        if stop:
            self.progress.set(0);self.time.configure(text='0:00 / 0:00')
        self.app.status.set(f'Track Editor: cleared {len(removed)} tracks · {len(self.records)} remaining')

    def add_files(self):
        if not self.check_idle():return
        paths=filedialog.askopenfilenames(title='Add tracks to Track Editor',filetypes=[('Music',FILE_PATTERN)])
        if paths:self.add_paths(paths)

    def add_folder(self):
        if not self.check_idle():return
        folder=filedialog.askdirectory(title='Add folder to Track Editor')
        if folder:self.add_paths([folder])

    def add_paths(self,paths,*,folders_only=False):
        """Add a batch directly to the editor, independently of organizer input."""
        if not self.check_idle():return False
        accepted=[];seen=set()
        for value in paths:
            try:
                path=Path(value)
                if not path.is_absolute() or not (path.is_dir() or (not folders_only and path.is_file() and path.suffix.lower() in EXTENSIONS)):continue
                path=path.resolve();key=os.path.normcase(str(path))
                if key not in seen:accepted.append(str(path));seen.add(key)
            except (OSError,ValueError,RuntimeError):continue
        if not accepted:
            self.app.status.set('Track Editor: add folders or supported music files.');return False
        recursive=self.app.scan_subfolders.get()
        def work():
            albums,issues=scan_folders(accepted,cancel=self.app.cancel,recursive=recursive)
            self.read_paths_worker([track.path for album in albums for track in album.tracks],issues)
        self.app.status.set('Reading tracks into Track Editor…')
        self.app.run_background(work)
        return True

    def import_scan(self):
        paths=[track.path for album in self.app.matched for track in album.tracks]
        if paths and self.check_idle():self.load_paths(paths)

    def load_paths(self,paths):
        paths=list(paths)
        self.app.run_background(lambda:self.read_paths_worker(paths))

    def read_paths_worker(self,paths,issues=()):
        records={};errors=list(issues)
        for path in paths:
            try:
                record=read_track(path);records[record['path']]=record
            except Exception as error:errors.append(str(path)+': '+str(error))
        self.app.queue.put(('manual_loaded',records,errors))

    def relocate_worker(self,mappings,folders,loaded):
        records={};actual={}
        for old in loaded:
            new=mappings.get(old,old)
            if old not in mappings:continue
            candidate=new if Path(new).is_file() else old
            if Path(candidate).is_file():
                record=read_track(candidate);records[record['path']]=record
                actual[old]=record['path']
        self.app.queue.put(('manual_relocated',actual,folders,records))

    def handle_event(self,kind,*args):
        if kind=='manual_loaded':
            if args[0]:self.list_cleared=False
            for path,record in args[0].items():
                if path not in self.pending:self.records[path]=record
            for error in args[1]:self.app.log('TRACK EDITOR: '+error)
            self.refresh();self.app.status.set(f'Track Editor: {len(self.records)} tracks loaded')
        elif kind=='manual_relocated':
            mappings,folders,records=args
            self.app.roots=[folders.get(p,mappings.get(p,p)) for p in self.app.roots];self.app.update_roots()
            for old,new in mappings.items():
                self.records.pop(old,None)
                if old in self.pending:self.pending[new]=self.pending.pop(old)
            self.records.update(records);self.cover_cache.clear()
            self.player.playlist=[];self.player.index=-1;self.refresh()
        elif kind=='manual_saved':
            journal,plans,records=args
            renamed={p['source']:p['destination'] for p in plans}
            self.app.roots=[renamed.get(p,p) for p in self.app.roots];self.app.update_roots()
            self.cover_cache.clear();self.player.playlist=[];self.player.index=-1
            for plan in plans:self.records.pop(plan['source'],None);self.pending.pop(plan['source'],None)
            self.records.update(records);self.refresh();self.app.status.set('Manual changes saved. Undo backup: '+Path(journal).name)
            self.app.log('Manual save: '+journal)
            self.app.matched=[];self.app.album_map={};self.app.populate_albums();self.app.refresh_preview()
        elif kind=='manual_undone':
            issues,mappings,records=args
            restored={old:new for old,new in mappings.items() if new in records}
            self.app.roots=[restored.get(p,p) for p in self.app.roots];self.app.update_roots()
            self.cover_cache.clear();self.player.playlist=[];self.player.index=-1
            for old in mappings:self.records.pop(old,None);self.pending.pop(old,None)
            self.records.update(records);self.refresh()
            if issues:messagebox.showwarning('Undo review','\n'.join(issues))
            else:self.app.status.set('Manual changes undone; original files restored.')
        if self.app._active_page=='tracks':self.app.btn_apply.state(['disabled'])

    def save(self):
        if not self.check_idle():return
        plans,issues=plan_manual(self.records,self.pending)
        if issues:messagebox.showwarning('Resolve edit conflicts','\n'.join(issues[:20]));return
        if not plans:messagebox.showinfo('Nothing to save','Stage edits first.');return
        size=sum(Path(p['source']).stat().st_size for p in plans)/(1024*1024)
        if not self.review_changes(plans,size):return
        self.player.stop()
        def work():
            journal=apply_manual(plans,self.storage_base,lambda s:self.app.queue.put(('status',s)))
            records={}
            for plan in plans:
                record=read_track(plan['destination']);records[record['path']]=record
            self.app.queue.put(('manual_saved',journal,plans,records))
        self.app.run_background(work)

    def review_changes(self,plans,size):
        dialog=tk.Toplevel(self.app);dialog.title('Review manual changes');dialog.transient(self.app)
        dialog.configure(bg=BG);dialog.geometry('700x460');dialog.minsize(500,340)
        tk.Label(dialog,text=f'{len(plans)} tracks · Full-file undo backups: about {size:.1f} MB',bg=BG,fg=GREEN).pack(fill='x',padx=12,pady=10)
        buttons=tk.Frame(dialog,bg=BG);buttons.pack(side='bottom',fill='x',padx=12,pady=10)
        answer=[False]
        def accept():answer[0]=True;dialog.destroy()
        Button(buttons,'Save Changes',accept,width=150,height=36,primary=True).pack(side='right')
        Button(buttons,'Cancel',dialog.destroy,width=100,height=36).pack(side='right',padx=8)
        body=tk.Frame(dialog,bg=PANEL);body.pack(fill='both',expand=True,padx=12)
        text=tk.Text(body,bg=PANEL,fg=FG,wrap='word',font=(self.app.ui_font,9),relief='flat')
        text.pack(side='left',fill='both',expand=True)
        scroll=Scrollbar(body,command=text.yview,style='Vertical.Goblin.TScrollbar');scroll.pack(side='right',fill='y');text.configure(yscrollcommand=scroll.set)
        bind_mousewheel(text,targets=(scroll,))
        for plan in plans:
            text.insert('end',Path(plan['source']).name+'\n')
            original=self.records[plan['source']]
            for key,value in plan['changes'].items():
                if key=='artwork':line='Front artwork: '+('Replace with selected image' if value else 'Remove front artwork')
                else:line=LABELS[key]+': '+repr(original.get(key,''))+' → '+repr(value)
                text.insert('end','  '+line+'\n')
            text.insert('end','\n')
        if getattr(getattr(self.app,'_phone',None),'active',False):self.app._phone.fit_dialog(dialog,460)
        text.configure(state='disabled');dialog.grab_set();self.app.wait_window(dialog)
        return answer[0]

    def undo(self):
        if not self.check_idle():return
        journal=newest_journal(self.storage_base)
        if not journal:messagebox.showinfo('No undo','No undo journal is available.');return
        data=json.loads(Path(journal).read_text())
        if data.get('kind')!='manual_tracks':
            messagebox.showinfo('Album undo','Use Undo / Backups for the latest album operation.');return
        if not messagebox.askyesno('Undo manual save?','Restore original tags, artwork and filenames from the last manual save?'):return
        self.player.stop()
        def work():
            issues=undo_journal(journal);records={};mappings={}
            for track in data['tracks']:
                mappings[track['destination']]=track['source']
                for path in {track['source'],track['destination']}:
                    if Path(path).is_file():
                        record=read_track(path);records[record['path']]=record
            self.app.queue.put(('manual_undone',issues,mappings,records))
        self.app.run_background(work)

    def build_player(self):
        # The host belongs to the sidebar, not to the editor page.
        self.player_panel=self.app.sidebar_player_panel
        bar=self.player_panel.body;bar.columnconfigure(0,weight=1)
        self.player_heading=tk.Label(bar,text='Now Playing',bg=PANEL,fg=FG,font=(self.app.ui_font,10,'bold'),anchor='w')
        self.player_heading.grid(row=0,column=0,sticky='ew')
        self.now=tk.Label(bar,text='Select a track and press Play',bg=PANEL,fg=GREEN,font=(self.app.ui_font,9,'bold'),anchor='w')
        self.now.grid(row=1,column=0,sticky='ew',pady=(2,3))
        details=tk.Frame(bar,bg=PANEL);details.grid(row=2,column=0,sticky='ew');details.columnconfigure(1,weight=1)
        self.player_cover=tk.Canvas(details,width=58,height=58,bg='#080e12',highlightthickness=1,highlightbackground=LINE)
        self.player_cover.grid(row=0,column=0,rowspan=2,padx=(0,6))
        self.player_artist=tk.Label(details,text='Artist',bg=PANEL,fg=FG,font=(self.app.ui_font,9),anchor='w')
        self.player_artist.grid(row=0,column=1,sticky='ew')
        self.player_album=tk.Label(details,text='Album · Year',bg=PANEL,fg=MUTED,font=(self.app.ui_font,8),anchor='w')
        self.player_album.grid(row=1,column=1,sticky='ew')
        controls=tk.Frame(bar,bg=PANEL);controls.grid(row=3,column=0,sticky='ew',pady=(4,0))
        self.play_buttons=[]
        for i,(text,command) in enumerate([('Back',lambda:self.player_command(self.player.previous)),('Play',self.play_pause),
                             ('Skip',lambda:self.player_command(self.player.next)),('Stop',lambda:self.player_command(self.player.stop))]):
            controls.columnconfigure(i,weight=1)
            button=Button(controls,text,command,width=38,height=40,primary=text=='Play',symbol=text.lower(),vertical=True,font=(self.app.ui_font,8))
            button.grid(row=0,column=i,sticky='ew',padx=(0,2 if i<3 else 0));self.play_buttons.append(button)
        self.progress=ttk.Scale(bar,from_=0,to=1,style='Player.Horizontal.TScale')
        self.progress.grid(row=4,column=0,sticky='ew')
        self.progress.bind('<ButtonPress-1>',lambda e:setattr(self,'seeking',True))
        self.progress.bind('<ButtonRelease-1>',self.seek)
        self.time=tk.Label(bar,text='0:00 / 0:00',bg=PANEL,fg=MUTED,font=(self.app.ui_font,8))
        self.time.grid(row=5,column=0,sticky='ew')
        volume=tk.Frame(bar,bg=PANEL);volume.grid(row=6,column=0,sticky='ew');volume.columnconfigure(1,weight=1)
        tk.Label(volume,text='Volume',bg=PANEL,fg=MUTED,font=(self.app.ui_font,8)).grid(row=0,column=0,padx=(0,4))
        self.volume=ttk.Scale(volume,from_=0,to=100,command=self.player.set_volume,style='Player.Horizontal.TScale')
        self.volume.set(70);self.volume.configure(length=70);self.volume.grid(row=0,column=1,sticky='ew')
        self.audio_output_button=Button(bar,'Audio Output',self.show_audio_output,width=118,height=22,font=(self.app.ui_font,8))
        self.audio_output_button.grid(row=7,column=0,sticky='ew',pady=(2,0))
        self.player_art_queue=queue.Queue();self.player_art_key=object();self.player_photo=None;self.player_art_size=58
        self.player_cover.bind('<Configure>',lambda event:self.update_player_art())

    def resize_player(self,compact):
        self.player_art_size=42 if compact else 58
        self.player_cover.configure(width=self.player_art_size,height=self.player_art_size)
        self.player_heading.configure(font=(self.app.ui_font,9 if compact else 10,'bold'))
        for button in self.play_buttons:
            button.configure(height=38 if compact else 40);button.draw()
        self.update_player_details()
        self.update_player_art()

    def update_player_details(self):
        from tkinter import font as tkfont
        current=self.player.current
        def fit(label,text,suffix=""):
            # Keep the sidebar width fixed even with long tags or filenames.
            text=' '.join(str(text).split())
            width=max(20,label.winfo_width()-4)
            font=tkfont.Font(master=self.app,font=label.cget('font'))
            if font.measure(text+suffix)>width:
                low,high=0,len(text)
                while low<high:
                    middle=(low+high+1)//2
                    if font.measure(text[:middle]+'…'+suffix)<=width:low=middle
                    else:high=middle-1
                text=text[:low]+'…'
            text+=suffix
            label.configure(text=text)
        fit(self.now,(current.get('title') or Path(current['path']).stem) if current else 'Select a track and press Play')
        fit(self.player_artist,(current.get('artist') or 'Unknown artist') if current else 'Artist')
        album=(current.get('album') or 'Unknown album') if current else 'Album'
        year=current.get('year','') if current else ''
        fit(self.player_album,album,(' ('+str(year)+')' if year else ''))

    def update_player_art(self):
        current=self.player.current
        key=(current['path'],tuple(current.get('signature',())),self.player_art_size) if current else None
        if key==self.player_art_key:return
        self.player_art_key=key;self.player_photo=None
        self.player_cover.delete('all')
        from groove_widgets import icon
        size=self.player_art_size
        icon(self.player_cover,'disc',4,4,size-8,MUTED)
        if not key:return
        def read():
            image=None
            try:
                art=read_track(key[0],include_artwork=True).get('artwork')
                if art:
                    with Image.open(BytesIO(art)) as source:
                        source.thumbnail((key[2],key[2]),Image.Resampling.LANCZOS);image=source.convert('RGB').copy()
            except (OSError,ValueError):pass
            self.player_art_queue.put((key,image))
        threading.Thread(target=read,daemon=True,name='sidebar-artwork').start()

    def show_audio_output(self):
        existing=getattr(self,'audio_dialog',None)
        if existing is not None and existing.winfo_exists():existing.lift();return
        dialog=tk.Toplevel(self.app,bg=BG);self.audio_dialog=dialog
        dialog.title('Audio Output');dialog.transient(self.app);dialog.geometry('560x350');dialog.minsize(520,350)
        body=tk.Frame(dialog,bg=BG);body.pack(fill='both',expand=True,padx=18,pady=16)
        buttons=tk.Frame(body,bg=BG);buttons.pack(side='bottom',fill='x',pady=(12,0))
        tk.Label(body,text='Audio Output',bg=BG,fg=GREEN,font=(self.app.ui_font,15,'bold')).pack(anchor='w',pady=(0,10))
        tk.Label(body,text='Choose the speakers or headphones you want to hear.',bg=BG,fg=FG,font=(self.app.ui_font,10)).pack(anchor='w')
        choice=tk.StringVar(value=self.player.device or 'System default')
        row=tk.Frame(body,bg=BG);row.pack(fill='x',pady=10)
        output=ttk.Combobox(row,textvariable=choice,state='readonly');output.pack(side='left',fill='x',expand=True)
        message=tk.StringVar(value='')
        def refresh():
            try:
                names=['System default',*self.player.output_devices()]
                output.configure(values=names)
                if choice.get() not in names:choice.set('System default')
            except Exception as error:
                output.configure(values=['System default']);choice.set('System default')
                message.set('Could not list outputs. Reconnect your speakers/headphones and try Refresh.')
                self.app.log('Audio outputs: '+str(error))
        Button(row,'Refresh',refresh,width=90,height=28,font=(self.app.ui_font,9)).pack(side='right',padx=(8,0))
        compatible=tk.BooleanVar(value=self.player.compatibility)
        Check(body,'Compatibility playback (stereo WAV)',compatible,width=480,font=(self.app.ui_font,10)).pack(anchor='w',pady=(2,6))
        tk.Label(body,text='Recommended on Windows. Plays a temporary listening copy;\nyour original music stays unchanged.',bg=BG,fg=MUTED,font=(self.app.ui_font,9),justify='left').pack(anchor='w')
        tk.Label(body,textvariable=message,bg=BG,fg=GREEN,font=(self.app.ui_font,9),justify='left',wraplength=480).pack(fill='x',pady=(12,0))
        if os.environ.get('SDL_AUDIODRIVER')=='dummy':
            message.set('Silent test output is active (SDL_AUDIODRIVER=dummy).\nClear that environment variable and restart to hear sound.')
        def reconnect(test=False):
            if self.app.worker_busy:
                message.set('Wait for the current operation to finish, then reconnect audio.');return
            try:
                self.player.configure_output(None if choice.get()=='System default' else choice.get(),compatibility=compatible.get())
                self.app.log('Audio output: '+(self.player.device or 'System default')+'; backend: '+self.player.audio_driver+'; compatibility: '+str(self.player.compatibility)+'; volume: '+str(round(self.player.volume))+'%')
                if test:
                    if self.player.volume==0:
                        message.set('Volume is 0%. Raise the player volume, then try Test Sound.');return
                    self.player.test_sound()
                    message.set('A short tone was sent to this output. If silent, check Windows\nVolume Mixer for this Python app and select the same output here.')
                else:message.set('Reconnected to '+(self.player.device or 'System default')+'.')
            except Exception as error:
                message.set(str(error).splitlines()[0]);self.app.log('Audio output: '+str(error))
        Button(buttons,'Reconnect',reconnect,width=116,height=34,primary=True,font=(self.app.ui_font,9)).pack(side='left')
        Button(buttons,'Test Sound',lambda:reconnect(True),width=118,height=34,font=(self.app.ui_font,9)).pack(side='left',padx=8)
        Button(buttons,'Close',dialog.destroy,width=80,height=34,font=(self.app.ui_font,9)).pack(side='right')
        dialog.bind('<Escape>',lambda event:dialog.destroy())
        refresh()

    def play_pause(self):
        if self.app.worker_busy:return
        selected=self.selected()
        path=selected[0] if selected else None
        if self.player.current and (self.app._active_page!='tracks' or path is None or self.player.current['path'] in selected):self.player_command(self.player.toggle)
        elif path:
            if Path(path).suffix.lower()=='.pcm' and not self.records[path].get('pcm'):
                settings=self.pcm_dialog()
                if settings is None:return
                for item in selected:
                    if Path(item).suffix.lower()=='.pcm':self.records[item]['pcm']=dict(settings)
            playlist=selected if len(selected)>1 else list(self.tree.get_children())
            self.player_command(lambda:self.player.play([self.records[p] for p in playlist],playlist.index(path)))

    def pcm_dialog(self):
        dialog=tk.Toplevel(self.app);dialog.title('Raw PCM playback settings');dialog.transient(self.app)
        dialog.configure(bg=PANEL);dialog.resizable(False,False)
        tk.Label(dialog,text='PCM has no header. Choose the actual recording settings.\nThese settings are used for playback only.',bg=PANEL,fg=FG,justify='left').grid(row=0,column=0,columnspan=2,padx=14,pady=12)
        values=[]
        for row,(label,options,default) in enumerate([
            ('Sample format',list(PCM_FORMATS),next(iter(PCM_FORMATS))),
            ('Sample rate (Hz)',['44100','48000','88200','96000','176400','192000','352800','384000'],'44100'),
            ('Channels',['1','2','4','6','8'],'2')],1):
            tk.Label(dialog,text=label,bg=PANEL,fg=MUTED).grid(row=row,column=0,sticky='w',padx=14,pady=5)
            value=tk.StringVar(value=default);values.append(value)
            ttk.Combobox(dialog,textvariable=value,values=options,state='readonly',width=30).grid(row=row,column=1,padx=14,pady=5)
        answer=[None]
        def accept():
            answer[0]={'format':PCM_FORMATS[values[0].get()],'rate':int(values[1].get()),'channels':int(values[2].get())};dialog.destroy()
        Button(dialog,'Play with these settings',accept,width=230,height=38,primary=True).grid(row=4,column=1,padx=14,pady=14)
        Button(dialog,'Cancel',dialog.destroy,width=100,height=38).grid(row=4,column=0,padx=14,pady=14)
        dialog.grab_set();self.app.wait_window(dialog);return answer[0]

    def player_command(self,command):
        if self.app.worker_busy and command!=self.player.stop:return
        try:command()
        except Exception as error:
            self.app.log('Playback: '+str(error));self.app.status.set('Playback: '+str(error).splitlines()[0])
            messagebox.showwarning('Playback',str(error))

    def seek(self,event=None):
        self.seeking=False
        self.player_command(lambda:self.player.seek(self.progress.get()))

    def tick(self):
        self.timer=None
        try:self.player.pump()
        except Exception as error:self.player.stop();self.app.log('Playback: '+str(error));self.app.status.set('Playback: '+str(error).splitlines()[0])
        self.update_player_details();self.update_player_art()
        while not self.player_art_queue.empty():
            key,image=self.player_art_queue.get_nowait()
            if key==self.player_art_key and image is not None:
                self.player_photo=ImageTk.PhotoImage(image,master=self.app)
                self.player_cover.delete('all')
                self.player_cover.create_image(self.player_art_size/2,self.player_art_size/2,image=self.player_photo)
        self.play_buttons[1].state(['disabled'] if self.player.state=='buffering' else ['!disabled'])
        playing=self.player.state=='playing'
        self.play_buttons[1].text='Wait' if self.player.state=='buffering' else ('Pause' if playing else 'Play')
        self.play_buttons[1].symbol='pause' if playing else 'play';self.play_buttons[1].draw()
        self.progress.configure(to=max(.01,self.player.duration))
        if not self.seeking:self.progress.set(self.player.position)
        def fmt(seconds):return f'{int(seconds)//60}:{int(seconds)%60:02d}'
        self.time.configure(text=fmt(self.player.position)+' / '+fmt(self.player.duration))
        self.timer=self.app.after(150,self.tick)

    def close(self,event):
        if event.widget is not self:return
        if self.timer:
            try:self.app.after_cancel(self.timer)
            except tk.TclError:pass
        self.player.close()
