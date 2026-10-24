"""Container-aware tag and artwork adapters. Never infer a tag type from a name alone."""
import base64
from pathlib import Path
import struct
from mutagen.flac import FLAC,Picture
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from mutagen.aiff import AIFF
from mutagen.dsf import DSF
from mutagen.dsdiff import DSDIFF
from mutagen.aac import AAC
from mutagen.mp4 import MP4,MP4Cover
from mutagen.monkeysaudio import MonkeysAudio
from mutagen.wavpack import WavPack
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
from mutagen.asf import ASF,ASFByteArrayAttribute
from mutagen.id3 import TIT2,TPE1,TPE2,TALB,TRCK,TPOS,TDRC,TYER,APIC
from mutagen.apev2 import APEBinaryValue

EXTENSIONS={'.wav','.wave','.aiff','.aif','.aifc','.pcm','.dsd','.dsf','.dff','.cda',
            '.flac','.alac','.ape','.wv','.mp3','.aac','.m4a','.mp4','.ogg','.oga','.wma','.opus'}
FILE_PATTERN=' '.join('*'+ext for ext in sorted(EXTENSIONS))
ID3_FIELDS={'title':('TIT2',TIT2),'artist':('TPE1',TPE1),'albumartist':('TPE2',TPE2),
            'album':('TALB',TALB),'track':('TRCK',TRCK),'disc':('TPOS',TPOS),'year':('TDRC',TDRC)}
VORBIS={'title':'title','artist':'artist','albumartist':'albumartist','album':'album',
        'track':'tracknumber','disc':'discnumber','year':'date'}
APE={'title':'Title','artist':'Artist','albumartist':'Album Artist','album':'Album',
     'track':'Track','disc':'Disc','year':'Year'}
MP4_FIELDS={'title':'\xa9nam','artist':'\xa9ART','albumartist':'aART','album':'\xa9alb',
            'track':'trkn','disc':'disk','year':'\xa9day'}
ASF_FIELDS={'title':'Title','artist':'Author','albumartist':'WM/AlbumArtist','album':'WM/AlbumTitle',
            'track':'WM/TrackNumber','disc':'WM/PartOfSet','year':'WM/Year'}


def can_tag(path):return Path(path).suffix.lower() in EXTENSIONS- {'.pcm','.aac','.cda'}
def can_rename(path):return Path(path).suffix.lower() in EXTENSIONS- {'.cda'}

def format_note(path):
    ext=Path(path).suffix.lower()
    if ext=='.cda':return 'CD track reference: rip the CD to an audio file before editing or playing.'
    if ext=='.pcm':return 'Raw PCM: filenames only; choose sample format, rate and channels before playback.'
    if ext=='.aac':return 'Raw AAC: filenames and playback; embedded tag editing is unavailable. Use M4A for tags.'
    return ''


def open_audio(path,fmt=None):
    ext=fmt or Path(path).suffix.lower()
    classes={'.flac':FLAC,'.mp3':MP3,'.wav':WAVE,'.wave':WAVE,'.aiff':AIFF,'.aif':AIFF,'.aifc':AIFF,
             '.dsf':DSF,'.dff':DSDIFF,'.alac':MP4,'.m4a':MP4,'.mp4':MP4,'.ape':MonkeysAudio,
             '.wv':WavPack,'.ogg':OggVorbis,'.oga':OggVorbis,'.opus':OggOpus,'.wma':ASF,'.aac':AAC}
    if ext=='.dsd':
        with open(path,'rb') as stream:magic=stream.read(4)
        if magic==b'DSD ':return DSF(path)
        if magic==b'FRM8':return DSDIFF(path)
        raise ValueError('.dsd must contain a DSF or DFF stream; use the original container file.')
    if ext in ('.ogg','.oga'):
        try:return OggVorbis(path)
        except Exception:return OggOpus(path)
    if ext not in classes:raise ValueError('Unsupported audio container: '+ext)
    return classes[ext](path)


def family(audio):
    if isinstance(audio,(MP3,WAVE,AIFF,DSF,DSDIFF)):return 'id3'
    if isinstance(audio,MP4):return 'mp4'
    if isinstance(audio,ASF):return 'asf'
    if isinstance(audio,(MonkeysAudio,WavPack)):return 'ape'
    return 'vorbis'


def mapping(audio):return {'id3':ID3_FIELDS,'mp4':MP4_FIELDS,'asf':ASF_FIELDS,'ape':APE,'vorbis':VORBIS}[family(audio)]


