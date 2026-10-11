"""Manual metadata/cover edits use disposable media and full-byte undo checks."""
import json
from pathlib import Path
from unittest.mock import patch
import unittest
from PIL import Image
from mutagen.flac import FLAC,Picture
from mutagen.id3 import ID3,APIC,TXXX
from groove_manual import read_track,plan_manual,apply_manual,digest,load_artwork
from groove_core import undo_journal,newest_journal


class ManualEditTests(unittest.TestCase):
    def setUp(self):
        from test_groove import GrooveTests
        self.f=GrooveTests();self.f.setUp();self.addCleanup(self.f.tearDown)
        self.fl=self.f.add_flac('FLAC','old.flac','Original')
        self.mp=self.f.add_mp3('MP3','old.mp3','Original')
        self.base=self.f.root/'program'
        self.image=self.f.root/'new.png';Image.new('RGB',(24,24),'red').save(self.image)
        pic=Picture();pic.type=4;pic.mime='image/png';pic.desc='Back cover';pic.data=self.image.read_bytes()
        tags=FLAC(self.fl);tags.add_picture(pic);tags['replaygain_track_gain']='-4 dB';tags.save()
        id3=ID3(self.mp);id3.add(APIC(type=4,mime='image/png',desc='Front cover',data=pic.data))
        id3.add(TXXX(desc='KEEP',text=['Untouched']));id3.save(self.mp)
        self.records={str(p):read_track(p) for p in (self.fl,self.mp)}
        self.before={p:digest(p) for p in (self.fl,self.mp)}

    def plans(self,pending):
        plans,issues=plan_manual(self.records,pending);self.assertFalse(issues,issues);return plans

    def test_batch_all_fields_and_artwork_preserves_unrelated_tags_and_exact_undo(self):
        art=load_artwork(self.image)
        edits={'title':'New title','artist':'Track artist','albumartist':'Album artist',
               'album':'New album','track':'03/12','disc':'2/3','year':'1997','artwork':art}
        pending={str(p):{**edits,'filename':'new'+p.suffix} for p in (self.fl,self.mp)}
        plans=self.plans(pending)
        for p,hashed in self.before.items():self.assertEqual(digest(p),hashed)
        journal=apply_manual(plans,self.base)
        for original in (self.fl,self.mp):
            path=original.with_name('new'+original.suffix)
            data=read_track(path)
            for key,value in edits.items():
                if key!='artwork':self.assertEqual(data[key],value)
            self.assertEqual(data['front_cover_count'],1);self.assertEqual(data['artwork_count'],2)
            self.assertFalse(original.exists())
        self.assertEqual(FLAC(self.fl.with_name('new.flac'))['replaygain_track_gain'],['-4 dB'])
        self.assertEqual(str(ID3(self.mp.with_name('new.mp3'))['TXXX:KEEP']),'Untouched')
        self.assertFalse(undo_journal(journal))
        for p,hashed in self.before.items():self.assertEqual(digest(p),hashed)

    def test_filename_only_rename_is_byte_identical_and_collision_is_blocked(self):
        pending={str(self.mp):{'filename':'Renamed'}}
        plans=self.plans(pending)
        target=self.mp.with_name('Renamed.mp3');target.write_bytes(b'existing')
        with self.assertRaisesRegex(ValueError,'already exists'):apply_manual(plans,self.base)
        self.assertEqual(target.read_bytes(),b'existing');self.assertEqual(digest(self.mp),self.before[self.mp])
        target.unlink();journal=apply_manual(plans,self.base)
        self.assertEqual(digest(target),self.before[self.mp])
        self.assertFalse(undo_journal(journal));self.assertEqual(digest(self.mp),self.before[self.mp])

    def test_stale_file_and_duplicate_batch_names_are_blocked_before_mutation(self):
        plans=self.plans({str(self.fl):{'title':'Changed'}})
        tags=FLAC(self.fl);tags['comment']='External edit';tags.save()
        with self.assertRaisesRegex(ValueError,'changed'):apply_manual(plans,self.base)
        self.assertEqual(FLAC(self.fl)['comment'],['External edit'])
        other=self.f.add_mp3('MP3','other.mp3','Other')
        self.records[str(other)]=read_track(other)
        plans,issues=plan_manual(self.records,{str(self.mp):{'filename':'same.mp3'},str(other):{'filename':'SAME.mp3'}})
        self.assertTrue(issues);self.assertIn('Duplicate output',issues[0])

    def test_partial_failure_undo_restores_completed_track_exactly(self):
        plans=self.plans({str(self.fl):{'title':'A'},str(self.mp):{'title':'B'}})
        from groove_manual import write_tags
        calls=[0]
        def fail_second(*args):
            calls[0]+=1
            if calls[0]==2:raise OSError('simulated save failure')
            return write_tags(*args)
        with patch('groove_manual.write_tags',side_effect=fail_second):
            with self.assertRaisesRegex(RuntimeError,'Manual save stopped'):apply_manual(plans,self.base)
        journal=newest_journal(self.base);self.assertEqual(json.loads(Path(journal).read_text())['state'],'partial_error')
        self.assertFalse(undo_journal(journal))
        for p,hashed in self.before.items():self.assertEqual(digest(p),hashed)

    def test_undo_refuses_to_overwrite_subsequent_external_edit(self):
        journal=apply_manual(self.plans({str(self.fl):{'title':'New'}}),self.base)
        tags=FLAC(self.fl);tags['title']='External';tags.save()
        issues=undo_journal(journal);self.assertTrue(issues)
        self.assertIn('changed after saving',issues[0]);self.assertEqual(FLAC(self.fl)['title'],['External'])

    def test_front_cover_removal_keeps_back_cover_and_other_fields(self):
        art=load_artwork(self.image)
        first=apply_manual(self.plans({str(self.mp):{'artwork':art}}),self.base)
        self.records[str(self.mp)]=read_track(self.mp)
        journal=apply_manual(self.plans({str(self.mp):{'artwork':None}}),self.base)
        data=read_track(self.mp);self.assertEqual(data['front_cover_count'],0);self.assertEqual(data['artwork_count'],1)
        self.assertEqual(data['title'],'Original')
        self.assertFalse(undo_journal(journal));self.assertEqual(read_track(self.mp)['front_cover_count'],1)
        self.assertFalse(undo_journal(first));self.assertEqual(digest(self.mp),self.before[self.mp])
