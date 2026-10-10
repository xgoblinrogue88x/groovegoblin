"""Music file inspection, preview, safe-ish batch apply and undo for Groove Goblin.
No file is modified by scanning or by online lookup.
"""
from __future__ import annotations
import json, os, re, shutil, time, uuid, unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
from typing import Optional

from mutagen.flac import FLAC
from mutagen.id3 import ID3, ID3NoHeaderError, TALB, TDRC, TYER
from mutagen.mp3 import MP3
from legacy_collections import match as legacy_match

EXTENSIONS={'.flac','.mp3'}
ILLEGAL=r'<>:"/\\|?*'
GENERIC={'', 'unknown', 'unknown album', 'the collection', 'collection', 'the collection ii', 'collection ii', 'greatest hits', 'disc 1', 'disc 2', 'disc 3', 'album', 'various', 'untitled'}

def norm(v):
    s=unicodedata.normalize('NFKD',str(v or '').casefold())
    return ''.join(c for c in s if c.isascii() and c.isalnum())

def safe_name(name):
    s=''.join(' - ' if c in '\\/' else ('_' if c in '<>:"|?*' or ord(c)<32 else c) for c in str(name))
    s=re.sub(r'\s+',' ',s).strip(' .')
    if s.upper().split('.')[0] in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}: s='_'+s
    return s[:180].rstrip(' .') or '_'

def year4(raw):
    m=re.match(r'^(18|19|20|21)\d{2}',str(raw or '').strip()); return m.group(0) if m else ''

def int_prefix(raw):
    m=re.match(r'\s*(\d+)',str(raw or '')); return int(m.group(1)) if m else None

def tag_first(tags,key):
    v=tags.get(key,[]) if tags else []
    return str(v[0]) if v else ''

def file_signature(p):
    s=Path(p).stat();return [s.st_size,s.st_mtime_ns]

@dataclass
class Track:
    path: str
    fmt: str
    artist: str
    albumartist: str
    album: str
    title: str
    year: str
    number: Optional[int]
    disc: Optional[int]
    signature: list

@dataclass
class Album:
    uid: str
    folder: str
    tracks: list[Track]
    artist: str
    old_album: str
    album: str=''
    year: str=''
    match_source: str='Unmatched'
    confidence: float=0.0
    approved: bool=False
    enabled: bool=True
    note: str=''
    mbid: str=''
    lookup_results: list=field(default_factory=list)

    @property
    def file_count(self): return len(self.tracks)
    @property
    def status(self):
        if not self.album or not year4(self.year) or not self.artist: return 'NEEDS REVIEW'
        if self.approved: return 'READY'
        return 'REVIEW MATCH'


def inspect_track(path):
    p=Path(path)
    if p.suffix.lower()=='.flac':
        tag=FLAC(str(p))
        d={str(k).lower():list(v) for k,v in (tag.tags or {}).items()}
        get=lambda key: tag_first(d,key)
        title=get('title');artist=get('artist');albumartist=get('albumartist');album=get('album')
        year=get('date') or get('year');number=int_prefix(get('tracknumber'));disc=int_prefix(get('discnumber'))
    elif p.suffix.lower()=='.mp3':
        # MP3(...) checks basic audio validity rather than treating unrelated files as MP3s.
        m=MP3(str(p))
        id3=m.tags
        def get(id):
            frames=id3.getall(id) if id3 else []
            return str(frames[0].text[0]) if frames and frames[0].text else ''
        title=get('TIT2');artist=get('TPE1');albumartist=get('TPE2');album=get('TALB')
        year=get('TDRC') or get('TYER');number=int_prefix(get('TRCK'));disc=int_prefix(get('TPOS'))
    else: raise ValueError('Unsupported format')
    if not title:
        title=re.sub(r'^\s*(?:\d+[-_. ])?\d+\s*[-_. ]+','',p.stem).replace('_',' ').strip()
    return Track(str(p),p.suffix.lower(),artist,albumartist,album,title,year,number,disc,file_signature(p))

def majority(values):
    data=[v.strip() for v in values if v and v.strip()]
    return Counter(data).most_common(1)[0][0] if data else ''

def infer_artist(folder,tracks):
    artist=majority(t.albumartist for t in tracks) or majority(t.artist for t in tracks)
    if artist and norm(artist) not in ('variousartists','unknownartist'):return artist
    match=re.match(r'^(.+?)\s+-\s+.+?\s*\(\d{4}\)\s*$',Path(folder).name)
    if match:return match.group(1)
    return artist or ''

def infer_album(folder,tracks):
    album=majority(t.album for t in tracks)
    if norm(album) in {norm(g) for g in GENERIC}:
        name=Path(folder).name
        m=re.match(r'^.+?\s+-\s+(.+?)\s*\(\d{4}\)$',name)
        if m:return album,m.group(1)
        if not re.search(r'^\s*(?:disc|disk|cd)\s*\d+\s*$',name,re.I) and 'collection' not in name.casefold():
            return album,name
        return album,''
    return album,album

