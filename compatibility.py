#!/usr/bin/env python3
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
import time
import os
import ast
#this script for compatibility between Version 2.0 and 2.1 of persepolis
home_address = os.path.expanduser("~")
config_folder = str(home_address) + "/.config/persepolis_download_manager"
download_info_folder = config_folder + "/download_info"
download_list_file = config_folder + "/download_list_file"
download_list_file_lines = []
if os.path.isdir(download_info_folder) == True :
    f = open(download_list_file)
    download_list_file_lines = f.readlines()
    f.close()

    for line in download_list_file_lines:
        gid = line.strip()
        download_info_file = download_info_folder + "/" + gid
        f_download_info_file = open(download_info_file) 
        download_info_file_lines = f_download_info_file.readlines()
        f_download_info_file.close()
        if len(download_info_file_lines) == 10 :
            list = []
            for i in range(10) :
                line_strip = download_info_file_lines[i].strip()
                if i == 9 :
                    line_strip = ast.literal_eval(line_strip)
                list.append(line_strip)
            dictionary =  {'list' : list }
            os.system('echo "' + str(dictionary) + '"  >  "' + str(download_info_file) + '"' )
            f_download_info_file = open (download_info_file , 'w')
            f_download_info_file.writelines(str(dictionary))
            f_download_info_file.close()
 
#compatibility between version 2.2 and version 2.3
    date_list = []
    for i in ['%Y' , '%m' , '%d' , '%H' , '%M' , '%S' ] :
        date_list.append(time.strftime(i))
 
    for line in download_list_file_lines:
        gid = line.strip()
        download_info_file = download_info_folder + "/" + gid
        f = open(download_info_file , 'r')
        f_string = f.readline()
        f.close()
        dictionary = ast.literal_eval(f_string.strip())
        list = dictionary ['list']

        if len(list) == 10 :
            add_link_dictionary = list[9]
            add_link_dictionary ['firs_try_date'] = date_list
            add_link_dictionary ['last_try_date'] = date_list

            list [9] = add_link_dictionary


            try_date = str(date_list[0]) + '/' + str(date_list[1]) + '/' + str(date_list[2]) + ' , ' + str(date_list[3]) + ':' +  str(date_list[4]) + ':' + str(date_list[5])
            
            list.append(try_date)
            list.append(try_date)

            dictionary =  {'list' : list }
            f = open(download_info_file , 'w')
            f.writelines(str(dictionary)) 
            f.close()


