import struct
from netaddr import IPGlob, IPSet
from typing import Optional
from itertools import chain

size_pack = struct.Struct('!I')
assert size_pack.size == 4

MAX_ALLOWED_PACKET_SIZE = 8 * 1024 * 1024

def utf8text(maybe_bytes, errors='strict') -> Optional[str]:
    if maybe_bytes is None:
        return None
    if isinstance(maybe_bytes, str):
        return maybe_bytes
    return maybe_bytes.decode('utf-8', errors)



def proxy_list(human_readable):
    globs = []
    addrs = []
    for item in human_readable:
        if '*' in item or '-' in item:
            globs.append(IPGlob(item))
        else:
            addrs.append(item)
    return IPSet(chain(chain.from_iterable(globs), addrs))


class Disconnect(Exception):
    pass
