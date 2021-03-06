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

import sys , ast
from PyQt5 import QtCore, QtGui, QtWidgets  
from PyQt5.QtWidgets import QSystemTrayIcon , QMenu , QTableWidgetItem , QApplication  
from PyQt5.QtGui import QIcon , QColor , QPalette 
from PyQt5.QtCore import QCoreApplication , QRect , QSize , QThread , pyqtSignal  , Qt
import os
from time import sleep
import random  
from after_download import AfterDownloadWindow 
from addlink import AddLinkWindow
from properties import PropertiesWindow
from progress import ProgressWindow
import download
from mainwindow_ui import MainWindow_Ui
from newopen import Open , writeList , readList
from play import playNotification
from bubble import notifySend
from setting import PreferencesWindow
from about import AboutWindow
import icons_resource
import spider
import osCommands
import glob

#shutdown_notification = 0 >> persepolis running , 1 >> persepolis is ready for close(closeEvent called) , 2 >> OK, let's close application!
global shutdown_notification
shutdown_notification = 0

# remove_flag : 0 >> normal situation ; 1 >> remove button or delete button pressed by user ; 2 >> check_download_info function is stopping until remove operation done ; 3 >> deleteFileAction is done it's job and It is called removeButtonPressed function
global remove_flag
remove_flag = 0
#when rpc connection between persepolis and aria is disconnected >> aria2_disconnected = 1
global aria2_disconnected
aria2_disconnected = 0

home_address = os.path.expanduser("~")
config_folder = str(home_address) + "/.config/persepolis_download_manager"

download_info_folder = config_folder + "/download_info"

temp_download_folder = str(home_address) + "/.persepolis"

#download_list_file contains GID of all downloads
download_list_file = config_folder + "/download_list_file"
#download_list_file_active for active downloads
download_list_file_active = config_folder + "/download_list_file_active"

#setting
setting_file = config_folder + '/setting'
f = Open(setting_file)
setting_file_lines = f.readlines()
f.close()
setting_dict_str = str(setting_file_lines[0].strip())
setting_dict = ast.literal_eval(setting_dict_str) 
#finding icons folder path
icons = ':/' + str(setting_dict['icons']) + '/'


#starting aria2 when Persepolis starts
class StartAria2Thread(QThread):
    ARIA2RESPONDSIGNAL = pyqtSignal(str)
    def __init__(self):
        QThread.__init__(self)
        
    def run(self):
        #aria_startup_answer is None when Persepolis starts! and after ARIA2RESPONDSIGNAL emitting yes , then startAriaMessage function changing aria_startup_answer to 'Ready'
        global aria_startup_answer
        aria_startup_answer = 'None'
        for i in range(5):
            answer = download.startAria()
            if answer == 'did not respond' and i != 4:
                signal_str = 'try again'
                self.ARIA2RESPONDSIGNAL.emit(signal_str)
                sleep(2)
            else :
                break

        #if Aria2 doesn't respond to Persepolis ,ARIA2RESPONDSIGNAL is emitting no  
        if answer == 'did not respond':
            signal_str = 'no'
        else :
            signal_str = 'yes'

        self.ARIA2RESPONDSIGNAL.emit(signal_str)



class CheckSelectedRowThread(QThread):
    CHECKSELECTEDROWSIGNAL = pyqtSignal()
    def __init__(self):
        QThread.__init__(self)

    def run(self):
        while shutdown_notification == 0 and aria_startup_answer != 'ready':
            sleep (1)
        while shutdown_notification == 0:
            sleep(0.2)
            self.CHECKSELECTEDROWSIGNAL.emit()




class CheckDownloadInfoThread(QThread):
    DOWNLOAD_INFO_SIGNAL = pyqtSignal(str)
    def __init__(self):
        QThread.__init__(self)
    def run(self):
        global remove_flag
        global shutdown_notification
        while True:

            while shutdown_notification == 0 and aria_startup_answer != 'ready':
                sleep (1)

            while shutdown_notification != 1:
            #if remove_flag is equal to 1, it means that user pressed remove or delete button . so checking download information must stop until removing done!
                if remove_flag == 1 :
                    remove_flag = 2
                    while remove_flag != 0 :
                        sleep(0.2)
                sleep(0.3)
                f = Open(download_list_file_active) 
                download_list_file_active_lines = f.readlines()
                f.close()
                if len(download_list_file_active_lines) != 0 :
                    for line in download_list_file_active_lines:
                        gid = line.strip()
                        try:
                            answer = download.downloadStatus(gid)
                        except:
                            answer = 'None'
                        if answer == 'ready' :
                            sleep(0.2)
                            download_info_file = download_info_folder + "/" + gid
                            if os.path.isfile(download_info_file) == True:
                                self.DOWNLOAD_INFO_SIGNAL.emit(gid)
            shutdown_notification = 2
            break
                            
                                
                            
                        


class SpiderThread(QThread):
    def __init__(self,add_link_dictionary , gid):
        QThread.__init__(self)
        self.add_link_dictionary = add_link_dictionary
        self.gid = gid

    def run(self):
        try :
            spider.spider(self.add_link_dictionary , self.gid)
        except :
            print("Spider couldn't find download informations")



#this threa sending download request to aria2            
class DownloadLink(QThread):
    ARIA2NOTRESPOND = pyqtSignal()
    def __init__(self,gid):
        QThread.__init__(self)
        self.gid = gid

    def run(self):
        #if request is not successful then persepolis is checking rpc connection whith download.aria2Version() function
        answer = download.downloadAria(self.gid)
        if answer == 'None':
            version_answer = download.aria2Version()
            if version_answer == 'did not respond':
                self.ARIA2NOTRESPOND.emit()

#CheckingThread have 3 duty!        
#1-this class is checking that user called flashgot .
#2-assume that user executed program before . if user is clicking on persepolis icon in menu this tread emit SHOWMAINWINDOWSIGNAL
#3-this class is checking aria2 rpc connection! if aria rpc is not availabile , this class restarts aria!
class CheckingThread(QThread):
    CHECKFLASHGOTSIGNAL = pyqtSignal()
    SHOWMAINWINDOWSIGNAL = pyqtSignal()
    RECONNECTARIASIGNAL = pyqtSignal(str)
    def __init__(self):
        QThread.__init__(self)

    def run(self):
        global shutdown_notification
        global aria2_disconnected
        while shutdown_notification == 0 and aria_startup_answer != 'ready':
            sleep (2)
        j = 0
        while shutdown_notification == 0:
            if os.path.isfile("/tmp/persepolis/show-window") == True:
                osCommands.remove('/tmp/persepolis/show-window')
                self.SHOWMAINWINDOWSIGNAL.emit()
            sleep(1)
            if os.path.isfile("/tmp/persepolis-flashgot")  == True and os.path.isfile("/tmp/persepolis-flashgot.lock") == False:
                self.CHECKFLASHGOTSIGNAL.emit()
             
            j = j + 1
