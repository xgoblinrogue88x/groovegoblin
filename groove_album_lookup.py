"""Dedicated MusicBrainz browsing and matching page; searches never write music."""
import tkinter as tk
from tkinter import ttk, messagebox
from types import SimpleNamespace
from groove_widgets import BG, PANEL, FG, MUTED, GREEN, Button, Panel, Table


class AlbumLookup(tk.Frame):
    def __init__(self,app):
        super().__init__(app.content,bg=BG)
        self.app=app;self.uid=None;self.hits=[];self.ids=[None];self.searching=False
        self.artist=tk.StringVar();self.title=tk.StringVar();self.info=tk.StringVar(value='Search by artist and album. Select a loaded album to use a result.')
        self.columnconfigure(0,weight=1);self.rowconfigure(2,weight=1)
        tk.Label(self,text='Album Lookup',bg=BG,fg=GREEN,font=(app.ui_font,14,'bold'),anchor='w').grid(row=0,column=0,sticky='ew',pady=(0,6))
        self.search_panel=Panel(self,height=182,padding=8);self.search_panel.grid(row=1,column=0,sticky='ew',pady=(0,8))
        form=self.search_panel.body;form.columnconfigure(1,weight=1)
        tk.Label(form,text='Loaded album',bg=PANEL,fg=MUTED,font=(app.ui_font,9)).grid(row=0,column=0,sticky='w',padx=(0,8),pady=3)
        self.target=ttk.Combobox(form,state='readonly',width=25);self.target.grid(row=0,column=1,sticky='ew',pady=3)
        self.target.bind('<<ComboboxSelected>>',lambda event:self.select_target(self.ids[self.target.current()]))
        self.entries=[]
        for row,(label,var) in enumerate([('Artist',self.artist),('Album',self.title)],1):
            tk.Label(form,text=label,bg=PANEL,fg=MUTED,font=(app.ui_font,9)).grid(row=row,column=0,sticky='w',pady=3)
            entry=ttk.Entry(form,textvariable=var,width=25);entry.grid(row=row,column=1,sticky='ew',pady=3)
            entry.bind('<Return>',lambda event:self.search());self.entries.append(entry)
        search_actions=tk.Frame(form,bg=PANEL);search_actions.grid(row=3,column=1,sticky='w',pady=(4,3))
        self.search_button=Button(search_actions,'Search MusicBrainz',self.search,width=185,height=32,symbol='search',primary=True,font=(app.ui_font,9))
        self.search_button.pack(side='left')
        self.cancel_button=Button(search_actions,'Cancel',app.cancel_search,width=85,height=32,font=(app.ui_font,9))
        self.cancel_button.pack(side='left',padx=(6,0))
        self.message=tk.Label(form,textvariable=self.info,bg=PANEL,fg=MUTED,font=(app.ui_font,8),anchor='w',justify='left',wraplength=450)
        self.message.grid(row=4,column=0,columnspan=2,sticky='ew')
        self.results_panel=Panel(self,padding=8);self.results_panel.grid(row=2,column=0,sticky='nsew')
        tk.Label(self.results_panel.body,text='MusicBrainz Results',bg=PANEL,fg=FG,font=(app.ui_font,10,'bold')).pack(anchor='w',pady=(0,6))
        self.results=Table(self.results_panel.body,mode='results',font=(app.ui_font,9),on_choose=self.choose)
        self.results.cover_provider=lambda row,size:app._art.request_result(self.hits[int(row)].get('id'),size) if int(row)<len(self.hits) else None
        self.results.pack(fill='both',expand=True)
        footer=tk.Frame(self,bg=BG);footer.grid(row=3,column=0,sticky='ew',pady=(6,0))
        self.choose_button=Button(footer,'Use Selected Result',self.choose,width=190,height=34,symbol='check',primary=True,font=(app.ui_font,9))
        self.choose_button.pack(side='left')
        self.scan_button=Button(footer,'Go to Scan & Rename',lambda:app.tabs.select(app.tab_albums),width=190,height=34,font=(app.ui_font,9))
        self.scan_button.pack(side='left',padx=(6,0))
        self.bind('<Configure>',self.resize)
        self.refresh_albums();self.set_busy(False)

    def resize(self,event=None):
        width=self.winfo_width();compact=width<1000 or self.winfo_height()<650
        phone=getattr(self.app,'_phone',None)
        if phone is not None and phone.active:
            size=round(12*getattr(phone,'unit',1))
            self.target.configure(width=1,font=(self.app.ui_font,size),style='Phone.TCombobox')
            for entry in self.entries:entry.configure(width=1,font=(self.app.ui_font,size),style='Phone.TEntry')
            self.search_button.master.grid_configure(column=0,columnspan=2,sticky='ew')
            self.search_button.symbol=None;self.search_button.text='Search MusicBrainz'
            for button in (self.search_button,self.cancel_button):
                button.font=(self.app.ui_font,11);button.configure(height=44);button.draw()
            for button,text in ((self.choose_button,'Use Result'),(self.scan_button,'Scan & Rename')):
                button.symbol=None;button.text=text;button.font=(self.app.ui_font,11)
                button.configure(width=max(100,(width-10)//2),height=44);button.draw()
            self.message.configure(wraplength=max(240,width-24),height=3)
            self.search_panel.configure(height=max(260,self.search_panel.body.winfo_reqheight()+20))
            self.results.rowheight=round(82*getattr(phone,'unit',1));self.results.font=(self.app.ui_font,size);self.results.schedule()
            return
        self.search_button.master.grid_configure(column=1,columnspan=1,sticky='w')
        self.target.configure(style='TCombobox')
        for entry in self.entries:entry.configure(style='TEntry')
        for button,text in ((self.choose_button,'Use Selected Result'),(self.scan_button,'Go to Scan & Rename')):
            button.text=text;button.configure(width=190,height=34);button.font=(self.app.ui_font,9);button.draw()
        self.choose_button.symbol='check';self.search_button.symbol='search';self.message.configure(height=0)
        self.search_panel.configure(height=182 if compact else 194)
        self.message.configure(wraplength=max(240,width-30))
        for panel in (self.search_panel,self.results_panel):
            panel.padding=6 if compact else 10
            panel.resize(SimpleNamespace(width=panel.winfo_width(),height=panel.winfo_height()))
        self.results.rowheight=56 if compact else 66;self.results.schedule()

    def refresh_albums(self):
        self.ids=[None,*[album.uid for album in self.app.matched]]
        labels=['Browse only (no target album)',*[f'{i}. {album.artist or "Unknown artist"} - {album.album or album.old_album or "Unknown album"}' for i,album in enumerate(self.app.matched,1)]]
        self.target.configure(values=labels)
        if self.uid not in self.ids:self.select_target(None)
        self.target.current(self.ids.index(self.uid))

    def select_target(self,uid):
        changed=uid!=self.uid;self.uid=uid
        self.app.selected_id=uid
        if uid in self.app.album_map:
            album=self.app.album_map[uid]
            if uid in self.app.albums_tree.data:self.app.albums_tree.selection_set(uid)
            if changed:self.artist.set(album.artist);self.title.set(album.album or album.old_album)
            self.show_results(album.lookup_results)
            self.info.set(f'{album.file_count} loaded tracks. Search, then choose the correct original release.')
        elif changed:
            self.show_results([]);self.info.set('Browse results without changing a loaded album. Choose a target to use a match.')
        if uid in self.ids:self.target.current(self.ids.index(uid))
        self.set_busy(self.app.worker_busy)

    def show_results(self,hits):
        self.hits=list(hits);self.results.delete(*self.results.get_children())
        for i,hit in enumerate(self.hits):
            self.results.insert('','end',iid=str(i),values=(hit.get('title',''),hit.get('artist',''),hit.get('year',''),hit.get('type',''),hit.get('score','')))
        self.set_busy(self.app.worker_busy)

    def search(self):
        if self.app.worker_busy:return
        artist=self.artist.get().strip();title=self.title.get().strip();uid=self.uid
        if not artist:messagebox.showwarning('Artist required','Enter an artist to search MusicBrainz.',parent=self.app);return
        self.info.set('Searching MusicBrainz…');self.show_results([]);self.searching=True
        def work():
            hits=self.app.mb.search_albums(artist,title,limit=35)
            if not hits and title and not self.app.cancel.is_set():hits=self.app.mb.search_albums(artist,'',limit=35)
            if self.app.cancel.is_set():
                self.app.queue.put(('lookup_canceled',uid));return
            self.app.queue.put(('lookup_hits',uid,hits))
        self.app.run_background(work)

    def receive(self,uid,hits):
        if uid!=self.uid:return
        self.show_results(hits)
        self.info.set(f'{len(hits)} results. Choose a release to prepare the preview.' if hits else 'No matches found. Try a different artist or album title.')

    def choose(self):
        if self.app.worker_busy:return
        selected=self.results.selection();album=self.app.album_map.get(self.uid)
        if not album:
            self.info.set('Choose a loaded album above before using a result.');return
        if not selected:
            self.info.set('Select a MusicBrainz result first.');return
        # Reuse the existing validation/approval path; Apply remains explicit.
        hit=self.hits[int(selected[0])]
        if not hit.get('year'):
            self.info.set('This result has no original release year. Choose another result or edit the year in Scan & Rename.')
        album.lookup_results=list(self.hits);self.app.selected_id=album.uid
        self.app.populate_results(album);self.app.results_tree.selection_set(selected[0])
        self.app.var_enabled.set(album.enabled);self.app.use_result()
        if hit.get('year') and album.approved:self.info.set('Album approved. Review the preview in Scan & Rename before applying.')

    def set_busy(self,busy):
        self.search_button.state(['disabled'] if busy else ['!disabled'])
        self.cancel_button.state(['!disabled'] if busy and self.searching else ['disabled'])
        if not busy:self.searching=False
        self.choose_button.state(['!disabled'] if not busy and self.uid in self.app.album_map and self.hits else ['disabled'])