def scan_folders(roots,callback=None,cancel=None):
    seen=set(); paths=[];errors=[]
    for root in roots:
        root=Path(root)
        if not root.is_dir():errors.append(f'Not a directory: {root}');continue
        for parent,dirs,files in os.walk(root):
            dirs[:]=[d for d in dirs if not d.startswith('.') and d.lower() not in {'$recycle.bin','system volume information'}]
            for f in files:
                p=Path(parent)/f
                if p.suffix.lower() in EXTENSIONS:
                    k=str(p.resolve()).casefold()
                    if k not in seen:seen.add(k);paths.append(p)
    byfolder=defaultdict(list)
    for i,p in enumerate(sorted(paths,key=lambda p:str(p).casefold())):
        if cancel and cancel.is_set():break
        try: t=inspect_track(p);byfolder[str(p.parent.resolve())].append(t)
        except Exception as ex:errors.append(f'{p}: {ex}')
        if callback and (i%15==0 or i+1==len(paths)):callback(f'Reading audio tags: {i+1}/{len(paths)}')
    albums=[]
    for folder,tracks in sorted(byfolder.items()):
        artist=infer_artist(folder,tracks)
        old,guess=infer_album(folder,tracks)
        year=majority(year4(t.year) for t in tracks)
        # If the release year in tags is from a remaster, online lookup should replace it.
        item=Album(uuid.uuid4().hex[:12],folder,tracks,artist,old,guess,year)
        if not artist:item.note='Artist could not be identified; enter it manually.'
        tracktitles=[t.title for t in sorted(tracks,key=lambda t:(t.number or 999,t.path))]
        hint=' '.join(str(Path(folder).resolve()).split(os.sep)[-3:])
        legacy=legacy_match(hint,artist,old,tracktitles,[t.disc for t in tracks])
        if legacy:
            item.album=legacy['album'];item.year=legacy['year'];item.approved=True
            item.match_source=legacy['source'];item.confidence=legacy['confidence']
        elif guess:
            item.match_source='Existing tags / folder; unverified';item.confidence=0.35
        albums.append(item)
    return albums,errors

def album_destination(album):
    return str(Path(album.folder).with_name(safe_name(f'{album.artist} - {album.album} ({year4(album.year)})')))

def filename_destination(track):
    prefix=f'{track.number:02d} - ' if track.number is not None else ''
    return safe_name(prefix+track.title)+track.fmt

def plan_actions(albums,options):
    opts={'tags':True,'folders':True,'filenames':False,**options}
    actions=[];problems=[];dest_map={}
    enabled=[a for a in albums if a.enabled]
    group_folders=Counter(a.folder.casefold() for a in enabled)
    nested={a.folder for a in enabled if any(a.folder!=b.folder and str(Path(b.folder)).casefold().startswith(str(Path(a.folder)).casefold()+os.sep) for b in albums)}
    for a in enabled:
        if a.status!='READY':problems.append(f'{a.folder}: requires confirmation of its album, artist and year');continue
        if group_folders[a.folder.casefold()]>1:problems.append(f'{a.folder}: multiple album groups share a folder');continue
        if a.folder in nested:problems.append(f'{a.folder}: contains other album folders; move or select only leaf folders');continue
        target_folder=album_destination(a) if opts['folders'] else a.folder
        if opts['folders'] and Path(target_folder).exists() and Path(target_folder).resolve()!=Path(a.folder).resolve():
            problems.append(f'{a.folder}: destination folder already exists: {target_folder}');continue
        if target_folder.casefold() in dest_map and dest_map[target_folder.casefold()]!=a.folder:
            problems.append(f'Duplicate folder destination: {target_folder}');continue
        dest_map[target_folder.casefold()]=a.folder
        tracks=[];names=set();bad=False
        for t in a.tracks:
            old_name=Path(t.path).name
            new_name=filename_destination(t) if opts['filenames'] else old_name
            if new_name.casefold() in names:
                problems.append(f'{a.folder}: duplicate output filename: {new_name}');bad=True;break
            names.add(new_name.casefold())
            newpath=Path(a.folder)/new_name
            if opts['filenames'] and newpath.exists() and newpath.resolve()!=Path(t.path).resolve():
                # A destination may be another track's original filename; simultaneous rename is unsafe.
                problems.append(f'{a.folder}: output filename already exists: {newpath}');bad=True;break
            needs_tags=opts['tags'] and (norm(t.album)!=norm(a.album) or year4(t.year)!=year4(a.year) or t.album!=a.album)
            tracks.append({'old_path':t.path,'old_name':old_name,'new_name':new_name,'signature':t.signature,
                           'title':t.title,'needs_tags':needs_tags,'old_album':t.album,'old_year':t.year})
        if bad:continue
        changed=(target_folder!=a.folder or any(t['needs_tags'] or t['old_name']!=t['new_name'] for t in tracks))
        actions.append({'album_uid':a.uid,'folder':a.folder,'dest_folder':target_folder,'artist':a.artist,
                        'album':a.album,'year':year4(a.year),'source':a.match_source,'tracks':tracks,'changed':changed})
    return actions,problems

