#
#    (c) University of Western Australia
#    International Centre of Radio Astronomy Research
#    M468/35 Stirling Hwy
#    Perth WA 6009
#    Australia
#
#    Copyright by UWA,
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
# cwu      20/09/2013  Created

import logging
import os

from ngamsLib import ngamsPlugInApi
from ngamsLib.ngamsCore import NGAMS_SOCK_TIMEOUT_DEF, NGAMS_STATUS_CMD, NGAMS_FAILURE
from ngamsPClient import ngamsPClient


logger = logging.getLogger(__name__)

file_ext = ['.fits', '.png']

def _shouldSend(fileId):
    try:
        tokens = fileId.split('_')
        if (len(tokens) != 5):
            return False
        if (tokens[2] == 'XX' or tokens[2] == 'YY'):
            if (tokens[3] == 'r0.0' and tokens[4] == 'v1.0.fits'):
                freqs = tokens[1].split('-')
                bandwidth = (int(freqs[1][:-3]) - int(freqs[0]) + 1)
                if (bandwidth > 31 and bandwidth < 34):
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False
    except Exception:
        errMsg = '_shouldRetain in rri purge thread failed'
        logger.exception(errMsg)
        return True

def ngamsGLEAM_RRI_FilterPI(srvObj,
                          plugInPars,
                          filename,
                          fileId,
                          fileVersion = -1,
                          reqPropsObj = None):

    """
    srvObj:        Reference to NG/AMS Server Object (ngamsServer).

    plugInPars:    Parameters to take into account for the plug-in
                   execution (string).

    fileId:        File ID for file to test (string).

    filename:      Filename of (complete) (string).

    fileVersion:   Version of file to test (integer).

    reqPropsObj:   NG/AMS request properties object (ngamsReqProps).

    Returns:       0 if the file does not match, 1 if it matches the
                   conditions (integer/0|1).
    """
    match = 0
    fn, fext = os.path.splitext(fileId)
    if (fext.lower() in file_ext and # only send FITS files, no measurement sets
        _shouldSend(fileId) and # # only send files satisfying certain string pattern criteria
        srvObj.getDb().isLastVersion(fileId, fileVersion) ): # only send the (known) latest version
        parDic = []
        pars = ""
        if ((plugInPars != "") and (plugInPars != None)):
            pars = plugInPars
        elif (reqPropsObj != None):
            if (reqPropsObj.hasHttpPar("plug_in_pars")):
                pars = reqPropsObj.getHttpPar("plug_in_pars")
        parDic = ngamsPlugInApi.parseRawPlugInPars(pars)
        if (not parDic.has_key("remote_host") or
            not parDic.has_key("remote_port")):
            errMsg = "ngamsGLEAM_VUW_FilterPI: Missing Plug-In Parameter: " +\
                     "remote_host / remote_port"
            #raise Exception, errMsg
            logger.error(errMsg)
            return 1 # matched as if the remote checking is done

        host = parDic["remote_host"]
        sport = parDic["remote_port"]

        if (not sport.isdigit()):
            errMsg = "ngamsGLEAM_VUW_FilterPI: Invalid port number: " + sport
            logger.error(errMsg)
            return 1 # matched as if the filter does not exist

        port = int(sport)

        # Perform the matching.
        client = ngamsPClient.ngamsPClient(host, port, timeOut = NGAMS_SOCK_TIMEOUT_DEF)
        try:
            if (fileVersion == -1):
                fileVersion = 1
            rest = client.get_status(NGAMS_STATUS_CMD, pars=[["file_id", fileId], ["file_version", fileVersion]])
            # since the queue will be sorted based on ingestion date, this will ensure the versions are sent by order:
            # e.g. version1, version2, version3, otherwise, this method will have disordered versions sent
            if (rest.getStatus().find(NGAMS_FAILURE) != -1):
                return 1 # matched since file id does not exist

        except Exception as e:
            errMsg = "Error occurred during checking remote file status " +\
                         "ngamsGLEAM_VUW_FilterPI. Exception: " + str(e)
            logger.error(errMsg)
            return 1 # matched as if the filter does not exist
        #info(5, "filter return status = " + rest.getStatus())
        #info(4, "filter match = " + str(match))

    return match
