import os
import sys

_base = os.path.join(os.path.dirname(__file__), '..', '..', 'Convertor pdf', 'tools')
if os.path.isdir(_base):
    if _base not in sys.path:
        sys.path.insert(0, _base)
    if _base not in __path__:
        __path__.append(_base)
