import os
from fancytools.os.PathStr import PathStr


PATH = PathStr.home().join('.dataArtist')


def isRunning():
    return not PATH.join('executable_path.txt').isfile()


def start():
    with open(PATH.join('executable_path.txt'), 'r') as f:
        txt = f.read()
    os.spawnl(os.P_NOWAIT, *eval(txt))


def importFile(path):
    if not isRunning():
        start()
    t = PATH.join('import_files.txt')
    with open(t, 'a') as f:
        f.write(path + '\n')


if __name__ == '__main__':
    path = r'C:\Users\serkgb\.dataArtistUploader\demo\local\A03\8A\5_th_Round_2.tiff'
    importFile(path)
