"""Shared, resize-safe Settings for the three application modes."""
import tkinter as tk
from tkinter import ttk
from groove_modes import switch_button
from groove_widgets import BG, FG, MUTED, Button, Check, Scrollbar, bind_mousewheel


def show_settings(app):
    app.tabs.select(app.tab_albums)
    window=tk.Toplevel(app,bg=BG)
    window.title('Groove Goblin - Settings');window.geometry('480x520');window.minsize(300,280)
    app.settings_window=window
    scroll=Scrollbar(window,orient='vertical',style='Vertical.Goblin.TScrollbar')
    canvas=tk.Canvas(window,bg=BG,highlightthickness=0,yscrollincrement=28)
    canvas.pack(fill='both',expand=True);scroll.configure(command=canvas.yview)
    canvas.configure(yscrollcommand=scroll.set)
    body=tk.Frame(canvas,bg=BG)
    item=canvas.create_window(0,0,window=body,anchor='nw')
    if hasattr(app,'_phone'):
        layout=tk.Frame(body,bg=BG);layout.pack(fill='x',padx=20,pady=(10,0))
        tk.Label(layout,text='Layout',bg=BG,fg=FG,font=(app.ui_font,11)).pack(side='left',padx=(0,10))
        choice=ttk.Combobox(layout,textvariable=app._phone.mode,values=['Auto','Phone'],state='readonly',width=10,font=(app.ui_font,11))
        choice.pack(side='left',fill='x',expand=True)
        def change_layout(event):
            if app._phone.mode.get()=='Phone':app._phone.open_phone()
            else:app._responsive.schedule()
        choice.bind('<<ComboboxSelected>>',change_layout)
    Check(body,'Search MusicBrainz after scan',app.auto_lookup,width=1,font=(app.ui_font,10)).pack(fill='x',padx=20,pady=(20,5))
    explanation=tk.Label(body,text='Online searches send artist / album lookup text, not audio files. Results can load public cover previews. Turn online scanning off to work offline.\n\nUndo journals save changed fields and paths. Keep separate music backups.',bg=BG,fg=MUTED,font=(app.ui_font,10),justify='left',anchor='w',wraplength=420)
    explanation.pack(fill='x',padx=20,pady=10)
    actions=tk.Frame(body,bg=BG);actions.pack(fill='x',padx=20,pady=(0,16))
    app.settings_search_button=Button(actions,'Search All Albums Online',app.lookup_all,width=260,height=48,
        wrap_label=True,font=(app.ui_font,11,'bold'))
    app.settings_search_button.pack(fill='x',pady=(0,8))
    targets={'desktop':('mobile','lite'),'mobile':('desktop','lite'),'lite':('mobile','desktop')}[app.app_mode]
    app.settings_switch_buttons={}
    for target in targets:
        button=switch_button(app,actions,target);button.pack(fill='x',pady=(0,8))
        app.settings_switch_buttons[target]=button
    buttons=(app.settings_search_button,*app.settings_switch_buttons.values())
    def fit_actions(event):
        if event.width<40:return
        height=max(button.label_height(event.width) for button in buttons)
        for button in buttons:
            button.min_label_height=height
            if int(button.cget('height'))!=height:button.configure(height=height)
            else:button.draw()
    actions.bind('<Configure>',fit_actions)
    fitting=False
    def fit(event=None):
        nonlocal fitting
        if fitting:return
        fitting=True
        try:
            width=max(1,canvas.winfo_width())
            canvas.itemconfigure(item,width=width)
            explanation.configure(wraplength=max(1,width-40))
            canvas.configure(scrollregion=canvas.bbox('all'))
            if body.winfo_reqheight()>canvas.winfo_height():scroll.pack(side='right',fill='y',before=canvas)
            else:scroll.pack_forget()
        finally:fitting=False
    canvas.bind('<Configure>',fit);body.bind('<Configure>',fit)
    def descendants(widget):
        return [widget,*[nested for child in widget.winfo_children() for nested in descendants(child)]]
    bind_mousewheel(canvas,targets=(*descendants(body),scroll))
    app.settings_canvas=canvas
    if getattr(getattr(app,'_phone',None),'active',False):app._phone.fit_dialog(window,560)
    return window