#every 30 seconds
            if j == 30 or aria2_disconnected == 1 : 
                j = 0
                aria2_disconnected = 0
                answer = download.aria2Version() #checking aria2 availability by aria2Version function
                if answer == 'did not respond':
                    for i in range(5):
                        answer = download.startAria() #starting aria2
                        if answer == 'did not respond' and i != 4: # checking answer
                            sleep(2)
                        else :
                            break
                    self.RECONNECTARIASIGNAL.emit(str(answer))  #emitting answer , if answer is 'did not respond' , it means that reconnecting aria was not successful         
 
   
 
class MainWindow(MainWindow_Ui):
    def __init__(self , start_in_tray):
        super().__init__()
#system_tray_icon
        self.system_tray_icon = QSystemTrayIcon() 
        self.system_tray_icon.setIcon(QIcon.fromTheme('persepolis',QIcon(':/icon.svg') ))
        system_tray_menu = QMenu()
        system_tray_menu.addAction(self.addlinkAction)
        system_tray_menu.addAction(self.pauseAllAction)
        system_tray_menu.addAction(self.stopAllAction)
        system_tray_menu.addAction(self.minimizeAction)
        system_tray_menu.addAction(self.exitAction)
        self.system_tray_icon.setContextMenu(system_tray_menu)
        self.system_tray_icon.activated.connect(self.systemTrayPressed)
        self.system_tray_icon.show()
        self.system_tray_icon.setToolTip('Persepolis Download Manager')
        f = Open(setting_file)
        setting_file_lines = f.readlines()
        f.close()
        setting_dict_str = str(setting_file_lines[0].strip())
        setting_dict = ast.literal_eval(setting_dict_str) 
        if setting_dict['tray-icon'] != 'yes' and start_in_tray == 'no' : 
            self.minimizeAction.setEnabled(False)
            self.trayAction.setChecked(False)
            self.system_tray_icon.hide()
        if start_in_tray == 'yes':
            self.minimizeAction.setText('Show main Window')
            self.minimizeAction.setIcon(QIcon(icons + 'window'))
#statusbar
        self.statusbar.showMessage('Please Wait ...')
        self.checkSelectedRow()

#touch download_list_file
        osCommands.touch(download_list_file)

#touch download_list_file_active
        osCommands.touch(download_list_file_active)


#lock files perventing to access a file simultaneously

#removing lock files in starting persepolis
        pattern = str(config_folder) + '/*.lock'
        for file in glob.glob(pattern):
            osCommands.remove(file)

        pattern = str(download_info_folder) + '/*.lock'
        for file in glob.glob(pattern):
            osCommands.remove(file)



#threads     
        self.threadPool=[]
#starting aria
        start_aria = StartAria2Thread()
        self.threadPool.append(start_aria)
        self.threadPool[0].start() 
        self.threadPool[0].ARIA2RESPONDSIGNAL.connect(self.startAriaMessage)

#initializing    
#add downloads to the download_table
        f_download_list_file = Open(download_list_file)
        download_list_file_lines = f_download_list_file.readlines()
        f_download_list_file.close()
            
        for line in download_list_file_lines:
            gid = line.strip()
            self.download_table.insertRow(0)
            download_info_file = download_info_folder + "/" + gid
            download_info_file_list = readList(download_info_file,'string')
            for i in range(12):
                item = QTableWidgetItem(download_info_file_list[i])
                self.download_table.setItem(0 , i , item)

        row_numbers = self.download_table.rowCount()
        for row in range(row_numbers):
            status = self.download_table.item(row , 1).text() 
            if (status != "complete" and status != "error"):
                gid = self.download_table.item(row,8).text() 
                add_link_dictionary_str = self.download_table.item(row,9).text() 
                add_link_dictionary = ast.literal_eval(add_link_dictionary_str.strip()) 
                add_link_dictionary['start_hour'] = None
                add_link_dictionary['start_minute'] = None
                add_link_dictionary['end_hour'] = None
                add_link_dictionary['end_minute'] = None
                add_link_dictionary['after_download'] = 'None'

                download_info_file = download_info_folder + "/" + gid
                download_info_file_list = readList(download_info_file,'string')

                for i in range(12):
                    if i == 1 :
                        download_info_file_list[i] = 'stopped'
                        item = QTableWidgetItem('stopped')
                        self.download_table.setItem(row , i , item )
                download_info_file_list[9] = add_link_dictionary
                writeList(download_info_file , download_info_file_list)

        self.addlinkwindows_list = []
        self.propertieswindows_list = []
        self.progress_window_list = []
        self.afterdownload_list = []
        self.progress_window_list_dict = {}
#CheckDownloadInfoThread
        check_download_info = CheckDownloadInfoThread()
        self.threadPool.append(check_download_info)
        self.threadPool[1].start()
        self.threadPool[1].DOWNLOAD_INFO_SIGNAL.connect(self.checkDownloadInfo)
#CheckSelectedRowThread
        check_selected_row = CheckSelectedRowThread()
        self.threadPool.append(check_selected_row)
        self.threadPool[2].start()
        self.threadPool[2].CHECKSELECTEDROWSIGNAL.connect(self.checkSelectedRow)
#CheckingThread
        check_flashgot = CheckingThread()
        self.threadPool.append(check_flashgot)
        self.threadPool[3].start()
        self.threadPool[3].CHECKFLASHGOTSIGNAL.connect(self.checkFlashgot)
        self.threadPool[3].SHOWMAINWINDOWSIGNAL.connect(self.showMainWindow)
        self.threadPool[3].RECONNECTARIASIGNAL.connect(self.reconnectAria)


#if user is doubleclicking on an item in download_table , then openFile function is executing
        self.download_table.itemDoubleClicked.connect(self.openFile)

