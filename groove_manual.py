"""Explicit manual container-aware edits with full-file undo backups and staged commits."""
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import tempfile
from datetime import datetime
import uuid
import warnings

from PIL import Image
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TPE2, TALB, TRCK, TPOS, TDRC, TYER, APIC
from groove_core import EXTENSIONS, safe_name, file_signature, atomic_json, backup_dir
from groove_version import __version__
from groove_formats import read_fields, write_fields, can_tag, can_rename, format_note

FIELDS=('filename','title','artist','albumartist','album','track','disc','year')
FLAC_KEYS={'title':'title','artist':'artist','albumartist':'albumartist','album':'album',
           'track':'tracknumber','disc':'discnumber','year':'date'}
ID3_KEYS={'title':('TIT2',TIT2),'artist':('TPE1',TPE1),'albumartist':('TPE2',TPE2),
          'album':('TALB',TALB),'track':('TRCK',TRCK),'disc':('TPOS',TPOS),'year':('TDRC',TDRC)}
MAX_IMAGE_BYTES=20*1024*1024


def digest(path):
    result=hashlib.sha256()
    with open(path,'rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
    return result.hexdigest()


def read_track(path,include_artwork=False):
    path=Path(path).resolve()
    if path.suffix.lower() not in EXTENSIONS:raise ValueError('Unsupported audio format.')
    values={'path':str(path),'filename':path.name,'signature':file_signature(path)}
    values.update(read_fields(path,include_artwork));return values


def load_artwork(path):
    path=Path(path)
    if path.stat().st_size>MAX_IMAGE_BYTES:raise ValueError('Choose an image smaller than 20 MB.')
    data=path.read_bytes()
    if len(data)>MAX_IMAGE_BYTES:raise ValueError('Choose an image smaller than 20 MB.')
    with warnings.catch_warnings():
        warnings.simplefilter('error',Image.DecompressionBombWarning)
        with Image.open(BytesIO(data)) as image:
            if image.width*image.height>25_000_000:raise ValueError('Choose an image under 25 megapixels.')
            image.load()
            if image.format in ('JPEG','PNG'):
                mime='image/jpeg' if image.format=='JPEG' else 'image/png'
            else:
                output=BytesIO();image.convert('RGBA' if 'A' in image.getbands() else 'RGB').save(output,format='PNG')
                data=output.getvalue();mime='image/png'
            if len(data)>MAX_IMAGE_BYTES:raise ValueError('Converted artwork is larger than 20 MB.')
            return {'data':data,'mime':mime,'width':image.width,'height':image.height,'depth':32 if 'A' in image.getbands() else 24}


def validate_changes(record,changes):
    unknown=set(changes)-set(FIELDS)-{'artwork'}
    if unknown:raise ValueError('Unknown fields: '+', '.join(sorted(unknown)))
    changes=dict(changes)
    if changes and not can_rename(record['path']):raise ValueError(format_note(record['path']))
    if not can_tag(record['path']) and any(field!='filename' for field in changes):raise ValueError(format_note(record['path']))
    for field,value in changes.items():
        if field=='artwork':
            if value is not None and (not isinstance(value,dict) or not isinstance(value.get('data'),bytes)
                                      or len(value['data'])>MAX_IMAGE_BYTES):
                raise ValueError('Invalid artwork; select a local image again.')
            continue
        if not isinstance(value,str) or '\0' in value:raise ValueError('Invalid value for '+field)
        if field in ('track','disc') and value:
            if not re.fullmatch(r'[1-9]\d*(?:/[1-9]\d*)?|0*[1-9]\d*(?:/0*[1-9]\d*)?',value):
                raise ValueError(field.title()+' must be a positive number, optionally number/total.')
        if field in ('track','disc') and value and Path(record['path']).suffix.lower() in {'.m4a','.alac','.mp4'}:
            if any(int(part)>65535 for part in value.split('/')):raise ValueError('MP4 track/disc numbers and totals must be at most 65535.')
        if field=='year' and value and not re.fullmatch(r'\d{4}(?:-\d{2}(?:-\d{2})?)?',value):
            raise ValueError('Year must be YYYY, YYYY-MM or YYYY-MM-DD, or blank to clear.')
        if field=='filename':
            if not value.strip() or PureWindowsPath(value).name!=value or any(c in value for c in '/\\:'):
                raise ValueError('Filename must be a name, not a folder path.')
            ext=Path(record['path']).suffix
            if value.lower().endswith(ext.lower()):value=value[:-len(ext)]
            elif Path(value).suffix.lower() in EXTENSIONS:
                raise ValueError('A filename change cannot change the audio format.')
            changes[field]=safe_name(value)+ext
    return changes


def plan_manual(records,pending):
    plans=[];targets=set();issues=[]
    for path,changes in pending.items():
        if not changes:continue
        record=records.get(path)
        if record is None:issues.append('Track is no longer loaded: '+path);continue
        try:
            changes=validate_changes(record,changes)
            src=Path(path)
            if file_signature(src)!=record['signature']:raise ValueError('File changed since loading; reload it first.')
            dest=src.with_name(changes.get('filename',src.name))
            key=str(dest).casefold()
            if key in targets:raise ValueError('Duplicate output filename: '+dest.name)
            for other in src.parent.iterdir():
                if other.name.casefold()==dest.name.casefold() and other.resolve()!=src.resolve():
                    raise ValueError('Output filename already exists: '+dest.name)
            targets.add(key)
            effective={k:v for k,v in changes.items() if k=='artwork' or v!=record.get(k)}
            if not effective:continue
            plans.append({'source':str(src),'destination':str(dest),'signature':record['signature'],'changes':effective})
        except (OSError,ValueError) as error:issues.append(Path(path).name+': '+str(error))
    return plans,issues


def write_tags(path,fmt,changes):
    if fmt not in {'.flac','.mp3'}:
        write_fields(path,fmt,changes);return
    if fmt=='.flac':
        tags=FLAC(path)
        for field,key in FLAC_KEYS.items():
            if field not in changes:continue
            value=changes[field]
            if value:tags[key]=[value]
            else:tags.pop(key,None)
            if field=='year' and 'year' in tags:
                if value:tags['year']=[value]
                else:tags.pop('year',None)
        if 'artwork' in changes:
            others=[p for p in tags.pictures if p.type!=3]
            tags.clear_pictures()
            for picture in others:tags.add_picture(picture)
            art=changes['artwork']
            if art:
                picture=Picture();picture.type=3;picture.mime=art['mime'];picture.desc='Front cover'
                picture.width=art['width'];picture.height=art['height'];picture.depth=art.get('depth',24);picture.data=art['data']
                tags.add_picture(picture)
        tags.save()
    else:
        try:tags=ID3(path)
        except ID3NoHeaderError:tags=ID3()
        version=tags.version[1] if tags.version[1] in (3,4) else 4
        for field,(key,cls) in ID3_KEYS.items():
            if field not in changes:continue
            tags.delall(key)
            if changes[field]:tags.add(cls(encoding=3,text=[changes[field]]))
            if field=='year':tags.delall('TYER')
        if 'artwork' in changes:
            others=[p for p in tags.getall('APIC') if p.type!=3]
            tags.delall('APIC')
            for picture in others:tags.add(picture)
            art=changes['artwork']
            if art:
                # APIC uses description as its key. Preserve non-front pictures
                # even if one already uses the standard Front cover description.
                descriptions={p.desc for p in others};description='Front cover'
                while description in descriptions:description+=' (new)'
                tags.add(APIC(encoding=3,mime=art['mime'],type=3,desc=description,data=art['data']))
        tags.save(path,v2_version=version)


def apply_manual(plans,app_base,callback=None):
    if not plans:return None
    # Revalidate the entire batch before making backups or touching any source.
    for plan in plans:
        src=Path(plan['source']);dest=Path(plan['destination'])
        checked=validate_changes({'path':str(src)},plan['changes'])
        if dest!=src.with_name(checked.get('filename',src.name)):
            raise ValueError('Manual edits may rename files in place only.')
        if file_signature(src)!=plan['signature']:raise ValueError('File changed since loading: '+str(src))
        for entry in src.parent.iterdir():
            if entry.name.casefold()==dest.name.casefold() and entry.resolve()!=src.resolve():
                raise ValueError('Output filename already exists: '+str(dest))
    logs=backup_dir(app_base)
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]
    journal_path=logs/('Groove_Goblin_Undo_'+stamp+'.json')
    backups=logs/'ManualBackups'/stamp;backups.mkdir(parents=True)
    journal={'kind':'manual_tracks','format_version':1,'version':__version__,'state':'preparing',
             'created':datetime.now().isoformat(timespec='seconds'),'undone':False,'tracks':[]}
    atomic_json(journal_path,journal)
    for index,plan in enumerate(plans):
        src=Path(plan['source']);backup=backups/(str(index)+src.suffix)
        shutil.copy2(src,backup)
        if file_signature(src)!=plan['signature']:raise ValueError('File changed during backup: '+str(src))
        journal['tracks'].append({'source':str(src),'destination':plan['destination'],'backup':str(backup),
                                 'original_hash':digest(backup),'prepared_hash':None,'fields':list(plan['changes']),'started':False,'done':False})
        atomic_json(journal_path,journal)
    journal['state']='applying';atomic_json(journal_path,journal)
    try:
        for plan,record in zip(plans,journal['tracks']):
            src=Path(plan['source']);dest=Path(plan['destination'])
            if callback:callback('Saving '+src.name)
            handle,temp=tempfile.mkstemp(prefix='.groove_',suffix='.tmp',dir=src.parent);os.close(handle)
            stage=Path(temp)
            try:
                shutil.copy2(record['backup'],stage)
                if any(k!='filename' for k in plan['changes']):write_tags(stage,src.suffix.lower(),plan['changes'])
                record['prepared_hash']=digest(stage)
                if digest(src)!=record['original_hash']:raise ValueError('File changed during preparation: '+str(src))
                record['started']=True;atomic_json(journal_path,journal)
                if src==dest or (os.name=='nt' and str(src).casefold()==str(dest).casefold()):
                    os.replace(stage,src)
                    if src.name!=dest.name:src.rename(dest)
                else:
                    if os.name=='nt':stage.rename(dest) # Windows refuses an occupied destination.
                    else:os.link(stage,dest);stage.unlink() # Atomic no-overwrite creation.
                    src.unlink()
                record['done']=True;atomic_json(journal_path,journal)
            finally:
                if stage.exists():stage.unlink()
        journal['state']='complete';atomic_json(journal_path,journal)
        atomic_json(logs/'last_apply.json',{'journal':str(journal_path)})
    except Exception as error:
        journal['state']='partial_error';atomic_json(journal_path,journal)
        raise RuntimeError('Manual save stopped. Undo backups are in '+str(journal_path)+'\n'+str(error)) from error
    return str(journal_path)


