#!/usr/bin/python
import os
import time
from datetime import datetime

from .settings import (
    db_User_Name, DB_User_Password, DB_Name, DB_Host)

backupDir = '/home/rcregsite/backup/'

now = datetime.now()
today = now.day

if int(today) in [7, 21]:

    datetime = time.strftime('%Y %m %d')
    datetimeBackupDir = backupDir + datetime+"/"

    if not os.path.exists(datetimeBackupDir):
        os.makedirs(datetimeBackupDir)

    mysqldump_cmd = ("mysqldump -u " + db_User_Name + " --password='"
                    + DB_User_Password + "' -h " + DB_Host + " --databases '"
                    + DB_Name + "' > '" + datetimeBackupDir + DB_Name + ".sql'")

    os.system(mysqldump_cmd)
    print "db copied"

else:
    print "No Scheduled DB backup today."
