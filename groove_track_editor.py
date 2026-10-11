"""Mp3tag-style staged editing, multi-selection, cover editing and playback."""
from io import BytesIO
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from groove_widgets import BG,PANEL,FG,MUTED,GREEN,Button,Check
from groove_manual import FIELDS,read_track,load_artwork,validate_changes,plan_manual,apply_manual
from groove_core import scan_folders,newest_journal,undo_journal
from groove_player import MusicPlayer

LABELS={'filename':'Filename','title':'Track title','artist':'Artist','albumartist':'Album artist',
        'album':'Album','track':'Track','disc':'Disc number','year':'Year'}


class TrackEditor(tk.Frame):
    def __init__(self,app):
        super().__init__(app.content,bg=BG)
        self.app=app;self.storage_base=Path(__file__).parent;self.records={};self.pending={};self.loading=False;self.photo=None;self.cover_cache={}
        self.player=MusicPlayer();self.seeking=False;self.timer=None;self.inline=None
        self.columnconfigure(0,weight=1);self.rowconfigure(1,weight=1)
        toolbar=tk.Frame(self,bg=BG);toolbar.grid(row=0,column=0,sticky='ew',pady=(0,6))
        tk.Label(toolbar,text='Track Editor',bg=BG,fg=GREEN,font=(app.ui_font,12,'bold')).pack(side='left',padx=(0,12))
        self.top_buttons=[]
        for text,command in [('Add Files',self.add_files),('Add Folder',self.add_folder),('Use Scan List',self.import_scan)]:
            button=Button(toolbar,text,command,width=105,height=34,font=(app.ui_font,9))
            button.pack(side='left',padx=(0,5));self.top_buttons.append(button)
        self.body=tk.Frame(self,bg=BG);self.body.grid(row=1,column=0,sticky='nsew')
        self.body.columnconfigure(0,weight=1);self.body.columnconfigure(1,minsize=320);self.body.rowconfigure(0,weight=1)
        listing=tk.Frame(self.body,bg=PANEL);listing.grid(row=0,column=0,sticky='nsew',padx=(0,8))
        listing.rowconfigure(1,weight=1);listing.columnconfigure(0,weight=1)
        tk.Label(listing,text='Ctrl / Shift selects tracks. Double-click a cell to edit; * marks staged changes.',
                 bg=PANEL,fg=MUTED,font=(app.ui_font,8),anchor='w').grid(row=0,column=0,sticky='ew',padx=6,pady=5)
        self.tree=ttk.Treeview(listing,columns=FIELDS,show='headings',selectmode='extended')
        for field in FIELDS:
            self.tree.heading(field,text=LABELS[field],command=lambda f=field:self.sort(f))
            self.tree.column(field,width=210 if field=='filename' else (60 if field in ('track','disc','year') else 145),minwidth=45,stretch=False)
        self.tree.grid(row=1,column=0,sticky='nsew')
        ttk.Scrollbar(listing,orient='vertical',command=self.tree.yview).grid(row=1,column=1,sticky='ns')
        self.tree.configure(yscrollcommand=listing.winfo_children()[-1].set)
        horizontal=ttk.Scrollbar(listing,orient='horizontal',command=self.tree.xview)
        horizontal.grid(row=2,column=0,sticky='ew');self.tree.configure(xscrollcommand=horizontal.set)
        self.tree.bind('<<TreeviewSelect>>',self.selection_changed)
        self.tree.bind('<Double-1>',self.begin_inline)
        self.tree.bind('<Control-a>',self.select_all)
        self.side=tk.Frame(self.body,bg=PANEL,width=320)
        self.side.grid(row=0,column=1,sticky='nsew');self.side.grid_propagate(False);self.side.columnconfigure(0,weight=1)
        self.selection_label=tk.Label(self.side,text='Select tracks to edit',bg=PANEL,fg=GREEN,font=(app.ui_font,10,'bold'),anchor='w')
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
        self.cover=tk.Label(self.art_frame,bg='#080e12',width=10,height=4,text='No artwork',fg=MUTED)
        self.cover.pack(side='left',padx=(0,7))
        art_buttons=tk.Frame(self.art_frame,bg=PANEL);art_buttons.pack(side='left',fill='x',expand=True)
        self.art_buttons=[]
        for text,command in [('Choose Artwork',self.choose_artwork),('Remove Front',self.remove_artwork)]:
            button=Button(art_buttons,text,command,width=145,height=30,font=(app.ui_font,8))
            button.pack(fill='x',pady=1);self.art_buttons.append(button)
        actions=tk.Frame(self.side,bg=PANEL);actions.grid(row=4,column=0,sticky='ew',padx=8,pady=3)
        actions.columnconfigure(0,weight=1);actions.columnconfigure(1,weight=1)
        self.stage_button=Button(actions,'Stage Edits',self.stage_fields,width=140,height=32,font=(app.ui_font,9),green_active=True)
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
        compact=self.winfo_width()<1000 or self.winfo_height()<650
        width=268 if compact else 320
        self.body.columnconfigure(1,minsize=width)
        self.side.configure(width=width)
        for field in FIELDS:
            self.checks[field].configure(width=93 if compact else 105,height=20 if compact else 24)
            self.checks[field].font=(self.app.ui_font,8 if compact else 9);self.checks[field].draw()
            self.entries[field].configure(font=(self.app.ui_font,8 if compact else 9))
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
        for path in self.records:
            data=self.values(path)
            values=[data.get(field,'') for field in FIELDS]
            if path in self.pending:values[0]='* '+values[0]
            self.tree.insert('','end',iid=path,values=values)
        self.tree.selection_set([p for p in selected if p in self.records])
        self.summary.configure(text=f'{len(self.records)} tracks · {len(self.pending)} staged')
        self.selection_changed()

    def selection_changed(self,event=None):
        selected=self.selected();self.selection_label.configure(text=f'{len(selected)} track(s) selected' if selected else 'Select tracks to edit')
        self.loading=True
        try:
            for field in FIELDS:
                values={self.values(p).get(field,'') for p in selected}
                self.vars[field].set(next(iter(values)) if len(values)==1 else '')
                self.enabled[field].set(False)
        finally:self.loading=False
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

    def add_files(self):
        if not self.check_idle():return
        paths=filedialog.askopenfilenames(title='Add tracks to Track Editor',filetypes=[('Music','*.flac *.mp3')])
        if paths:self.load_paths(paths)

    def add_folder(self):
        if not self.check_idle():return
        folder=filedialog.askdirectory(title='Add folder to Track Editor')
        if not folder:return
        def work():
            albums,issues=scan_folders([folder],recursive=self._recursive)
            paths=[track.path for album in albums for track in album.tracks]
            self.read_paths_worker(paths,issues)
        self._recursive=self.app.scan_subfolders.get()
        self.app.run_background(work)

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
        scroll=ttk.Scrollbar(body,command=text.yview);scroll.pack(side='right',fill='y');text.configure(yscrollcommand=scroll.set)
        for plan in plans:
            text.insert('end',Path(plan['source']).name+'\n')
            original=self.records[plan['source']]
            for key,value in plan['changes'].items():
                if key=='artwork':line='Front artwork: '+('Replace with selected image' if value else 'Remove front artwork')
                else:line=LABELS[key]+': '+repr(original.get(key,''))+' → '+repr(value)
                text.insert('end','  '+line+'\n')
            text.insert('end','\n')
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
        bar=tk.Frame(self,bg=PANEL);bar.grid(row=2,column=0,sticky='ew',pady=(6,0));bar.columnconfigure(1,weight=1)
        self.now=tk.Label(bar,text='Select a track and press Play',bg=PANEL,fg=MUTED,font=(self.app.ui_font,8),anchor='w')
        self.now.grid(row=0,column=0,columnspan=3,sticky='ew',padx=5)
        controls=tk.Frame(bar,bg=PANEL);controls.grid(row=1,column=0,sticky='w')
        self.play_buttons=[]
        for text,command in [('Back',lambda:self.player_command(self.player.previous)),('Play',self.play_pause),
                             ('Skip',lambda:self.player_command(self.player.next)),('Stop',lambda:self.player_command(self.player.stop))]:
            button=Button(controls,text,command,width=54,height=28,font=(self.app.ui_font,8))
            button.pack(side='left',padx=2);self.play_buttons.append(button)
        self.progress=ttk.Scale(bar,from_=0,to=1)
        self.progress.grid(row=1,column=1,sticky='ew',padx=8)
        self.progress.bind('<ButtonPress-1>',lambda e:setattr(self,'seeking',True))
        self.progress.bind('<ButtonRelease-1>',self.seek)
        self.time=tk.Label(bar,text='0:00 / 0:00',bg=PANEL,fg=FG,font=(self.app.ui_font,8));self.time.grid(row=1,column=2,padx=5)
        volume=tk.Frame(bar,bg=PANEL);volume.grid(row=2,column=0,columnspan=3,sticky='ew')
        tk.Label(volume,text='Volume',bg=PANEL,fg=MUTED,font=(self.app.ui_font,8)).pack(side='left',padx=5)
        self.volume=ttk.Scale(volume,from_=0,to=100,command=self.player.set_volume);self.volume.set(70);self.volume.pack(side='left',fill='x',expand=True,padx=(0,8))

    def play_pause(self):
        if self.app.worker_busy:return
        selected=self.selected()
        path=selected[0] if selected else None
        if self.player.current and (path is None or self.player.current['path'] in selected):self.player_command(self.player.toggle)
        elif path:
            playlist=selected if len(selected)>1 else list(self.tree.get_children())
            self.player_command(lambda:self.player.play([self.records[p] for p in playlist],playlist.index(path)))

    def player_command(self,command):
        if self.app.worker_busy and command!=self.player.stop:return
        try:command()
        except Exception as error:messagebox.showwarning('Playback',str(error))

    def seek(self,event=None):
        self.seeking=False
        self.player_command(lambda:self.player.seek(self.progress.get()))

    def tick(self):
        self.timer=None
        try:self.player.pump()
        except Exception as error:self.player.stop();self.app.log('Playback: '+str(error))
        current=self.player.current
        self.now.configure(text=(self.player.state.title()+': '+Path(current['path']).name) if current else 'Select a track and press Play')
        self.play_buttons[1].text='Pause' if self.player.state=='playing' else 'Play';self.play_buttons[1].draw()
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