# startAriaMessage function is showing some message on statusbar and sending notification when aria failed to start! see StartAria2Thread for more details
    def startAriaMessage(self,message):
        global aria_startup_answer
        if message == 'yes':
            sleep (2)
            self.statusbar.showMessage('Ready...')
            aria_startup_answer = 'ready'
        elif message == 'try again':
            self.statusbar.showMessage("Aria2 didn't respond! be patient!Persepolis tries again in 2 seconds!")
        else:
            self.statusbar.showMessage('Error...')
            notifySend('Persepolis can not connect to Aria2' , 'Restart Persepolis' ,10000,'critical' , systemtray = self.system_tray_icon )
            self.propertiesAction.setEnabled(True)

    def reconnectAria(self,message):
        #this function is executing if RECONNECTARIASIGNAL is emitted by CheckingThread . 
        #if message is 'did not respond' then a message(Persepolis can not connect to Aria2) shown 
        #if message is not 'did not respond' , it means that reconnecting Aria2 was successful. 
        if message == 'did not respond' : 
            self.statusbar.showMessage('Error...')
            notifySend('Persepolis can not connect to Aria2' , 'Restart Persepolis' ,10000,'critical' , systemtray = self.system_tray_icon )
        else:
            self.statusbar.showMessage('Reconnecting aria2...')
            #this section is checking download status of items in download table , if status is downloading then restarting this download.
            for row in range(self.download_table.rowCount()):
                status_download_table = str(self.download_table.item( row , 1 ).text())
                gid = self.download_table.item( row , 8).text()
                if status_download_table == 'downloading': 
                    new_download = DownloadLink(gid)
                    self.threadPool.append(new_download)
                    self.threadPool[len(self.threadPool) - 1].start()
                    self.threadPool[len(self.threadPool) - 1].ARIA2NOTRESPOND.connect(self.aria2NotRespond)
            #if status is paused , then this section is stopping download.
                if status_download_table == 'paused':
                    download.downloadStop(gid)

            notifySend('Persepolis reconnected aria2' , 'successfully!' ,10000,'warning' , systemtray = self.system_tray_icon )
            self.statusbar.showMessage('Persepolis Download Manager') 

#when this function is called , aria2_disconnected value is changing to 1! and it means that aria2 rpc connection disconnected.so CheckingThread is trying to fix it .          
    def aria2Disconnected(self):
        global aria2_disconnected
        aria2_disconnected = 1




    def checkDownloadInfo(self,gid):
        try:

#get download information from download_info_file according to gid and write them in download_table cells
            download_info_file = config_folder + "/download_info/" + gid
            download_info_file_list = readList(download_info_file)
            download_info_file_list_string = readList(download_info_file ,'string')
#finding row of this gid!
            for i in range(self.download_table.rowCount()):
                row_gid = self.download_table.item(i , 8).text()
                if gid == row_gid :
                    row = i 
                    break

            for i in range(12):
#check flag of download!
#It's showing that selection mode is active or not!
                if i == 0 :
                    flag = int(self.download_table.item(row , i).flags())

#remove gid of completed download from active downloads list file
                elif i == 1 :
                    status = str(download_info_file_list[i])
                    status_download_table = str(self.download_table.item(row , 1 ).text())
                    if status == "complete":
                        f = Open(download_list_file_active)
                        download_list_file_active_lines = f.readlines()
                        f.close()
                        f = Open(download_list_file_active , "w")
                        for line in download_list_file_active_lines :
                            if line.strip() != gid :
                                f.writelines(line.strip() + "\n")
                        f.close()
                    
#update download_table cells
                item = QTableWidgetItem(download_info_file_list_string[i])
#48 means that item is checkable and enabled
                if i == 0 and flag == 48:
                    item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                    if self.download_table.item(row , i).checkState() == 2:
                        item.setCheckState(QtCore.Qt.Checked)
                    else:
                        item.setCheckState(QtCore.Qt.Unchecked)


                self.download_table.setItem(row , i , item)
                self.download_table.viewport().update()
#update progresswindow
            try :

#finding progress_window for gid            
                member_number = self.progress_window_list_dict[gid]
                progress_window = self.progress_window_list[member_number]
                #link
                add_link_dictionary = download_info_file_list[9]
                link = "<b>Link</b> : " +  str(add_link_dictionary ['link'])
                progress_window.link_label.setText(link)
                progress_window.link_label.setToolTip(link)

                #Save as
                final_download_path = add_link_dictionary['final_download_path']
                if final_download_path == None :
                    final_download_path = str(add_link_dictionary['download_path'])
                        
                save_as = "<b>Save as</b> : " + final_download_path + "/" + str(download_info_file_list[0])
                progress_window.save_label.setText(save_as)
                progress_window.save_label.setToolTip(save_as)

                #status
                progress_window.status = download_info_file_list[1]
                status = "<b>Status</b> : " + progress_window.status 
                progress_window.status_label.setText(status)
                if progress_window.status == "downloading":
                    progress_window.resume_pushButton.setEnabled(False)
                    progress_window.stop_pushButton.setEnabled(True)
                    progress_window.pause_pushButton.setEnabled(True)
                elif progress_window.status == "paused":
                    progress_window.resume_pushButton.setEnabled(True)
                    progress_window.stop_pushButton.setEnabled(True)
                    progress_window.pause_pushButton.setEnabled(False)
                elif progress_window.status == "waiting":
                    progress_window.resume_pushButton.setEnabled(False)
                    progress_window.stop_pushButton.setEnabled(True)
                    progress_window.pause_pushButton.setEnabled(False)
                elif progress_window.status == "scheduled":
                    progress_window.resume_pushButton.setEnabled(False)
                    progress_window.stop_pushButton.setEnabled(True)
                    progress_window.pause_pushButton.setEnabled(False)
                elif progress_window.status == "stopped" or progress_window.status == "error" or progress_window.status == "complete" :
#close progress_window if download status is stopped or completed or error
                    progress_window.saveWindowSize()
                    progress_window.close()
                    self.progress_window_list[member_number] = []
                    del self.progress_window_list_dict[gid]
                    if progress_window.status == "stopped":
                        notifySend("Download Stopped" , str(download_info_file_list[0]) , 10000 , 'no', systemtray = self.system_tray_icon )

                    elif progress_window.status == "error":
                        notifySend("Error - " + add_link_dictionary['error'] , str(download_info_file_list[0]) , 10000 , 'fail', systemtray = self.system_tray_icon )
               
                        add_link_dictionary['start_hour'] = None
                        add_link_dictionary['start_minute'] = None
                        add_link_dictionary['end_hour'] = None
                        add_link_dictionary['end_minute'] = None
                        add_link_dictionary['after_download'] = 'None'

                        for i in range(12):
                            if i == 9 :
                                download_info_file_list[i] = add_link_dictionary
                                
                        download_info_file_list[9] = add_link_dictionary 
                        writeList(download_info_file , download_info_file_list )


#this section is sending shutdown signal to the shutdown script(if user select shutdown for after download)
                    if os.path.isfile('/tmp/persepolis/shutdown/' + gid ) == True and progress_window.status != 'stopped':
                        answer = download.shutDown()
#KILL aria2c if didn't respond
                        if answer == 'error':
                            os.system('killall aria2c')
                        f = Open('/tmp/persepolis/shutdown/' + gid , 'w')
                        notifySend('Persepolis is shutting down','your system in 20 seconds' , 15000 ,'warning', systemtray = self.system_tray_icon )
                        f.writelines('shutdown')
                        f.close()
                    elif os.path.isfile('/tmp/persepolis/shutdown/' + gid ) == True and progress_window.status == 'stopped':
                        f = Open('/tmp/persepolis/shutdown/' + gid , 'w')
                        f.writelines('canceled')
                        f.close()