# Targeted fields only. Other artist, title, track, pictures, comments, ReplayGain etc. are preserved.
def tag_snapshot(path):
    p=Path(path)
    if p.suffix.lower()=='.flac':
        a=FLAC(str(p)); d={str(k).lower():list(v) for k,v in (a.tags or {}).items()}
        return {'format':'flac','fields':{key:d.get(key) for key in ('album','date','year')}}
    try: id3=ID3(str(p))
    except ID3NoHeaderError: id3=ID3()
    fields={}
    for key in ('TALB','TDRC','TYER'):
        frames=id3.getall(key)
        fields[key]=[list(map(str,f.text)) for f in frames]
    return {'format':'mp3','fields':fields,'id3_existed':bool(id3.keys()),'v2_major':id3.version[1] if id3.version[1] in (3,4) else 4}

def set_tags(path,album,year):
    p=Path(path)
    if p.suffix.lower()=='.flac':
        a=FLAC(str(p)); a['album']=[album];a['date']=[year]
        if 'year' in a:a['year']=[year]
        a.save()
    else:
        try:id3=ID3(str(p))
        except ID3NoHeaderError:id3=ID3()
        major=id3.version[1] if id3.version[1] in (3,4) else 4
        id3.delall('TALB');id3.add(TALB(encoding=3,text=[album]))
        id3.delall('TDRC');id3.add(TDRC(encoding=3,text=[year]))
        if id3.getall('TYER'):id3.delall('TYER');id3.add(TYER(encoding=3,text=[year]))
        id3.save(str(p),v2_version=major)

def restore_tags(path,snapshot):
    p=Path(path)
    d=snapshot['fields']
    if snapshot['format']=='flac':
        a=FLAC(str(p))
        for k,v in d.items():
            if v is None:a.pop(k,None)
            else:a[k]=v
        a.save()
    else:
        try:id3=ID3(str(p))
        except ID3NoHeaderError:id3=ID3()
        cls={'TALB':TALB,'TDRC':TDRC,'TYER':TYER}
        for key,v in d.items():
            id3.delall(key)
            for t in v:id3.add(cls[key](encoding=3,text=t))
        if not snapshot.get('id3_existed') and not id3.keys():
            try: ID3.delete(str(p))
            except Exception:pass
        else:id3.save(str(p),v2_version=snapshot.get('v2_major',4))

def atomic_json(path,data):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_suffix('.tmp');temp.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8');os.replace(temp,p)

def backup_dir(app_base):
    p=Path(app_base)/'Logs';p.mkdir(parents=True,exist_ok=True);return p

def preflight(actions):
    problems=[]
    for a in actions:
        src=Path(a['folder']);dest=Path(a['dest_folder'])
        if not src.is_dir():problems.append('Source folder no longer exists: '+str(src))
        if dest!=src and dest.exists():problems.append('Destination folder now exists: '+str(dest))
        for t in a['tracks']:
            p=Path(t['old_path'])
            if not p.is_file():problems.append('File missing: '+str(p))
            elif file_signature(p)!=t['signature']:problems.append('File changed since scan: '+str(p))
    return problems

