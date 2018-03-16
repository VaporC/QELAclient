import socket
import sys
import importlib
import os
import traceback

from PyQt5 import QtWidgets, QtGui, QtCore
from zipfile import ZipFile
from io import BytesIO

from dAwebAPI.WebAPI import WebAPI


#######################
# temporary fix: app crack doesnt through exception
# https://stackoverflow.com/questions/38020020/pyqt5-app-exits-on-error-where-pyqt4-app-would-not
sys.excepthook = lambda t, v, b: sys.__excepthook__(t, v, b)
#######################

# TODO: replace with final IP
HOST, PORT = '192.168.60.30', 443
HOST, PORT = socket.gethostbyname(socket.gethostname()), 443  # local


def getcwd():
    try:
        return sys._MEIPASS
    except AttributeError:
        return os.getcwd()


class _StartThread(QtCore.QThread):
    sigUpdate = QtCore.pyqtSignal(str)
    sigError = QtCore.pyqtSignal(str)
    sigDone = QtCore.pyqtSignal(object, object)

    def run(self):
        self.sigUpdate.emit('Connect to server')
        try:
            conn = WebAPI(HOST, PORT)
        except Exception as e:
            return self.sigError.emit(str(e))

        cl_path = os.path.join(getcwd(), 'client')

        def version():
            try:
                with open(os.path.join(cl_path, 'version.txt'), 'r') as f:
                    return f.read()
            except Exception:
                return ''

        def update(ver):
            self.sigUpdate.emit('Checking for updates')
            try:

                buffer = conn.getClient(ver)

                if buffer != b'0':
                    self.sigUpdate.emit('Unzip client')

                    with ZipFile(BytesIO(buffer)) as myzip:
                        myzip.extractall(cl_path)

                sys.path.insert(0, cl_path)
        #         os.chdir(cl_path)
                self.sigUpdate.emit('Starting...')

                client = importlib.import_module('client')
                client.__version__ = ver

                mod = importlib.import_module('Login')

                self.sigDone.emit(mod, conn)
            except Exception as e:
                return e

        err = update(version())
        if err:
            # could not start program with updating existing client folder
            # no try do receive full client in hope it will work now:
            traceback.print_exc()
            err = update('')
            if err:
                self.sigError.emit(str(err))


if __name__ == '__main__':
    ICON = os.path.join(getcwd(), 'client')
    ICON = os.path.join(ICON, 'media')
    ICON = os.path.join(ICON, 'logo.svg')

    app = QtWidgets.QApplication([])
    pixmap = QtGui.QPixmap(ICON)
    splash = QtWidgets.QSplashScreen(pixmap)
    splash.show()

    startthread = _StartThread()

    def fn(mod, conn):
        fn._l = mod.Login(conn)

    def fnError(errtxt):
        msg = QtWidgets.QMessageBox()
        txt = """Failed connecting to server.
Are you connected to the internet?
Please try again at a later time."""
        if errtxt:
            txt += '\n\n%s' % errtxt
        msg.setText(txt)
        msg.setIcon(QtWidgets.QMessageBox.Critical)
        msg.exec_()
        app.quit()

    startthread.sigDone.connect(fn)
    startthread.sigDone.connect(splash.close)
    startthread.sigUpdate.connect(splash.showMessage)
    startthread.sigError.connect(fnError)

    startthread.start()

    sys.exit(app.exec_())
