"""Reference-inspired desktop layout for the existing Groove Goblin workflow."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont

BG = '#090f14'
PANEL = '#10191f'
GREEN = '#69f58b'
MUTED = '#9aa9b7'


class PageNavigation:
    """Keep existing workflow navigation while showing editor and preview together."""
    def __init__(self, app):
        self.app = app

    def select(self, page):
        app = self.app
        if page is app.tab_history:
            app.dashboard.grid_remove()
            app.tab_history.grid(row=0, column=0, sticky='nsew')
        else:
            app.tab_history.grid_remove()
            app.dashboard.grid(row=0, column=0, sticky='nsew')
            if page is app.tab_editor:
                app.album_entry.focus_set()


def install_layout(cls):
    old_style = cls.build_style
    old_refresh = cls.refresh_preview
    old_clear = cls.clear

    def build_style(self):
        old_style(self)
        s = ttk.Style(self)
        self.ui_font = 'Segoe UI' if 'Segoe UI' in tkfont.families(self) else 'Helvetica'
        s.configure('.', background=BG, foreground='#e5edf3', font=(self.ui_font, self.font_size))
        s.configure('Panel.TFrame', background=PANEL)
        s.configure('Card.TLabelframe', background=BG, bordercolor='#2b3b45', relief='solid')
        s.configure('Card.TLabelframe.Label', foreground='#e5edf3', background=BG, font=(self.ui_font, self.font_size, 'bold'))
        s.configure('TButton', background='#17232c', bordercolor='#344652', padding=(10, 9), relief='flat')
        s.map('TButton', background=[('active', '#253742'), ('disabled', '#111a21')])
        s.configure('Go.TButton', background='#7909bc', bordercolor='#b543ec', padding=(15, 12))
        s.map('Go.TButton', background=[('active', '#9423d2'), ('disabled', '#33203d')])
        s.configure('Apply.TButton', background='#7909bc', bordercolor='#b543ec', padding=(15, 10))
        s.map('Apply.TButton', background=[('active', '#9423d2'), ('disabled', '#33203d')])
        s.configure('Nav.TButton', anchor='w', padding=(15, 9), background=BG, borderwidth=0)
        s.configure('TCheckbutton', background=BG, foreground='#e5edf3', indicatorsize=16, indicatormargin=5)
        s.map('TCheckbutton', indicatorbackground=[('selected', GREEN), ('!selected', '#17232c')], indicatorforeground=[('selected', BG)])
        s.configure('Treeview', background=PANEL, fieldbackground=PANEL, bordercolor='#283842', rowheight=31, font=(self.ui_font, self.font_size))
        s.configure('Treeview.Heading', background='#1b2832', foreground='#e0e9f0', padding=(8, 9), font=(self.ui_font, self.font_size))
        s.configure('TScrollbar', troughcolor=BG, background='#253641', bordercolor=BG, arrowcolor=MUTED)

    def build_ui(self):
        self.geometry('1480x900')
        self.minsize(800, 600)
        self.preview_filter = tk.StringVar(value='All')
        # Reserve the action bar; scroll the workspace at smaller resolutions.
        footer = ttk.Frame(self, padding=(12, 8))
        footer.pack(side='bottom', fill='x')
        commands = ttk.Frame(footer)
        commands.pack(side='bottom', anchor='e')
        self.btn_apply = ttk.Button(commands, text='✓  Apply Selected Changes', style='Apply.TButton', command=self.apply)
        self.btn_apply.pack(side='right', padx=(7, 0))
        self.btn_apply.state(['disabled'])
        ttk.Button(commands, text='↶  Undo Last Apply', command=self.undo).pack(side='right', padx=(7, 0))
        ttk.Button(commands, text='▣  Save Report', command=self.export).pack(side='right', padx=(7, 0))
        self.btn_cancel = ttk.Button(commands, text='Cancel', command=self.cancel_search)
        self.btn_cancel.pack(side='right')
        self.btn_cancel.state(['disabled'])
        ttk.Label(footer, textvariable=self.status, style='Muted.TLabel', wraplength=750).pack(side='top', anchor='w', pady=(0, 5))

        viewport = ttk.Frame(self)
        viewport.pack(fill='both', expand=True)
        self.workspace_canvas = tk.Canvas(viewport, bg=BG, highlightthickness=0)
        ys = ttk.Scrollbar(viewport, orient='vertical', command=self.workspace_canvas.yview)
        xs = ttk.Scrollbar(viewport, orient='horizontal', command=self.workspace_canvas.xview)
        self.workspace_canvas.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        viewport.rowconfigure(0, weight=1)
        viewport.columnconfigure(0, weight=1)
        self.workspace_canvas.grid(row=0, column=0, sticky='nsew')
        ys.grid(row=0, column=1, sticky='ns')
        xs.grid(row=1, column=0, sticky='ew')
        desktop = ttk.Frame(self.workspace_canvas, padding=10)
        item = self.workspace_canvas.create_window(0, 0, anchor='nw', window=desktop)
        def resize(event):
            self.workspace_canvas.itemconfigure(item, width=max(1120, event.width), height=max(760, event.height))
            self.workspace_canvas.configure(scrollregion=self.workspace_canvas.bbox('all'))
        self.workspace_canvas.bind('<Configure>', resize)
        desktop.bind('<Configure>', lambda e: self.workspace_canvas.configure(scrollregion=self.workspace_canvas.bbox('all')))
        desktop.rowconfigure(0, weight=1)
        desktop.columnconfigure(1, weight=1)

        side = ttk.Frame(desktop, width=220, padding=(5, 8, 15, 8))
        side.grid(row=0, column=0, sticky='nsew')
        side.pack_propagate(False)
        try:
            self.logo = tk.PhotoImage(file=str(Path(__file__).parent / 'assets' / 'groove_goblin_logo.png'))
            # Raster wordmark is bundled; preserve its aspect ratio and branding.
            self.logo = self.logo.zoom(4, 4).subsample(5, 5)
            ttk.Label(side, image=self.logo).pack(pady=(0, 8))
        except tk.TclError:
            ttk.Label(side, text='GROOVE\nGOBLIN', foreground=GREEN, font=(self.ui_font, 24, 'bold')).pack()
        ttk.Label(side, text='MUSIC TAGGER & ORGANIZER', font=(self.ui_font, 9, 'bold')).pack(pady=(0, 20))
        self.content = ttk.Frame(desktop)
        self.content.grid(row=0, column=1, sticky='nsew')
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)
        self.dashboard = ttk.Frame(self.content)
        self.dashboard.grid(row=0, column=0, sticky='nsew')
        self.dashboard.columnconfigure(0, weight=1)
        self.dashboard.rowconfigure(1, weight=1)
        self.tab_history = ttk.Frame(self.content, padding=12)
        self.tabs = PageNavigation(self)
        ttk.Label(side, text='Groove Goblin / Desktop prototype', style='Muted.TLabel', font=(self.ui_font, 8)).pack(side='bottom', pady=8)
        formats = ttk.LabelFrame(side, text='Supported Formats', style='Card.TLabelframe', padding=12)
        formats.pack(side='bottom', fill='x', pady=12)
        ttk.Label(formats, text='FLAC   ✓\nMP3     ✓', foreground=GREEN, font=(self.ui_font, 12), justify='left').pack(anchor='w')
        for label, command in [
            ('⌕  Scan & Fix', lambda: self.tabs.select(self.tab_albums)),
            ('◉  Album Lookup', self.go_editor),
            ('✎  Manual Edit', self.go_editor),
            ('⚙  Settings', lambda: (self.tabs.select(self.tab_albums), self.filename_check.focus_set())),
            ('↶  Undo / Journals', lambda: self.tabs.select(self.tab_history)),
            ('☷  View Logs', lambda: self.tabs.select(self.tab_history)),
            ('ⓘ  About', lambda: messagebox.showinfo('Groove Goblin', 'Music tagger & organizer\nFLAC and MP3\n\nScans and previews are read-only.\nUndo journals are not full audio backups.')),
        ]:
            ttk.Button(side, text=label, style='Nav.TButton', command=command).pack(fill='x', pady=2)


        toolbar = ttk.Frame(self.dashboard, padding=(10, 4, 0, 10))
        toolbar.grid(row=0, column=0, columnspan=2, sticky='ew')
        ttk.Button(toolbar, text='♫  Add Folders', command=self.add_folder).pack(side='left', padx=(0, 8))
        ttk.Button(toolbar, text='✕  Clear List', command=self.clear).pack(side='left', padx=(0, 8))
        self.btn_scan = ttk.Button(toolbar, text='▶  Start Scan', style='Go.TButton', command=self.scan)
        self.btn_scan.pack(side='left', padx=(0, 8))
        self.btn_auto = ttk.Button(toolbar, text='Search All Online', command=self.lookup_all)
        self.btn_auto.pack(side='left')
        ttk.Label(toolbar, textvariable=self.count, style='Muted.TLabel').pack(side='right', padx=8)

        center = ttk.Frame(self.dashboard, padding=(10, 0, 10, 0))
        center.grid(row=1, column=0, sticky='nsew')
        checks = ttk.Frame(center)
        checks.pack(fill='x', pady=(0, 5))
        ttk.Checkbutton(checks, text='Search MusicBrainz after scan', variable=self.auto_lookup).pack(side='left')
        ttk.Label(checks, text='Subfolders included / grouped by folder', style='Muted.TLabel', font=(self.ui_font, 8)).pack(side='right')
        self.root_text = ttk.Label(center, text='No folders selected', style='Muted.TLabel')
        self.root_text.pack(fill='x', pady=(0, 8))
        panes = ttk.Panedwindow(center, orient='vertical')
        panes.pack(fill='both', expand=True)
        self.after_idle(lambda: panes.sashpos(0, int(panes.winfo_height() * .58)))
        self.tab_albums = ttk.LabelFrame(panes, text='Albums Found', style='Card.TLabelframe', padding=9)
        self.tab_preview = ttk.LabelFrame(panes, text='Preview Changes — read-only', style='Card.TLabelframe', padding=9)
        panes.add(self.tab_albums, weight=3)
        panes.add(self.tab_preview, weight=2)
        row = ttk.Frame(self.tab_albums)
        row.pack(fill='x', pady=(0, 5))
        ttk.Label(row, text='Select an album to inspect its match.', style='Muted.TLabel').pack(side='left')
        ttk.Button(row, text='Include / Skip', command=self.toggle_selected).pack(side='right')
        self.albums_tree = self.new_tree(self.tab_albums, ('Use', 'Artist', 'Current album', 'Proposed album', 'Year', 'Tracks', 'Status', 'Match'), [45, 120, 150, 170, 60, 60, 115, 65])
        self.albums_tree.bind('<<TreeviewSelect>>', self.on_album_select)
        self.albums_tree.bind('<Double-1>', lambda e: self.go_editor())
        filters = ttk.Frame(self.tab_preview)
        filters.pack(fill='x', pady=(0, 6))
        for name in ('All', 'Folders', 'Tags', 'Filenames'):
            ttk.Radiobutton(filters, text=name, variable=self.preview_filter, value=name, command=self.refresh_preview).pack(side='left', padx=(0, 8))
        self.preview_summary = ttk.Label(self.tab_preview, text='Run a scan to build a preview.', style='Muted.TLabel', wraplength=600)
        self.preview_summary.pack(fill='x', pady=(0, 5))
        self.preview_tree = self.new_tree(self.tab_preview, ('Action', 'Existing', 'Proposed', 'Detail'), [95, 240, 260, 170])
        self.preview_errors = tk.Text(self.tab_preview, height=2, bg=PANEL, fg='#ffc777', relief='flat', wrap='word', font=(self.ui_font, 9))
        self.preview_errors.pack(fill='x', pady=(6, 0))
        self.preview_errors.configure(state='disabled')

        self.tab_editor = ttk.Frame(self.dashboard, width=310, padding=(0, 0, 5, 0))
        self.tab_editor.grid(row=1, column=1, sticky='nsew')
        self.tab_editor.pack_propagate(False)
        opts = ttk.LabelFrame(self.tab_editor, text='Rename & Tag Options', style='Card.TLabelframe', padding=10)
        opts.pack(fill='x', pady=(0, 10))
        self.filename_check = ttk.Checkbutton(opts, text='Rename music files (optional)', variable=self.opt_filenames, command=self.refresh_preview)
        self.filename_check.pack(anchor='w')
        ttk.Checkbutton(opts, text='Rename album folders', variable=self.opt_folders, command=self.refresh_preview).pack(anchor='w')
        ttk.Label(opts, text='Artist - Album Title (Year)', foreground=GREEN, font=(self.ui_font, 9)).pack(anchor='w', padx=24, pady=4)
        ttk.Checkbutton(opts, text='Update album / year tags', variable=self.opt_tags, command=self.refresh_preview).pack(anchor='w')
        ttk.Label(opts, text='Undo journal saved before changes\nKeep separate music backups.', style='Muted.TLabel', font=(self.ui_font, 8)).pack(anchor='w', pady=(6, 0))
        details = ttk.LabelFrame(self.tab_editor, text='Selected Album Details', style='Card.TLabelframe', padding=10)
        details.pack(fill='x', pady=(0, 10))
        self.current_label = ttk.Label(details, text='Select an album to see its details.', style='Muted.TLabel', wraplength=275)
        self.current_label.pack(fill='x', pady=(0, 8))
        form = ttk.Frame(details)
        form.pack(fill='x')
        form.columnconfigure(1, weight=1)
        for n, (label, var) in enumerate([('Artist', self.var_artist), ('Album (new)', self.var_album), ('Year', self.var_year)]):
            ttk.Label(form, text=label).grid(row=n, column=0, sticky='w', padx=(0, 5))
            entry = ttk.Entry(form, textvariable=var, width=18)
            entry.grid(row=n, column=1, sticky='ew', pady=4)
            if var is self.var_album: self.album_entry = entry
        ttk.Checkbutton(details, text='Include in batch', variable=self.var_enabled, command=self.set_enabled).pack(anchor='w')
        ttk.Button(details, text='✓  Save & Approve Match', style='Go.TButton', command=self.save_match).pack(fill='x', pady=(5, 0))
        ttk.Button(details, text='⌕  Search Online', command=self.lookup_selected).pack(fill='x', pady=(5, 0))
        results = ttk.LabelFrame(self.tab_editor, text='Search Results / MusicBrainz', style='Card.TLabelframe', padding=8)
        results.pack(fill='both', expand=True)
        self.tracks_info = ttk.Label(results, text='', style='Muted.TLabel', wraplength=275, font=(self.ui_font, 8))
        self.tracks_info.pack(side='bottom', fill='x', pady=(4, 0))
        ttk.Button(results, text='Select Highlighted Result', command=self.use_result).pack(side='bottom', fill='x', pady=(5, 0))
        self.results_tree = self.new_tree(results, ('Album', 'Artist', 'Year', 'Type', 'Score'), [145, 100, 55, 70, 55])
        self.results_tree.bind('<Double-1>', lambda e: self.use_result())
        self.make_history()
        self.refresh_preview()

    def refresh_preview(self):
        old_refresh(self)
        if not hasattr(self, 'preview_filter'): return
        wanted = {'Folders': 'FOLDER', 'Tags': 'TAGS', 'Filenames': 'FILENAME'}.get(self.preview_filter.get())
        if wanted:
            for item in self.preview_tree.get_children():
                if self.preview_tree.item(item, 'values')[0] != wanted:
                    self.preview_tree.delete(item)

    def clear(self):
        old_clear(self)
        if self.worker_busy: return
        self.current_label.configure(text='Select an album to see its details.')
        for var in (self.var_artist, self.var_album, self.var_year): var.set('')
        self.results_tree.delete(*self.results_tree.get_children())
        self.tracks_info.configure(text='')

    cls.build_style = build_style
    cls.build_ui = build_ui
    cls.refresh_preview = refresh_preview
    cls.clear = clear
