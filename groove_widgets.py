"""Small Tk canvas widgets for Groove Goblin's reference design.

No framework change: all widgets stay in Tk and all callbacks run on the UI thread.
"""
from collections import OrderedDict
import math
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw, ImageTk

BG = '#090f13'
PANEL = '#0c141a'
LINE = '#2c3b46'
FG = '#edf2f8'
MUTED = '#a8b5c6'
GREEN = '#72f98b'
PURPLE = '#ab16ec'


def rounded(canvas, x1, y1, x2, y2, radius=5, **kw):
    r = min(radius, (x2-x1)/2, (y2-y1)/2)
    return canvas.create_polygon(x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,
                                 x2,y2,x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,
                                 x1,y1+r,x1,y1, smooth=True, **kw)


def icon(c, name, x, y, size=24, color=MUTED):
    """Draw crisp vector icons, independent of emoji/font availability."""
    def line(points, width=2):
        c.create_line(*[v for point in points for v in point], fill=color, width=width, capstyle='round', joinstyle='round')
    s = size/24
    def p(a,b): return x+a*s,y+b*s
    if name in ('folder', 'files'):
        if name == 'folder':
            pts=[p(2,6),p(9,6),p(11,9),p(22,9),p(22,21),p(2,21),p(2,6)]
            line(pts,2*s)
            line([p(2,11),p(22,11)],2*s)
        else:
            line([p(5,2),p(15,2),p(21,8),p(21,22),p(5,22),p(5,2)],2*s)
            line([p(15,2),p(15,8),p(21,8)],2*s)
            for a in (12,16): line([p(9,a),p(17,a)],1.5*s)
    elif name == 'music':
        line([p(9,18),p(9,5),p(21,2),p(21,16)],3*s)
        line([p(9,8),p(21,5)],3*s)
        for a,b in ((5,18),(17,16)):
            c.create_oval(*p(a-3,b-2),*p(a+4,b+3),fill=color,outline=color)
    elif name == 'search':
        c.create_oval(*p(3,2),*p(17,16),outline=color,width=2*s)
        line([p(15,14),p(22,22)],3*s)
    elif name == 'play':
        c.create_polygon(*p(7,3),*p(7,21),*p(21,12),fill=color,outline=color)
    elif name == 'cross':
        line([p(4,4),p(20,20)],3*s);line([p(20,4),p(4,20)],3*s)
    elif name == 'check':
        line([p(3,12),p(9,18),p(21,4)],3*s)
    elif name == 'edit':
        line([p(4,20),p(7,13),p(18,2),p(22,6),p(11,17),p(4,20)],2*s)
        line([p(16,4),p(20,8)],2*s)
    elif name == 'list':
        for a in (5,12,19):
            c.create_oval(*p(2,a-1),*p(4,a+1),fill=color,outline=color)
            line([p(9,a),p(21,a)],2*s)
    elif name in ('disc','info','undo','gear'):
        c.create_oval(*p(3,3),*p(21,21),outline=color,width=2*s)
        if name == 'disc':c.create_oval(*p(9,9),*p(15,15),outline=color,width=2*s)
        elif name == 'info':
            line([p(12,10),p(12,17)],2*s);c.create_oval(*p(11,6),*p(13,8),fill=color,outline=color)
        elif name == 'undo':
            line([p(3,3),p(3,10),p(9,10)],2*s);line([p(12,6),p(12,12),p(8,12)],2*s)
        else:
            c.create_oval(*p(9,9),*p(15,15),outline=color,width=2*s)
            for angle in range(0,360,45):
                a=math.radians(angle);line([(x+12*s+9*s*math.cos(a),y+12*s+9*s*math.sin(a)),(x+12*s+12*s*math.cos(a),y+12*s+12*s*math.sin(a))],3*s)
    elif name == 'save':
        line([p(3,3),p(18,3),p(21,6),p(21,21),p(3,21),p(3,3)],2*s)
        line([p(8,3),p(8,10),p(16,10),p(16,3)],2*s)
        line([p(7,21),p(7,14),p(17,14),p(17,21)],2*s)


