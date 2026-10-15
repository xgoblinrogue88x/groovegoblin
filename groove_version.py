"""One version string for the window, About, journals and network user agent."""
__version__ = '1.5'

def is_lite():
    """Internal compatibility name for the Mobile Remote controller layout."""
    import os
    import sys
    if '--mobile' in sys.argv or '--phone' in sys.argv:return True
    if '--desktop' in sys.argv:return False
    return os.environ.get('GROOVE_GOBLIN_EDITION','FULL').upper() in ('MOBILE','LITE')
