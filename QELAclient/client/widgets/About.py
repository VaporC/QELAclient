from appbase.mainWindowRessources.menuabout import MenuAbout

import client


class About(MenuAbout):
    '''
    Show the general information about QELA, license and terms of use
    '''

    def __init__(self, gui):
        super().__init__()
        self.setWindowIcon(gui.windowIcon())
        self.setLogo(client.ICON)
        addr = 'http://%s' % gui.server.address[0]
        self.setInfo(client.__name__,
                     client.__doc__, client.__author__, client.__email__,
                     client.__version__,  client.__license__,
                     addr)
        self.setInstitutionLogo([(
            client.MEDIA_PATH.join('logo_seris.svg'),
            "http://www.seris.nus.edu.sg/")])

        txt = '''QELA allows correcting EL images from camera and perspective distortion
and analysing spatial and temporal changes. All image processing is done remotely
on a GPU enabled server. After processing a PDF report is generated. 
Report and corrected images can be downloaded from the DATA tab.
'''
        self.addTab('About', txt.replace('\n', '<br>'))

        txt = '''This program is free software: you can redistribute it and/or modify
it under the terms of the <b>GNU General Public License</b> as published by
the Free Software Foundation, either <b>version 3</b> of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <a href='http://www.gnu.org/licenses/'>http://www.gnu.org/licenses.</a>'''
        self.addTab('License', txt.replace('\n', '<br>'))

        self.addTab('Terms of Use', gui.server.page('terms_of_use.htm'))


if __name__ == '__main__':
    from PyQt5 import QtWidgets

    app = QtWidgets.QApplication([])

    w = About(None)

    w.show()
    app.exec_()
