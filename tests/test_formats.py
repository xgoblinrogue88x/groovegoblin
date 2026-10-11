"""Generated audio/container fixtures for broad tag, artwork, rename and undo coverage."""
import hashlib
import base64
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import time
import unittest
from PIL import Image
from groove_formats import open_audio,write_fields,read_fields,read_pictures,replace_artwork,can_tag,EXTENSIONS,family,asf_picture
from groove_manual import read_track,plan_manual,apply_manual,load_artwork,validate_changes
from groove_core import scan_folders,plan_actions,apply_actions,undo_journal


def make_dsd(root):
    payload=b'\x69'*163840
    dsf=root/'signal.dsf'
    size=28+52+12+len(payload)
    dsf.write_bytes(b'DSD '+struct.pack('<QQQ',28,size,0)+b'fmt '+struct.pack('<QIIIIIIQII',52,1,0,2,2,2822400,1,655360,4096,0)+b'data'+struct.pack('<Q',12+len(payload))+payload)
    def chunk(name,data):return name+struct.pack('>Q',len(data))+data+(b'\0' if len(data)%2 else b'')
    prop=b'SND '+chunk(b'FS  ',struct.pack('>I',2822400))+chunk(b'CHNL',struct.pack('>H',2)+b'SLFTSRGT')+chunk(b'CMPR',b'DSD '+b'\x0e' + b'not compressed'+b'\0')
    body=b'DSD '+chunk(b'FVER',struct.pack('>I',0x01050000))+chunk(b'PROP',prop)+chunk(b'DSD ',payload)
    dff=root/'signal.dff';dff.write_bytes(chunk(b'FRM8',body))
    return [dsf,dff]


def fixtures(root):
    paths=[]
    for ext,codec,extra in [('.wav','pcm_s16le',[]),('.aiff','pcm_s16be',[]),('.m4a','aac',[]),
                           ('.alac','alac',['-f','ipod']),('.ogg','libvorbis',[]),('.opus','libopus',[]),
                           ('.wma','wmav2',[]),('.wv','wavpack',[]),('.aac','aac',['-f','adts']),
                           ('.pcm','pcm_s16le',['-f','s16le'])]:
        dest=root/('signal'+ext)
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i','sine=frequency=440:duration=0.4','-ac','2','-c:a',codec,*extra,'-y',str(dest)],check=True)
        paths.append(dest)
    paths+=make_dsd(root)
    # Synthetic Monkey's Audio header: validates the parser and APEv2 handling,
    # not the decoder. FFmpeg has no Monkey's Audio encoder.
    ape=root/'signal.ape';header=bytearray(76);header[:4]=b'MAC ';struct.pack_into('<H',header,4,3990)
    struct.pack_into('<IIIHHI',header,56,73728,17640,1,16,2,44100);ape.write_bytes(header)
    paths.append(ape)
    for old,ext in [('signal.wav','.wave'),('signal.aiff','.aif'),('signal.dsf','.dsd'),('signal.ogg','.oga')]:
        dest=root/('signal'+ext);shutil.copyfile(root/old,dest);paths.append(dest)
    return paths


class FormatTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.paths=fixtures(self.root)
        self.picture=self.root/'art.png';Image.new('RGB',(24,24),'green').save(self.picture)
        self.art=load_artwork(self.picture)
        self.base=self.root/'program'

    def test_all_new_tag_containers_manual_batch_art_and_exact_undo(self):
        selected=[p for p in self.paths if can_tag(p)]
        for p in selected:
            audio=open_audio(p)
            if audio.tags is None:audio.add_tags()
            from mutagen.id3 import TXXX,APIC
            from mutagen.flac import Picture
            from mutagen.mp4 import MP4Cover
            from mutagen.apev2 import APEBinaryValue
            from mutagen.asf import ASFByteArrayAttribute
            kind=family(audio)
            if kind=='id3':
                audio.tags.add(TXXX(desc='KEEP',text=['untouched']))
                audio.tags.add(APIC(type=4,mime='image/png',desc='Back cover',data=self.art['data']))
            elif kind=='ape':audio.tags['Cover Art (Back)']=APEBinaryValue(b'back.png\0'+self.art['data'])
            elif kind=='mp4':audio.tags['covr']=[MP4Cover(self.art['data'],imageformat=MP4Cover.FORMAT_PNG)]*2
            elif kind=='asf':
                raw=struct.pack('<BI',4,len(self.art['data']))+'image/png'.encode('utf-16le')+b'\0\0'+'Back cover'.encode('utf-16le')+b'\0\0'+self.art['data']
                audio.tags['WM/Picture']=[ASFByteArrayAttribute(raw)]
            else:
                picture=Picture();picture.type=4;picture.mime='image/png';picture.data=self.art['data']
                audio.tags['metadata_block_picture']=[base64.b64encode(picture.write()).decode()]
            if p.suffix not in {'.dsf','.dsd','.dff','.wav','.wave','.aiff','.aif'}:
                audio.tags['keep-me']=['untouched'] if p.suffix not in {'.ape','.wv'} else 'untouched'
                # MP4 only supports registered atoms; use an iTunes freeform value.
                if p.suffix in {'.m4a','.alac'}:
                    audio.tags.pop('keep-me');audio.tags['----:com.apple.iTunes:KEEP']=[b'untouched']
            audio.save()
        records={str(p):read_track(p) for p in selected};before={p:p.read_bytes() for p in selected}
        def audio_hash(path):
            return subprocess.check_output(['ffmpeg','-hide_banner','-loglevel','error','-i',str(path),'-map','0:a:0','-f','hash','-hash','sha256','-'])
        decoded={p:audio_hash(p) for p in selected if p.suffix!='.ape'}
        fields={'title':'New title','artist':'Track Artist','albumartist':'Album Artist','album':'New album',
                'track':'3/12','disc':'2/3','year':'1997','artwork':self.art}
        pending={str(p):{**fields,'filename':'renamed'+p.suffix} for p in selected}
        plans,issues=plan_manual(records,pending);self.assertFalse(issues,issues)
        journal=apply_manual(plans,self.base)
        for p in selected:
            with self.subTest(format=p.suffix):
                new=p.with_name('renamed'+p.suffix);data=read_track(new)
                if p.suffix!='.ape':self.assertEqual(audio_hash(new),decoded[p],p.suffix)
                else:self.assertEqual(new.read_bytes()[:76],before[p][:76])
                for key,value in fields.items():
                    if key!='artwork':self.assertEqual(data[key],value)
                self.assertEqual(data['front_cover_count'],1);self.assertEqual(data['artwork_count'],2)
                audio=open_audio(new)
                if family(audio)=='id3':self.assertEqual(str(audio.tags.getall('TXXX')[0]),'untouched')
                if p.suffix in {'.m4a','.alac'}:self.assertEqual(bytes(audio.tags['----:com.apple.iTunes:KEEP'][0]),b'untouched')
                elif p.suffix in {'.ape','.wv'}:self.assertEqual(str(audio.tags['keep-me']),'untouched')
                elif p.suffix in {'.ogg','.oga','.opus','.wma'}:self.assertEqual(str(audio.tags['keep-me'][0]),'untouched')
        self.assertFalse(undo_journal(journal))
        for p,raw in before.items():self.assertEqual(p.read_bytes(),raw,p.suffix)

    def test_organizer_tag_snapshot_restore_for_every_new_container(self):
        for p in [p for p in self.paths if can_tag(p)]:
            with self.subTest(format=p.suffix):
                write_fields(p,p.suffix,{'artist':'Artist','album':'Old Album','year':'2025','title':'Song','track':'1'})
                albums,issues=scan_folders([p]);self.assertFalse(issues)
                a=albums[0];a.album='Correct Album';a.year='1997';a.approved=True
                options={'tags':True,'folders':False,'filenames':True}
                actions,issues=plan_actions(albums,options);self.assertFalse(issues,issues)
                journal=apply_actions(actions,self.base,options)
                new=p.with_name('01 - Artist - Song'+p.suffix)
                self.assertEqual(read_fields(new)['album'],'Correct Album')
                self.assertFalse(undo_journal(journal))
                restored=read_fields(p);self.assertEqual(restored['album'],'Old Album');self.assertEqual(restored['year'],'2025')

    def test_raw_files_limits_and_filename_only_exact_undo(self):
        for p in [p for p in self.paths if not can_tag(p)]:
            before=p.read_bytes();record=read_track(p)
            self.assertTrue(record['format_note'])
            with self.assertRaises(ValueError):validate_changes(record,{'artist':'Unsafe ID3 prefix'})
            plans,issues=plan_manual({str(p):record},{str(p):{'filename':'renamed'+p.suffix}});self.assertFalse(issues)
            journal=apply_manual(plans,self.base);self.assertFalse(undo_journal(journal));self.assertEqual(p.read_bytes(),before)
        cda=self.root/'Track01.cda';cda.write_bytes(b'RIFF'+struct.pack('<I',36)+b'CDDA'+b'\0'*32)
        record=read_track(cda);self.assertIn('rip',record['format_note'])
        with self.assertRaises(ValueError):validate_changes(record,{'filename':'rename.cda'})
        fake=self.root/'invalid.wav';fake.write_bytes(b'not an audio file')
        with self.assertRaises(Exception):read_track(fake)

    def test_partial_scope_and_raw_tag_capabilities_block_unsafe_operations(self):
        wav=self.root/'signal.wav';albums,errors=scan_folders([wav]);self.assertFalse(errors)
        album=albums[0];album.artist='Artist';album.album='Album';album.year='1997';album.approved=True
        actions,issues=plan_actions(albums,{'tags':False,'folders':True,'filenames':False})
        self.assertTrue(issues);self.assertFalse(actions)
        for ext in ('.pcm','.aac'):
            p=self.root/('signal'+ext);before=p.read_bytes();albums,errors=scan_folders([p]);self.assertFalse(errors)
            album=albums[0];album.artist='Artist';album.album='Album';album.year='1997';album.approved=True
            actions,issues=plan_actions(albums,{'tags':True,'folders':False,'filenames':False})
            self.assertTrue(issues);self.assertFalse(actions)
            actions,issues=plan_actions(albums,{'tags':False,'folders':False,'filenames':True,'file_format':'Artist - Title'})
            self.assertFalse(issues);self.assertTrue(actions[0]['changed']);self.assertEqual(p.read_bytes(),before)

    def test_new_formats_background_playback_and_pcm_configuration(self):
        from groove_player import MusicPlayer
        import os
        os.environ.setdefault('SDL_AUDIODRIVER','dummy')
        player=MusicPlayer();self.addCleanup(player.close)
        # Each real generated encoding goes through FFmpeg, SDL playback and seek.
        for p in [p for p in self.paths if p.suffix not in {'.ape','.wave','.aif','.dsd','.oga'}]:
            with self.subTest(format=p.suffix):
                raw=p.read_bytes();record=read_track(p)
                if p.suffix=='.pcm':record['pcm']={'format':'s16le','rate':44100,'channels':2}
                player.play([record]);self.assertEqual(player.state,'buffering')
                deadline=time.monotonic()+10
                while player.state=='buffering' and time.monotonic()<deadline:time.sleep(.02);player.pump()
                self.assertEqual(player.state,'playing');player.toggle();self.assertEqual(player.state,'paused')
                player.seek(.03);self.assertEqual(player.state,'paused');player.stop()
                self.assertEqual(p.read_bytes(),raw)
        # No implicit PCM guess and no attempt to play a CD reference as audio.
        record=read_track(self.root/'signal.pcm');player.play([record])
        deadline=time.monotonic()+3
        with self.assertRaisesRegex(ValueError,'sample format'):
            while player.state=='buffering' and time.monotonic()<deadline:time.sleep(.02);player.pump()
        with self.assertRaisesRegex(ValueError,'CD track'):
            player.play([{'path':str(self.root/'track.cda'),'duration':0}])
