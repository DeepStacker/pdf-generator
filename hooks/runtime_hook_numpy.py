import os

_original_isdir = os.path.isdir


def _patched_isdir(path):
    if 'numpy' in path:
        for sentinel in ('/core/src', '/core/include', '/random/src', '/random/include'):
            if sentinel in path:
                return False
    return _original_isdir(path)


os.path.isdir = _patched_isdir
