"""One version string for the window, About, journals and network user agent."""
__version__ = '1.3.6'

def is_lite():
    import os
    return os.environ.get('GROOVE_GOBLIN_EDITION','LITE').upper()=='LITE'
