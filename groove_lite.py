"""Remote-desktop layout; retains the read-only plan and confirmation internally."""
from PIL import Image, ImageTk
from groove_widgets import Button
from groove_version import __version__


def install_lite(app):
    app.minsize(800,540)
    w=app._responsive.w
    toolbar=w['toolbar']
    toolbar.grid_forget()
    # Recreate the small actions in a single row across the entire workspace.
    import tkinter as tk
    from tkinter import ttk
    from groove_naming import FILE_FORMATS, FOLDER_FORMATS
    from groove_widgets import PANEL, FG
    # Keep the album actions together, with naming presets immediately below.
    header=app.remove_albums_button.master
    app.btn_verify.pack_forget()
    app.btn_verify.pack(in_=header,side='right',padx=(0,5))
    formats=tk.Frame(app.tab_albums,bg=PANEL)
    formats.pack(fill='x',before=app.albums_tree,pady=(0,7))
    for column,(label,var,presets,attribute) in enumerate([
        ('Track rename format',app.file_format,FILE_FORMATS,'lite_file_format_box'),
        ('Album rename format',app.folder_format,FOLDER_FORMATS,'lite_folder_format_box'),
    ]):
        formats.columnconfigure(column,weight=1,uniform='formats')
        field=tk.Frame(formats,bg=PANEL)
        field.grid(row=0,column=column,sticky='ew',padx=(0,6 if column==0 else 0))
        tk.Label(field,text=label,bg=PANEL,fg=FG,font=(app.ui_font,8),anchor='w').pack(fill='x')
        combo=ttk.Combobox(field,textvariable=var,values=list(presets),state='readonly',width=1,font=(app.ui_font,9))
        combo.pack(fill='x',pady=(2,0))
        combo.bind('<<ComboboxSelected>>',lambda event:app.refresh_preview())
        setattr(app,attribute,combo)
    app.lite_formats=formats
    top=tk.Frame(app.dashboard,bg=app.cget('bg'))
    top.grid(row=0,column=0,columnspan=2,sticky='ew',pady=(0,5))
    app.dashboard.rowconfigure(0,weight=0)
    app.dashboard.rowconfigure(1,weight=1)
    w['center'].grid_configure(row=1)
    app.tab_editor.grid_configure(row=1)
    specs=[('Add Folders','Folders',app.add_folder,'folder',False),
           ('Add Files','Files',app.add_files,'music',False),
           ('Clear List','Clear',app.clear,'cross',False),
           ('Start Scan','Scan',app.scan,'play',True),
           ('Apply Changes','Apply',app.apply,'check',True),
           ('Undo Changes','Undo',app.undo,'undo',False)]
    buttons=[]
    for column,(text,short,command,symbol,primary) in enumerate(specs):
        top.columnconfigure(column,weight=1,uniform='actions')
        button=Button(top,text,command,width=120,height=36,symbol=symbol,
                      primary=primary,accent={0:'#ffd443',1:'#b52bf4',2:'#ff464e'}.get(column),font=(app.ui_font,8))
        button.grid(row=0,column=column,sticky='ew',padx=(0,4 if column<5 else 0))
        button.lite_label=text;button.lite_short=short;buttons.append(button)
    app.btn_scan=buttons[3];app.btn_apply=buttons[4];app.btn_undo=buttons[5]
    app.btn_apply.state(['disabled'])
    app.lite_toolbar=top;app.lite_buttons=buttons
    # A cancel action stays reachable without restoring the footer controls.
    cancel=Button(w['checkrow'],'Cancel',app.cancel_search,width=70,height=22,font=(app.ui_font,8))
    cancel.grid(row=3,column=0,sticky='w')
    cancel.on_state=lambda:cancel.grid_remove() if cancel.disabled else cancel.grid()
    cancel.state(['disabled']);app.btn_cancel=cancel
    app._footer_controls.pack_forget()
    app._footer.configure(pady=0)
    app._footer.pack_configure(pady=(3,4))

    def apply_layout():
        compact=app._desktop.winfo_width()<1200 or app._desktop.winfo_height()<750
        for button,width in ((app.btn_verify,104 if compact else 140),(app.remove_albums_button,140 if compact else 170)):
            button.configure(width=width,height=27)
            button.font=(app.ui_font,8 if compact else 9);button.draw()
        w['toolbar'].grid_remove();w['preview'].grid_remove();w['opts'].grid_remove();w['player'].grid_remove()
        app._footer_controls.pack_forget();w['footer_spacer'].pack_forget()
        app.status_label.configure(height=1)
        w['center'].rowconfigure(0,weight=0,minsize=0)
        w['center'].rowconfigure(2,weight=1,minsize=0)
        w['center'].rowconfigure(3,weight=0,minsize=0)
        w['albums'].grid_configure(pady=0)
        app.tab_editor.rowconfigure(0,weight=0)
        app.tab_editor.rowconfigure(1,weight=1)
        app.tab_editor.rowconfigure(2,weight=0)
        w['details'].grid_configure(row=0,pady=(0,5))
        w['results'].grid_configure(row=1)
        # The three detail actions need room for their icon and label on Windows.
        app.update_idletasks()
        w['details'].configure(height=max(246 if compact else 290,
            w['details'].body.winfo_reqheight()+w['details'].padding*2+2))
        available=max(1,app.content.winfo_width())
        for button in buttons:
            button.configure(width=max(70,available//6-4),height=36 if compact else 42)
            button.font=(app.ui_font,8 if compact else 10)
            button.text=button.lite_short if available//6<125 else button.lite_label
            button.draw()
        # Restore clear LITE wording after the shared plan updates its count.
        app.btn_apply.text='Apply' if available//6<125 else 'Apply Changes'
        app.btn_apply.draw()
        budget=max(48,app._desktop.winfo_height()-len(app.nav_buttons)*(26 if compact else 38)-60)
        size=min(150 if compact else 228,int(budget*app._responsive.logo_source.width/app._responsive.logo_source.height))
        image=app._responsive.logo_source.copy();image.thumbnail((size,320),Image.Resampling.LANCZOS)
        app.logo=ImageTk.PhotoImage(image,master=app);app._logo_label.configure(image=app.logo)
        app._responsive.logo_size=None
        app._responsive.version.configure(text=f'Groove Goblin LITE v{__version__}')
    app._lite_apply=apply_layout
    apply_layout()
