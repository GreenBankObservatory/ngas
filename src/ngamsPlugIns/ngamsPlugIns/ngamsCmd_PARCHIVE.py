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
#
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# chen.wu@icrar.org   6-Mar-2012    created
"""
This command forwards the QARCHIVE request to another remote NGAS server C (where files
MAY be physically stored, MAYBE not since C can forwards the request to another NGAS server.

The URL of C is encoded in this command's URI parameter "nexturl"

PARCHIVE CMD is very similar to the original QARCHIVE CMD, the only difference is that
instead of saveFromHttpToFile, it saveFromHttpToAnotherHttp
"""

import binascii
import logging
import os
import time

from six.moves import http_client as httplib  # @UnresolvedImport
from six.moves.urllib import request as urlrequest  # @UnresolvedImport

from ngamsLib.ngamsCore import NGAMS_SUCCESS, NGAMS_HTTP_SUCCESS, \
    NGAMS_FAILURE, NGAMS_HTTP_POST, getHostName, \
    NGAMS_HTTP_HDR_CHECKSUM, TRACE, genLog, NGAMS_IDLE_SUBSTATE
from ngamsLib import ngamsStatus, ngamsHighLevelLib,  ngamsLib


logger = logging.getLogger(__name__)

def processHttpReply(http, basename, url):
    """
    After file is sent, collect the ngams status from the remote server
    parse error message, and log if necessary

    http:        the HTTP Client

    basename    Name of the file sent to the remote ngas server (used in the content disposition)

    url:        the url of the remote ngas server that receives the file
    """
    logger.debug("Waiting for reply ...")
    # ngamsLib._setSocketTimeout(None, http)
    reply, msg, hdrs = http.getreply()
    if (hdrs == None):
        errMsg = "Illegal/no response to HTTP request encountered!"
        raise Exception(errMsg)

    if (hdrs.has_key("content-length")):
        dataSize = int(hdrs["content-length"])
    else:
        dataSize = 0

    data = http.getfile().read(dataSize)

    stat = ngamsStatus.ngamsStatus()
    if (data.strip() != ""):
        stat.clear().unpackXmlDoc(data)
    else:
        # TODO: For the moment assume success in case no
        #       exception was thrown.
        stat.clear().setStatus(NGAMS_SUCCESS)

    if ((reply != NGAMS_HTTP_SUCCESS) or
                (stat.getStatus() == NGAMS_FAILURE)):
        errMsg = 'Error occurred while proxy quick archive file %s to %s' % (basename, url)
        if (stat.getMessage() != ""):
            errMsg += " Message: " + stat.getMessage()
        raise Exception(errMsg)

def buildHttpClient(url,
                    mimeType,
                    contentDisp,
                    contentLength,
                    checksum = None):
    """
    construct the http client which sends file data to the remote next url

    Returns:        httplib
    """
    # Separate the URL from the command.
    idx = (url[7:].find("/") + 7)
    tmpUrl = url[7:idx]
    cmd    = url[(idx + 1):]
    http = httplib.HTTP(tmpUrl)

    logger.debug("Sending HTTP header ...")
    logger.debug("HTTP Header: %s: %s", NGAMS_HTTP_POST, cmd)
    http.putrequest(NGAMS_HTTP_POST, cmd)
    logger.debug("HTTP Header: Content-Type: %s", mimeType)
    http.putheader("Content-Type", mimeType)

    logger.debug("HTTP Header: Content-Disposition: %s", contentDisp)
    http.putheader("Content-Disposition", contentDisp)
    logger.debug("HTTP Header: Content-Length: %s", str(contentLength))
    http.putheader("Content-Length", str(contentLength))

    logger.debug("HTTP Header: Host: %s", getHostName())
    http.putheader("Host", getHostName())

    if (checksum):
        http.putheader(NGAMS_HTTP_HDR_CHECKSUM, checksum)

    http.endheaders()
    logger.debug("HTTP header sent")

    # rtobar, 14/3/16: the default timeout here was 1 [hr]! I'm keeping it like
    #                  that, but probably it's too much
    http._conn.sock.settimeout(3600)

    return http


