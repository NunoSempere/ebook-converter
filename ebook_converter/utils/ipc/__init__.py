import errno
import functools
import os
import sys
import threading

from ebook_converter import force_unicode
from ebook_converter.constants import filesystem_encoding
from ebook_converter.constants import get_windows_username
from ebook_converter.constants import islinux
from ebook_converter.constants import ispy3
from ebook_converter.constants import iswindows
from ebook_converter.utils.filenames import ascii_filename


__license__ = 'GPL v3'
__copyright__ = '2009, Kovid Goyal <kovid@kovidgoyal.net>'
__docformat__ = 'restructuredtext en'

VADDRESS = None


def eintr_retry_call(func, *args, **kwargs):
    while True:
        try:
            return func(*args, **kwargs)
        except EnvironmentError as e:
            if getattr(e, 'errno', None) == errno.EINTR:
                continue
            raise


@functools.lru_cache()
def socket_address(which):
    if iswindows:
        ans = r'\\.\pipe\Calibre' + which
        try:
            user = get_windows_username()
        except Exception:
            user = None
        if user:
            user = ascii_filename(user).replace(' ', '_')
            if user:
                ans += '-' + user[:100] + 'x'
    else:
        user = force_unicode(os.environ.get('USER') or os.path.basename(os.path.expanduser('~')), filesystem_encoding)
        sock_name = '{}-calibre-{}.socket'.format(ascii_filename(user).replace(' ', '_'), which)
        if islinux:
            ans = '\0' + sock_name
        else:
            from tempfile import gettempdir
            tmp = force_unicode(gettempdir(), filesystem_encoding)
            ans = os.path.join(tmp, sock_name)
    if not ispy3 and not isinstance(ans, bytes):
        ans = ans.encode(filesystem_encoding)
    return ans


def gui_socket_address():
    return socket_address('GUI' if iswindows else 'gui')


def viewer_socket_address():
    return socket_address('Viewer' if iswindows else 'viewer')


class RC(threading.Thread):

    def __init__(self, print_error=True, socket_address=None):
        self.print_error = print_error
        self.socket_address = socket_address or gui_socket_address()
        threading.Thread.__init__(self)
        self.conn = None
        self.daemon = True

    def run(self):
        from multiprocessing.connection import Client
        self.done = False
        try:
            self.conn = Client(self.socket_address)
            self.done = True
        except Exception:
            if self.print_error:
                print('Failed to connect to address {}', file=sys.stderr).format(repr(self.socket_address))
                import traceback
                traceback.print_exc()
