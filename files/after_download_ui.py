# -*- coding: utf-8 -*-

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from PyQt5 import QtWidgets , QtGui
from PyQt5.QtWidgets import QCheckBox , QWidget , QVBoxLayout , QHBoxLayout , QPushButton , QLabel , QLineEdit  
from PyQt5.QtGui import QIcon
import ast , os
from newopen import Open


import icons_resource
home_address = os.path.expanduser("~")
config_folder = str(home_address) + "/.config/persepolis_download_manager"

#setting
setting_file = config_folder + '/setting'
f = Open(setting_file)
setting_file_lines = f.readlines()
f.close()
setting_dict_str = str(setting_file_lines[0].strip())
setting_dict = ast.literal_eval(setting_dict_str) 

icons =':/' + str(setting_dict['icons']) + '/'



class AfterDownloadWindow_Ui(QWidget):
    def __init__(self):
        super().__init__()
#finding windows_size
        windows_size = config_folder + '/windows_size'
        f = Open(windows_size)
        windows_size_file_lines = f.readlines()
        f.close()
        windows_size_dict_str = str(windows_size_file_lines[0].strip())
        windows_size_dict = ast.literal_eval(windows_size_dict_str) 
        AfterDownloadWindow_Ui_size= windows_size_dict['AfterDownloadWindow_Ui']

        self.resize(AfterDownloadWindow_Ui_size[0],AfterDownloadWindow_Ui_size[1])
        self.setWindowIcon(QIcon.fromTheme('persepolis' ,QIcon(':/icon.svg')))
        self.setWindowTitle("Persepolis Download Manager")
#complete_label
        self.verticalLayout_1 = QVBoxLayout()
        self.verticalLayout_1.setContentsMargins(21, 21, 21, 21)

        self.complete_label = QLabel()
        self.verticalLayout_1.addWidget(self.complete_label)
#file_name_label
        self.file_name_label = QLabel()
        self.verticalLayout_1.addWidget(self.file_name_label)
#size_label
        self.size_label = QLabel()
        self.verticalLayout_1.addWidget(self.size_label)

#link
        self.link_label = QLabel()
        self.verticalLayout_1.addWidget(self.link_label)

        self.link_lineEdit = QLineEdit()
        self.verticalLayout_1.addWidget(self.link_lineEdit)
#save_as
        self.save_as_label = QLabel()
        self.verticalLayout_1.addWidget(self.save_as_label)
        self.save_as_lineEdit = QLineEdit()
        self.verticalLayout_1.addWidget(self.save_as_lineEdit)
#open_pushButtun
        button_horizontalLayout = QHBoxLayout()
        button_horizontalLayout.setContentsMargins(10, 10, 10, 10)

        button_horizontalLayout.addStretch(1)
        self.open_pushButtun = QPushButton()
        self.open_pushButtun.setIcon(QIcon(icons + 'file'))
        button_horizontalLayout.addWidget(self.open_pushButtun)

#open_folder_pushButtun
        self.open_folder_pushButtun = QPushButton()
        self.open_folder_pushButtun.setIcon(QIcon(icons + 'folder'))
        button_horizontalLayout.addWidget(self.open_folder_pushButtun)

#ok_pushButton
        self.ok_pushButton = QPushButton()
        self.ok_pushButton.setIcon(QIcon(icons + 'ok'))
        button_horizontalLayout.addWidget(self.ok_pushButton)

        self.verticalLayout_1.addLayout(button_horizontalLayout)
#dont_show_checkBox
        self.dont_show_checkBox = QCheckBox()
        self.verticalLayout_1.addWidget(self.dont_show_checkBox)


        self.setLayout(self.verticalLayout_1)

#labels 
        self.open_pushButtun.setText("  Open File  ")
        self.open_folder_pushButtun.setText("Open Download Folder")
        self.ok_pushButton.setText("   OK   ")
        self.dont_show_checkBox.setText("Don't show this message again.")
        self.complete_label.setText("<b>Download Completed!</b>")
        self.save_as_label.setText("<b>Save as</b> : ")
        self.link_label.setText("<b>Link</b> : " ) 