def saveFromHttpToHttp(reqPropsObj,
                       basename,
                       blockSize,
                       rfile,
                       reportHost = None,
                       checkCRC = 0):
    """
    Save the data available on an HTTP channel into the given file.

    ngamsCfgObj:     NG/AMS Configuration object (ngamsConfig).

    reqPropsObj:     NG/AMS Request Properties object (ngamsReqProps).

    basename:        filename that will be put into HTTP content disposition (string).

    blockSize:       Block size (bytes) to apply when reading the data
                     from the HTTP channel (integer).

    Returns:         Tuple. Element 0: Time in took to write
                     file (s) (tuple).
    """
    T = TRACE()

    mimeType = reqPropsObj.getMimeType()
    nexturl = reqPropsObj.getHttpPar('nexturl')
    if (reqPropsObj.hasHttpPar('reporturl')):
        rpurl = reqPropsObj.getHttpPar('reporturl')
    else:
        rpurl = None
    #path = reqPropsObj.getHttpHdr('path')
    #nexturl = path.split('=')[1]
    contDisp = "attachment; filename=\"" + basename + "\""
    contDisp += "; no_versioning=1"

    logger.debug("Transferring data to : %s", nexturl)

    start = time.time()

    http = None

    try:
        # Distinguish between Archive Pull and Push Request. By Archive
        # Pull we may simply read the file descriptor until it returns "".
        sizeKnown = 0
        if (reqPropsObj.is_GET() and
            not reqPropsObj.getFileUri().startswith('http://')):
            # (reqPropsObj.getSize() == -1)):
            # Just specify something huge.
            logger.debug("It is an Archive Pull Request/data with unknown size")
            remSize = int(1e11)
        elif reqPropsObj.getFileUri().startswith('http://'):
            logger.debug("It is an HTTP Archive Pull Request: trying to get Content-Length")
            httpInfo = rfile.info()
            headers = httpInfo.headers
            hdrsDict = ngamsLib.httpMsgObj2Dic(''.join(headers))
            if hdrsDict.has_key('content-length'):
                remSize = int(hdrsDict['content-length'])
            else:
                logger.debug("No HTTP header parameter Content-Length!")
                logger.debug("Header keys: %s",hdrsDict.keys())
                remSize = int(1e11)
        else:
            remSize = reqPropsObj.getSize()
            logger.debug("Archive Push/Pull Request - Data size: %d", remSize)
            sizeKnown = 1

        http = buildHttpClient(nexturl, mimeType, contDisp, remSize, checksum = reqPropsObj.getHttpHdr(NGAMS_HTTP_HDR_CHECKSUM))

        # Receive the data.
        buf = "-"
        rdSize = blockSize
        slow = blockSize / (512 * 1024.)  # limit for 'slow' transfers
#        sizeAccu = 0
        lastRecepTime = time.time()
        rdtt = 0  # total read time
        wdtt = 0  # total write time
        nb = 0    # number of blocks
        srb = 0   # number of slow read blocks
        swb = 0   # number of slow write blocks
        tot_size = 0 # total number of bytes
        nfailread = 0
        crc = 0   # initialize CRC value
        while ((remSize > 0) and ((time.time() - lastRecepTime) < 30.0)):
            if (remSize < rdSize): rdSize = remSize
            rdt = time.time()
            buf = rfile.read(rdSize)
            rdt = time.time() - rdt
            if (rdt > slow):
                srb += 1
            rdtt += rdt

            sizeRead = len(buf)
            remSize -= sizeRead
            tot_size += sizeRead

            if (sizeRead > 0):
                if (checkCRC):
                    crc = binascii.crc32(buf, crc)
                wdt = time.time()
                http._conn.sock.sendall(buf)
                wdt = time.time() - wdt
                wdtt += wdt
                if wdt >= slow: swb += 1
                nb += 1
                lastRecepTime = time.time()
            else:
                logger.debug("Unsuccessful read attempt from HTTP stream! Sleeping 50 ms")
                nfailread += 1
                time.sleep(0.050)

        deltaTime = time.time() -start
        reqPropsObj.setBytesReceived(tot_size)

        logger.debug("Data sent")
        logger.debug("Receiving transfer time: %.3f s; Sending transfer time %.3f s", rdtt, wdtt)
        msg = "Sent data in file: %s. Bytes received / sent: %d. Time: %.3f s. " +\
              "Rate: %.2f Bytes/s"
        logger.debug(msg, basename, int(reqPropsObj.getBytesReceived()),
                      deltaTime, (float(reqPropsObj.getBytesReceived()) /
                                  deltaTime))
        # Raise a special info message if the transfer speed to disk or over network was
        # slower than 512 kB/s
        if srb > 0:
            logger.warning("Number of slow network reads during this transfer: %d out of %d blocks. \
            Consider checking the upstream network link!", srb, nb)
        if swb > 0:
            logger.warning("Number of slow network sends during this transfer: %d out of %d blocks. \
            Consider checking your downstream network link!", swb, nb)
        if nfailread > 0:
            logger.warning("Number of failed reads during this transfer: %d out of %d blocks. \
            Consider checking your upstream network!", nfailread, nb)
        # Raise exception if less byes were received as expected.
        if (sizeKnown and (remSize > 0)):
            msg = genLog("NGAMS_ER_ARCH_RECV",
                         [reqPropsObj.getFileUri(), reqPropsObj.getSize(),
                          (reqPropsObj.getSize() - remSize)])
            raise Exception(msg)

        if (checkCRC):
            checksum = reqPropsObj.getHttpHdr(NGAMS_HTTP_HDR_CHECKSUM)
            if (checksum):
                if (checksum != str(crc)):
                    msg = 'Checksum error for file %s, proxy crc = %s, but remote crc = %s' % (reqPropsObj.getFileUri(), str(crc), checksum)
                    raise Exception(msg)
                else:
                    logger.debug("%s CRC checked, OK!", reqPropsObj.getFileUri())


        processHttpReply(http, basename, nexturl)
    except Exception as err:
        if (str(err).find('Connection refused') > -1):
            # The host on the nexturl is probably down
            logger.exception("Fail to connect to the nexturl '%s'", nexturl)
            # report this incident if the reporturl is available

            if (rpurl):
                logger.debug('Reporing this error to %s', rpurl)
                urlreq = '%s?errorurl=%s&file_id=%s' % (rpurl, nexturl, basename)
                try:
                    urlrequest.urlopen(urlreq)
                except Exception:
                    logger.exception("Cannot report the error of nexturl '%s' to reporturl '%s' either", nexturl, rpurl)

            if (reportHost):
                try:
                    rereply = urlrequest.urlopen('http://%s/report/hostdown?file_id=%s&next_url=%s' % (reportHost, basename, urllib2.quote(nexturl)), timeout = 15).read()
                    logger.info('Reply from sending file %s host-down event to server %s - %s', basename, reportHost, rereply)
                except Exception:
                    logger.exception('Fail to send host-down event to server %s', reportHost)

        raise err
    finally:
        if (http != None):
            #http.close()
            del http

