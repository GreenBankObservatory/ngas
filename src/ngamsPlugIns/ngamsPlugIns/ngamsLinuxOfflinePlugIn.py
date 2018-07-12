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
# "@(#) $Id: ngamsLinuxOfflinePlugIn.py,v 1.5 2008/08/19 20:51:50 jknudstr Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  10/05/2001  Created.
#
"""
Module that contains a System Offline Plug-In used by the ESO NGAS
installations.
"""

import logging

from ngamsLib import ngamsPlugInApi
from ngamsLib.ngamsCore import genLog
from . import ngamsLinuxSystemPlugInApi
from .eso import ngamsEscaladeUtils


logger = logging.getLogger(__name__)

def ngamsLinuxOfflinePlugIn(srvObj,
                            reqPropsObj = None):
    """
    Function unmounts all NGAMS disks and removes the kernel module for
    the IDE controller card.

    srvObj:        Reference to instance of the NG/AMS Server class
                   (ngamsServer).

    reqPropsObj:   NG/AMS request properties object (ngamsReqProps).

    Returns:       Void.
    """
    rootMtPt = srvObj.getCfg().getRootDirectory()
    parDicOnline = ngamsPlugInApi.\
                   parseRawPlugInPars(srvObj.getCfg().getOnlinePlugInPars())

    # Old format = unfortunately some Disk IDs of WDC/Maxtor were
    # generated wrongly due to a mistake by IBM, which lead to a wrong
    # implementation of the generation of the Disk ID.
    if "old_format" not in parDicOnline:
        raise Exception("Missing Online Plug-In Parameter: old_format=0|1")
    else:
        oldFormat = int(parDicOnline["old_format"])

    # The controllers Plug-In Parameter, specifies the number of controller
    # in the system.
    if "controllers" not in parDicOnline:
        controllers = None
    else:
        controllers = parDicOnline["controllers"]

    # Select between 3ware WEB Interface and 3ware Command Line Tool.
    if (parDicOnline["uri"].find("http") != -1):
        diskDic = ngamsEscaladeUtils.\
                  parseHtmlInfo(parDicOnline["uri"], rootMtPt)
    else:
        diskDic = ngamsEscaladeUtils.parseCmdLineInfo(rootMtPt, controllers,
                                                      oldFormat, rescan=0)

    parDicOffline = ngamsPlugInApi.\
                    parseRawPlugInPars(srvObj.getCfg().getOfflinePlugInPars())

    # This is only unmounting the NGAMS disks and may lead to problems
    # if someone mounts other disks off-line.
    if "unmount" in parDicOffline:
        unmount = int(parDicOffline["unmount"])
    else:
        unmount = 1
    if (unmount):
        try:
            ngamsLinuxSystemPlugInApi.ngamsUmount(diskDic,
                                                  srvObj.getCfg().getSlotIds())
            if "module" in parDicOffline:
                stat = ngamsLinuxSystemPlugInApi.rmMod(parDicOnline["module"])
            else:
                stat = 0
            if (stat):
                errMsg = "Problem executing ngamsLinuxOfflinePlugIn! " +\
                         "The system is in not in a safe state!"
                errMsg = genLog("NGAMS_ER_OFFLINE_PLUGIN", [errMsg])
                raise Exception(errMsg)
            if "module" in parDicOffline:
                logger.info("Kernel module %s unloaded", parDicOnline["module"])
        except:
            pass

        # Fallback umount.
        ngamsLinuxSystemPlugInApi.umount(rootMtPt)