#showing download compelete dialog
#check user's Preferences
                    f = Open(setting_file)
                    setting_file_lines = f.readlines()
                    f.close()
                    setting_dict_str = str(setting_file_lines[0].strip())
                    setting_dict = ast.literal_eval(setting_dict_str) 

                    if progress_window.status == "complete" :
                        if setting_dict['after-dialog'] == 'yes' :
                            afterdownloadwindow = AfterDownloadWindow(download_info_file_list,setting_file)
                            self.afterdownload_list.append(afterdownloadwindow)
                            self.afterdownload_list[len(self.afterdownload_list) - 1].show()
                        else :
                            notifySend("Download Complete" ,str(download_info_file_list[0])  , 10000 , 'ok' , systemtray = self.system_tray_icon )



             
                #downloaded
                downloaded = "<b>Downloaded</b> : " + str(download_info_file_list[3]) + "/" + str(download_info_file_list[2])
                progress_window.downloaded_label.setText(downloaded)

                #Transfer rate
                rate = "<b>Transfer rate</b> : " + str(download_info_file_list[6])
                progress_window.rate_label.setText(rate)

                #Estimate time left
                estimate_time_left = "<b>Estimate time left</b> : " + str(download_info_file_list[7]) 
                progress_window.time_label.setText(estimate_time_left)

                #Connections
                connections = "<b>Connections</b> : " + str(download_info_file_list[5])
                progress_window.connections_label.setText(connections)


                #progressbar
                value = download_info_file_list[4]
                file_name = str(download_info_file_list[0])
                if file_name != "***":
                    windows_title = '(' + str(value) + ')' +  str(file_name)
                    progress_window.setWindowTitle(windows_title) 

                value = value[:-1]
                progress_window.download_progressBar.setValue(int(value))



            except :
                pass

        except:
            pass
                   



#contex menu
    def contextMenuEvent(self, event):
        self.tablewidget_menu = QMenu(self)
        self.tablewidget_menu.addAction(self.openFileAction)
        self.tablewidget_menu.addAction(self.openDownloadFolderAction)
        self.tablewidget_menu.addAction(self.resumeAction)
        self.tablewidget_menu.addAction(self.pauseAction)
        self.tablewidget_menu.addAction(self.stopAction)
        self.tablewidget_menu.addAction(self.removeAction)
        self.tablewidget_menu.addAction(self.deleteFileAction)
        self.tablewidget_menu.addAction(self.propertiesAction)
        self.tablewidget_menu.addAction(self.progressAction)
        self.tablewidget_menu.popup(QtGui.QCursor.pos())
