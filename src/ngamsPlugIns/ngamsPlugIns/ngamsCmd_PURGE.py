#    ICRAR - International Centre for Radio Astronomy Research
#    Copyright by UWA (in the framework of the ICRAR)
#    All rights reserved
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston,
#    MA 02111-1307  USA
#
#******************************************************************************
#
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# cwu      2013-12-21  Created
#
"""
Retain the latest (or earliest) version of files on this host, and purge all previous (or subsequent) versions
Does not support multiple threads

Two important parameters:

keep_earliest    flag parameter (no value), if present, the command will keep earliest version (thus purging all later versions)
                 By default, this command keeps only the latest version (thus purging all previous versions)

pv_on_any_hosts  flag parameter (no value), this flag is only read if the flag keep_earliest is present (actually this should be changed)
                 if present, the command will consider all previous versions on all hosts within the NGAS cluster
                 Otherwise (default), the command only consider previous versions on the current host

                 For example, if a file has the first version on ngas_host_001, and a second version on ngas_host_002.

                 Now if we issue a purge command to ngas_host_002
                 Without pv_on_any_hosts by default, (e.g. http://ngas_host_002:7777/PURGE?keep_earliest)
                                                 the command will not remove the second version on ngas_host_002
                 With pv_on_any_hosts, (e.g. http://ngas_host_002:7777/PURGE?keep_earliest&pv_on_any_hosts)
                                                 the command will remove the second version on ngas_host_002

"""

import datetime
import logging
import threading

from ngamsLib.ngamsCore import NGAMS_TEXT_MT
from ngamsServer import ngamsDiscardCmd


logger = logging.getLogger(__name__)

QUERY_PREV_VER = "SELECT a.disk_id, a.file_id, a.file_version FROM ngas_files a, "+\
                 "(SELECT file_id, MAX(file_version) AS max_ver FROM ngas_files, ngas_disks WHERE ngas_files.disk_id = ngas_disks.disk_id AND ngas_disks.host_id = {0} GROUP BY file_id) c, " +\
                 "ngas_disks b "+\
                 "WHERE a.file_id = c.file_id AND a.file_version < c.max_ver AND a.disk_id = b.disk_id AND b.host_id = {1}"

QUERY_LATER_VER = "SELECT a.disk_id, a.file_id, a.file_version FROM ngas_files a, "+\
                 "(SELECT file_id, MIN(file_version) AS min_ver FROM ngas_files, ngas_disks WHERE ngas_files.disk_id = ngas_disks.disk_id AND ngas_disks.host_id = {0} GROUP BY file_id) c, " +\
                 "ngas_disks b "+\
                 "WHERE a.file_id = c.file_id AND a.file_version > c.min_ver AND a.disk_id = b.disk_id AND b.host_id = {1}"

# the previous versions can be On any (valid) hosts
QUERY_LATER_VER_POAH = "SELECT a.disk_id, a.file_id, a.file_version FROM ngas_files a, "+\
                 "(SELECT file_id, MIN(file_version) AS min_ver FROM ngas_files, ngas_disks WHERE ngas_files.disk_id = ngas_disks.disk_id AND ngas_disks.host_id <> '' GROUP BY file_id) c, " +\
                 "ngas_disks b "+\
                 "WHERE a.file_id = c.file_id AND a.file_version > c.min_ver AND a.disk_id = b.disk_id AND b.host_id = {0}"

purgeThrd = None
is_purgeThrd_running = False
total_todo = 0
num_done = 0

def _purgeThread(srvObj, reqPropsObj, httpRef):
    global is_purgeThrd_running, total_todo, num_done
    is_purgeThrd_running = True

    hostId = srvObj.getHostId()
    try:
        if (reqPropsObj.hasHttpPar("keep_earliest")): # early could be 1, or 2,...
            if (reqPropsObj.hasHttpPar("pv_on_any_hosts")):
                resDel = srvObj.getDb().query2(QUERY_LATER_VER_POAH, args=(hostId,)) # grab all later versions on this host to remove
            else:
                resDel = srvObj.getDb().query2(QUERY_LATER_VER, args=(hostId, hostId)) # grab all later versions on this host to remove
        else: # by default, keep latest
            resDel = srvObj.getDb().query2(QUERY_PREV_VER, args=(hostId, hostId)) # grab all previous versions to remove
        if not resDel:
            raise Exception('Could not find any files to discard / retain')
        else:
            total_todo = len(resDel)
            for fileDelInfo in resDel:
                try:
                    ngamsDiscardCmd._discardFile(srvObj, fileDelInfo[0], fileDelInfo[1], int(fileDelInfo[2]), execute = 1)
                    num_done += 1
                except Exception as e1:
                    if (str(e1).find('DISCARD Command can only be executed locally') > -1):
                        #warning(str(e1))
                        continue
                    else:
                        raise e1
    except Exception:
        errMsg = 'Fail to execute the retainThread'
        logger.exception(errMsg)
    finally:
        is_purgeThrd_running = False
        total_todo = 0
        num_done = 0

def handleCmd(srvObj, reqPropsObj, httpRef):
    """
    Purge all old versions on this host given a file id

    srvObj:         Reference to NG/AMS server class object (ngamsServer).

    reqPropsObj:    Request Property object to keep track of actions done
                    during the request handling (ngamsReqProps).

    httpRef:        Reference to the HTTP request handler
                    object (ngamsHttpRequestHandler).

    Returns:        Void.
    """
    # need to check if an existing worker thread is running, if so, return an error
    # TODO - should provide an option to force stop the thread, if it is still running

    global purgeThrd
    global is_purgeThrd_running
    if (is_purgeThrd_running):
        if (purgeThrd):
            msg = 'Thread %s has successfully purged %d out of %d files.\n' % (purgeThrd.getName(), num_done, total_todo)
            httpRef.send_data(msg, NGAMS_TEXT_MT)
        else:
            is_purgeThrd_running = False
            raise Exception('Purge thread\'s instance is gone!')
    else:
        args = (srvObj, reqPropsObj, httpRef)
        dt = datetime.datetime.now()
        thrdName = 'PURGE_THREAD_' + dt.strftime('%Y%m%dT%H%M%S') + '.' + str(dt.microsecond / 1000)
        purgeThrd = threading.Thread(None, _purgeThread, thrdName, args)
        purgeThrd.setDaemon(0)
        purgeThrd.start()
        msg = 'Thread %s is successfully launched to purge files.\n' % thrdName
        httpRef.send_data(msg, NGAMS_TEXT_MT)