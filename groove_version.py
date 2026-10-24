"""One version string for the window, About, journals and network user agent."""
__version__ = '1.8'

MODE_LABELS = {'desktop':'Desktop Mode','lite':'LITE Mode','mobile':'Mobile Mode'}
MODE_EXECUTABLES = {mode:'Groove Goblin '+label+'.exe' for mode,label in MODE_LABELS.items()}
SUITE_EXECUTABLE = 'Launch Groove Goblin Suite.exe'


def initial_mode():
    import os
    from pathlib import Path
    import sys
    for mode in (*MODE_LABELS,'suite'):
        if '--'+mode in sys.argv:return mode
    if '--phone' in sys.argv:return 'mobile'
    if getattr(sys,'frozen',False):
        name=Path(sys.executable).name.casefold()
        for mode,filename in MODE_EXECUTABLES.items():
            if name==filename.casefold():return mode
        if name==SUITE_EXECUTABLE.casefold():return 'suite'
        if name=='groovegoblinmobile.exe':return 'mobile'  # Legacy launcher name.
        return 'desktop'
    return {'FULL':'desktop','DESKTOP':'desktop','LITE':'lite','MOBILE':'mobile'}.get(
        os.environ.get('GROOVE_GOBLIN_EDITION','FULL').upper(),'desktop')

def is_lite():
    """Both compact modes share the LITE organizer and apply confirmation."""
    return initial_mode() in ('lite','mobile')
