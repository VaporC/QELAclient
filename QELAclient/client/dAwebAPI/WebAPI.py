import ssl
import socket
import builtins
from queue import Queue

from PyQt5 import QtCore  # TODO: replace with normal thread
from inspect import Signature, Parameter

from dAwebAPI.parseArgStr import applyTyp
# that's a soft link pointing to fancytools.os.PathStr:
from dAwebAPI.PathStr import PathStr


class _UploadThread(QtCore.QThread):
    sigUpdate = QtCore.pyqtSignal(int, int)
    sigDone = QtCore.pyqtSignal()

    def __init__(self, conn, paths, new_paths, fnUpdate, fnDone):
        super().__init__()
        self.conn = conn
        self.paths = paths
        if new_paths is None:
            new_paths = paths
        self.new_paths = new_paths

        self.active = True
        if fnUpdate:
            self.sigUpdate.connect(fnUpdate)
        if fnDone:
            self.sigDone.connect(fnDone)

    def run(self):
        for index, (p, npath) in enumerate(zip(self.paths, self.new_paths)):
            p = PathStr(p)
            self.conn.send(str('upload(%s,%s)' % (p.size(), npath)).encode())

            answer = self.conn.recv(1024).decode()
            if answer == 'OK':
                with open(p, 'rb') as f:

                    data = f.read()
                    self.conn.send(data)
                    while True:
                        answer = self.conn.recv(1024).decode()
                        if answer == 'DONE':
                            break

                        self.sigUpdate.emit(index, int(answer[:-2]))
            else:
                print('Received from server: ' + answer)
            if not self.active:
                break
        self.sigDone.emit()


def _totyp(ss):
    return getattr(builtins, ss, ss)


def signatureFromStr(args, ret):
    return_annotation = _totyp(ret) if ret else Signature.empty
    X = Parameter.POSITIONAL_OR_KEYWORD
    params = []
    for pi in args.split(', '):

        ss = pi.split(':')
        if len(ss) == 2:
            # param has type hint
            P = Parameter(ss[0], X, annotation=_totyp(ss[1]))
        else:
            ss = pi.split('=')
            if len(ss) == 2:
                # param has default value
                P = Parameter(ss[0], X, default=ss[1])
            elif len(ss[0]):
                P = Parameter(ss[0], X)

            else:
                continue
        params.append(P)
    return Signature(parameters=params,
                     return_annotation=return_annotation)


class WebAPI(QtCore.QObject):
    sigError = QtCore.pyqtSignal(bytes)

    def __init__(self, IPOrSocket, port=443):
        super(). __init__()
        self._isready = True
        self._q = Queue()
        self._q.put(1)
        if isinstance(IPOrSocket, ssl.SSLSocket):
            self.conn = IPOrSocket
        else:
            self.conn = self._connection(IPOrSocket, port)

        # temporarily overrides self._format, because it refers to self._api:
        self._api = {}
        # sync buffs with server - this is an essential thep when receiving
        # bicker packages:
        self._buffsize = 4096
        # need to pre-define types, so __getAttr_ + _format works:
        self._api['buffSize'] = signatureFromStr('', 'int'), ''
        self._api['api_json'] = signatureFromStr('', 'json'), ''

        self._buffsize = self.buffSize()
        self._api = self.api_json()

        for key, (args, ret,  doc) in self._api.items():
            self._api[key] = signatureFromStr(args, ret), doc

    def help(self):
        return self.api_md()

    def __dir__(self):
        return list(self._api.keys())

    @staticmethod
    def _connection(HOST, PORT):
        sock = socket.socket(socket.AF_INET)

        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1  # optional

        ###################################################################
        # FIXME: as long as the server certificate is self-signed and not added to a
        # certificate authority, disable trust check:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        ###################################################################
        conn = context.wrap_socket(sock, server_hostname=HOST)

        # raise socket.timeout, if nothing comes after X sec
        conn.setblocking(False)
        conn.settimeout(10)  # max wait time= 10 sec

        conn.connect((HOST, PORT))
        return conn

    @staticmethod
    def _buildCmd(fn, args):
        cmd = fn
        if args is not None:
            cmd += '(%s)' % ','.join([str(a) for a in args])
        return cmd

    def _format(self, fn, out):
        if callable(fn):
            sig = fn.__signature__
        else:
            try:
                sig = self._api[fn][0]
            except KeyError:
                return out
        ret = sig.return_annotation
        if ret is not Signature.empty:
            try:
                return applyTyp(out, ret)
            except Exception:
                print('ERROR formating output [%s] to type [%s]' % (
                    out[:100], ret))
        return out

    def __getattr__(self, request):
        # translate all (undefined) method calls into send commands following
        # 'METHOD(ARG1, ARG2)'
        try:
            sig, doc = self._api[request]
        except KeyError:
            raise AttributeError()
        else:
            def fn(*args):
                request = self._buildCmd(fn.request, args)
                self._q.get()
                self.conn.send(request.encode())
                # only receive answer if a receive type is given:
                if fn.__signature__.return_annotation is not Signature.empty:
                    answer = self._format(fn, self._recv())
                else:
                    answer = None
                self._q.put(1)
                return answer
            fn.request = request
            fn.__doc__ = doc
            fn.__signature__ = sig
            return fn

    def close(self):
        self._recv()
        self.sock.close()

    def _recv(self):
        out = None
        try:
            out = self.conn.recv(self._buffsize)
            if out[0:1] == b'%':
                n_recv = int.from_bytes(out[1:3], 'big')
                out = bytearray(out[3:])
                for _ in range(n_recv):
                    answer = self.conn.recv(self._buffsize)  # .decode()
                    out.extend(answer)
        except Exception:
            if out is None:
                raise
            if isinstance(out, bytearray):
                out = bytes(out)
            self.sigError.emit(out)
        return out

    def upload(self, paths, new_paths=None, fnUpdate=None, fnDone=None):
        self._t = _UploadThread(self.conn, paths, new_paths, fnUpdate, fnDone)
        self._isready = False
        self._t.sigDone.connect(lambda: setattr(self, '_isready', True))
        self._t.start()

    def isReady(self):
        return not self._q.empty() and self._isready

    def download(self, serverpath, localpath):
        self._q.get()

        c = 0
        self.conn.send(str('download(%s)' % serverpath).encode())
        answer = self._recv()
        if answer[:2] == 'OK':
            fsize = int(answer[2:])
            nn = PathStr(serverpath).splitNames()
            # ensure file path exists:
            PathStr(localpath).mkdir(*nn[:-1])
#             nn = PathStr(localpath).dirname().mkdir()
            localpath = localpath.join(serverpath)
            with open(localpath, 'wb') as f:
                while True:
                    data = self.conn.recv(self._buffsize)
                    f.write(data)
                    c += self._buffsize
                    if c >= fsize:
                        break
        else:
            print('error', 22334554, answer)
        self._q.put(1)

    def cancelUpload(self):
        self._t.active = False

    @property
    def address(self):
        '''returns host IP and port'''
        return self.conn.getpeername()


if __name__ == '__main__':
    # try to connect to local server
    # TODO: provide accessible test server
    HOST, PORT = socket.gethostbyname(socket.gethostname()), 443  # local
    S = WebAPI(HOST, PORT)
    print(dir(S))
    print(S.user.__doc__)
    print(S.help())