class Button(tk.Canvas):
    def __init__(self, parent, text, command=None, *, width=140, height=44,
                 symbol=None, accent=None, subtitle='', primary=False, font=('Segoe UI',10),
                 vertical=False, navigation=False, green_active=False, **kw):
        super().__init__(parent, width=width, height=height, bg=parent.cget('bg'),
                         highlightthickness=0, bd=0, takefocus=True, cursor='hand2', **kw)
        self.text=text;self.command=command;self.symbol=symbol;self.accent=accent
        self.subtitle=subtitle;self.primary=primary;self.font=font
        self.vertical=vertical;self.navigation=navigation;self.green_active=green_active;self.disabled=False;self.active=False
        self.hover=False
        self.bind('<Configure>',lambda e:self.draw())
        self.bind('<Enter>',lambda e:self.set_hover(True))
        self.bind('<Leave>',lambda e:self.set_hover(False))
        self.bind('<FocusIn>',lambda e:self.draw());self.bind('<FocusOut>',lambda e:self.draw())
        self.bind('<Button-1>',lambda e:self.invoke())
        self.bind('<space>',lambda e:self.invoke());self.bind('<Return>',lambda e:self.invoke())
        self.draw()

    def set_hover(self, value):self.hover=value;self.draw()

    def state(self, states=None):
        if states is not None:
            for state in states:
                if state == 'disabled':self.disabled=True
                elif state == '!disabled':self.disabled=False
            self.configure(cursor='arrow' if self.disabled else 'hand2');self.draw()
            if getattr(self,'on_state',None):self.on_state()
        return ('disabled',) if self.disabled else ()

    def configure(self, cnf=None, **kw):
        if 'text' in kw:self.text=kw.pop('text')
        if 'font' in kw:self.font=kw.pop('font')
        out=super().configure(cnf, **kw)
        if hasattr(self,'text'):self.draw()
        return out

    config=configure

    def invoke(self):
        if not self.disabled and self.command:
            self.focus_set();return self.command()

    def draw(self):
        self.delete('all')
        w=max(self.winfo_width(),int(self.cget('width')));h=max(self.winfo_height(),int(self.cget('height')))
        green_selected=self.green_active and self.active
        purple=(self.primary or self.active) and not green_selected
        if green_selected:
            top,bottom=('#76ff97','#37d760')
        elif purple:
            top,bottom=('#9811d7','#550c88') if not self.disabled else ('#482c55','#2a2033')
        else:top,bottom=('#1a252d','#0d141a') if self.hover else ('#131d24','#0a1116')
        if self.navigation and not purple and not self.hover:
            top=bottom=self.cget('bg')
        # Supersampled rounded gradient background.
        image=Image.new('RGB',(w,h),top);d=ImageDraw.Draw(image)
        t=tuple(bytes.fromhex(top[1:]));b=tuple(bytes.fromhex(bottom[1:]))
        for y in range(h):
            v=y/max(1,h-1);d.line((0,y,w,y),fill=tuple(int(t[i]*(1-v)+b[i]*v) for i in range(3)))
        mask=Image.new('L',(w*2,h*2));ImageDraw.Draw(mask).rounded_rectangle((1,1,w*2-2,h*2-2),radius=10,fill=255)
        image=image.convert('RGBA');image.putalpha(mask.resize((w,h),Image.Resampling.LANCZOS))
        self._background=ImageTk.PhotoImage(image,master=self)
        self.create_image(0,0,anchor='nw',image=self._background)
        outline=GREEN if green_selected else ('#b229ef' if purple else LINE)
        if self.focus_get() is self:outline=GREEN
        if not self.navigation or purple or self.hover:
            rounded(self,1,1,w-1,h-1,5,fill='',outline=outline,width=1)
        fg='#7d8998' if self.disabled else (BG if green_selected else FG)
        col=self.accent or ('#ffffff' if purple else '#b3bfd7')
        if self.disabled:col='#647181'
        if self.vertical:
            if self.symbol:icon(self,self.symbol,w/2-12,10,24,col)
            self.create_text(w/2,h-13,text=self.text,font=(self.font[0],9),fill=fg)
        else:
            x=50 if self.symbol else 14
            icon_x=14
            if self.primary:
                import tkinter.font as font
                text_width=font.Font(master=self,font=(*self.font,'bold')).measure(self.text)
                group_width=text_width+(36 if self.symbol else 0)
                icon_x=max(8,(w-group_width)/2)
                x=icon_x+(36 if self.symbol else 0)
            if self.symbol:icon(self,self.symbol,icon_x,h/2-13,26 if self.subtitle else 22,col)
            if self.navigation:x=58
            self.create_text(x,h/2-(9 if self.subtitle else 0),anchor='w',text=self.text,font=(*self.font, 'bold') if purple or self.subtitle else self.font,fill=fg)
            if self.subtitle:self.create_text(w/2 if self.primary else x,h/2+13,anchor='center' if self.primary else 'w',text=self.subtitle,font=(self.font[0],8),fill=MUTED,width=w-16 if self.primary else w-x-9)


