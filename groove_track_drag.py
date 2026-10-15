"""Track selection gestures and UI-thread reconciliation of Windows file drags."""
import os
from pathlib import Path
import threading
from groove_manual import read_track


class TrackFileDrag:
    def __init__(self,editor):
        self.editor=editor;self.app=editor.app;self.tree=editor.tree
        self.enabled=os.name=='nt';self.active=False;self.press_info=None
        self.cancel=threading.Event();self.gui_thread=threading.get_native_id()
        self.api_factory=self.native_api
        self.tree.bind('<ButtonPress-1>',self.press,add='+')
        self.tree.bind('<B1-Motion>',self.motion,add='+')
        self.tree.bind('<ButtonRelease-1>',self.release,add='+')

    def native_api(self):
        from groove_windows_drag import WindowsFileDrag
        return WindowsFileDrag(self.gui_thread)

    def press(self,event):
        self.press_info=None
        if not self.enabled or self.active:return
        row=self.tree.identify_row(event.y)
        if not row or self.tree.identify_region(event.x,event.y) not in ('cell','tree'):return
        selected=row in self.tree.selection()
        self.press_info={'row':row,'x':event.x_root,'y':event.y_root,'state':event.state,
                         'defer':selected,'unsaved':any(v.get() for v in self.editor.enabled.values())}
        if selected:
            # Defer selection changes until mouse-up. Otherwise pressing a
            # selected row collapses a multi-track selection before dragging.
            self.tree.focus_set();return 'break'

    def release(self,event):
        info=self.press_info;self.press_info=None
        if self.active:return 'break'
        if not info or not info['defer']:return
        row=info['row']
        if info['state']&1:
            rows=list(self.tree.get_children());anchor=self.tree.focus()
            if anchor in rows:
                first,last=sorted((rows.index(anchor),rows.index(row)))
                self.tree.selection_set(rows[first:last+1])
            else:self.tree.selection_set(row);self.tree.focus(row)
        elif info['state']&4:self.tree.selection_remove(row)
        else:self.tree.selection_set(row);self.tree.focus(row)
        return 'break'

    def motion(self,event):
        if self.active:return 'break'
        info=self.press_info
        if not info:return
        if max(abs(event.x_root-info['x']),abs(event.y_root-info['y']))<6:return 'break'
        self.press_info=None
        self.begin(unsaved=info['unsaved'])
        return 'break'

    def begin(self,*,unsaved=False):
        e=self.editor;a=self.app
        if not self.enabled or self.active or a.worker_busy or getattr(getattr(a,'_mode_switch',None),'active',False):return False
        paths=[path for path in self.tree.get_children() if path in self.tree.selection()]
        if not paths:return False
        if unsaved or e.inline or any(v.get() for v in e.enabled.values()) or any(path in e.pending for path in paths):
            a.status.set('Save or discard edits for the selected tracks before dragging files.');return False
        unavailable=[path for path in paths if not Path(path).is_file()]
        if unavailable:
            a.status.set('A selected file is no longer available. Reload the tracks before dragging.');return False
        self.active=True;self.cancel.clear()
        e.player.stop()
        e.selection_changed()
        a.status.set(f'Dragging {len(paths)} track(s) to Windows. Ctrl copies; Shift moves; Esc cancels.')
        def work():
            result={'canceled':False,'effect':0,'locations':{},'error':''};records={};mappings={};missing=[]
            try:result=self.api_factory().drag(paths,self.cancel)
            except Exception as error:result['error']=str(error)
            a.queue.put(('status','Updating Track Editor after the Windows file drag…'))
            for old in paths:
                new=result['locations'].get(old)
                if new and os.path.normcase(new)!=os.path.normcase(old):
                    try:
                        record=read_track(new);mappings[old]=record['path'];records[record['path']]=record
                    except Exception as error:
                        missing.append(old);result['error']+='\nCould not reload moved track: '+str(error)
                elif not Path(old).is_file():missing.append(old)
            a.queue.put(('manual_drag_finished',result,mappings,records,missing))
        a.run_background(work)
        a.btn_cancel.state(['disabled'])
        return True

    def finish(self,result,mappings,records,missing):
        self.active=False;e=self.editor;a=self.app
        selected=list(self.tree.selection());affected=set(mappings)|set(missing)
        for old in affected:
            e.records.pop(old,None);e.pending.pop(old,None)
        e.records.update(records);e.cover_cache.clear()
        e.player.playlist=[];e.player.index=-1
        if affected:
            # An organizer plan containing moved files is stale. Keep plans for
            # unrelated albums, and leave the music/undo journals untouched.
            a.matched=[album for album in a.matched if not any(track.path in affected for track in album.tracks)]
            a.album_map={album.uid:album for album in a.matched}
            if a.selected_id not in a.album_map:a.selected_id=None
            a.roots=[mappings.get(path,path) for path in a.roots if path not in missing]
            a.update_roots();a.populate_albums();a.refresh_preview();a.lookup_page.refresh_albums()
        e.refresh()
        self.tree.selection_set([mappings.get(path,path) for path in selected if mappings.get(path,path) in e.records])
        if affected:
            text=f'Updated {len(mappings)} moved track(s). '
            if missing:text+=f'{len(missing)} removed from the list; add the destination folder to reload them. '
            text+='Use Explorer for file-move undo.'
        elif result['canceled']:text='Windows file drag canceled; track list retained.'
        else:text='Windows file drag finished; original tracks remain in the list.'
        if result.get('error'):
            a.log('FILE DRAG: '+result['error']);text+=' '+result['error'].strip().splitlines()[0]
        a.status.set(text)

    def close(self):self.cancel.set()