def text_values(tags,key,kind):
    if not tags or key not in tags:return []
    if kind=='id3':return [str(text) for frame in tags.getall(key) for text in frame.text]
    if kind=='ape':return list(tags[key]) if tags[key].kind==0 else []
    return [str(value) for value in tags[key]]


def read_fields(path,include_artwork=False):
    ext=Path(path).suffix.lower();values={key:'' for key in VORBIS}
    values.update(duration=0,artwork_count=0,front_cover_count=0,artwork=None,format_note=format_note(path),taggable=can_tag(path))
    if ext in {'.pcm','.cda'}:
        with open(path,'rb') as stream:head=stream.read(44)
        if ext=='.cda' and not (head[:4]==b'RIFF' and head[8:12]==b'CDDA'):
            raise ValueError('Not a valid CDA track reference. Rip an audio CD to real audio files.')
        if ext=='.pcm' and not Path(path).stat().st_size:raise ValueError('Raw PCM file is empty.')
        return values
    audio=open_audio(path);tags=audio.tags;kind=family(audio)
    for field,key in mapping(audio).items():
        if kind=='id3':key=key[0]
        if kind=='mp4' and field in ('track','disc'):
            number=(tags or {}).get(key,[])
            if number:
                n,total=number[0];values[field]=str(n)+('/'+str(total) if total else '') if n else ''
        else:
            texts=text_values(tags,key,kind);values[field]=texts[0] if texts else ''
    if not values['year']:
        texts=text_values(tags,'TYER' if kind=='id3' else 'year',kind);values['year']=texts[0] if texts else ''
    values['duration']=float(audio.info.length)
    pictures=read_pictures(audio)
    values['artwork_count']=len(pictures);values['front_cover_count']=sum(t==3 for t,data in pictures)
    if include_artwork:
        values['artwork']=next((data for t,data in pictures if t==3),pictures[0][1] if pictures else None)
    return values


def asf_picture(data):
    raw=bytes(data);kind,length=struct.unpack('<BI',raw[:5]);pos=5
    for _ in range(2):
        while raw[pos:pos+2]!=b'\0\0':
            pos+=2
            if pos+2>len(raw):raise ValueError('Malformed WMA picture')
        pos+=2
    if len(raw[pos:])!=length:raise ValueError('Malformed WMA picture length')
    return kind,raw[pos:]


def read_pictures(audio):
    tags=audio.tags or {};kind=family(audio)
    if kind=='id3':return [(p.type,p.data) for p in audio.tags.getall('APIC')] if audio.tags else []
    if isinstance(audio,FLAC):return [(p.type,p.data) for p in audio.pictures]
    if kind=='mp4':return [(3 if i==0 else 0,bytes(p)) for i,p in enumerate(tags.get('covr',[]))]
    pictures=[]
    if kind=='ape':
        for key in tags:
            if key.lower().startswith('cover art (') and tags[key].kind==1:
                raw=bytes(tags[key]);_,sep,data=raw.partition(b'\0')
                if sep:pictures.append((3 if key.lower()=='cover art (front)' else 0,data))
    elif kind=='asf':
        for value in tags.get('WM/Picture',[]):
            try:pictures.append(asf_picture(value.value))
            except (ValueError,struct.error):continue
    else:
        for value in tags.get('metadata_block_picture',[]):
            try:
                p=Picture(base64.b64decode(value));pictures.append((p.type,p.data))
            except Exception:continue
        if not pictures:
            for value in tags.get('coverart',[]):
                try:pictures.append((3,base64.b64decode(value)))
                except Exception:continue
    return pictures


def remove_key(tags,key):
    if key in tags:del tags[key]


