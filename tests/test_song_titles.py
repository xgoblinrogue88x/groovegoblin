"""Read-only tracklist matching and targeted title writes with reversible temp media."""
import hashlib
import subprocess
import unittest
from pathlib import Path
from mutagen.flac import FLAC,Picture
from mutagen.id3 import ID3,TIT2,APIC,TXXX
from groove_core import scan_folders,plan_actions,apply_actions,undo_journal,export_preview
from groove_formats import read_fields,write_fields,can_tag
from musicbrainz_client import MusicBrainz


class SongTitleTests(unittest.TestCase):
    def setUp(self):
        from test_groove import GrooveTests
        self.f=GrooveTests();self.f.setUp();self.addCleanup(self.f.tearDown)
        self.mb=MusicBrainz()
        from PIL import Image
        from io import BytesIO
        image=BytesIO();Image.new('RGB',(4,4),'green').save(image,format='PNG');self.cover=image.getvalue()

    def album(self,paths):
        albums,errors=scan_folders(paths);self.assertFalse(errors);self.assertEqual(len(albums),1)
        a=albums[0];a.album='Correct Album';a.artist='Artist';a.year='1998';a.approved=True;a.mbid='group'
        return a

    def releases(self,lists):
        def get(endpoint,params):
            if endpoint=='release/':return {'releases':[{'id':str(i),'status':'Official','date':'1998'} for i in range(len(lists))]}
            return {'media':[{'position':disc,'tracks':[{'position':n,'title':title} for n,title in enumerate(titles,1)]} for disc,titles in enumerate(lists[int(endpoint.split('/')[1])],1)]}
        self.mb.get=get

    def match(self,a):
        return self.mb.track_title_match(a,{'id':a.mbid,'title':a.album,'artist':a.artist})

    def test_multidisc_wrong_titles_match_numbers_not_filename_or_selection_order(self):
        paths=[]
        for disc,number,name in ((2,2,'a'),(1,2,'b'),(2,1,'c'),(1,1,'d')):
            p=self.f.add_flac('Album',name+'.flac','Wrong '+name,trackno=str(number))
            write_fields(p,'.flac',{'disc':str(disc)});paths.append(p)
        a=self.album([paths[0].parent]);before={p:p.read_bytes() for p in paths}
        self.releases([[['Disc One A','Disc One B'],['Disc Two A','Disc Two B']]]*2)
        a.title_match=self.match(a)
        self.assertEqual(a.title_match['titles'][str(paths[0])],'Disc Two B')
        actions,issues=plan_actions([a],{'tags':True,'folders':False,'filenames':False})
        self.assertFalse(issues);self.assertTrue(all(t['needs_title'] for t in actions[0]['tracks']))
        self.assertEqual({p:p.read_bytes() for p in paths},before)
        self.assertTrue(all(t.title.startswith('Wrong') for t in a.tracks))

    def test_ambiguous_editions_missing_numbers_and_disc_tags_do_not_guess(self):
        p=self.f.add_mp3('Album','song.mp3','Incorrect')
        a=self.album([p.parent]);self.releases([[['One']],[['Different song']]])
        self.assertFalse(self.match(a)['titles']);self.assertIn('disagree',self.match(a)['note'])
        self.releases([[['Disc One'],['Disc Two']]])
        self.assertFalse(self.match(a)['titles'])
        a.tracks[0].number=None
        self.assertIn('numbers are missing',self.match(a)['note'])
        a.tracks[0].number=1;a.tracks[0].disc=2
        self.assertEqual(self.match(a)['titles'][str(p)],'Disc Two')
        a.tracks[0].disc=4;self.releases([[['Single Album Song']]])
        self.assertEqual(self.match(a)['titles'][str(p)],'Single Album Song')

    def test_canceled_title_lookup_stops_before_next_request(self):
        import threading
        p=self.f.add_mp3('Album','song.mp3','Wrong');a=self.album([p.parent]);cancel=threading.Event();calls=[]
        def get(endpoint,params):
            calls.append(endpoint);cancel.set()
            return {'releases':[{'id':'release','status':'Official'}]}
        self.mb.get=get
        result=self.mb.track_title_match(a,{'id':'group','title':a.album,'artist':a.artist},cancel=cancel)
        self.assertFalse(result['titles']);self.assertIn('canceled',result['note']);self.assertEqual(calls,['release/'])

    def test_correct_existing_titles_can_identify_an_edition_and_partial_selection_is_explicit(self):
        paths=[self.f.add_flac('Album',str(i)+'.flac',title,trackno=str(i)) for i,title in enumerate(('One','Two','Wrong'),1)]
        a=self.album([paths[0].parent]);self.releases([[['One','Two','Correct']],[['Different','Two','Other']]])
        self.assertEqual(self.match(a)['titles'][str(paths[2])],'Correct')
        a.tracks=a.tracks[:1]
        self.assertFalse(self.match(a)['titles'])
        a.partial_selection=True;self.releases([[['One','Two','Three']]])
        self.assertEqual(self.match(a)['titles'],{str(paths[0]):'One'})

    def test_mp3_flac_apply_title_and_filename_preserve_audio_other_tags_art_and_undo(self):
        for ext in ('mp3','flac'):
            with self.subTest(ext=ext):
                p=(self.f.add_mp3('Album '+ext,'old.mp3','Wrong') if ext=='mp3' else self.f.add_flac('Album '+ext,'old.flac','Wrong'))
                if ext=='mp3':
                    tags=ID3(p);tags.add(TIT2(encoding=3,text=['Wrong','Alternate']));tags.add(APIC(type=3,mime='image/png',data=self.cover));tags.add(TXXX(desc='REPLAYGAIN_TRACK_GAIN',text=['-3 dB']));tags.save(p)
                else:
                    tags=FLAC(p);tags['title']=['Wrong','Alternate'];tags['replaygain_track_gain']='-3 dB';art=Picture();art.type=3;art.mime='image/png';art.data=self.cover;tags.add_picture(art);tags.save()
                pcm=lambda path:subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-f','s16le','-'])
                audio=hashlib.sha256(pcm(p)).digest();a=self.album([p.parent]);self.releases([[['Correct Song']]])
                a.title_match=self.match(a);options={'tags':True,'folders':True,'filenames':True}
                actions,issues=plan_actions([a],options);self.assertFalse(issues)
                self.assertIn('Correct Song',actions[0]['tracks'][0]['new_name'])
                report=self.f.root/(ext+'-preview.txt');export_preview(actions,issues,report)
                self.assertIn('Wrong -> Correct Song',report.read_text())
                journal=apply_actions(actions,self.f.root/'program',options)
                q=Path(actions[0]['dest_folder'])/actions[0]['tracks'][0]['new_name']
                self.assertEqual(read_fields(q)['title'],'Correct Song');self.assertEqual(hashlib.sha256(pcm(q)).digest(),audio)
                if ext=='mp3':
                    after=ID3(q);self.assertEqual(after.getall('APIC')[0].data,self.cover);self.assertTrue(after.getall('COMM'));self.assertEqual(str(after['TXXX:REPLAYGAIN_TRACK_GAIN']),'-3 dB')
                else:
                    after=FLAC(q);self.assertEqual(after['comment'],['DO NOT TOUCH']);self.assertEqual(after.pictures[0].data,self.cover);self.assertEqual(after['replaygain_track_gain'],['-3 dB'])
                self.assertFalse(undo_journal(journal));self.assertTrue(p.exists());self.assertEqual(hashlib.sha256(pcm(p)).digest(),audio)
                original=ID3(p)['TIT2'].text if ext=='mp3' else FLAC(p)['title']
                self.assertEqual(list(original),['Wrong','Alternate'])

    def test_missing_title_is_written_even_when_filename_fallback_already_matches_and_undo_removes_it(self):
        p=self.f.add_flac('Album','01 - Correct Song.flac','');tags=FLAC(p);tags.pop('title');tags.save()
        a=self.album([p.parent]);self.releases([[['Correct Song']]]);a.title_match=self.match(a)
        actions,issues=plan_actions([a],{'folders':False,'filenames':False})
        self.assertFalse(issues);self.assertTrue(actions[0]['tracks'][0]['needs_title'])
        journal=apply_actions(actions,self.f.root/'program',{});self.assertEqual(FLAC(p)['title'],['Correct Song'])
        self.assertFalse(undo_journal(journal));self.assertNotIn('title',FLAC(p))

    def test_titles_off_stale_match_collisions_and_stale_music_remain_protected(self):
        p=self.f.add_mp3('Album','old.mp3','Wrong');a=self.album([p.parent]);self.releases([[['Correct']]]);a.title_match=self.match(a)
        actions,issues=plan_actions([a],{'tags':False,'folders':False,'filenames':True})
        self.assertFalse(issues);self.assertFalse(actions[0]['tracks'][0]['needs_title']);self.assertIn('Wrong',actions[0]['tracks'][0]['new_name'])
        a.album='Another'
        actions,_=plan_actions([a],{'folders':False});self.assertFalse(actions[0]['tracks'][0]['needs_title'])
        a.album='Correct Album';before=p.read_bytes()
        actions,_=plan_actions([a],{'folders':False});write_fields(p,'.mp3',{'title':'New user edit'})
        with self.assertRaisesRegex(ValueError,'Re-scan'):apply_actions(actions,self.f.root/'program',{})
        self.assertEqual(read_fields(p)['title'],'New user edit')
        # Destination collisions must still stop title-derived renames.
        q=p.with_name('01 - Other Artist - Correct.mp3');q.write_bytes(before)
        _,issues=plan_actions([a],{'folders':False,'filenames':True});self.assertTrue(issues)

    def test_container_title_snapshots_restore_values_and_absence(self):
        from test_formats import fixtures
        root=self.f.root/'containers';root.mkdir();paths=fixtures(root)
        from groove_core import tag_snapshot,set_tags,restore_tags
        for p in paths:
            if not can_tag(p):continue
            with self.subTest(container=p.suffix):
                before=read_fields(p)['title'];snapshot=tag_snapshot(p,include_title=True)
                set_tags(p,'Album','1998',title='Correct Song')
                self.assertEqual(read_fields(p)['title'],'Correct Song')
                restore_tags(p,snapshot);self.assertEqual(read_fields(p)['title'],before)

    def test_partial_title_write_failure_has_write_ahead_undo(self):
        from unittest.mock import patch
        import groove_core
        p=self.f.add_mp3('Album','old.mp3','Wrong');a=self.album([p.parent]);self.releases([[['Correct']]]);a.title_match=self.match(a)
        actions,issues=plan_actions([a],{'folders':False});self.assertFalse(issues)
        original=groove_core.set_tags
        def interrupted(*args,**kwargs):
            original(*args,**kwargs);raise OSError('Interrupted after title write')
        with patch.object(groove_core,'set_tags',side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError,'some changes may have completed'):apply_actions(actions,self.f.root/'program',{})
        self.assertEqual(read_fields(p)['title'],'Correct')
        journal=next((self.f.root/'program/Logs').glob('Groove_Goblin_Undo_*.json'))
        self.assertFalse(undo_journal(journal));self.assertEqual(read_fields(p)['title'],'Wrong')