class Check(tk.Canvas):
    def __init__(self, parent, text, variable, command=None, *, width=210, disabled=False, font=('Segoe UI',9)):
        super().__init__(parent,width=width,height=25,bg=parent.cget('bg'),highlightthickness=0,
                         bd=0,takefocus=not disabled,cursor='arrow' if disabled else 'hand2')
        self.text=text;self.variable=variable;self.command=command;self.disabled=disabled;self.font=font
        self.trace=variable.trace_add('write',lambda *args:self.draw())
        self.bind('<Button-1>',lambda e:self.invoke());self.bind('<space>',lambda e:self.invoke())
        self.bind('<FocusIn>',lambda e:self.draw());self.bind('<FocusOut>',lambda e:self.draw())
        self.bind('<Destroy>',self.cleanup)
        self.draw()
    def cleanup(self,event):
        if event.widget is self:
            try:self.variable.trace_remove('write',self.trace)
            except tk.TclError:pass
    def invoke(self):
        if self.disabled:return
        self.focus_set();self.variable.set(not self.variable.get())
        if self.command:self.command()
    def draw(self):
        self.delete('all');enabled=bool(self.variable.get())
        color=GREEN if enabled else '#132029'
        rounded(self,3,4,20,21,2,fill=color,outline='#788c98' if not enabled else color,width=1)
        if enabled:icon(self,'check',6,7,11,BG)
        self.create_text(31,13,anchor='w',text=self.text,font=self.font,fill='#8291a2' if self.disabled and not enabled else FG)
        if self.focus_get() is self:self.create_rectangle(0,1,max(self.winfo_width(),int(self.cget('width')))-1,24,outline=GREEN)


class Radio(Check):
    def __init__(self, parent, text, variable, value, command=None, **kw):
        self.value=value
        super().__init__(parent,text,variable,command,**kw)
    def invoke(self):
        self.focus_set();self.variable.set(self.value)
        if self.command:self.command()
    def draw(self):
        self.delete('all');selected=self.variable.get()==self.value
        self.create_oval(4,5,20,21,fill=GREEN if selected else BG,outline=GREEN if selected else '#647887')
        if selected:self.create_oval(9,10,15,16,fill=BG,outline=BG)
        self.create_text(28,13,anchor='w',text=self.text,font=self.font,fill=FG)