def replace_artwork(audio,art):
    tags=audio.tags;kind=family(audio)
    if kind=='id3':
        others=[p for p in tags.getall('APIC') if p.type!=3];tags.delall('APIC')
        for p in others:tags.add(p)
        if art:
            descriptions={p.desc for p in others};desc='Front cover'
            while desc in descriptions:desc+=' (new)'
            tags.add(APIC(encoding=3,mime=art['mime'],type=3,desc=desc,data=art['data']))
    elif kind=='mp4':
        others=list(tags.get('covr',[]))[1:]
        if art:others.insert(0,MP4Cover(art['data'],imageformat=MP4Cover.FORMAT_JPEG if art['mime']=='image/jpeg' else MP4Cover.FORMAT_PNG))
        if others:tags['covr']=others
        else:remove_key(tags,'covr')
    elif kind=='ape':
        remove_key(tags,'Cover Art (Front)')
        if art:tags['Cover Art (Front)']=APEBinaryValue(('cover.jpg' if art['mime']=='image/jpeg' else 'cover.png').encode()+b'\0'+art['data'])
    elif kind=='asf':
        others=[]
        for value in tags.get('WM/Picture',[]):
            try:front=asf_picture(value.value)[0]==3
            except (ValueError,struct.error):front=False
            if not front:others.append(value)
        if art:
            raw=struct.pack('<BI',3,len(art['data']))+art['mime'].encode('utf-16le')+b'\0\0'+'Front cover'.encode('utf-16le')+b'\0\0'+art['data']
            others.append(ASFByteArrayAttribute(raw))
        if others:tags['WM/Picture']=others
        else:remove_key(tags,'WM/Picture')
    else:
        others=[]
        for raw in tags.get('metadata_block_picture',[]):
            try:front=Picture(base64.b64decode(raw)).type==3
            except Exception:front=False
            if not front:others.append(raw)
        if isinstance(audio,FLAC):
            pictures=[p for p in audio.pictures if p.type!=3];audio.clear_pictures()
            for p in pictures:audio.add_picture(p)
        remove_key(tags,'coverart');remove_key(tags,'coverartmime')
        if art:
            p=Picture();p.type=3;p.mime=art['mime'];p.desc='Front cover';p.data=art['data']
            p.width=art['width'];p.height=art['height'];p.depth=art.get('depth',24)
            if isinstance(audio,FLAC):audio.add_picture(p)
            else:others.append(base64.b64encode(p.write()).decode('ascii'))
        if others:tags['metadata_block_picture']=others
        else:remove_key(tags,'metadata_block_picture')


def write_fields(path,fmt,changes):
    if not can_tag('track'+fmt):raise ValueError(format_note('track'+fmt))
    audio=open_audio(path,fmt)
    if audio.tags is None:audio.add_tags()
    tags=audio.tags;kind=family(audio)
    for field,key in mapping(audio).items():
        if field not in changes:continue
        value=changes[field]
        if kind=='id3':
            key,cls=key;tags.delall(key)
            if value:tags.add(cls(encoding=3,text=[value]))
            if field=='year':tags.delall('TYER')
        elif kind=='mp4' and field in ('track','disc'):
            if value:
                n,_,total=value.partition('/');tags[key]=[(int(n),int(total) if total else 0)]
            else:remove_key(tags,key)
        else:
            if value:tags[key]=value if kind=='ape' else [value]
            else:remove_key(tags,key)
            if kind=='vorbis' and field=='year' and 'year' in tags:
                if value:tags['year']=[value]
                else:remove_key(tags,'year')
    if 'artwork' in changes:replace_artwork(audio,changes['artwork'])
    if kind=='id3':audio.save(v2_version=tags.version[1] if tags.version[1] in (3,4) else 4)
    else:audio.save()


def snapshot_album(path,include_title=False,include_track=False):
    audio=open_audio(path);kind=family(audio);tags=audio.tags
    keys={'id3':['TALB','TDRC','TYER'],'mp4':['\xa9alb','\xa9day'],'asf':['WM/AlbumTitle','WM/Year'],
          'ape':['Album','Year'],'vorbis':['album','date','year']}[kind]
    if include_title:keys=[*keys,{'id3':'TIT2','mp4':'\xa9nam','asf':'Title','ape':'Title','vorbis':'title'}[kind]]
    if include_track:keys=[*keys,{'id3':'TRCK','mp4':'trkn','asf':'WM/TrackNumber','ape':'Track','vorbis':'tracknumber'}[kind]]
    return {'format':'container','family':kind,'fields':{key:([list(pair) for pair in tags[key]] if kind=='mp4' and key=='trkn' else text_values(tags,key,kind)) if tags is not None and key in tags else None for key in keys},
            'version':tags.version[1] if kind=='id3' and tags else 4,'tags_existed':tags is not None}


def restore_album(path,snapshot):
    audio=open_audio(path)
    if audio.tags is None:audio.add_tags()
    tags=audio.tags;kind=snapshot['family']
    for key,values in snapshot['fields'].items():
        if kind=='id3':
            tags.delall(key)
            cls={'TALB':TALB,'TDRC':TDRC,'TYER':TYER,'TIT2':TIT2,'TRCK':TRCK}[key]
            if values:tags.add(cls(encoding=3,text=values))
        elif values is None:remove_key(tags,key)
        elif kind=='mp4' and key=='trkn':tags[key]=[tuple(pair) for pair in values]
        else:tags[key]=values
    if not snapshot['tags_existed'] and not tags:audio.delete()
    elif kind=='id3':audio.save(v2_version=snapshot.get('version',4))
    else:audio.save()
