# -*- mode: python -*-
import time
global pkg_dir
pkg_dir = os.path.dirname(os.path.abspath(os.curdir))


def addDataFiles():
    import os
    extraDatas = []
    dirs = [
        ('client', os.path.join(
            pkg_dir, 'QELAclient', 'QELAclient', 'client')),
    ]
    for loc, d in dirs:
        for root, subFolders, files in os.walk(d):
            for file in files:
                r = os.path.join(root, file)
                extraDatas.append((r[r.index(loc):], r, 'DATA'))
    return extraDatas


a = Analysis(['QELAclient\\start.py'],
             pathex=[os.path.join(pkg_dir, f)
                     for f in os.listdir(pkg_dir)],

             hiddenimports=[
    'client.widgets.Login',
    'json',
    'geopy',
    'geopy.geocoders',
    'numpy',
    'typing',  # by webAPI
    'exifread'],

    excludes=[
    'sphinx', 'cython',
    '_gtkagg', '_tkagg', 'bsddb', 'curses', 'pywin.debugger', 'pandas',
    'pywin.debugger.dbgcon', 'pywin.dialogs', 'tcl', 'Tkconstants', 'tkinter'],

    hookspath=None,
    runtime_hooks=None)

# to prevent the error: 'WARNING: file already exists but should not:
# ...pyconfig.h'
for d in a.datas:
    if 'pyconfig' in d[0]:
        a.datas.remove(d)
        break

a.datas += addDataFiles()

# remove dlls that were added in win10 but not in win7:
# import platform
# if platform.platform().startswith("Windows-10"):


def keep(x):
    for dll in ('mkl_', 'icudt57.dll'):
        if dll in x[0]:
            return False
    return True


a.binaries = [x for x in a.binaries if keep(x)]


pyz = PYZ(
    a.pure,
    a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=1,

    name='QELAclient.exe',
    debug=False,
    strip=False,
    upx=False,
    console=True,
    icon=os.path.join(pkg_dir, 'QELAclient', 'QELAclient',
                      'client', 'media', 'logo.ico')
)

dist = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               name="QELAclient")


# write version.txt, so first time client is updated and not fully downloaded:
with open(os.path.join(DISTPATH,  'QELAclient', 'client', 'version.txt'), 'w') as f:
    f.write(time.strftime("%x %X", time.gmtime()))