def undo_manual(journal_path,callback=None):
    path=Path(journal_path);journal=json.loads(path.read_text());issues=[]
    if journal.get('undone'):raise ValueError('This operation has already been undone.')
    for record in reversed(journal['tracks']):
        if not record.get('started') or record.get('restored'):continue
        src=Path(record['source']);dest=Path(record['destination']);backup=Path(record['backup'])
        try:
            if not backup.is_file() or digest(backup)!=record['original_hash']:raise ValueError('Undo backup is missing or changed.')
            same=src==dest or (os.name=='nt' and str(src).casefold()==str(dest).casefold())
            current=src if same else dest
            if current.exists() and digest(current) not in (record['prepared_hash'],record['original_hash']):
                raise ValueError('Track changed after saving; refusing to overwrite it.')
            if not same and src.exists() and digest(src)!=record['original_hash']:
                raise ValueError('Original filename is occupied by a different file.')
            if same and not current.exists():raise ValueError('Edited track is missing; locate it before undoing.')
            handle,temp=tempfile.mkstemp(prefix='.groove_undo_',suffix='.tmp',dir=src.parent);os.close(handle)
            stage=Path(temp)
            try:
                shutil.copy2(backup,stage)
                os.replace(stage,src)
                if not same and dest.exists():dest.unlink()
            finally:
                if stage.exists():stage.unlink()
            record['restored']=True;atomic_json(path,journal)
            if callback:callback('Restored '+src.name)
        except (OSError,ValueError) as error:issues.append(str(src)+': '+str(error))
    journal['undone']=not issues;journal['state']='undone' if not issues else 'undo_incomplete';atomic_json(path,journal)
    return issues
