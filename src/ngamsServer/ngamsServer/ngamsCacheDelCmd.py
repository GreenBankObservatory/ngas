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
# "@(#) $Id: ngamsCacheDelCmd.py,v 1.2 2008/08/19 20:51:50 jknudstr Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  31/07/2008  Created
#

"""
Contains code for handling the CACHEDEL Command.
"""

import logging

from ngamsLib.ngamsCore import NGAMS_HOST_LOCAL, NGAMS_HOST_CLUSTER, TRACE

from . import ngamsFileUtils, ngamsCacheControlThread


logger = logging.getLogger(__name__)

def cacheDel(srvObj,
             reqPropsObj,
             httpRef,
             diskId,
             fileId,
             fileVersion):
    """
    Schedule the file referenced for deletion from the NGAS Cache, or act
    as proxy and forward the CACHEDEL Command to the node concerned, or
    return an HTTP re-direction response.

    srvObj:       Reference to NG/AMS server class object (ngamsServer).

    reqPropsObj:  Request Property object to keep track of actions done
                  during the request handling (ngamsReqProps).

    httpRef:      Reference to the HTTP request handler
                  object (ngamsHttpRequestHandler).

    diskId:       Disk ID of volume hosting the file (string).

    fileId:       File ID for file to consider (string).

    fileVersion:  Version of file (integer).

    Returns:      Void.
    """
    # Get the info for the file matching the query.
    fileLocInfo = ngamsFileUtils.locateArchiveFile(srvObj, fileId, fileVersion,
                                                   diskId)
    fileLocation  = fileLocInfo[0]
    fileHostId    = fileLocInfo[1]
    if (fileLocation == NGAMS_HOST_LOCAL):
        msg = "Scheduling file for deletion from the cache according to " +\
              "CACHEDEL Command: %s/%s/%s"
        logger.info(msg, diskId, fileId, str(fileVersion))
        sqlFileInfo = (diskId, fileId, fileVersion)
        ngamsCacheControlThread.scheduleFileForDeletion(srvObj, sqlFileInfo)
        return "Handled CACHEDEL Command"

    elif (srvObj.getCfg().getProxyMode() or
          (fileLocInfo[0] == NGAMS_HOST_CLUSTER)):
        logger.debug("File is remote or located within the private network of " +\
             "the contacted NGAS system -- this server acting as proxy " +\
             "and forwarding request to remote NGAS system: %s", fileHostId)
        host, port = srvObj.get_remote_server_endpoint(fileHostId)
        httpRef.proxy_request(fileHostId, host, port)
    else:
        # Send back an HTTP re-direction response to the requestor.
        logger.debug("File to be deleted from the NGAS Cache is stored on a " +\
             "remote host not within private network, Proxy Mode is off " +\
             "- sending back HTTP re-direction response")
        host, port = srvObj.get_remote_server_endpoint(fileHostId)
        reqPropsObj.setCompletionTime(1)
        httpRef.redirect(host, port)


def handleCmd(srvObj,
                      reqPropsObj,
                      httpRef):
    """
    Handle CACHEDEL Command.

    srvObj:         Reference to NG/AMS server class object (ngamsServer).

    reqPropsObj:    Request Property object to keep track of actions done
                    during the request handling (ngamsReqProps).

    httpRef:        Reference to the HTTP request handler
                    object (ngamsHttpRequestHandler).

    Returns:        Void.
    """
    T = TRACE()

    diskId = None
    fileId = None
    fileVersion = None
    for httpPar in reqPropsObj.getHttpParNames():
        if (httpPar == "disk_id"):
            diskId = reqPropsObj.getHttpPar("disk_id")
        elif (httpPar == "file_id"):
            fileId = reqPropsObj.getHttpPar("file_id")
        elif (httpPar == "file_version"):
            fileVersion = int(reqPropsObj.getHttpPar("file_version"))
        else:
            pass
    if ((not diskId) or (not fileId) or (not fileVersion)):
        msg = "Must specify disk_id/file_id/file_version for " +\
              "CACHEDEL Command"
        raise Exception(msg)

    cacheDel(srvObj, reqPropsObj, httpRef, diskId, fileId, fileVersion)

# EOF
