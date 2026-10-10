"""Optional verified offline mappings for legacy Van Halen The Collection box sets."""
import re
import unicodedata
DATA = {'I': [('Van Halen', '1978', ['Runnin With the Devil', 'Eruption', 'You Really Got Me', 'Aint Talkin Bout Love', 'Im the One', 'Jamies Cryin', 'Atomic Punk', 'Feel Your Love Tonight', 'Little Dreamer', 'Ice Cream Man', 'On Fire']), ('Van Halen II', '1979', ['Youre No Good', 'Dance the Night Away', 'Somebody Get Me a Doctor', 'Bottoms Up', 'Outta Love Again', 'Light Up the Sky', 'Spanish Fly', 'D.O.A.', 'Women in Love', 'Beautiful Girls']), ('Women and Children First', '1980', ['And the Cradle Will Rock', 'Everybody Wants Some', 'Fools', 'Romeo Delight', 'Tora Tora', 'Loss of Control', 'Take Your Whiskey Home', 'Could This Be Magic', 'In a Simple Rhyme']), ('Fair Warning', '1981', ['Mean Street', 'Dirty Movies', 'Sinners Swing', 'Hear About It Later', 'Unchained', 'Push Comes to Shove', 'So This Is Love', 'Sunday Afternoon in the Park', 'One Foot Out the Door']), ('Diver Down', '1982', ['Where Have All the Good Times Gone', 'Hang Em High', 'Cathedral', 'Secrets', 'Intruder', 'Oh Pretty Woman', 'Dancing in the Street', 'Little Guitars Intro', 'Little Guitars', 'Big Bad Bill Is Sweet William Now', 'The Full Bug', 'Happy Trails']), ('1984', '1984', ['1984', 'Jump', 'Panama', 'Top Jimmy', 'Drop Dead Legs', 'Hot for Teacher', 'Ill Wait', 'Girl Gone Bad', 'House of Pain']), ('Best Of - Volume I', '1996', ['Cant Get This Stuff No More', 'Me Wise Magic']), ('Tokyo Dome Live in Concert', '2015', ['Unchained', 'Runnin With the Devil', 'Shes the Woman', 'Im the One', 'Tattoo', 'Everybody Wants Some', 'Somebody Get Me a Doctor', 'China Town', 'Hear About It Later', 'Oh Pretty Woman', 'Drum Struck', 'You Really Got Me', 'Dance the Night Away', 'Ill Wait', 'And the Cradle Will Rock', 'Hot for Teacher', 'Women in Love', 'Romeo Delight', 'Mean Street', 'Beautiful Girls', 'Ice Cream Man', 'Panama', 'Eruption', 'Aint Talkin Bout Love', 'Jump'])], 'II': [('5150', '1986', ['Good Enough', 'Why Cant This Be Love', 'Get Up', 'Dreams', 'Summer Nights', 'Best Of Both Worlds', 'Love Walks In', '5150', 'Inside']), ('OU812', '1988', ['Mine All Mine', 'When Its Love', 'AFU Naturally Wired', 'Cabo Wabo', 'Source of Infection', 'Feels So Good', 'Finish What Ya Started', 'Black and Blue', 'Sucker in a 3 Piece']), ('For Unlawful Carnal Knowledge', '1991', ['Poundcake', 'Judgement Day', 'Spanked', 'Runaround', 'Pleasure Dome', 'In N Out', 'Man on a Mission', 'The Dream Is Over', 'Right Now', '316', 'Top of the World']), ('Balance', '1995', ['The Seventh Seal', 'Cant Stop Lovin You', 'Dont Tell Me What Love Can Do', 'Amsterdam', 'Big Fat Money', 'Doin Time', 'Aftershock', 'Strung Out', 'Not Enough', 'Take Me Back Deja Vu', 'Feelin']), ('Studio Rarities 1989-2004', '2023', ['A Apolitical Blues', 'Crossing Over', 'Baluchitherium', 'Humans Being', 'Respect the Wind', 'Its About Time', 'Up for Breakfast', 'Learning to See'])]}

def normalize(value):
    value = unicodedata.normalize('NFKD', str(value or '').casefold())
    return ''.join(c for c in value if c.isascii() and c.isalnum())

def match(folder, artist, album, track_titles, disc_numbers):
    if normalize(artist) != 'vanhalen':
        return None
    context = str(folder).lower().replace('_',' ').replace('-',' ')
    context = context + ' ' + str(album).lower()
    coll = 'II' if re.search(r'collection\s*(ii|2)\b',context) else ('I' if 'collection' in context else None)
    if not coll:
        return None
    nums = [x for x in disc_numbers if x is not None]
    disc = nums[0] if nums and len(set(nums))==1 else None
    if disc is None:
        m = re.search(r'(?i)(?:disc|disk|cd)\s*0?(\d{1,2})', str(folder).split('/')[-1].split('\\')[-1])
        if m: disc = int(m.group(1))
    if not disc or not 1 <= disc <= len(DATA[coll]):
        return None
    title,year,expected = DATA[coll][disc-1]
    have = {normalize(x) for x in track_titles if x}
    known = {normalize(x) for x in expected}
    fraction = len(have & known)/max(1,len(have))
    if fraction < 0.70:
        return None
    return {'album': title, 'year': year, 'confidence': 0.99, 'source': 'Verified Van Halen collection map'}
