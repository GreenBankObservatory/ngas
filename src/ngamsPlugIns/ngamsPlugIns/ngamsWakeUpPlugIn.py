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
# "@(#) $Id: ngamsWakeUpPlugIn.py,v 1.4 2008/08/19 20:51:50 jknudstr Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  23/01/2002  Created
#
"""
Test WakeUp Plug-In to simulate the NGAS host suspension.
"""

import logging

from ngamsLib import ngamsHighLevelLib
from ngamsLib.ngamsCore import execCmd


logger = logging.getLogger(__name__)

def ngamsWakeUpPlugIn(srvObj,
                      hostId):
    """
    Wake-Up Plug-In to wake up a suspended NGAS host.

    srvObj:         Reference to instance of the NG/AMS Server (ngamsServer).

    hostId:         Name of NGAS host to be woken up (string).

    Returns:        Void.
    """
    hostDic = ngamsHighLevelLib.\
              getHostInfoFromHostIds(srvObj.getDb(), [hostId])
    if hostId not in hostDic:
        errMsg = "ngamsWakeUpPlugIn: Could not wake up host: " + hostId +\
                 " - host not defined in NGAS DB."
        raise Exception(errMsg)

    networkDevs = srvObj.getCfg().getWakeUpPlugInPars()
    cmdFormat = "sudo /sbin/ether-wake -i %s -b " +\
                hostDic[hostId].getMacAddress()
    logger.debug("Waking up suspended host: %s", hostId)
    for dev in networkDevs.split(","):
        cmd = cmdFormat % dev
        logger.debug("Broadcasting wake-up package - command: %s", cmd)
        stat, out, _ = execCmd(cmd)
        if (stat != 0):
            format = "ngamsWakeUpPlugIn: Problem waking up host: %s " +\
                     ". Error: %s."
            errMsg = format % (hostId, str(out).replace("\n", " "))
            raise Exception(errMsg)


# EOF
