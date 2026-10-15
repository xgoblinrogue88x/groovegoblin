"""Adapt the desktop to the live window size, without an outer scroll area."""
from pathlib import Path
from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk, font as tkfont
from PIL import Image, ImageTk
from groove_widgets import Button, Check


class ResponsiveLayout:
    def __init__(self,app,widgets):
        self.app=app;self.w=widgets;self.pending=None;self.fonts={};self.buttons={}
        self.nav_text={name:b.text for name,b in app.nav_buttons.items()}
        self.tooltip=None;self.tooltip_timer=None
        self.logo_source=Image.open(Path(__file__).parent/'assets/groove_goblin_logo.png').convert('RGBA')
        self.logo_size=None
        self.walk(app)
        self.toolbar=list(widgets['toolbar'].winfo_children())
        self.checks=[child for child in widgets['checkrow'].winfo_children() if isinstance(child,Check)]
        self.version=[c for c in widgets['side'].winfo_children() if isinstance(c,tk.Label)][0]
        self.detail_title=widgets['details'].body.winfo_children()[0]
        for name,button in app.nav_buttons.items():
            button.bind('<Enter>',lambda e,b=button,text=self.nav_text[name]:self.show_tip(b,text),add='+')
            button.bind('<Leave>',lambda e:self.hide_tip(),add='+')
            button.bind('<Destroy>',lambda e:self.hide_tip(),add='+')
        app._desktop.bind('<Configure>',lambda e:self.schedule(),add='+')
        app.after_idle(self.apply)

    def walk(self,widget):
        if isinstance(widget,(Button,Check)):
            self.fonts[widget]=widget.font
        elif isinstance(widget,(tk.Label,tk.Text,ttk.Entry,ttk.Combobox)):
            font=tkfont.Font(master=self.app,font=widget.cget('font')).actual()
            self.fonts[widget]=(font['family'],abs(font['size']),font['weight'])
        if isinstance(widget,Button):
            self.buttons[widget]=(int(widget.cget('width')),int(widget.cget('height')),widget.subtitle)
        for child in widget.winfo_children():self.walk(child)

    def schedule(self):
        if self.pending:self.app.after_cancel(self.pending)
        self.pending=self.app.after(16,self.apply)

    def show_tip(self,button,text):
        self.hide_tip()
        if not getattr(self,'icon_nav',False):return
        def display():
            self.tooltip_timer=None
            self.tooltip=tk.Toplevel(self.app);self.tooltip.overrideredirect(True)
            tk.Label(self.tooltip,text=text,bg='#17252f',fg='#edf2f8',padx=9,pady=5,font=(self.app.ui_font,9)).pack()
            self.tooltip.geometry(f'+{button.winfo_rootx()+button.winfo_width()+5}+{button.winfo_rooty()}')
        self.tooltip_timer=self.app.after(500,display)

    def hide_tip(self):
        if self.tooltip_timer:
            try:self.app.after_cancel(self.tooltip_timer)
            except tk.TclError:pass
            self.tooltip_timer=None
        if self.tooltip:
            self.tooltip.destroy();self.tooltip=None

    def apply(self):
        self.pending=None
        a=self.app;w=self.w;width=a._desktop.winfo_width();height=a._desktop.winfo_height()
        if width<100 or height<100:return
        phone=getattr(a,'_phone',None)
        if phone is not None:
            if phone.wants():phone.apply();return
            phone.restore()
        compact=width<1000 or height<650
        medium=not compact and (width<1350 or height<850)
        self.icon_nav=False
        sidebar_width=180 if compact else (210 if medium else 260)
        rail_width=244 if compact else (294 if medium else 342)
        center_width=max(300,width-sidebar_width-rail_width-32)
        scale=.82 if compact else (.92 if medium else 1)
        a._responsive_mode='compact' if compact else ('medium' if medium else 'wide')
        a._desktop.columnconfigure(0,minsize=sidebar_width)
        w['sidebar'].configure(width=sidebar_width)
        a.content.grid_propagate(False)
        a.content.grid_configure(padx=(6,6) if compact else (12,10),pady=(5,0) if compact else (10,0))
        a.dashboard.columnconfigure(1,minsize=rail_width)
        a.tab_editor.configure(width=rail_width)
        w['center'].grid_propagate(False)
        w['center'].rowconfigure(2,minsize=0,weight=3)
        w['center'].rowconfigure(3,minsize=0,weight=2)
        w['albums'].configure(height=170 if compact else (260 if medium else 420))
        w['preview'].configure(height=155 if compact else (210 if medium else 220))
        w['albums'].grid_configure(pady=(0,5 if compact else 9))
        for widget,base in self.fonts.items():
            size=max(8,round(base[1]*scale));font=(base[0],size,*base[2:])
            if isinstance(widget,(Button,Check)):
                widget.font=font
                if isinstance(widget,Check):widget.configure(height=20 if compact else (23 if medium else 25))
                widget.draw()
            else:widget.configure(font=font)
        for panel in (w['sidebar'],w['albums'],w['preview'],w['details'],w['results'],w['player']):
            panel.padding=6 if compact else (9 if medium else 11)
            panel.resize(SimpleNamespace(width=panel.winfo_width(),height=panel.winfo_height()))

        a.track_editor.resize_player(compact)
        # Native Segoe UI metrics can need a few pixels more than Helvetica.
        # Measure the grid after updating fonts so Audio Output remains inside
        # its panel instead of being clipped on Windows.
        a.update_idletasks()
        player_height=max(226 if compact else (242 if medium else 252),
                          w['player'].body.winfo_reqheight()+w['player'].padding*2+2)
        self.version.grid()
        self.version.grid_configure(pady=(0,4) if compact else (4,8))
        for name,button in a.nav_buttons.items():
            button.text=self.nav_text[name]
            # Keep the full navigation titles readable in the narrower sidebar.
            font=button.font
            available=sidebar_width-w['sidebar'].padding*2-66
            while button.text and font[1]>8 and tkfont.Font(master=a,font=(*font,'bold')).measure(button.text)>available:
                font=(font[0],font[1]-1,*font[2:])
            button.font=font
            button.configure(width=sidebar_width-20,height=24 if compact else (36 if medium else 39));button.draw()
            button.pack_configure(pady=0 if compact else 1)
        a.update_idletasks()
        # Reserve the measured navigation before sizing the logo, so the player
        # and version stay inside the rail.
        logo_budget=max(1,height-w['sidebar'].padding*2-w['nav'].winfo_reqheight()-player_height-6-self.version.winfo_reqheight()-(4 if compact else 12)-8)
        logo_width=max(1,min(40 if compact else (174 if medium else 238),int(logo_budget*self.logo_source.width/self.logo_source.height)))
        if logo_width!=self.logo_size:
            img=self.logo_source.copy();img.thumbnail((logo_width,max(1,int(logo_budget))),Image.Resampling.LANCZOS)
            a.logo=ImageTk.PhotoImage(img,master=a);a._logo_label.configure(image=a.logo);self.logo_size=logo_width
        w['player'].configure(height=player_height)
        w['player'].grid_configure(pady=(3,3))

        columns=2 if center_width<660 else 4
        for col in range(4):w['toolbar'].columnconfigure(col,weight=1 if col<columns else 0,minsize=0)
        for i,button in enumerate(self.toolbar):
            base_width,base_height,subtitle=self.buttons[button]
            button.subtitle='' if compact or medium else subtitle
            button.configure(width=max(100,int(center_width/columns)-8),height=36 if compact else (48 if medium else 66))
            button.grid_configure(row=i//columns,column=i%columns,padx=(0,5 if i%columns<columns-1 else 0),pady=(0,4 if columns==2 else 0))
        w['toolbar'].grid_configure(pady=(2,5 if compact else 10))
        check_columns=2 if center_width<700 else 4
        for col in range(4):w['checkrow'].columnconfigure(col,weight=1 if col<check_columns else 0,minsize=0)
        for i,check in enumerate(self.checks):
            check.configure(width=int(center_width/check_columns)-6)
            check.grid_configure(row=i//check_columns,column=i%check_columns,padx=(0,2))
        a.root_text.grid_configure(row=(len(self.checks)-1)//check_columns+1,column=0,columnspan=check_columns)
        a.root_text.configure(wraplength=int(center_width)-10,height=1)
        w['checkrow'].grid_configure(pady=(0,5 if compact else 10))

        for name,button in a.preview_tabs.items():
            button.short_labels=compact or medium
            button.configure(width=max(64,int((center_width-24)/4)-4),height=26 if compact else (30 if medium else 34))
        w['filters'].pack_configure(pady=(0,3 if compact else 7))
        w['views'].pack_configure(pady=(0,2 if compact else 5))
        a.preview_summary.configure(text=a.preview_summary.cget('text'),wraplength=max(100,center_width-210),height=1)
        for check in w['views'].winfo_children():
            if isinstance(check,Check):check.configure(width=58 if check.value=='All' else 102,height=20 if compact else 25)

        for check in w['opts'].winfo_children():
            if isinstance(check,Check):check.configure(width=rail_width-12)
        w['opts'].grid_configure(pady=(2 if compact else 8,5 if compact else 9))
        a.current_label.configure(wraplength=rail_width-22,height=2 if compact else 1)
        a.current_label.pack_configure(pady=(1,1) if compact else (4,4))
        self.detail_title.pack_configure(pady=(0,3 if compact else 10))
        a.artist_entry.grid_configure(pady=(0,1) if compact else (1,6))
        a.album_entry.grid_configure(pady=(0,1) if compact else (1,5))
        a.old_album_label.grid_configure(pady=(0,1) if compact else (0,4))
        w['yearrow'].pack_configure(pady=(1,0) if compact else (4,0))
        w['details'].configure(height=254 if compact else (304 if medium else 322))
        w['details'].grid_configure(pady=(0,5 if compact else 9))
        a.cover_size=68 if compact else (108 if medium else 142)
        a.cover_box.configure(width=a.cover_size,height=86 if compact else (116 if medium else 146))
        a.cover_box.grid_configure(padx=(0,5 if compact else 10))
        for button in w['actions'].winfo_children():
            button.configure(width=max(60,(rail_width-20)//3-4),height=38 if compact else (48 if medium else 58))
        a.update_cover()
        for table in (a.albums_tree,a.preview_tree,a.results_tree):
            table.font=(a.ui_font,max(8,round(a.font_size*scale)))
            table.rowheight=(56 if compact else 66) if table.mode=='results' else (28 if compact else 32)
            if table.mode!='results':table.head.configure(height=25 if compact else 30)
            table.schedule()
        for button in w['controls'].winfo_children():
            button.configure(height=40 if compact else (44 if medium else 50))
        w['footer_spacer'].configure(width=sidebar_width+12)
        a.status_label.configure(height=1 if a._active_page in ('tracks','lookup') else (2 if compact else 1))
        a.preview_errors.configure(height=1)
        if a.is_lite and hasattr(a,'_lite_apply'):a._lite_apply()