class Panel(tk.Canvas):
    def __init__(self,parent,*,padding=11,**kw):
        super().__init__(parent,bg=parent.cget('bg'),highlightthickness=0,bd=0,**kw)
        self.padding=padding
        self.body=tk.Frame(self,bg=PANEL)
        self.window=self.create_window(padding,padding,anchor='nw',window=self.body)
        self.bind('<Configure>',self.resize)
    def resize(self,event):
        self.delete('border')
        rounded(self,1,1,event.width-1,event.height-1,7,fill=PANEL,outline=LINE,tags='border')
        self.tag_lower('border')
        self.itemconfigure(self.window,width=max(1,event.width-self.padding*2),height=max(1,event.height-self.padding*2))


class Table(tk.Frame):
    """Keyboard-accessible virtual table with cell colors, covers and badges.

    Implements the subset of Treeview used by the existing controller.
    Rows are painted only in the visible viewport, even for large libraries.
    """
    def __init__(self,parent,*,mode='albums',font=('Segoe UI',10),on_toggle=None,on_choose=None):
        super().__init__(parent,bg=PANEL,highlightthickness=1,highlightbackground=LINE)
        self.mode=mode;self.font=font;self.on_toggle=on_toggle;self.on_choose=on_choose
        self.data=OrderedDict();self.selected=None;self.serial=0;self.photos={};self.cover_provider=None
        self.rowheight=32 if mode!='results' else 66
        self.redraw_id=None;self.on_toggle_all=None
        self.head=tk.Canvas(self,height=30,bg='#1a252e',highlightthickness=0)
        if mode!='results':self.head.pack(fill='x')
        self.head.bind('<Button-1>',lambda e:self.on_toggle_all() if e.x<35 and self.on_toggle_all else None)
        self.body=tk.Canvas(self,bg=PANEL,highlightthickness=0,takefocus=True)
        scroll=ttk.Scrollbar(self,orient='vertical',command=self.yview)
        scroll.pack(side='right',fill='y');self.body.pack(fill='both',expand=True)
        self.body.configure(yscrollcommand=lambda lo,hi:(scroll.set(lo,hi),self.schedule()))
        self.body.bind('<Configure>',lambda e:self.schedule())
        self.head.bind('<Configure>',lambda e:self.schedule())
        self.body.bind('<Button-1>',self.click)
        self.body.bind('<Double-1>',lambda e:self.double_click())
        self.body.bind('<MouseWheel>',lambda e:self.yview('scroll',-int(e.delta/120) or (-1 if e.delta>0 else 1),'units'))
        self.body.bind('<Button-4>',lambda e:self.yview('scroll',-1,'units'))
        self.body.bind('<Button-5>',lambda e:self.yview('scroll',1,'units'))
        self.body.bind('<Up>',lambda e:self.move(-1));self.body.bind('<Down>',lambda e:self.move(1))
        self.body.bind('<space>',lambda e:self.toggle_current());self.body.bind('<Return>',lambda e:self.double_click())
        self.double_command=None
        self.bind('<Destroy>',self.cleanup)
    def cleanup(self,event):
        if event.widget is self and self.redraw_id:
            self.after_cancel(self.redraw_id);self.redraw_id=None
    def bind(self,sequence=None,func=None,add=None):
        if sequence=='<Double-1>':self.double_command=func;return None
        return super().bind(sequence,func,add)
    def double_click(self):
        if self.double_command:self.double_command(None)
        elif self.mode=='results' and self.on_choose:self.on_choose()
    def get_children(self,item=''):return tuple(self.data)
    def insert(self,parent,index,iid=None,values=(),tags=(),**kw):
        if iid is None:self.serial+=1;iid='row'+str(self.serial)
        self.data[str(iid)]={'values':tuple(values),'tags':tuple(tags),**kw};self.schedule();return str(iid)
    def delete(self,*ids):
        for key in ids:self.data.pop(str(key),None)
        if self.selected not in self.data:self.selected=None
        self.schedule()
    def item(self,key,option=None,**kw):
        if kw:self.data[str(key)].update(kw);self.schedule()
        row=self.data[str(key)]
        return row.get(option) if option else row
    def selection(self):return (self.selected,) if self.selected in self.data else ()
    def selection_set(self,key):
        if isinstance(key,(list,tuple)):key=key[0] if key else None
        key=str(key) if key is not None else None
        changed=key!=self.selected
        self.selected=key if key in self.data else None
        self.schedule()
        if changed:self.event_generate('<<TreeviewSelect>>',when='tail')
    def tag_configure(self,*args,**kw):pass
    def yview(self,*args):
        self.body.yview(*args);self.schedule()
    def move(self,delta):
        keys=list(self.data)
        if not keys:return
        current=keys.index(self.selected) if self.selected in keys else -1
        index=max(0,min(len(keys)-1,current+delta));self.selection_set(keys[index])
        y=index*self.rowheight;top=self.body.canvasy(0);height=self.body.winfo_height()
        if y<top:self.body.yview_moveto(y/max(1,len(keys)*self.rowheight))
        elif y+self.rowheight>top+height:self.body.yview_moveto((y+self.rowheight-height)/max(1,len(keys)*self.rowheight))
    def toggle_current(self):
        if self.selected and self.on_toggle:self.on_toggle(self.selected)
    def click(self,event):
        self.body.focus_set();index=int(self.body.canvasy(event.y)//self.rowheight)
        keys=list(self.data)
        if 0<=index<len(keys):
            self.selection_set(keys[index])
            if self.mode=='results' and event.x>self.body.winfo_width()-88:
                if self.on_choose:self.on_choose()
            elif event.x<35 and self.on_toggle:self.on_toggle(keys[index])
    def schedule(self):
        if not self.redraw_id:self.redraw_id=self.after_idle(self.draw)
    def text(self,c,x,y,value,width,color=FG,anchor='w',bold=False):
        # Clip long metadata without allowing text to bleed into other columns.
        import tkinter.font as f
        value=str(value);face=(*self.font,'bold') if bold else self.font
        measure=f.Font(master=self,font=face).measure
        if measure(value)>max(0,width-8):
            while value and measure(value+'...')>max(0,width-8):value=value[:-1]
            value+='...' if value else ''
        c.create_text(x,y,text=value,anchor=anchor,fill=color,font=face)
    def checkbox(self,c,x,y,checked=True):
        rounded(c,x,y-8,x+16,y+8,2,fill=GREEN if checked else BG,outline=GREEN if checked else '#697d8d')
        if checked:icon(c,'check',x+3,y-5,11,BG)
    def badge(self,c,x,y,label,ready=True,width=63):
        rounded(c,x,y-10,x+width,y+10,4,fill='#123a1c' if ready else '#3d3108',outline='#27bd49' if ready else '#ad840d')
        c.create_text(x+width/2,y,text=label,fill=GREEN if ready else '#ffcf32',font=(self.font[0],9))
    def draw(self):
        self.redraw_id=None
        if not self.winfo_exists():return
        c=self.body;c.delete('all');self.head.delete('all');w=max(1,c.winfo_width())
        count=len(self.data);region=(0,0,w,max(c.winfo_height(),count*self.rowheight))
        if getattr(self,'_region',None)!=region:
            self._region=region;c.configure(scrollregion=region)
        if self.mode=='albums':
            widths=[34,44,.17,.23,.27,60,55,92]
            fixed=sum(v for v in widths if v>=1);remaining=max(200,w-fixed)
            widths=[v if v>=1 else v*remaining/.67 for v in widths]
            labels=['','', 'Artist','Current Album Tag','Suggested Album','Year','Tracks','Status']
        elif self.mode=='preview':
            widths=[34,.39,.45,52,100];remaining=max(200,w-186)
            widths=[v if v>=1 else v*remaining/.84 for v in widths]
            labels=['','Current Folder / File','New Folder / Tags','Files','Status']
        else:widths=[];labels=[]
        x=0
        for i,(width,label) in enumerate(zip(widths,labels)):
            self.text(self.head,x+9,15,label,width,color='#c5d2e4')
            self.head.create_line(x+width,0,x+width,30,fill='#2b3641');x+=width
        if self.mode!='results':
            checked=bool(self.data) and all(row['values'][0]=='✓' if self.mode=='albums' else row.get('enabled',True) for row in self.data.values())
            self.checkbox(self.head,8,15,checked)
        keys=list(self.data)
        first=max(0,int(c.canvasy(0)//self.rowheight));last=min(count,first+int(c.winfo_height()/self.rowheight)+2)
        for index in range(first,last):
            key=keys[index];row=self.data[key];values=row['values'];y=index*self.rowheight;mid=y+self.rowheight/2
            c.create_rectangle(0,y,w,y+self.rowheight,fill='#17242e' if key==self.selected else ('#101a21' if index%2==0 else '#0b141a'),outline='')
            c.create_line(0,y+self.rowheight,w,y+self.rowheight,fill='#24313c')
            if self.mode=='albums':
                use,artist,old,new,year,tracks,status,confidence=values
                self.checkbox(c,8,mid,use=='✓')
                if self.cover_provider:
                    photo=self.cover_provider(key,28)
                    if photo:c.create_image(40,mid,anchor='w',image=photo)
                    else:icon(c,'disc',43,mid-11,22,'#7c93a3')
                x=78
                ready=status=='READY';color=MUTED if 'disabled' in row['tags'] else FG
                for i,value in enumerate((artist,old,new,year,tracks)):
                    width=widths[i+2];self.text(c,x+9,mid,value,width,color=GREEN if i==2 and color!=MUTED else color,bold=i==2);x+=width
                self.badge(c,x+12,mid,'Match' if ready else 'Verify',ready)
            elif self.mode=='preview':
                action,old,new,detail=values
                self.checkbox(c,8,mid,row.get('enabled',True))
                x=widths[0]
                icon(c,'folder' if action=='FOLDER' else 'music',x+5,mid-10,20,'#ffca40')
                self.text(c,x+35,mid,PathName(old),widths[1]-30)
                x+=widths[1];self.text(c,x+9,mid,PathName(new) if action=='FOLDER' else new,widths[2],GREEN if action!='SKIP' else '#ffce53', bold=True)
                x+=widths[2];self.text(c,x+9,mid,row.get('files','—'),widths[3]);x+=widths[3]
                self.badge(c,x+7,mid,('Skipped' if not row.get('enabled',True) else 'Review') if action=='SKIP' else ('Will Rename' if action in ('FOLDER','FILENAME') else 'Will Tag'),action!='SKIP',width=83)
            else:
                album,artist,year,kind,score=values
                photo=self.cover_provider(key,48) if self.cover_provider else None
                if photo:c.create_image(7,mid,anchor='w',image=photo)
                else:icon(c,'disc',10,mid-19,38,'#91a4b6')
                self.text(c,58,y+17,album,max(50,w-150),GREEN if key==self.selected else FG,bold=True)
                self.text(c,58,y+35,artist,max(50,w-150),MUTED)
                self.text(c,58,y+52,f'{year or "Year unknown"} · {kind or "Release group"}',max(50,w-150),MUTED)
                bx=max(0,w-81);selected=key==self.selected
                rounded(c,bx,mid-15,bx+70,mid+15,4,fill='#123a1c' if selected else '#172128',outline='#26bd48' if selected else '#485966')
                c.create_text(bx+35,mid,text='Select',fill=GREEN if selected else FG,font=(self.font[0],9))
        if not count:
            self.text(c,12,24,'Add folders or files to begin.' if self.mode=='albums' else ('No changes to preview.' if self.mode=='preview' else 'Search online to see album matches.'),w-24,MUTED)


def PathName(value):
    from pathlib import PureWindowsPath
    return PureWindowsPath(str(value)).name