import os
import time
from unittest.mock import patch

@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Tk display required')
class TitleFlowTests(unittest.TestCase):
    edition_name='FULL'
    def setUp(self):
        from test_lite import LiteTests
        LiteTests.setUp(self)
    def tearDown(self):
        from test_lite import LiteTests
        LiteTests.tearDown(self)
    def wait(self):
        until=time.monotonic()+8
        while self.app.worker_busy and time.monotonic()<until:self.app.update();time.sleep(.01)
        self.app.update();self.assertFalse(self.app.worker_busy)

    def test_verify_preview_apply_and_undo_titles_in_mode(self):
        from groove_manual import read_track
        a=self.app;f=self.fixture;p=f.add_mp3('Album','old.mp3','Wrong');original=p.read_bytes()
        a.roots=[str(p.parent)];a.matched,_=scan_folders(a.roots);album=a.matched[0]
        a.album_map={album.uid:album};a.selected_id=album.uid;a.populate_albums()
        a.track_editor.records={str(p):read_track(p)};a.track_editor.refresh()
        result={'id':'group','artist':album.artist,'title':'Correct Album','year':'1998','score':99}
        def get(endpoint,params):
            if endpoint=='release/':return {'releases':[{'id':'release','status':'Official'}]}
            return {'media':[{'position':1,'tracks':[{'position':1,'title':'Correct Song'}]}]}
        with patch.object(a.mb,'suggest',return_value=(result,[result])),patch.object(a.mb,'get',side_effect=get):
            a.lookup_all();self.wait()
        self.assertFalse(album.approved);self.assertEqual(p.read_bytes(),original)
        self.assertEqual(album.title_match['titles'],{str(p):'Correct Song'})
        a.opt_filenames.set(True);a.approve_all();a.refresh_preview()
        action=a.actions[0];self.assertTrue(action['tracks'][0]['needs_title'])
        q=Path(action['dest_folder'])/action['tracks'][0]['new_name']
        if not a.is_lite:
            a.set_preview_filter('Tags')
            self.assertTrue(any('Correct Song' in str(row) for row in a.preview_tree.data.values()))
        with patch.object(self.module.messagebox,'askyesno',return_value=True) as confirm,patch.object(self.module.messagebox,'showinfo'):
            a.apply();self.wait()
            self.assertIn('Update 1 song-title tags',confirm.call_args.args[1])
            self.assertEqual(read_fields(q)['title'],'Correct Song');self.assertFalse(p.exists())
            self.assertEqual(a.track_editor.records[str(q)]['title'],'Correct Song')
            a.undo();self.wait()
        self.assertTrue(p.exists());self.assertEqual(read_fields(p)['title'],'Wrong')
        self.assertEqual(a.track_editor.records[str(p)]['title'],'Wrong')

    def test_manual_result_title_lookup_failure_and_stale_result_preserve_music(self):
        a=self.app;f=self.fixture;p=f.add_mp3('Album','old.mp3','Wrong');before=p.read_bytes()
        a.matched,_=scan_folders([p.parent]);album=a.matched[0];a.album_map={album.uid:album};a.selected_id=album.uid
        album.lookup_results=[{'id':'group','artist':album.artist,'title':'Correct Album','year':'1998'}]
        a.populate_albums();a.populate_results(album);a.results_tree.selection_set('0')
        with patch.object(a.mb,'get',side_effect=OSError('Offline test')):
            a.use_result();self.wait()
        self.assertTrue(album.approved);self.assertFalse(album.title_match['titles'])
        self.assertIn('lookup failed',album.title_match['note']);self.assertEqual(p.read_bytes(),before)
        a.var_album.set('Another Album');a.var_artist.set(album.artist);a.var_year.set('1998');a.save_match()
        self.assertFalse(album.mbid);self.assertFalse(album.title_match)
        a.queue.put(('title_match',album.uid,{'group_id':'group','album':'Correct Album','artist':album.artist,'titles':{str(p):'Wrong stale title'},'note':'Old response'}))
        a.poll_queue();self.assertFalse(album.title_match)
        self.assertFalse(a.actions[0]['tracks'][0]['needs_title'])
        # A failed title check must also be explained if folder/album tags
        # already match and there are no other changes to apply.
        a.opt_folders.set(False);a.opt_filenames.set(False)
        album.album=album.tracks[0].album;album.year=album.tracks[0].year;album.mbid='group'
        album.title_match={'group_id':'group','album':album.album,'artist':album.artist,'titles':{},'note':'Song titles unchanged: lookup failed.'}
        with patch.object(self.module.messagebox,'showinfo') as info:
            a.apply();self.assertIn('lookup failed',info.call_args.args[1])


class LiteTitleFlowTests(TitleFlowTests):edition_name='LITE'
class MobileTitleFlowTests(TitleFlowTests):edition_name='MOBILE'