#drag and drop for links
    def dragEnterEvent(self, droplink):

        text = str(droplink.mimeData().text())
      
        if ("tp:/" in text[2:6]) or ("tps:/" in text[2:7]) :
            droplink.accept()
        else:
            droplink.ignore() 

    def dropEvent(self, droplink):
        link_clipborad = QApplication.clipboard()
        link_clipborad.clear(mode=link_clipborad.Clipboard )
        link_string = droplink.mimeData().text() 
        link_clipborad.setText(str(link_string), mode=link_clipborad.Clipboard) 
        self.addLinkButtonPressed(button =link_clipborad )
    
	
    def gidGenerator(self):
        my_gid = hex(random.randint(1152921504606846976,18446744073709551615))
        my_gid = my_gid[2:18]
        my_gid = str(my_gid)
        f = Open(download_list_file_active)
        active_gid_list = f.readlines()
        f.close()
        while my_gid in active_gid_list :
            my_gid = self.gidGenerator()
        active_gids = download.activeDownloads()
        while my_gid in active_gids:
            my_gid = self.gidGenerator()
        
        return my_gid

    def selectedRow(self):
        try:
            item = self.download_table.selectedItems()
            selected_row_return = self.download_table.row(item[1]) 
            download_info = self.download_table.item(selected_row_return , 9).text()
            download_info = ast.literal_eval(download_info) 
            link = download_info['link']
            self.statusbar.showMessage(str(link))

        except :
            selected_row_return = None

        return selected_row_return 

    def checkSelectedRow(self):
        try:
            item = self.download_table.selectedItems()
            selected_row_return = self.download_table.row(item[1]) 
        except :
            selected_row_return = None

        if selected_row_return != None :
            status = self.download_table.item(selected_row_return , 1).text() 
            if status == "scheduled":
                self.resumeAction.setEnabled(False)
                self.pauseAction.setEnabled(False)
                self.stopAction.setEnabled(True)
                self.removeAction.setEnabled(False)
                self.propertiesAction.setEnabled(False)
                self.progressAction.setEnabled(True)
                self.openDownloadFolderAction.setEnabled(False)
                self.openFileAction.setEnabled(False)            
                self.deleteFileAction.setEnabled(False)

            elif status == "stopped" or status == "error" :
                self.stopAction.setEnabled(False)
                self.pauseAction.setEnabled(False)
                self.resumeAction.setEnabled(True)
                self.removeAction.setEnabled(True)
                self.propertiesAction.setEnabled(True)
                self.progressAction.setEnabled(False)
                self.openDownloadFolderAction.setEnabled(False)
                self.openFileAction.setEnabled(False)            
                self.deleteFileAction.setEnabled(False)



            elif status == "downloading":
                self.resumeAction.setEnabled(False)
                self.pauseAction.setEnabled(True)
                self.stopAction.setEnabled(True)
                self.removeAction.setEnabled(False)
                self.propertiesAction.setEnabled(False)
                self.progressAction.setEnabled(True)
                self.openDownloadFolderAction.setEnabled(False)
                self.openFileAction.setEnabled(False)            
                self.deleteFileAction.setEnabled(False)



            elif status == "waiting": 
                self.stopAction.setEnabled(True)
                self.resumeAction.setEnabled(False)
                self.pauseAction.setEnabled(False)
                self.removeAction.setEnabled(False)
                self.propertiesAction.setEnabled(False)
                self.progressAction.setEnabled(True)
                self.openDownloadFolderAction.setEnabled(False)
                self.openFileAction.setEnabled(False)            
                self.deleteFileAction.setEnabled(False)



            elif status == "complete":
                self.stopAction.setEnabled(False)
                self.resumeAction.setEnabled(False)
                self.pauseAction.setEnabled(False)
                self.removeAction.setEnabled(True)
                self.propertiesAction.setEnabled(True)
                self.progressAction.setEnabled(False)
                self.openDownloadFolderAction.setEnabled(True)
                self.openFileAction.setEnabled(True)            
                self.deleteFileAction.setEnabled(True)



            elif status == "paused":
                self.stopAction.setEnabled(True)
                self.resumeAction.setEnabled(True)
                self.pauseAction.setEnabled(False)
                self.removeAction.setEnabled(False)
                self.propertiesAction.setEnabled(False)
                self.progressAction.setEnabled(True)
                self.openDownloadFolderAction.setEnabled(False)
                self.openFileAction.setEnabled(False)            
                self.deleteFileAction.setEnabled(False)


              
 
            else:
                self.progressAction.setEnabled(False)
                self.resumeAction.setEnabled(False)
                self.stopAction.setEnabled(False)
                self.pauseAction.setEnabled(False)
                self.removeAction.setEnabled(False)
                self.propertiesAction.setEnabled(False)
                self.openDownloadFolderAction.setEnabled(False)
                self.openFileAction.setEnabled(False)            
                self.deleteFileAction.setEnabled(False)



        else:
            self.progressAction.setEnabled(False)
            self.resumeAction.setEnabled(False)
            self.stopAction.setEnabled(False)
            self.pauseAction.setEnabled(False)
            self.removeAction.setEnabled(False)
            self.propertiesAction.setEnabled(False)
            self.openDownloadFolderAction.setEnabled(False)
            self.openFileAction.setEnabled(False)            
            self.deleteFileAction.setEnabled(False)



           
    def checkFlashgot(self):
        sleep(0.5)
        flashgot_file = Open("/tmp/persepolis-flashgot")
        flashgot_line = flashgot_file.readlines()
        flashgot_file.close()
        flashgot_file.remove()
        flashgot_add_link_dictionary_str = flashgot_line[0]
        flashgot_add_link_dictionary = ast.literal_eval(flashgot_add_link_dictionary_str) 
        self.flashgotAddLink(flashgot_add_link_dictionary)


    def flashgotAddLink(self,flashgot_add_link_dictionary):
        addlinkwindow = AddLinkWindow(self.callBack , flashgot_add_link_dictionary)
        self.addlinkwindows_list.append(addlinkwindow)
        self.addlinkwindows_list[len(self.addlinkwindows_list) - 1].show()

       
            



    def addLinkButtonPressed(self ,button):
        addlinkwindow = AddLinkWindow(self.callBack)
        self.addlinkwindows_list.append(addlinkwindow)
        self.addlinkwindows_list[len(self.addlinkwindows_list) - 1].show()

    def callBack(self , add_link_dictionary , download_later):
        #aria2 identifies each download by the ID called GID. The GID must be hex string of 16 characters.
        gid = self.gidGenerator()

	#download_info_file_list is a list that contains ['file_name' , 'status' , 'size' , 'downloaded size' ,'download percentage' , 'number of connections' ,'Transfer rate' , 'estimate_time_left' , 'gid' , 'add_link_dictionary' , 'firs_try_date' , 'last_try_date']

        #if user or flashgot defined filename then file_name is valid in add_link_dictionary['out']
        if add_link_dictionary['out'] != None :
            file_name = add_link_dictionary['out']
        else:
            file_name = '***'

        if download_later == 'no':
            download_info_file_list = [ file_name ,'waiting','***','***','***','***','***','***',gid , add_link_dictionary , '***' , '***' ]
        else:
            download_info_file_list = [ file_name ,'stopped', '***' ,'***','***','***','***','***',gid , add_link_dictionary , '***' ,'***' ]


        #after user pushs ok button on add link window , a gid is generating for download and a file (with name of gid) is creating in download_info_folder . this file is containing download_info_file_list
        download_info_file = config_folder + "/download_info/" + gid
        osCommands.touch(download_info_file)
         
        writeList(download_info_file , download_info_file_list)
        
        #creating a row in download_table
        self.download_table.insertRow(0)
        j = 0
        download_info_file_list[9] = str(download_info_file_list[9])
        for i in download_info_file_list :
            item = QTableWidgetItem(i)
            self.download_table.setItem(0,j,item)
            j = j + 1
        #this section is adding checkBox to the row , if user selected selectAction
        if self.selectAction.isChecked() == True:
            item = self.download_table.item(0 , 0)
            item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            item.setCheckState(QtCore.Qt.Unchecked)
        # adding gid of download to download_list_file . download_list_file contains gid of all downloads.
        f = Open (download_list_file , "a")
        f.writelines(gid + "\n")
        f.close()

        #adding gid to download_list_file_active . this file contains gid of active downloads . 
        f = Open (download_list_file_active , "a")
        f.writelines(gid + "\n")
        f.close()

        #if user didn't press download_later_pushButton in add_link window then this section is creating new qthread for new download!
        if download_later == 'no':
            new_download = DownloadLink(gid)
            self.threadPool.append(new_download)
            self.threadPool[len(self.threadPool) - 1].start()
            self.threadPool[len(self.threadPool) - 1].ARIA2NOTRESPOND.connect(self.aria2NotRespond)
        #opening progress window for download.
            self.progressBarOpen(gid) 
        #notifiying user for scheduled download or download starting.
            if add_link_dictionary['start_hour'] == None :
                message = "Download Starts"
            else:
                new_spider = SpiderThread(add_link_dictionary , gid )
                self.threadPool.append(new_spider)
                self.threadPool[len(self.threadPool) - 1].start()
                message = "Download Scheduled"
            notifySend(message ,'' , 10000 , 'no', systemtray = self.system_tray_icon )

        else :
            new_spider = SpiderThread(add_link_dictionary , gid )
            self.threadPool.append(new_spider)
            self.threadPool[len(self.threadPool) - 1].start()


    def resumeButtonPressed(self,button):
        self.resumeAction.setEnabled(False)
        selected_row_return = self.selectedRow() #finding user selected row

        if selected_row_return != None:
            gid = self.download_table.item(selected_row_return , 8 ).text()
            download_status = self.download_table.item(selected_row_return , 1).text()
 
                
            if download_status == "paused" :
                answer = download.downloadUnpause(gid)
#if aria2 did not respond , then this function is checking for aria2 availability , and if aria2 disconnected then aria2Disconnected is executed 
                if answer == 'None':
                    version_answer = download.aria2Version()
                    if version_answer == 'did not respond':
                        self.aria2Disconnected()
                        notifySend("Aria2 disconnected!","Persepolis is trying to connect!be patient!",10000,'warning' , systemtray = self.system_tray_icon )
                    else:
                        notifySend("Aria2 did not respond!","Try agian!",10000,'warning' , systemtray = self.system_tray_icon )



            else:
                new_download = DownloadLink(gid)
                self.threadPool.append(new_download)
                self.threadPool[len(self.threadPool) - 1].start()
                self.threadPool[len(self.threadPool) - 1].ARIA2NOTRESPOND.connect(self.aria2NotRespond)

                sleep(1)
                self.progressBarOpen(gid)




    def aria2NotRespond(self):
        self.aria2Disconnected()
        notifySend('Aria2 did not respond' , 'Try again' , 5000 , 'critical' , systemtray = self.system_tray_icon )

    def stopButtonPressed(self,button):
        self.stopAction.setEnabled(False)
        selected_row_return = self.selectedRow()#finding user selected row

        if selected_row_return != None:
            gid = self.download_table.item(selected_row_return , 8 ).text()
            answer = download.downloadStop(gid)