def handleCmd(srvObj,
              reqPropsObj,
              httpRef):
    """
    Handle the Proxy Quick Archive (PROXYQARCHIVE) Command.

    srvObj:         Reference to NG/AMS server class object (ngamsServer).

    reqPropsObj:    Request Property object to keep track of actions done
                    during the request handling (ngamsReqProps).

    httpRef:        Reference to the HTTP request handler
                    object (ngamsHttpRequestHandler).

    Returns:        Void.
    """
    T = TRACE()
    # Check if the URI is correctly set.
    logger.debug("Check if the URI is correctly set.")
    if (reqPropsObj.getFileUri() == ""):
        errMsg = genLog("NGAMS_ER_MISSING_URI")
        raise Exception(errMsg)

    #path = reqPropsObj.getHttpHdr('path')
    if (not reqPropsObj.hasHttpPar('nexturl')):
        errMsg = "Paremeter 'nexturl' is missing."
        raise Exception(errMsg)

    # Get mime-type (try to guess if not provided as an HTTP parameter).
    logger.debug("Get mime-type (try to guess if not provided as an HTTP parameter).")
    if (reqPropsObj.getMimeType() == ""):
        mimeType = ngamsHighLevelLib.\
                   determineMimeType(srvObj.getCfg(), reqPropsObj.getFileUri())
        reqPropsObj.setMimeType(mimeType)

    ## Set reference in request handle object to the read socket.
    logger.debug("Set reference in request handle object to the read socket.")
    rfile = httpRef.rfile
    if reqPropsObj.getFileUri().startswith('http://'):
        readFd = urlrequest.urlopen(reqPropsObj.getFileUri())
        rfile = readFd

    logger.debug("Generate basename filename from URI: %s", reqPropsObj.getFileUri())
    if (reqPropsObj.getFileUri().find("file_id=") >= 0):
        file_id = reqPropsObj.getFileUri().split("file_id=")[1]
        baseName = os.path.basename(file_id)
    else:
        baseName = os.path.basename(reqPropsObj.getFileUri())

    blockSize = srvObj.getCfg().getBlockSize()
    jobManHost = srvObj.getCfg().getNGASJobMANHost()
    doCRC = srvObj.getCfg().getProxyCRC()
    if (jobManHost):
        saveFromHttpToHttp(reqPropsObj, baseName, blockSize, rfile, reportHost = jobManHost, checkCRC = doCRC)
    else:
        saveFromHttpToHttp(reqPropsObj, baseName, blockSize, rfile, checkCRC = doCRC)

    # Request after-math ...
    srvObj.setSubState(NGAMS_IDLE_SUBSTATE)
    msg = "Successfully handled Proxy (Quick) Archive Pull Request for data file " +\
          "with URI: " + reqPropsObj.getSafeFileUri()
    logger.info(msg)
    return msg