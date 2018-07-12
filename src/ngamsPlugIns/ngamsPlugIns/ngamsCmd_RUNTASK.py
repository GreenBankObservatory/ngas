#
#    ICRAR - International Centre for Radio Astronomy Research
#    (c) UWA - The University of Western Australia, 2012
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
# Who       When        What
# --------  ----------  -------------------------------------------------------
# cwu      28/May/2013  Created
"""
This module is responsible for running local tasks, i.e.
1. Maintain a task queue (this is important for mutually-exclusve GPU resource access)
2. Receive task execution request from the JobManager (running on another NGAS server)
3. Execute the task on local machine using local I/O
4. Receive task monitor request
5. Monitor task progress, including error handling
"""

import logging
import os
import threading

from six.moves import cPickle as pickle  # @UnresolvedImport
from six.moves.queue import Queue  # @UnresolvedImport
from six.moves.urllib import error as urlerror # @UnresolvedImport
from six.moves.urllib import parse as urlparse # @UnresolvedImport
from six.moves.urllib import request as urlrequest # @UnresolvedImport

from ngamsLib.ngamsCore import TRACE, NGAMS_TEXT_MT
from ngamsPClient import ngamsPClient
from ngamsPlugIns.mwa.job.ngamsJobProtocol import MRLocalTaskResult, ERROR_LT_UNEXPECTED


logger = logging.getLogger(__name__)

queScanThread = None
queTasks = Queue()
mime_type = 'application/octet-stream'
cancelDict = {} #key - taskId that has been cancelled, value - 1 (place holder)
g_mrLocalTask = None # the current running task

def _getPostContent(srvObj, reqPropsObj, httpRef):
    """
    Get the MapLocalTask sub-class from the HTTP Post
    """
    remSize = reqPropsObj.getSize()
    #info(3,"Post Data size: %d" % remSize)
    buf = httpRef.rfile.read(remSize) #TODO - use proper loop on read here! given remSize is small, should be okay for now
    sizeRead = len(buf)
    #info(3,"Read buf size: %d" % sizeRead)
    #info(3,"Read buf: %s" % buf)
    if (sizeRead == remSize):
        reqPropsObj.setBytesReceived(sizeRead)
    return buf

def _queScanThread(jobManHost, ngas_hostId, ngas_client):
    svrUrl = 'http://%s/localtask/result' % jobManHost
    dqUrl = 'http://%s/localtask/dequeue?task_id=' % jobManHost
    global g_mrLocalTask
    while (1):
        g_mrLocalTask = queTasks.get()
        # skip tasks that have been cancelled
        if (cancelDict.has_key(g_mrLocalTask._taskId)):
            logger.debug('Task %s has been cancelled, skip it', g_mrLocalTask._taskId)
            continue

        # before executing the task, inform JobMAN that
        # this task is just dequeued and about to start...
        try:
            strRes = urlrequest.urlopen(dqUrl + urlparse.quote(g_mrLocalTask._taskId), timeout = 15).read() #HTTP Get (need to encode url)
            if (strRes.find('Error response') > -1):
                logger.error('Error when sending dequeue event to JobMAN: %s', strRes)
        except urlerror.URLError as urlerr:
            logger.error('Fail to send dequeue event to JobMAN: %s', str(urlerr))

        # execute the task
        localTaskResult = None
        try:
            localTaskResult = g_mrLocalTask.execute()
        except Exception as execErr:
            logger.exception('Fail to execute task %s: Unexpected exception', g_mrLocalTask._taskId)
            localTaskResult = MRLocalTaskResult(g_mrLocalTask._taskId, ERROR_LT_UNEXPECTED, str(execErr), True)

        # archive the file locally if required
        if (localTaskResult.getErrCode() == 0 and
            localTaskResult.isResultAsFile()):
            fpath = localTaskResult.getInfo()
            #if (os.path.exists(fpath)):
            fpath = fpath.strip('\n') #get rid of the trailing '\n' produced by the python "print" statement in the localTask
            _archiveFileLocal(fpath, localTaskResult, ngas_hostId, ngas_client)
            #else:
                #warning('Cannot locate the image local path - %s' % fpath)

        #send result back to the JobMAN
        strReq = pickle.dumps(localTaskResult)
        logger.debug('Sending local result back to JobMAN %s', svrUrl)
        try:
            strRes = urlrequest.urlopen(svrUrl, data = strReq, timeout = 15).read() #HTTP Post
            logger.debug("Got result from JobMAN: '%s'", strRes)
        except urlerror.URLError:
            logger.exception('Fail to send local result to JobMAN')