#if aria2 did not respond , then this function is checking for aria2 availability , and if aria2 disconnected then aria2Disconnected is executed 
            if answer == 'None':
                version_answer = download.aria2Version()
                if version_answer == 'did not respond':
                    self.aria2Disconnected()
                    notifySend("Aria2 disconnected!","Persepolis is trying to connect!be patient!",10000,'warning' , systemtray = self.system_tray_icon )
               

    def pauseButtonPressed(self,button):
        self.pauseAction.setEnabled(False)
        selected_row_return = self.selectedRow()#finding user selected row

        if selected_row_return != None:
            gid = self.download_table.item(selected_row_return , 8 ).text()
            answer = download.downloadPause(gid)
#if aria2 did not respond , then this function is checking for aria2 availability , and if aria2 disconnected then aria2Disconnected is executed 
            if answer == 'None':
                version_answer = download.aria2Version()
                if version_answer == 'did not respond':
                    self.aria2Disconnected()
                    download.downloadStop(gid)
                    notifySend("Aria2 disconnected!","Persepolis is trying to connect!be patient!",10000,'warning' , systemtray = self.system_tray_icon )
                else:
                    notifySend("Aria2 did not respond!" , "Try agian!" , 10000 , 'critical' , systemtray = self.system_tray_icon )
        sleep(1)

    def propertiesButtonPressed(self,button):
        self.propertiesAction.setEnabled(False)
        selected_row_return = self.selectedRow() #finding user selected row

        if selected_row_return != None :
            add_link_dictionary_str = self.download_table.item(selected_row_return , 9).text() 
            add_link_dictionary = ast.literal_eval(add_link_dictionary_str) 
            gid = self.download_table.item(selected_row_return , 8 ).text()
            propertieswindow = PropertiesWindow(self.propertiesCallback ,gid)
            self.propertieswindows_list.append(propertieswindow)
            self.propertieswindows_list[len(self.propertieswindows_list) - 1].show()

    def propertiesCallback(self,add_link_dictionary , gid ):
        download_info_file = download_info_folder + "/" + gid
        download_info_file_list = readList(download_info_file )
        download_info_file_list [9] = add_link_dictionary
        writeList(download_info_file , download_info_file_list)
            
    def progressButtonPressed(self,button):
        selected_row_return = self.selectedRow() #finding user selected row
        if selected_row_return != None:
            gid = self.download_table.item(selected_row_return , 8 ).text()
        # if gid is in self.progress_window_list_dict , it means that progress window  for this gid (for this download) is created before and it's available!
            if gid in self.progress_window_list_dict :
                member_number = self.progress_window_list_dict[gid]
                #if window is visible >> hide it , and if window is hide >> make it visible!
                if self.progress_window_list[member_number].isVisible() == False:
                    self.progress_window_list[member_number].show()
                else :
                    self.progress_window_list[member_number].hide()
            else :
                self.progressBarOpen(gid) #if window is not availabile , let's create it!
    def progressBarOpen(self,gid):
        progress_window = ProgressWindow(parent = self,gid = gid) #creating a progress window
        self.progress_window_list.append(progress_window) #adding progress window to progress_window_list
        member_number = len(self.progress_window_list) - 1
        self.progress_window_list_dict[gid] = member_number #in progress_window_list_dict , key is gid and value is member's rank(number) in progress_window_list
        self.progress_window_list[member_number].show() #showing progress window
 
#close event
#when user wants to close application then this function is called
    def closeEvent(self, event):
        self.saveWindowSize()
        self.hide()
        QCoreApplication.instance().closeAllWindows()
        print("Please Wait...")

        self.stopAllDownloads(event) #stopping all downloads
        self.system_tray_icon.hide() #hiding system_tray_icon

        download.shutDown() #shutting down Aria2
        sleep(0.5)
        global shutdown_notification #see start of this script and see inherited QThreads 
#shutdown_notification = 0 >> persepolis running , 1 >> persepolis is ready for close(closeEvent called) , 2 >> OK, let's close application!
        shutdown_notification = 1
        while shutdown_notification != 2:
            sleep (0.1)


        QCoreApplication.instance().quit
        print("Persepolis Closed")
        sys.exit(0)

#showTray function is showing/hiding system tray icon
    def showTray(self,menu):
        if self.trayAction.isChecked() == True :
            self.system_tray_icon.show() #show system_tray_icon
            self.minimizeAction.setEnabled(True) #enabling minimizeAction in menu
        else:
            self.system_tray_icon.hide() #hide system_tray_icon
            self.minimizeAction.setEnabled(False) #disabaling minimizeAction in menu

#when user click on mouse's left button , then this function is called
    def systemTrayPressed(self,click):
        if click == 3 :
            self.minMaxTray(click)
            
#minMaxTray function is showing/hiding main window
    def minMaxTray(self,menu):
        if self.isVisible() == False:
            self.show()
            self.menubar.show() #this line is for solving unity(ubuntu 16.04) problem
            self.minimizeAction.setText('Minimize to system tray')
            self.minimizeAction.setIcon(QIcon(icons + 'minimize'))
        
        else :
            self.minimizeAction.setText('Show main Window')
            self.minimizeAction.setIcon(QIcon(icons + 'window'))
            self.hide()

#showMainWindow is show main window in normal mode , see CheckingThread 
    def showMainWindow(self):
        self.showNormal()
        self.minimizeAction.setText('Minimize to system tray')
        self.minimizeAction.setIcon(QIcon(icons + 'minimize'))
 
#stopAllDownloads is stopping all downloads
    def stopAllDownloads(self,menu):
        active_gids = []
        for i in range(self.download_table.rowCount()):
            try:
                row_status = self.download_table.item(i , 1).text()
                if row_status == 'downloading' or row_status == 'paused' or row_status == 'waiting': #checking status of downloads
                    row_gid = self.download_table.item(i , 8).text() #finding gid
                    active_gids.append(row_gid) #adding gid to active_gids list
            except :
                pass
        #executing downloadStop function for all gid in active_gids list
        for gid in active_gids:
            answer = download.downloadStop(gid)
            if answer == 'None': #sending error if Aria2 didn't respond
                notifySend("Aria2 did not respond!" , "Try agian!" , 10000 , 'critical' , systemtray = self.system_tray_icon )


            sleep(0.3)

           
#this function is paussing all downloads
    def pauseAllDownloads(self,menu):
#getting active gid of downloads from aria
        active_gids = download.activeDownloads()
