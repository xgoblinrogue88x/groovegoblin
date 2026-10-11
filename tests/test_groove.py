import unittest,tempfile,sys,subprocess,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mutagen.flac import FLAC
from mutagen.id3 import ID3, TIT2,TPE1,TALB,TDRC,TRCK,COMM,APIC
from groove_core import scan_folders,plan_actions,apply_actions,undo_journal,inspect_track,preflight
from musicbrainz_client import MusicBrainz

class GrooveTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  (self.root/'.fixtures').mkdir();self.masterflac=self.root/'.fixtures/master.flac';self.mastermp3=self.root/'.fixtures/master.mp3'
  for dest,codec in [(self.masterflac,'flac'),(self.mastermp3,'libmp3lame')]:
   cmd=['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i','sine=frequency=500:duration=0.2','-ac','2','-c:a',codec,'-y',str(dest)]
   subprocess.run(cmd,check=True)
 def tearDown(self):self.tmp.cleanup()
 def add_flac(self,dirname,filename,title,album='The Collection',year='2015',trackno='1'):
  dest=self.root/dirname;dest.mkdir(parents=True,exist_ok=True)
  p=dest/filename;p.write_bytes(self.masterflac.read_bytes());f=FLAC(p)
  f['artist']='Van Halen';f['albumartist']='Van Halen';f['album']=album;f['date']=year
  f['title']=title;f['tracknumber']=trackno;f['comment']='DO NOT TOUCH';f.save()
  return p
 def add_mp3(self,dirname,filename,title,artist='Other Artist',album='Bad Album',year='2025'):
  dest=self.root/dirname;dest.mkdir(parents=True,exist_ok=True)
  p=dest/filename;p.write_bytes(self.mastermp3.read_bytes());d=ID3()
  for c,val in [(TIT2,title),(TPE1,artist),(TALB,album),(TDRC,year),(TRCK,'1')]:d.add(c(encoding=3,text=[val]))
  d.add(COMM(encoding=3,lang='eng',desc='note',text=['DO NOT TOUCH']));d.save(p)
  return p
 def test_mixed_scan_apply_undo(self):
  fl=self.add_flac('Van Halen - The Collection/Disc 4','05 - Unchained.flac','Unchained','The Collection','2015','5')
  fl2=self.add_flac('Van Halen - The Collection/Disc 4','01 - Mean Street.flac','Mean Street','The Collection','2015','1')
  mp=self.add_mp3('Other Artist/Disc 1','01 - Song.mp3','Song')
  albums,errors=scan_folders([self.root]);self.assertFalse(errors);self.assertEqual(len(albums),2)
  vh=[a for a in albums if a.artist=='Van Halen'][0];self.assertEqual(vh.album,'Fair Warning');self.assertEqual(vh.year,'1981');self.assertTrue(vh.approved)
  other=[a for a in albums if a.artist=='Other Artist'][0];other.album='Correct Album';other.year='1997';other.approved=True
  actions,problems=plan_actions(albums,{'tags':True,'folders':True,'filenames':False});self.assertFalse(problems);self.assertEqual(len(actions),2)
  old_comment=FLAC(fl)['comment']
  journal=apply_actions(actions,self.root/'program',{'tags':True,'folders':True,'filenames':False})
  vh_new=fl.parent.with_name('Van Halen - Fair Warning (1981)')/'05 - Unchained.flac'
  self.assertTrue(vh_new.exists());self.assertEqual(FLAC(vh_new)['album'],['Fair Warning']);self.assertEqual(FLAC(vh_new)['date'],['1981']);self.assertEqual(FLAC(vh_new)['comment'],old_comment)
  mp_new=mp.parent.with_name('Other Artist - Correct Album (1997)')/mp.name
  self.assertTrue(mp_new.exists());self.assertEqual(str(ID3(mp_new)['TALB']), 'Correct Album')
  self.assertTrue(ID3(mp_new).getall('COMM'))
  errs=undo_journal(journal);self.assertFalse(errs,errs);self.assertTrue(fl.exists());self.assertTrue(mp.exists())
  self.assertEqual(FLAC(fl)['album'],['The Collection']);self.assertEqual(FLAC(fl)['date'],['2015'])
  self.assertEqual(str(ID3(mp)['TALB']),'Bad Album');self.assertEqual(str(ID3(mp)['TDRC']),'2025')
 def test_collision(self):
  p=self.add_mp3('An Album','track.mp3','Good Track',artist='AAA',album='Old',year='2000')
  (self.root/'AAA - New (1980)').mkdir()
  albums,_=scan_folders([self.root]); a=albums[0];a.album='New';a.year='1980';a.approved=True
  actions,problems=plan_actions(albums,{'tags':True,'folders':True,'filenames':False});self.assertTrue(problems);self.assertFalse(actions)
 def test_stale_file_protected(self):
  p=self.add_flac('Van Halen - The Collection/Disc 4','05 - Unchained.flac','Unchained')
  albums,_=scan_folders([self.root]);a=albums[0];a.album='Fair Warning';a.year='1981';a.approved=True
  actions,problems=plan_actions(albums,{'tags':True,'folders':False,'filenames':False});self.assertFalse(problems)
  f=FLAC(p);f['album']='Someone Edited This';f.save()
  self.assertTrue(preflight(actions))
 def test_same_size_edit_with_original_timestamp_is_still_stale(self):
  import os
  from groove_core import file_signature
  p=self.add_flac('Album','track.flac','Track')
  albums,_=scan_folders([self.root]);a=albums[0];a.album='Correct Album';a.year='1981';a.approved=True
  actions,problems=plan_actions(albums,{'tags':True,'folders':False,'filenames':False});self.assertFalse(problems)
  before=p.stat();original=file_signature(p)
  raw=bytearray(p.read_bytes());raw[-1]^=1;p.write_bytes(raw)
  os.utime(p,ns=(before.st_atime_ns,before.st_mtime_ns))
  self.assertEqual(file_signature(p)[:2],original[:2])
  self.assertNotEqual(file_signature(p),original)
  self.assertTrue(preflight(actions))
 def test_filename_apply_undo(self):
  p=self.add_mp3('Music','dirty filename.mp3','Purple Song',artist='Purple Person',album='Purple Era')
  albums,_=scan_folders([self.root]);a=albums[0];a.album='Purple Era';a.year='1989';a.approved=True
  actions,problems=plan_actions(albums,{'tags':True,'folders':False,'filenames':True});self.assertFalse(problems)
  journal=apply_actions(actions,self.root/'program',{'tags':True,'folders':False,'filenames':True})
  q=p.with_name('01 - Purple Person - Purple Song.mp3');self.assertTrue(q.exists());self.assertFalse(p.exists())
  self.assertFalse(undo_journal(journal));self.assertTrue(p.exists())
 def test_manual_search_mock(self):
  mb=MusicBrainz()
  mb.get=lambda endpoint,params:{'release-groups':[{'id':'123','title':'1984','first-release-date':'1984-01-09','artist-credit':[{'name':'Van Halen'}], 'primary-type':'Album','score':99}]}
  results=mb.search_albums('Van Halen','1984');self.assertEqual(results[0]['year'],'1984');self.assertEqual(results[0]['artist'],'Van Halen')

if __name__=='__main__':unittest.main(verbosity=2)
