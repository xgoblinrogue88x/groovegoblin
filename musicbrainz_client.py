"""MusicBrainz public API client. Standard-library HTTPS, throttled to 1 req/sec.
Online matching returns SUGGESTIONS and never writes files.
"""
import json,re,time,threading,urllib.parse,urllib.request,urllib.error
from collections import Counter
from groove_core import norm, year4

class MusicBrainz:
    def __init__(self):
        self.lock=threading.Lock();self.last_request=0
        self.cache={}
        self.agent='GrooveGoblin/1.0 (desktop music tagger; https://musicbrainz.org/doc/MusicBrainz_API)'

    def get(self,endpoint,params):
        url='https://musicbrainz.org/ws/2/'+endpoint+'?'+urllib.parse.urlencode({**params,'fmt':'json'})
        if url in self.cache:return self.cache[url]
        with self.lock:
            delay=1.1-(time.monotonic()-self.last_request)
            if delay>0:time.sleep(delay)
            self.last_request=time.monotonic()
            req=urllib.request.Request(url,headers={'User-Agent':self.agent,'Accept':'application/json'})
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(req,timeout=18) as r:
                        result=json.load(r)
                    self.cache[url]=result
                    return result
                except urllib.error.HTTPError as ex:
                    if ex.code not in (429,500,502,503) or attempt==2:raise
                    time.sleep(2+attempt*3);self.last_request=time.monotonic()

    @staticmethod
    def clean(q):
        # Escape Lucene punctuation within a quoted search phrase.
        return re.sub(r'([+\-&|!(){}\[\]^"~*?:\\/])',r'\\\1',str(q).strip())

    @staticmethod
    def result(r):
        ac=r.get('artist-credit',[])
        artist=''.join(part if isinstance(part,str) else part.get('name','') for part in ac).strip()
        return {'title':r.get('title',''), 'artist':artist,
                'year':year4(r.get('first-release-date','')),
                'id':r.get('id',''), 'type':r.get('primary-type',''),
                'score':int(r.get('score',0) or 0),'date':r.get('first-release-date','')}

    def search_albums(self,artist,title='',limit=20):
        if not artist and not title:return []
        parts=[]
        if artist:parts.append('artist:"'+self.clean(artist)+'"')
        if title:parts.append('releasegroup:"'+self.clean(title)+'"')
        data=self.get('release-group/',{'query':' AND '.join(parts),'limit':min(100,limit)})
        return [self.result(r) for r in data.get('release-groups',[])]

    def recording_candidates(self,artist,titles):
        scores=Counter(); details={}
        picks=[];seen=set()
        for title in titles:
            if norm(title) and norm(title) not in seen:
                picks.append(title);seen.add(norm(title))
            if len(picks)>=3:break
        for title in picks:
            term='recording:"'+self.clean(title)+'" AND artist:"'+self.clean(artist)+'"'
            data=self.get('recording/',{'query':term,'limit':15})
            matching=set()
            for rec in data.get('recordings',[]):
                if norm(rec.get('title'))!=norm(title):continue
                for rel in rec.get('releases',[]):
                    group=rel.get('release-group') or {}
                    rid=group.get('id')
                    if not rid:continue
                    matching.add(rid)
                    if rid not in details:
                        details[rid]={'id':rid,'title':group.get('title') or rel.get('title',''),
                                      'artist':artist,'year':year4(group.get('first-release-date','')),
                                      'date':group.get('first-release-date',''),
                                      'type':group.get('primary-type',''), 'score':0}
            for k in matching:scores[k]+=1
        results=[]
        for rid,num in scores.most_common(16):
            item=details[rid].copy();item['hits']=num;item['tested']=len(picks);item['score']=int(100*num/max(1,len(picks)))
            results.append(item)
        return results

    def album_track_match(self,groupid,titles):
        """Verify against an official release's tracklist when available."""
        if not groupid:return None
        data=self.get('release/',{'release-group':groupid,'limit':12})
        releases=sorted(data.get('releases',[]),key=lambda x:(x.get('status')!='Official',x.get('date') or '9999'))
        want={norm(t) for t in titles if norm(t)}
        if not want:return None
        best=0.0
        for r in releases[:4]:
            if not r.get('id'):continue
            d=self.get('release/'+r['id'],{'inc':'recordings'})
            actual=set()
            for medium in d.get('media',[]):
                for track in medium.get('tracks',[]):
                    actual.add(norm(track.get('title') or track.get('recording',{}).get('title')))
            best=max(best,len(want & actual)/len(want))
            if best>=0.94:break
        return best

    def suggest(self,album):
        """Guess conservatively from existing tags or recordings, always requires review unless verified."""
        if not album.artist:return None,[]
        titles=[t.title for t in sorted(album.tracks,key=lambda x:(x.number or 999,x.path))]
        old=album.album if album.album and norm(album.album) not in ('thecollection','collection','thecollectionii','greatesthits','unknownalbum') else ''
        if old:
            results=self.search_albums(album.artist,old,limit=12)
            exact=[r for r in results if norm(r['title'])==norm(old) and norm(r['artist'])==norm(album.artist)]
            if exact:
                top=exact[0];top['score']=95
                return top,results
            if results:
                return None,results
        candidates=self.recording_candidates(album.artist,titles)
        candidates=sorted(candidates,key=lambda r:(-r['score'],r.get('type')!='Album',not r.get('year')))
        if not candidates:return None,[]
        top=candidates[0]
        if top.get('hits',0)>=2 and top.get('score',0)>=67 and top.get('year'):
            # Tracklist cross-validation catches compilations that happen to share songs.
            similarity=self.album_track_match(top['id'],titles)
            if similarity is not None and similarity>=0.75:
                top['score']=int(100*similarity)
                top['verified_tracks']=round(similarity,2)
                return top,candidates
        return None,candidates
