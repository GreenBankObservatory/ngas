#
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
# Who       When        What
# --------  ----------  -------------------------------------------------------
# chen.wu@icrar.org   14-Mar-2012    created
"""
this command updates an existing subscriber's information
including priority, url, start_date, and num_concurrent_threads
"""

from ngams import *
import ngamsSubscriptionThread

import threading

def changeNumThreads(srvObj, subscrId, oldNum, newNum):         
    # key: threadName (unique), value - dummy 0
    deliveryThreadRefDic = srvObj._subscrDeliveryThreadDicRef
    # key: subscriberId, value - a List of deliveryThreads for that subscriber
    deliveryThreadList = srvObj._subscrDeliveryThreadDic[subscrId]
    
    if (oldNum > newNum):
        for tid in range(oldNum - 1, -1, -1):
            if (tid >= newNum):
                thrdName = NGAMS_DELIVERY_THR + subscrId + str(tid)
                del deliveryThreadRefDic[thrdName] # set the condition _deliveryThread will exit, see ngamsSubscriptionThread._checkStopDataDeliveryThread()
                del deliveryThreadList[tid]
    elif (oldNum < newNum):        
        num_threads = newNum - oldNum
        quChunks = srvObj._subscrQueueDic[subscrId]
        
        for tid in range(int(num_threads)):
            args = (srvObj, srvObj.getSubscriberDic()[subscrId], quChunks, srvObj._subscrFileCountDic, srvObj._subscrFileCountDic_Sem, None)
            thrdName = NGAMS_DELIVERY_THR + subscrId + str(oldNum - 1 + tid)
            deliveryThrRef = threading.Thread(None, ngamsSubscriptionThread._deliveryThread, thrdName, args)
            deliveryThrRef.setDaemon(0)
            deliveryThrRef.start()
            deliveryThreadList.append(deliveryThrRef)  
            deliveryThreadRefDic[thrdName] = 1
    

def handleCmd(srvObj,
              reqPropsObj,
              httpRef):
    """
    Handle the update subscriber (USUBSCRIBE) Command.
        
    srvObj:         Reference to NG/AMS server class object (ngamsServer).
    
    reqPropsObj:    Request Property object to keep track of actions done
                    during the request handling (ngamsReqProps).
        
    httpRef:        Reference to the HTTP request handler
                    object (ngamsHttpRequestHandler).
        
    Returns:        Void.
    """
    T = TRACE()
    errMsg = ''
    err = 0
    if (not reqPropsObj.hasHttpPar("subscr_id")):
        srvObj.reply(reqPropsObj, httpRef, NGAMS_HTTP_SUCCESS, NGAMS_FAILURE, #let HTTP returns OK so that curl can continue printing XML code
                 'UNSUBSCRIBE command failed: \'subscr_id\' is not specified')
        return
    
    subscrId = reqPropsObj.getHttpPar("subscr_id")
    if (not srvObj.getSubscriberDic().has_key(subscrId)):
        if (not reqPropsObj.hasHttpPar("subscr_id")):
            srvObj.reply(reqPropsObj, httpRef, NGAMS_HTTP_SUCCESS, NGAMS_FAILURE, #let HTTP returns OK so that curl can continue printing XML code
                 "UNSUBSCRIBE command failed: Cannot find subscriber '%s'" % subscrId)
        return
    
    if (reqPropsObj.hasHttpPar("suspend")):
        suspend = reqPropsObj.getHttpPar("suspend")
        suspend_processed = 0
        # could use locks, but the race condition should not really matter here if only one request of suspend is issued at a time (by a system admin?)
        if (suspend == 1 and srvObj._subscrSuspendDic[subscrId].is_set()): # suspend condition met
            srvObj._subscrSuspendDic[subscrId].clear()
            suspend_processed = 1
            action = 'SUSPENDED'
        elif (suspend == 0 and (not srvObj._subscrSuspendDic[subscrId].is_set())): # resume condition met
            srvObj._subscrSuspendDic[subscrId].set()
            suspend_processed = 1
            action = 'RESUMED'
        if (suspend_processed):
            reMsg = "Successfully %s for the subscriber %s" % (action, subscrId)
            srvObj.reply(reqPropsObj, httpRef, NGAMS_HTTP_SUCCESS, NGAMS_SUCCESS, reMsg)
        else:
            reMsg = "No suspend/resume action is taken for the subscriber %s" % subscrId
            srvObj.reply(reqPropsObj, httpRef, NGAMS_HTTP_SUCCESS, NGAMS_FAILURE, reMsg)
        return  
    
    subscriber = srvObj.getSubscriberDic()[subscrId]
    
    if (reqPropsObj.hasHttpPar("priority")):
        priority = reqPropsObj.getHttpPar("priority")
        subscriber.setPriority(priority)
    
    if (reqPropsObj.hasHttpPar("url")):
        priority = reqPropsObj.getHttpPar("url")
        subscriber.setUrl(priority)
    
    if (reqPropsObj.hasHttpPar("start_date")):
        priority = reqPropsObj.getHttpPar("start_date")
        tmpStartDate = reqPropsObj.getHttpPar("start_date")
        if (tmpStartDate.strip() != ""): startDate = tmpStartDate.strip()
        subscriber.setStartDate(startDate)
    
    if (reqPropsObj.hasHttpPar("filter_plug_in")):
        filterPi = reqPropsObj.getHttpPar("filter_plug_in")
        subscriber.setFilterPi(filterPi)
    
    if (reqPropsObj.hasHttpPar("plug_in_pars")):
        pipars = reqPropsObj.getHttpPar("plug_in_pars")
        subscriber.setFilterPiPars(pipars)
    
    if (reqPropsObj.hasHttpPar("concurrent_threads")):
        ccthrds = reqPropsObj.getHttpPar("concurrent_threads")
        origthrds = subscriber.getConcurrentThreads()
        if (ccthrds != origthrds):
            subscriber.setConcurrentThreads(ccthrds)
            try:
                changeNumThreads(srvObj, subscrId, origthrds, ccthrds)
            except Exception, e:
                msg = " Exception updating subscriber's concurrent threads: %s." % str(e)
                warning(msg)
                err += 1
                errMsg += msg    
    try:
        subscriber.write(srvObj.getDb())
    except Exception, e:
        msg = " Update subscriber in DB exception: %s." % str(e)
        warning(msg)
        err += 1
        errMsg += msg        
    if (err):
        srvObj.reply(reqPropsObj, httpRef, NGAMS_HTTP_SUCCESS, NGAMS_FAILURE, "UNSUBSCRIBE command failed. Exception: %s" % errMsg)
    else:
        srvObj.reply(reqPropsObj, httpRef, NGAMS_HTTP_SUCCESS, NGAMS_SUCCESS, "UNSUBSCRIBE command succeeded")