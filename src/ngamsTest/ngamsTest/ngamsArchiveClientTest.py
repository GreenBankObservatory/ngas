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
# "@(#) $Id: ngamsArchiveClientTest.py,v 1.7 2008/08/19 20:51:50 jknudstr Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  10/11/2003  Created
#
"""
This module contains the Test Suite for the NG/AMS Archive Client.
"""

import glob
import os
import shutil
import subprocess
import time
import unittest

from ngamsLib import ngamsStatus
from ngamsLib.ngamsCore import terminate_or_kill
from .ngamsTestLib import ngamsTestSuite, saveInFile, filterDbStatus1, \
    has_program


arcCliDir = "/tmp/ngamsTest/NGAMS_ARCHIVE_CLIENT"


@unittest.skipUnless(has_program('ngamsArchiveClient'), "No Archive C client")
class ngamsArchiveClientTest(ngamsTestSuite):
    """
    Synopsis:
    NG/AMS Archive Client.

    Description:
    Excersize the NG/AMS Archive Client and check that it can handle properly
    the various normal Use Cases but also the abnormal ones.

    It is important to verify that the buffering mechanism in the archive
    client works as expected so that no data is lost in case it is not
    possible (temporarily) to submit files for archiving to the spefied,
    remote NGAS Archive.

    Missing Test Cases:
    - Test that if a file which was archived is not found in the remote
      NGAS System, it remains in the Archived Files Area.
    """

    def setUp(self):
        ngamsTestSuite.setUp(self)
        self.client_proc = None

    def tearDown(self):
        if self.client_proc is not None:
            terminate_or_kill(self.client_proc, 20)
        ngamsTestSuite.tearDown(self)

    def startArchiveClient(self):
        cmd = ["ngamsArchiveClient",
               "-host", '127.0.0.1', "-port", "8888",
               "-rootDir", "/tmp/ngamsTest", "-pollTime", "5",
               "-checksum", "ngamsCrc32", "-cleanUpTimeOut", "10",
               "-logLevel", "3", "-logRotate", "0", "-logHistory", "2",
               "-v", "0"]
        self.client_proc = subprocess.Popen(cmd)

    def test_NormalOp_1(self):
        """
        Synopsis:
        Test normal operation of the NG/AMS Archive Client.

        Description:
        It is tested that a file can be archived via a link in the Archive
        Queue.

        Expected Result:
        After the archiving the link is moved to the Archive Files
        Area. It is also checked that the NG/AMS XML Status Document is
        created in the Archived Files Area. After the expiration time for
        keeping archived files has expired, the archived file and the XML
        status document should be deleted.

        Test Steps:
        - Start NG/AMS Server.
        - Start instance of the NG/AMS Archive Client.
        - Create a link from a legal test (FITS) file into the Archive Queue.
        - Test that the file is archived within 20s and moved to the Archived
          Files Area.
        - Test that the XML Status Document from NG/AMS is stored in the
          Archived Files Area.
        - Check that after the given expiration time for the Archived Files
          Area, that the archived file + the XML Status Document are removed.
        - Stop the Archive Client.

        Remarks:
        ...
        """
        self.prepExtSrv()

        # Make sure the the queue subdir exist before the launch the client;
        # otherwise the client and this test might find themselves in a race
        # condition and the test might fail
        d = os.path.abspath(os.path.join(arcCliDir, 'queue'))
        if not os.path.exists(d):
            os.makedirs(d)

        self.startArchiveClient()

        # Archive a file as copy and link.
        # Make sure at least the quee dir is already created
        srcFile = os.path.abspath("src/SmallFile.fits")
        shutil.copy(srcFile, os.path.join(arcCliDir, 'queue'))
        os.symlink(srcFile, os.path.join(arcCliDir, 'queue', 'Test.fits'))

        # Check that files are being archived (within 20s) + NG/AMS Status
        # Documents created.
        file1Pat     = arcCliDir + "/archived/*___SmallFile.fits"
        file1StatPat = file1Pat + "___STATUS.xml"
        file2Pat     = arcCliDir + "/archived/*___Test.fits"
        file2StatPat = file2Pat + "___STATUS.xml"
        startTime    = time.time()
        filesFound   = 0
        while ((time.time() - startTime) < 20):
            globFile1Pat     = glob.glob(file1Pat)
            globFile1StatPat = glob.glob(file1StatPat)
            globFile2Pat     = glob.glob(file2Pat)
            globFile2StatPat = glob.glob(file2StatPat)
            if ((len(globFile1Pat) == 1) and (len(globFile1StatPat) == 1) and
                (len(globFile2Pat) == 1) and (len(globFile2StatPat) == 1)):
                filesFound = 1
                break
        if (not filesFound):
            if (not len(globFile1Pat)):
                errMsg = "Did not find status file: " + file1Pat
            elif (not len(globFile1StatPat)):
                errMsg = "Did not find status XML document: " + file1StatPat
            elif (not len(globFile2Pat)):
                errMsg = "Did not find status file: " + file2Pat
            else:
                # (not len(globFile2StatPat)):
                errMsg = "Did not find status XML document: " + file2StatPat
            self.fail(errMsg)

        # Check the contents of one of the status documents.
        statObj = ngamsStatus.ngamsStatus().load(globFile1StatPat[0])
        refStatFile = "ref/ngamsArchiveClientTest_test_NormalOp_1_1_ref"
        tmpStatFile = saveInFile(None, filterDbStatus1(statObj.dumpBuf(),
                                                       ["BytesStored:",
                                                        "NumberOfFiles:",
                                                        "FileName:",
                                                        "FileVersion:"]))
        self.checkFilesEq(refStatFile, tmpStatFile,
                          "Incorrect info in Archive Command " +\
                          "XML Status Document")

        # Check that the status documents are removed within 10s.
        filesRemoved = 0
        startTime = time.time()
        while ((time.time() - startTime) < 20):
            globFile1Pat     = glob.glob(file1Pat)
            globFile1StatPat = glob.glob(file1StatPat)
            globFile2Pat     = glob.glob(file2Pat)
            globFile2StatPat = glob.glob(file2StatPat)
            if ((len(globFile1Pat) == 0) and (len(globFile1StatPat) == 0) and
                (len(globFile2Pat) == 0) and (len(globFile2StatPat) == 0)):
                filesRemoved= 1
                break
        if (not filesRemoved):
            if (len(globFile1Pat)):
                errMsg = "Did not remove status file: " + globFile1Pat[0]
            elif (len(globFile1StatPat)):
                errMsg = "Did not remove status XML document: " +\
                         globFile1StatPat[0]
            elif (len(globFile2Pat)):
                errMsg = "Did not remove status file: " + file2Pat[0]
            else:
                # (len(globFile2StatPat)):
                errMsg = "Did not remove status XML document: "+file2StatPat[0]
            self.fail(errMsg)