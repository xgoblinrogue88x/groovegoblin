"""MusicBrainz public API client. Standard-library HTTPS, throttled to 1 req/sec.
Online matching returns SUGGESTIONS and never writes files.
"""
import json,re,time,threading,unicodedata,urllib.parse,urllib.request,urllib.error
from collections import Counter
from groove_core import norm, year4
from groove_version import __version__

class MusicBrainz:
    def __init__(self):
        self.lock=threading.Lock();self.last_request=0
        self.cache={}
        self.agent=f'GrooveGoblin/{__version__} (desktop music tagger; https://musicbrainz.org/doc/MusicBrainz_API)'

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

    def track_title_match(self,album,result,cancel=None):
        """Read-only title proposals; never pair files by their display order.

        Release groups contain multiple editions. Match unique song names or
        numbered positions, complete discs (or explicit file selections), and
        require consensus between matching
        editions unless existing song titles clearly identify one tracklist.
        """
        match={'group_id':result.get('id',''),'album':result.get('title',''),
               'artist':result.get('artist') or album.artist,'titles':{},'note':''}
        def unchanged(reason):
            match['note']='Song titles unchanged: '+reason
            return match
        if not match['group_id']:return unchanged('no MusicBrainz release selected.')
        if cancel and cancel.is_set():return unchanged('verification canceled.')
        data=self.get('release/',{'release-group':match['group_id'],'limit':12})
        releases=sorted((r for r in data.get('releases',[]) if r.get('status')=='Official' and r.get('id')),
                        key=lambda r:r.get('date') or '9999')[:4]
        def key(text):
            return ''.join(c for c in unicodedata.normalize('NFKC',str(text)).casefold() if c.isalnum())
        candidates=[]
        for release in releases:
            if cancel and cancel.is_set():return unchanged('verification canceled.')
            details=self.get('release/'+release['id'],{'inc':'recordings+artist-credits'})
            media=details.get('media',[]);positions={};credits={};counts=Counter();valid=True
            for medium in media:
                disc=medium.get('position')
                if not isinstance(disc,int) or disc<1:valid=False;break
                for track in medium.get('tracks',[]):
                    number=track.get('position');title=track.get('title') or track.get('recording',{}).get('title')
                    if (not isinstance(number,int) or number<1 or not isinstance(title,str)
                        or not title.strip() or any(ord(c)<32 for c in title) or (disc,number) in positions):
                        valid=False;break
                    positions[disc,number]=title.strip();counts[disc]+=1
                    ac=track.get('artist-credit') or track.get('recording',{}).get('artist-credit',[])
                    credit=''.join(part if isinstance(part,str) else (part.get('name') or part.get('artist',{}).get('name',''))+part.get('joinphrase','') for part in ac).strip()
                    if credit:credits[disc,number]=credit
            if not valid or not positions:continue
            # Missing disc tags are safe only for a single-disc release.
            if len(counts)>1 and any(not t.disc for t in album.tracks):continue
            sole_disc=next(iter(counts)) if len(counts)==1 else None
            # A box-set disc can become a single-disc album without rewriting
            # its disc tag (e.g. Collection disc 4 -> Fair Warning disc 1).
            if sole_disc and len({t.disc for t in album.tracks if t.disc})>1:continue
            local=[]
            for t in album.tracks:
                hits=[p for p,title in positions.items() if key(t.title) and key(title)==key(t.title)
                      and (sole_disc or not t.disc or p[0]==t.disc)]
                local.append(hits[0] if len(hits)==1 else (sole_disc or t.disc,t.number))
            if len(set(local))!=len(local) or any(p not in positions for p in local):continue
            if not album.partial_selection and any(count!=counts[disc] for disc,count in Counter(d for d,n in local).items()):continue
            titles={t.path:positions[p] for t,p in zip(album.tracks,local)}
            score=sum(bool(key(t.title)) and key(t.title)==key(titles[t.path]) for t in album.tracks)
            numbers={t.path:str(p[1]) for t,p in zip(album.tracks,local)}
            artists={t.path:credits[p] for t,p in zip(album.tracks,local) if p in credits}
            candidates.append((score,release['id'],titles,numbers,artists))
        if not candidates:return unchanged('track numbers are missing or no release fits the songs, disc/track numbers and track counts; review in Track Editor.')
        variants={(tuple(sorted(titles.items())),tuple(sorted(numbers.items()))) for score,rid,titles,numbers,artists in candidates}
        if len(variants)>1:
            best=max(score for score,rid,titles,numbers,artists in candidates)
            candidates=[c for c in candidates if c[0]==best]
            if best<max(2,(len(album.tracks)+1)//2) or len({(tuple(sorted(c[2].items())),tuple(sorted(c[3].items()))) for c in candidates})>1:
                return unchanged('release editions disagree on song names; review in Track Editor.')
        match['titles']=candidates[0][2];match['numbers']=candidates[0][3];match['artists']={p:v for p,v in candidates[0][4].items() if all(c[4].get(p)==v for c in candidates)};match['release_id']=candidates[0][1]
        match['note']=f'Song titles matched for {len(match["titles"])} tracks using disc/track numbers.'
        return match

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