#check that if gid is in download_list_file_active
        f = Open(download_list_file_active)
        download_list_file_active_lines = f.readlines()
        f.close()
        for i in range(len(download_list_file_active_lines)):
            download_list_file_active_lines[i] = download_list_file_active_lines[i].strip()

        for gid in active_gids :
            if gid in download_list_file_active_lines :
                answer = download.downloadPause(gid) #pausing downloads in loop
                if answer == 'None': #sending error if Aria2 didn't respond
                    notifySend("Aria2 did not respond!" , "Try agian!" , 10000 , 'critical' , systemtray = self.system_tray_icon )

                sleep(0.3)
            

    def openPreferences(self,menu):
        self.preferenceswindow = PreferencesWindow(self)
        self.preferenceswindow.show() #showing Preferences Window



    def openAbout(self,menu):
        self.about_window = AboutWindow()
        self.about_window.show() #showing about window

#This function is openning user's default download folder
    def openDefaultDownloadFolder(self,menu):
        #finding user's default download folder from setting file
        f = Open(setting_file)
        setting_file_lines = f.readlines()
        f.close()
        setting_dict_str = str(setting_file_lines[0].strip())
        setting_dict = ast.literal_eval(setting_dict_str) 
        download_path = setting_dict ['download_path']
        if os.path.isdir(download_path): #checking that if download folder is availabile or not
            osCommands.xdgOpen(download_path) #openning folder
        else:
            notifySend(str(download_path) ,'Not Found' , 5000 , 'warning' , systemtray = self.system_tray_icon ) #showing error message if folder didn't existed



#this function is openning download folder , if download was finished
    def openDownloadFolder(self,menu):
        selected_row_return = self.selectedRow() #finding user selected row

        if selected_row_return != None:
            gid = self.download_table.item(selected_row_return , 8 ).text() #finding gid
            download_status = self.download_table.item(selected_row_return , 1).text() #finding download status
            if download_status == 'complete':
            #finding download path
                add_link_dictionary_str = self.download_table.item(selected_row_return , 9).text() 
                add_link_dictionary = ast.literal_eval(add_link_dictionary_str) 
                if 'file_path' in add_link_dictionary :
                    file_path = add_link_dictionary ['file_path']
                    file_path_split = file_path.split('/')
                    del file_path_split[-1]
                    download_path = '/'.join(file_path_split)
                    if os.path.isdir(download_path):
                        osCommands.xdgOpen(download_path) #openning file
                    else:
                        notifySend(str(download_path) ,'Not Found' , 5000 , 'warning' , systemtray = self.system_tray_icon ) #showing error message , if folder did't existed


#this function is executing(openning) download file if download was finished
    def openFile(self,menu):
        selected_row_return = self.selectedRow() #finding user selected row

        if selected_row_return != None:
            gid = self.download_table.item(selected_row_return , 8 ).text() #finding gid
            download_status = self.download_table.item(selected_row_return , 1).text() #finding download status
            if download_status == 'complete':
                #finding file path
                add_link_dictionary_str = self.download_table.item(selected_row_return , 9).text() 
                add_link_dictionary = ast.literal_eval(add_link_dictionary_str) 
                if 'file_path' in add_link_dictionary:
                    file_path = add_link_dictionary['file_path']
                    if os.path.isfile(file_path):
                        osCommands.xdgOpen(file_path) #openning file
                    else:
                        notifySend(str(file_path) ,'Not Found' , 5000 , 'warning' , systemtray = self.system_tray_icon ) #showing error message , if file was deleted or moved

    def removeButtonPressed(self,button):
        self.removeAction.setEnabled(False)
        global remove_flag
        if remove_flag !=3 :
            remove_flag = 1
            while remove_flag != 2 :
                sleep(0.1)
        selected_row_return = self.selectedRow()
        if selected_row_return != None:
            gid = self.download_table.item(selected_row_return , 8 ).text()
            file_name = self.download_table.item(selected_row_return , 0).text()
            status = self.download_table.item(selected_row_return , 1).text()

            self.download_table.removeRow(selected_row_return)

#remove gid of download from download list file
            f = Open(download_list_file)
            download_list_file_lines = f.readlines()
            f.close()
            f = Open(download_list_file , "w")
            for i in download_list_file_lines:
                if i.strip() != gid:
                    f.writelines(i.strip() + "\n")
            f.close()
#remove gid of download from active download list file
            f = Open(download_list_file_active)
            download_list_file_active_lines = f.readlines()
            f.close()
            f = Open(download_list_file_active , "w")
            for i in download_list_file_active_lines:
                if i.strip() != gid:
                    f.writelines(i.strip() + "\n")
            f.close()
#remove download_info_file
            download_info_file = download_info_folder + "/" + gid
            f = Open(download_info_file)
            f.close()
            f.remove()
#remove file of download form download temp folder
            if file_name != '***' and status != 'complete' :
                file_name_path = temp_download_folder + "/" +  str(file_name)
                osCommands.remove(file_name_path) #removing file

                file_name_aria = file_name_path + str('.aria2')
                osCommands.remove(file_name_aria) #removin file.aria 
        else:
            self.statusbar.showMessage("Please select an item first!")
        remove_flag = 0
        self.selectedRow()





    def deleteFile(self,menu):
        selected_row_return = self.selectedRow() #finding user selected row

        global remove_flag
        remove_flag = 1
        while remove_flag != 2 :
            sleep(0.1)
#This section is checking the download status , if download was completed then download file is removing
        if selected_row_return != None:
            gid = self.download_table.item(selected_row_return , 8 ).text()
            download_status = self.download_table.item(selected_row_return , 1).text()
            if download_status == 'complete':
                add_link_dictionary_str = self.download_table.item(selected_row_return , 9).text() 
                add_link_dictionary = ast.literal_eval(add_link_dictionary_str) 
                if 'file_path' in add_link_dictionary:
                    file_path = add_link_dictionary['file_path'] #finding file_path from add_link_dictionary
                    remove_answer = osCommands.remove(file_path) #removing file_path file
                    if remove_answer == 'no': #notifiying user if file_path is not valid
                        notifySend(str(file_path) ,'Not Found' , 5000 , 'warning' , systemtray = self.system_tray_icon )
                    remove_flag = 3
                    self.removeButtonPressed(menu)

    def selectDownloads(self,menu):
        if self.selectAction.isChecked() == True:
#selectAllAction is checked >> activating actions and adding removeSelectedAction and deleteSelectedAction to the toolBar
            self.toolBar.clear()
            for i in self.addlinkAction,self.resumeAction, self.pauseAction , self.stopAction, self.removeSelectedAction , self.deleteSelectedAction , self.propertiesAction, self.progressAction, self.minimizeAction , self.exitAction :
                self.toolBar.addAction(i)
         

            self.toolBar.insertSeparator(self.addlinkAction)
            self.toolBar.insertSeparator(self.resumeAction)     
            self.toolBar.insertSeparator(self.removeSelectedAction)
            self.toolBar.insertSeparator(self.exitAction)
            self.toolBar.addSeparator()

            for i in range(self.download_table.rowCount()):
                item = self.download_table.item(i , 0)
                item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                item.setCheckState(QtCore.Qt.Unchecked)
                self.selectAllAction.setEnabled(True)
                self.removeSelectedAction.setEnabled(True)
                self.deleteSelectedAction.setEnabled(True)
                 
        else:
