# -*- coding: utf-8 -*-
import os
import stat
import sys

from fancytools.os.isAdmin import isAdmin


class StartMenuEntry(object):
    """
    this class creates a shortcut for a given target in the start menu of the
    used os depending either system wide or user specific

    ===========   =========================================================
    kwargs        description
    ===========   =========================================================
    icon          [path of the program icon]
    directory     [start dir of the program],
    version       [version number]
    description   [of the program]
    console       False -> hide console (only GUI applications)
    categories    e.g. "Application;Science;Graphics;Office;" # Linux only
    ===========   =========================================================


    >>> entry = StartMenuEntry('myLittleTest', 'www.python.org')
    >>> entry.create()

    Now look for the entry in your start menu

    >>> entry.remove()
    """

    def __init__(self, name, target, **kwargs):
        # update kwargs with defaults if not already defined
        defaults = dict(icon=None, directory=None,
                        version='-', description='',
                        categories='',
                        console=True)
        kwargs.update({k: v for k, v in defaults.items() if k not in kwargs})
        kwargs.update({k: v for k, v in list(
            defaults.items()) if k not in kwargs})

        # check the os to setup further procedures
        if os.name == 'posix':  # for linux-systems
            self.__class__ = _LinuxStartMenuEntry
        elif os.name == 'nt':
            self.__class__ = _WindowsStartMenuEntry
        else:
            raise OSError(
                'creating start menu entries is not implemented for mac at the moment')

        self.__init__(name=name, target=target, **kwargs)


class _LinuxStartMenuEntry(object):

    def __init__(self, **kwargs):
        self.opts = kwargs
        if isAdmin():
            self.filename = '/usr/share/applications/%s.desktop' % self.opts[
                'name']
        else:
            self.filename = os.path.expanduser(
                "~") + '/.local/share/applications/%s.desktop' % self.opts['name']

    def create(self):
        # create starter
        d = os.path.dirname(self.filename)
        if not os.path.exists(d):
            os.mkdir(d)

        if getattr(sys, 'frozen', False):
            py = ''
        else:
            py = sys.executable + ' '

        with open(self.filename, 'w') as f:
            text = '''
[Desktop Entry]
Version=%s
Name=%s
Comment=%s
Icon=%s
Exec=%s%s
Terminal=false
Type=Application
Categories=%s
MimeType=PYZ''' % (
                self.opts['version'],
                self.opts['name'],
                self.opts['description'],
                self.opts['icon'],
                py, self.opts['target'],
                self.opts['categories']
            )
            # enable unicode-characters ('ä' etc.) and write to file
            f.write(text)  # .encode('UTF-8'))
        os.chmod(self.filename, os.stat(self.filename).st_mode | stat.S_IEXEC)

    def remove(self):
        if (os.path.exists(self.filename)):
            os.remove(self.filename)


class _WindowsStartMenuEntry(object):

    def __init__(self, **kwargs):
        self.opts = kwargs
        import win32com.client

        self.sh = win32com.client.Dispatch("WScript.Shell")
        if isAdmin():
            # this folder doesnt exists... - doenst work a.t.m.
            folder = "AllUsersPrograms"
        else:
            folder = "StartMenu"
        self.path = self.sh.SpecialFolders(folder)
        assert(os.path.isdir(self.path))

        if self.opts['directory']:
            self.path = os.path.join(self.path, self.opts['directory'])
        self.lnkPath = os.path.join(self.path, self.opts['name'] + ".lnk")
        self.lnk = self.sh.CreateShortcut(self.lnkPath)
        t = self.opts['target']
        self.lnk.TargetPath = t
        if not self.opts['console']:
            self.lnk.WindowStyle = 1
        self.lnk.WorkingDirectory = os.path.dirname(t)

    def create(self):
        # create shortcut group is not existent:
        if (not os.path.isdir(self.path)):
            os.makedirs(self.path)
        icon = self.opts['icon']
        if icon:
            if not icon.filetype().lower() == 'ico':
                # look wehter the icon also is store  in ico format:
                icon = icon.setFiletype('ico')
                if not icon.exists():
                    raise ValueError('only icons of type ICO are accepted')
            self.lnk.IconLocation = icon
        self.lnk.Save()

    def remove(self):
        if (os.path.exists(self.lnkPath)):
            os.remove(self.lnkPath)
            # if shortcut-group is empty now: delete it
            if self.opts['directory'] and not os.listdir(self.path):
                os.removedirs(self.path)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
