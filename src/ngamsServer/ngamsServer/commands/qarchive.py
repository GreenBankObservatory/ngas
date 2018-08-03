#
#    ALMA - Atacama Large Millimiter Array
#    (c) European Southern Observatory, 2002
#    Copyright by ESO (in the framework of the ALMA collaboration),
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
# "@(#) $Id: ngamsCmd_QARCHIVE.py,v 1.6 2009/12/07 16:36:40 awicenec Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  03/02/2009  Created
#
"""
NGAS Command Plug-In, implementing a Quick Archive Command.

This works in a similar way as the 'standard' ARCHIVE Command, but has been
simplified in a few ways:

  - No replication to a Replication Volume is carried out.
  - Target disks are selected randomly, disregarding the Streams/Storage Set
    mappings in the configuration. This means that 'volume load balancing' is
    provided.
  - Archive Proxy Mode is not supported.
  - No probing for storage availability is supported.
"""

import logging

from ngamsLib.ngamsCore import NGAMS_IDLE_SUBSTATE
from ngamsServer import ngamsArchiveUtils


logger = logging.getLogger(__name__)

def handleCmd(srvObj,
              reqPropsObj,
              httpRef):
    """
    Handle the Quick Archive (QARCHIVE) Command.

    srvObj:         Reference to NG/AMS server class object (ngamsServer).

    reqPropsObj:    Request Property object to keep track of actions done
                    during the request handling (ngamsReqProps).

    httpRef:        Reference to the HTTP request handler
                    object (ngamsHttpRequestHandler).

    Returns:        (fileId, filePath) tuple.
    """

    mimeType = ngamsArchiveUtils.archiveInitHandling(srvObj, reqPropsObj, httpRef,
                                   do_probe=False, try_to_proxy=True)
    if (not mimeType):
        # Set ourselves to IDLE; otherwise we'll stay in BUSY even though we
        # are doing nothing
        srvObj.setSubState(NGAMS_IDLE_SUBSTATE)
        return

    ngamsArchiveUtils.dataHandler(srvObj, reqPropsObj, httpRef,
                                  volume_strategy=ngamsArchiveUtils.VOLUME_STRATEGY_RANDOM,
                                  pickle_request=False, sync_disk=False,
                                  do_replication=False)