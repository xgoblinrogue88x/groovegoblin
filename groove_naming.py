"""Fixed, reviewable naming presets inspired by common music-library layouts."""
from string import Formatter

FILE_FORMATS = {
    '## - Artist - Title': '{track} - {artist} - {title}',
    '## - Title': '{track} - {title}',
    '## Title': '{track} {title}',
    'Artist - Title': '{artist} - {title}',
    'Title': '{title}',
    'Disc-## - Title': '{disc}-{track} - {title}',
    'Disc-## - Artist - Title': '{disc}-{track} - {artist} - {title}',
    'Artist - Album - ## - Title': '{artist} - {album} - {track} - {title}',
}
FOLDER_FORMATS = {
    'Artist - Album (Year)': '{artist} - {album} ({year})',
    'Artist - Album': '{artist} - {album}',
    'Artist - Year - Album': '{artist} - {year} - {album}',
    'Artist - (Year) Album': '{artist} - ({year}) {album}',
    'Album (Year)': '{album} ({year})',
    'Year - Album': '{year} - {album}',
    'Album': '{album}',
}
DEFAULT_FILE_FORMAT = next(iter(FILE_FORMATS))
DEFAULT_FOLDER_FORMAT = next(iter(FOLDER_FORMATS))


def render_preset(presets, name, values):
    if name not in presets:
        raise ValueError('Unknown naming format: '+str(name))
    template=presets[name]
    for _,field,_,_ in Formatter().parse(template):
        if field and not values.get(field):
            label={'track':'track number','disc':'disc number'}.get(field,field)
            raise ValueError('missing or invalid '+label+'; add that tag or choose another naming format')
    return template.format(**values)