#selectAction is unchecked deactivate actions and adding removeAction and deleteFileAction to the toolBar
            self.toolBar.clear()
            for i in self.addlinkAction,self.resumeAction, self.pauseAction , self.stopAction, self.removeAction , self.deleteFileAction , self.propertiesAction, self.progressAction , self.minimizeAction  , self.exitAction :
                self.toolBar.addAction(i)
         

            self.toolBar.insertSeparator(self.addlinkAction)
            self.toolBar.insertSeparator(self.resumeAction)     
            self.toolBar.insertSeparator(self.removeSelectedAction)
            self.toolBar.insertSeparator(self.exitAction)
            self.toolBar.addSeparator()
 
            for i in range(self.download_table.rowCount()):
                item_text = self.download_table.item(i , 0).text()
                item = QTableWidgetItem(item_text) 
                self.download_table.setItem(i , 0 , item)
                self.selectAllAction.setEnabled(False)
                self.removeSelectedAction.setEnabled(False)
                self.deleteSelectedAction.setEnabled(False)
                


    def selectAll(self,menu):
        for i in range(self.download_table.rowCount()):
            item = self.download_table.item(i , 0)
            item.setCheckState(QtCore.Qt.Checked)
 
    def removeSelected(self,menu):
#if remove_flag is equal to 1, it means that user pressed remove or delete button . so checking download information must stop until removing done!

        global remove_flag
        remove_flag = 1
        while remove_flag != 2 :
            sleep(0.1)

 #finding checked rows! and append gid of checked rows to gid_list
        gid_list = []
        for row in range(self.download_table.rowCount()):
            status = self.download_table.item(row , 1).text() 
            item = self.download_table.item(row , 0)
            if (item.checkState() == 2) and (status == 'complete' or status == 'error' or status == 'stopped' ):
                gid = self.download_table.item(row , 8 ).text()
                gid_list.append(gid)

#removing checked rows
        for gid in gid_list:        
            for i in range(self.download_table.rowCount()):
                row_gid = self.download_table.item(i , 8).text()
                if gid == row_gid :
                    row = i 
                    break

           
            file_name = self.download_table.item(row , 0).text()

            self.download_table.removeRow(row)

#remove gid of download from download list file
            f = Open(download_list_file)
            download_list_file_lines = f.readlines()
            f.close()
            f = Open(download_list_file , "w")
            for i in download_list_file_lines:
                if i.strip() != gid:
                    f.writelines(i.strip() + "\n")
            f.close()
#remove gid of download from active download list file
            f = Open(download_list_file_active)
            download_list_file_active_lines = f.readlines()
            f.close()
            f = Open(download_list_file_active , "w")
            for i in download_list_file_active_lines:
                if i.strip() != gid:
                    f.writelines(i.strip() + "\n")
            f.close()
#remove download_info_file
            download_info_file = download_info_folder + "/" + gid
            f = Open(download_info_file)
            f.close()
            f.remove()
#remove file of download form download temp folder
            if file_name != '***' and status != 'complete' :
                file_name_path = temp_download_folder + "/" +  str(file_name)
                osCommands.remove(file_name_path) #removing file : file_name_path
                file_name_aria = file_name_path + str('.aria2')
                osCommands.remove(file_name_aria) #removing aria2 information file *.aria

        remove_flag = 0

    def deleteSelected(self,menu):
#if remove_flag is equal to 1, it means that user pressed remove or delete button . so checking download information must stop until removing done!

        global remove_flag
        remove_flag = 1
        while remove_flag != 2 :
            sleep(0.1)
#finding checked rows! and append gid of checked rows to gid_list
        gid_list = []
        for row in range(self.download_table.rowCount()):
            status = self.download_table.item(row , 1).text() 
            item = self.download_table.item(row , 0)
            if (item.checkState() == 2) and (status == 'complete' or status == 'error' or status == 'stopped' ):
                gid = self.download_table.item(row , 8 ).text()
                gid_list.append(gid)

#removing checked rows
        for gid in gid_list:        
            for i in range(self.download_table.rowCount()):
                row_gid = self.download_table.item(i , 8).text()
                if gid == row_gid :
                    row = i 
                    break
            file_name = self.download_table.item(row , 0).text()
            add_link_dictionary_str = self.download_table.item(row , 9).text() 
            add_link_dictionary = ast.literal_eval(add_link_dictionary_str) 


            self.download_table.removeRow(row)
#remove gid of download from download list file
            f = Open(download_list_file)
            download_list_file_lines = f.readlines()
            f.close()
            f = Open(download_list_file , "w")
            for i in download_list_file_lines:
                if i.strip() != gid:
                    f.writelines(i.strip() + "\n")
            f.close()
#remove gid of download from active download list file
            f = Open(download_list_file_active)
            download_list_file_active_lines = f.readlines()
            f.close()
            f = Open(download_list_file_active , "w")
            for i in download_list_file_active_lines:
                if i.strip() != gid:
                    f.writelines(i.strip() + "\n")
            f.close()


#remove download_info_file
            download_info_file = download_info_folder + "/" + gid
            f = Open(download_info_file)
            f.close()
            f.remove()

#remove file of download form download temp folder
            if file_name != '***' and status != 'complete' :
                file_name_path = temp_download_folder + "/" +  str(file_name)
                osCommands.remove(file_name_path) #removing file : file_name_path

                file_name_aria = file_name_path + str('.aria2') #removing aria2 download information file : file_name_aria
                osCommands.remove(file_name_aria)
#remove download file
            if status == 'complete':
                if 'file_path' in add_link_dictionary:
                    file_path = add_link_dictionary['file_path']
                    remove_answer = osCommands.remove(file_path)
                    if remove_answer == 'no':
                        notifySend(str(file_path) ,'Not Found' , 5000 , 'warning' , systemtray = self.system_tray_icon )

        remove_flag = 0

    def saveWindowSize(self):
#finding last windows_size that saved in windows_size file
        windows_size = config_folder + '/windows_size'
        f = Open(windows_size)
        windows_size_file_lines = f.readlines()
        f.close()
        windows_size_dict_str = str(windows_size_file_lines[0].strip())
        windows_size_dict = ast.literal_eval(windows_size_dict_str) 

        
#getting current windows_size
        width = int(self.frameGeometry().width())
        height = int(self.frameGeometry().height())
#replacing current size with old size in window_size_dict
        windows_size_dict ['MainWindow_Ui'] = [ width , height ]
        f = Open(windows_size, 'w')
        f.writelines(str(windows_size_dict))
        f.close()