def apply_actions(actions,app_base,options,callback=None):
    actions=[a for a in actions if a['changed']]
    if not actions:return None
    problems=preflight(actions)
    if problems:raise ValueError('Re-scan before applying:\n'+'\n'.join(problems[:12]))
    ts=datetime.now().strftime('%Y%m%d_%H%M%S')
    journal_path=backup_dir(app_base)/(f'Groove_Goblin_Undo_{ts}_{uuid.uuid4().hex[:5]}.json')
    journal={'format_version':1,'created':datetime.now().isoformat(timespec='seconds'),'state':'applying',
             'options':options,'albums':[],'undone':False}
    # Write ahead BEFORE the first mutation; append each operation with its original tag values.
    atomic_json(journal_path,journal)
    try:
        for n,a in enumerate(actions,1):
            if callback:callback(f'Applying {n}/{len(actions)}: {a["artist"]} - {a["album"]}')
            entry={'folder_before':a['folder'],'folder_after':a['dest_folder'],'folder_renamed':False,
                   'tracks':[],'status':'working'}
            journal['albums'].append(entry);atomic_json(journal_path,journal)
            for t in a['tracks']:
                need_tags=t['needs_tags'];rename_file=t['new_name']!=t['old_name']
                if not need_tags and not rename_file:continue
                src=Path(t['old_path']);dst=src.with_name(t['new_name'])
                snapshot=tag_snapshot(src) if need_tags else None
                rec={'old_name':src.name,'new_name':dst.name,'snapshot':snapshot,'tags_changed':False,'file_renamed':False}
                entry['tracks'].append(rec);atomic_json(journal_path,journal)
                if need_tags:
                    rec['tags_changed']=True;atomic_json(journal_path,journal)
                    set_tags(src,a['album'],a['year'])
                if rename_file:
                    rec['file_renamed']=True;atomic_json(journal_path,journal)
                    src.rename(dst)
            if a['folder']!=a['dest_folder']:
                entry['folder_renamed']=True;atomic_json(journal_path,journal)
                Path(a['folder']).rename(a['dest_folder'])
            entry['status']='complete';atomic_json(journal_path,journal)
        journal['state']='complete';atomic_json(journal_path,journal)
        atomic_json(backup_dir(app_base)/'last_apply.json',{'journal':str(journal_path)})
    except Exception as ex:
        journal['state']='PARTIAL_ERROR: '+str(ex);atomic_json(journal_path,journal)
        raise RuntimeError(f'Apply stopped; some changes may have completed. Use Undo. Journal: {journal_path}\n{ex}') from ex
    return str(journal_path)

def newest_journal(app_base):
    lst=sorted(backup_dir(app_base).glob('Groove_Goblin_Undo_*.json'),reverse=True)
    for p in lst:
        try:
            if not json.loads(p.read_text(encoding='utf-8')).get('undone'):return p
        except Exception:continue
    return None

def undo_journal(path,callback=None):
    jpath=Path(path)
    if not jpath.is_file():raise ValueError('No saved undo journal was found.')
    data=json.loads(jpath.read_text(encoding='utf-8'))
    if data.get('undone'):raise ValueError('This operation has already been undone.')
    errors=[]
    for entry in reversed(data.get('albums',[])):
        before=Path(entry['folder_before']);after=Path(entry['folder_after'])
        current=after if entry.get('folder_renamed') else before
        if entry.get('folder_renamed'):
            if not after.exists() and before.exists():
                # Rename was journaled but not performed before an interruption.
                current=before;entry['folder_renamed']=False;atomic_json(jpath,data)
            elif before.exists():errors.append(f'Original folder already exists, cannot undo: {before}');continue
            elif not after.exists():errors.append(f'Folder missing, cannot undo: {after}');continue
            else:
                try:after.rename(before);current=before;entry['folder_renamed']=False;atomic_json(jpath,data)
                except Exception as ex:errors.append(f'Folder restore failed: {after}: {ex}');continue
        for rec in reversed(entry.get('tracks',[])):
            current_file=current/(rec['new_name'] if rec.get('file_renamed') else rec['old_name'])
            old_file=current/rec['old_name']
            if rec.get('file_renamed') and not current_file.is_file() and old_file.is_file():
                # Same principle: journal commit preceded the attempted file rename.
                current_file=old_file;rec['file_renamed']=False;atomic_json(jpath,data)
            if not current_file.is_file():errors.append('Cannot locate '+str(current_file));continue
            try:
                if rec.get('file_renamed'):
                    if old_file.exists():raise ValueError('original filename already exists')
                    current_file.rename(old_file);current_file=old_file;rec['file_renamed']=False;atomic_json(jpath,data)
                if rec.get('tags_changed') and rec.get('snapshot'):
                    restore_tags(current_file,rec['snapshot']);rec['tags_changed']=False;atomic_json(jpath,data)
            except Exception as ex: errors.append(str(current_file)+': '+str(ex))
        if callback:callback(f'Restored: {before.name}')
    data['undone']=not errors;data['state']='undone' if not errors else 'undo_incomplete';atomic_json(jpath,data)
    return errors

def export_preview(actions,problems,destination):
    rows=['Groove Goblin - Read-only preview',datetime.now().isoformat(timespec='seconds'),'']
    for a in actions:
        rows+= [f'[{a["artist"]}] {a["album"]} ({a["year"]})',
                f'Folder: {a["folder"]}',f'Proposed folder: {a["dest_folder"]}',
                f'Files: {len(a["tracks"])}']
        for t in a['tracks']:
            tags=('tag update' if t['needs_tags'] else 'tags unchanged')
            rows.append(f'  {t["old_name"]} -> {t["new_name"]} [{tags}]')
        rows.append('')
    rows.extend(['Problems / skipped:']+[f'- {p}' for p in problems])
    Path(destination).write_text('\n'.join(rows),encoding='utf-8')