def _archiveFileLocal(fpath, localTaskResult, ngas_hostId, ngas_client):
    try:
        stat = ngas_client.pushFile(fpath, mime_type, cmd = 'QARCHIVE')
    except Exception as e:
        errmsg = "Exception '%s' occurred while archiving file %s" % (str(e), fpath)
        logger.exception(errmsg)
        localTaskResult.setErrCode(1)
        localTaskResult.setInfo(errmsg)
        return
    msg = stat.getMessage().split()[0]
    if (msg != 'Successfully'):
        #raise Exception('Fail to archive \"%s\"' % fileUri)
        errmsg = "Exception '%s' occurred while archiving file %s" % (stat.getMessage(), fpath)
        logger.exception(errmsg)
        localTaskResult.setErrCode(1)
        localTaskResult.setInfo(errmsg)
    else:
        localTaskResult.setResultURL('http://%s/RETRIEVE?file_id=%s' % (ngas_hostId, os.path.basename(fpath)))

def _scheduleQScanThread(srvObj, mrLocalTask):
    global queScanThread
    if (queScanThread == None or (not queScanThread.isAlive())):
        if (not queScanThread):
            logger.debug('queScanThread is None !!! Create it')
        else:
            logger.debug('queScanThread is Dead !!! Re-launch it')

        ngas_hostId = srvObj.getHostId()
        ngas_host = ngas_hostId.split(':')[0]
        ngas_port = int(ngas_hostId.split(':')[1])
        ngas_client = ngamsPClient.ngamsPClient(ngas_host, ngas_port)

        jobManHost = srvObj.getCfg().getNGASJobMANHost()
        args = (jobManHost,ngas_hostId, ngas_client)
        queScanThread = threading.Thread(None, _queScanThread, 'QUESCAN_THRD', args)
        queScanThread.setDaemon(1)
        queScanThread.start()
    queTasks.put(mrLocalTask)

def handleCmd(srvObj,
              reqPropsObj,
              httpRef):
    """
    Handle the RUN TASK (RUNTASK) Command.

    srvObj:         Reference to NG/AMS server class object (ngamsServer).

    reqPropsObj:    Request Property object to keep track of actions done
                    during the request handling (ngamsReqProps).

    httpRef:        Reference to the HTTP request handler
                    object (ngamsHttpRequestHandler).

    Returns:        Void.
    """
    T = TRACE()
    global queScanThread
    httpMethod = reqPropsObj.getHttpMethod()
    if (httpMethod != 'POST'):
        errMsg = 'OK'
        if (reqPropsObj.hasHttpPar('action')):
            action_req = reqPropsObj.getHttpPar('action')
            if ('cancel' == action_req):
                if (reqPropsObj.hasHttpPar('task_id')):
                    taskId = reqPropsObj.getHttpPar('task_id')
                    cancelDict[taskId] = 1
                    if (g_mrLocalTask and taskId == g_mrLocalTask._taskId):
                        res = g_mrLocalTask.stop()
                        if (res[0]):
                            errMsg = 'Cancel result failed: %s\n' % str(res[1])
                else:
                    errMsg = 'task_id is missing'
            else:
                errMsg = 'Unknown RUNTASK command action %s' % action_req
        else:
            errMsg = 'RUNTASK command needs action for GET request\n'

        httpRef.send_data(errMsg, NGAMS_TEXT_MT)
    else:
        postContent = _getPostContent(srvObj, reqPropsObj, httpRef)
        mrLocalTask = pickle.loads(postContent)
        if (not mrLocalTask):
            errMsg = 'Cannot instantiate local task from POST'
            mrr = MRLocalTaskResult(None, -2, errMsg)
            httpRef.send_data(pickle.dumps(mrr), NGAMS_TEXT_MT)
        else:
            logger.debug('Local task %s is submitted', mrLocalTask._taskId)
            mrr = MRLocalTaskResult(mrLocalTask._taskId, 0, '')
            httpRef.send_data(pickle.dumps(mrr), NGAMS_TEXT_MT)

            args = (srvObj, mrLocalTask)
            scheduleThread = threading.Thread(None, _scheduleQScanThread, 'SCHEDULE_THRD', args)
            scheduleThread.setDaemon(0)
            scheduleThread.start()