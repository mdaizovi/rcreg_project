#!/usr/bin/python
import os
import time
from datetime import datetime

#from https://www.pythonanywhere.com/forums/topic/119/
# FYI, emergency reference: http://help.pythonanywhere.com/pages/MySQLBackupRestore/


############Production
# #mysqldump -u rcregsite -p -h rcregsite.mysql.pythonanywhere-services.com --databases 'rcregsite$default' > /home/rcregsite/dump.sql

db_User_Name = 'rcregsite'
DB_User_Password = 'mice4rice'
DB_Name = 'rcregsite$default'
DB_Host= db_User_Name+'.mysql.pythonanywhere-services.com'
backupDir = '/home/rcregsite/backup/'

now = datetime.now()
today=now.day
print "today is ",today

if int(today) in [7, 21]:

    datetime = time.strftime('%Y %m %d')
    datetimeBackupDir = backupDir + datetime+"/"

    print "finding backup folder"
    if not os.path.exists(datetimeBackupDir):
        print "creating backup folder"
        os.makedirs(datetimeBackupDir)

    mysqldump_cmd = "mysqldump -u " + db_User_Name + " --password='" + DB_User_Password + "' -h "+DB_Host+" --databases '" + DB_Name + "' > '" + datetimeBackupDir +DB_Name + ".sql'"
    #print "mysqldump_cmd ",mysqldump_cmd
    os.system(mysqldump_cmd)
    print "db dumped"

else:
    print "No Scheduled DB backup today.\n"
