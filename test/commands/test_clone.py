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
# "@(#) $Id: ngamsCloneCmdTest.py,v 1.6 2008/08/19 20:51:50 jknudstr Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  20/11/2003  Created
#
"""
This module contains the Test Suite for the CLONE Command.
"""

import functools

from ngamsLib.ngamsCore import getHostName, NGAMS_CLONE_CMD
from ngamsLib import ngamsFileInfo
from ..ngamsTestLib import ngamsTestSuite, waitReqCompl, genErrMsgVals, \
    unzip, genTmpFilename, tmp_path, as_ngas_disk_id


def _sortRepFileList(report):
    """
    Sorts a clone report file list such that it always has the same order.

    The Clone Status Report has the following contents, e.g.:

    <Email Header>

    CLONE STATUS REPORT:

    ==Summary:

    Disk ID:                    tmp-ngamsTest-NGAS-FitsStorage1-Main-1
    File ID:                    -----
    File Version:               -----
    Total Number of Files:      10
    Number of Cloned Files:     10
    Number of Failed Files:     0

    ==File List:

    Source File                        Target File                     Status
    ---------------------------------- ------------------------------- -------
    <File Clone Info>
    ...
    --------------------------------------------------------------------------

    We simply get out the lines between the '---...---'s and sort them.

    report:    Clone Status Report (string).

    Returns:   Sorted Clone Status Report (string).
    """
    sortBuf = ""
    repLines = report.split("\n")
    idx = -1
    while (1):
        idx += 1
        if idx >= len(repLines):
            return sortBuf
        sortBuf += repLines[idx] + "\n"
        if (repLines[idx].find("-----") == 0): break
    # Put the lines containing info about each file in a list, sort, and
    # add it in the final report.
    fileInfoLines = []
    while (1):
        idx += 1
        if (repLines[idx].find("-----") == 0): break
        fileInfoLines.append(repLines[idx])
    fileInfoLines.sort()
    for fileInfoLine in fileInfoLines:
        sortBuf += fileInfoLine + "\n"
    # Get the last part of the buffer.
    for line in repLines[idx:]:
        sortBuf += line + "\n"
    return sortBuf


# Test disks/files.
srcDiskId    = as_ngas_disk_id(tmp_path("NGAS/FitsStorage1/Main/1"))
trgDiskId    = as_ngas_disk_id(tmp_path("NGAS/FitsStorage3/Main/5"))
nmuTrgDiskId = as_ngas_disk_id(tmp_path("NGAS:8000/FitsStorage3/Main/5"))
ncuSrcDiskId = as_ngas_disk_id(tmp_path("NGAS:8011/FitsStorage1/Main/1"))
nmuFileId    = "TEST.2001-05-08T15:25:00.123"
ncuFileId    = "NCU.2003-11-11T11:11:11.111"
refFilePat1  = "ref/ngamsCloneCmdTest_test_NormalExec_%d_%d"
refFilePat2  = "ref/ngamsCloneCmdTest_test_ErrExec_%d_%d"


class ngamsCloneCmdTest(ngamsTestSuite):
    """
    Synopsis:
    Test Suite testing the CLONE Command.

    Description:
    ...

    Missing Test Cases:
    - Check handling of HTTP Authorization when cloning between node.
    - Check disk switching.
    - Clone Reporting/failed/successfull clonings.
    - Parallel handling of CLONE Commands.
    - Clone specifying:
      - Illegal file_id.
      - Illegal file_id/file_version.
      - Illegal file_id/file_version/disk_id.
      - Illegal disk_id.
      - Illegal target_disk_id.
      - target_disk_id is Replication Disk.
      - Disk ID of src disk = target_disk_id.
      - Disk ID, via File ID of src disk = target_disk_id.
      - Failed cloning, no free disks.
    - Check that cloning recovers from broken DB connection.
    - Check that cloning recovers from empty SQL query results.
    - If a file is cloned twice, it ends up on two Main Disks.
    - Estimation of required disk space is correct.
    - Rejection of CLONE Command when the required disk space is not enough.
    """

    mail_startwith_filters = (
        'NGAS Host:', 'Total processing time (s): ', 'Handling time per file (s): ')

    def assert_clone_mail(self, ref_file, msg):
        mail = self.smtp_server.pop()
        self.assertTrue(mail.is_multipart())
        parts_iter = iter(mail.walk())
        next(parts_iter)
        part = next(parts_iter)
        mail_body = _sortRepFileList(part.get_payload())
        self.assert_ref_file(ref_file, mail_body, msg=msg,
                            startswith_filters=self.mail_startwith_filters)


    def _test_clone(self, testData, refStatFile, mail_expected=True):
        """
        Execute the Clone Command Test based on the given input data. There is
        always waited for command execution.
        """

        self.start_smtp_server()

        diskId, fileId, fileVer, trgDisk, subNode = testData
        if subNode:
            self.prepCluster((8000, 8011))
            main_archive = functools.partial(self.archive, 8000)
            node_archive = functools.partial(self.archive, 8011)
            main_client = self.client(8000)
        else:
            self.prepExtSrv(port=8000)
            main_archive = self.archive
            main_client = self.client

        for _ in range(5):
            main_archive("src/SmallFile.fits")
            if subNode:
                node_archive("src/TinyTestFile.fits")

        cmdPars = [["async", "0"], ["notif_email", 'alice@localhost.local']]
        if diskId:
            cmdPars.append(["disk_id", diskId])
        if fileId:
            cmdPars.append(["file_id", fileId])
        if fileVer:
            cmdPars.append(["file_version", fileVer])
        if trgDisk:
            cmdPars.append(["target_disk_id", trgDisk])
        statObj = main_client.get_status(NGAMS_CLONE_CMD, pars = cmdPars)

        # Check returned status.
        errMsg = "Executed CLONE Command: Disk ID: %s, File ID: %s, " +\
                 "File Version: %s, Target Disk: %s. Message: %s"
        self.assert_status_ref_file(refStatFile + "_1_ref", statObj, msg=errMsg %
                                             (str(diskId), str(fileId), str(fileVer), str(trgDisk),
                                              str(statObj.getMessage())),
                                             status_dump_args=(0, 1, 1))

        if mail_expected:
            msg = errMsg % (str(diskId), str(fileId), str(fileVer), str(trgDisk),
                    "Illegal CLONE Command Email Notification Message")
            self.assert_clone_mail(refStatFile + "_2_ref", msg=msg)


    def test_NormalExec_1(self):
        """
        Synopsis:
        Normal execution of CLONE Command specifying file_id.

        Description:
        The Test Case exercises the Clone Command whereby a successfull
        Clone Request is executed, specifying the file_id of a file to clone.
        The cloning takes place within the scope of one NG/AMS Server
        (simulating one node).

        Expected Result:
        The file should be cloned onto a Main Disk, which does not already
        host that file.

        Test Steps:
        - Start instance of NG/AMS Server.
        - Archive a file 5 times.
        - Clone it via its File ID, specify the test user as recepient of
          the Clone Status Report.
        - Check that the response returned is as expected.
        - Check that a proper Clone Status Report was sent out as a
          Notification Email.

        Remarks:
        ...
        """
        testData = [None, nmuFileId, None, None, 0]
        self._test_clone(testData, refFilePat1 % (1, 1))


    def test_NormalExec_2(self):
        """
        Synopsis:
        Normal execution of CLONE Command specifying file_id/file_version.

        Description:
        Check normal execution of the Clone Command specifying file_id and
        file_version.

        Expected Result:
        The selected file should be cloned onto a Main Disk not already
        hosting that file.

        Test Steps:
        Same as test_NormalExec_1 with the exception that file_version is
        also given.

        Remarks:
        ...

        """
        testData = [None, nmuFileId, "2", None, 0]
        self._test_clone(testData, refFilePat1 % (2, 1))


    def test_NormalExec_3(self):
        """
        Synopsis:
        Normal execution of CLONE Command, specifying disk_id, file_id and
        file_version.

        Description:
        Check normal execution of the Clone Command specifying disk_id,
        file_id and file_version.

        Expected Result:
        Same as test_NormalExec_1.

        Test Steps:
        Same as test_NormalExec_1 with the exception that disk_id and
        file_version also are given.

        Remarks:
        ...

        """
        testData = [srcDiskId, nmuFileId, "1", None, 0]
        self._test_clone(testData, refFilePat1 % (3, 1))


    def test_NormalExec_4(self):
        """
        Synopsis:
        Normal execution of CLONE Command specifying disk_id.

        Description:
        The Test Case tests the CLONE Command when specifying a valid
        disk_id of a disk to be cloned.

        Expected Result:
        Same as test_NormalExec_1.

        Test Steps:
        Same as test_NormalExec_1 but specifying disk_id.

        Remarks:
        ...
        """
        testData = [srcDiskId, None, None, None, 0]
        self._test_clone(testData, refFilePat1 % (4, 1))


    def test_NormalExec_5(self):
        """
        Synopsis:
        Normal execution of CLONE Command specifying disk_id, file_id,
        file_version and target_disk_id.

        Description:
        Exercise a normal execution of the CLONE Command speciyfing a valid
        combination of disk_id, file_id, file_version and target_disk_id.

        Expected Result:
        Same as test_NormalExec_1 but the file should end up on the specified
        Target Disk.

        Test Steps:
        Same as test_NormalExec_1 but specifying a valid combination of
        disk_id, file_id, file_version and target_disk_id.

        Remarks:
        ...
        """
        testData = [srcDiskId, nmuFileId, "3", trgDiskId, 0]
        self._test_clone(testData, refFilePat1 % (5, 1))


    def test_NormalExec_6(self):
        """
        Synopsis:
        Normal execution of CLONE Command specifying disk_id and
        target_disk_id.

        Description:
        Test Case to exercise proper handling of the CLONE Command when
        specifying a valid combination of disk_id and target_disk_id.

        Expected Result:
        The contents of the specified Source Disk should be cloned onto the
        specified Target Disk.

        Test Steps:
        Same as test_NormalExec_1 but specifying a disk_id and target_disk_id.

        Remarks:
        ...
        """
        testData = [srcDiskId, None, None, trgDiskId, 0]
        self._test_clone(testData, refFilePat1 % (6, 1))


    def test_NormalExec_7(self):
        """
        Synopsis:
        Normal execution of CLONE Command specifying disk_id whereby Source
        Disk not in Target Node (Proxy Mode cloning).

        Description:
        The purpose of the Test Case is to check the proper execution of the
        CLONE Command when th contacted node has to clone a disk registered
        within the context of another NG/AMS Server (Proxy Mode).

        Expected Result:
        The files contained on the specified disk located in another NGAS
        Node, should be cloned onto a disk in the contacted node and stored
        on a Main Disk not already containing the files.

        Test Steps:
        - Start two instances of the NG/AMS Server on the test node.
        - Archive a file 5 times onto one of the NGAS Systems.
        - Clone the disk onto the other NGAS System, by specifying the
          disk hosting the files in the other NGAS System (async=0).
        - Check that the response from the NG/AMS Server is as expected.
        - Check that the Clone Status Report (sent via Email Notification)
          is as expected.

        Remarks:
        Should also check that the files have been cloned (check copies on
        Target Disk + info in NGAS DB).
        """
        testData = [ncuSrcDiskId, None, None, None, 1]
        self._test_clone(testData, refFilePat1 % (7, 1))


    def test_NormalExec_8(self):
        """
        Synopsis:
        Normal execution of CLONE Command specifying file_id and file_version
        (Proxy Mode cloning).

        Description:
        Same as test_NormalExec_7 but where file_id and file_version are
        specified.

        Expected Result:
        The given file should be cloned onto the Target NGAS System.

        Test Steps:
        Same as test_NormalExec_7 but where file_id/file_version are specified
        rather than disk_id.

        Remarks:
        Should test that the file has arrived on the Target Disk and that the
        info is properly updated in the DB.
        """
        testData = [None, ncuFileId, "4", None, 1]
        self._test_clone(testData, refFilePat1 % (8, 1))


    def test_NormalExec_9(self):
        """
        Synopsis:
        Normal execution of CLONE Command specifying disk_id, file_id and
        file_version (Proxy Mode cloning).

        Description:
        Same as test_NormalExec_7 but specifying also file_id and file_version.

        Expected Result:
        Same as test_NormalExec_7 cloning only one file.

        Test Steps:
        Same as test_NormalExec_7.

        Remarks:
        Should also check that cloned file has arrived on the Target Disk
        and is registered in the NGAS DB.
        """
        testData = [ncuSrcDiskId, ncuFileId, "3", None, 1]
        self._test_clone(testData, refFilePat1 % (9, 1))


    def test_NormalExec_10(self):
        """
        Synopsis:
        Normal execution of CLONE Command specifying disk_id, file_id,
        file_version and  target_disk_id (Proxy Mode cloning).
        Description:

        Expected Result:
        Same as test_NormalExec_7 but specifying also file_id, file_version
        and target_disk_id.

        Test Steps:
        Same as test_NormalExec_7 cloning only one file.

        Remarks:
        Should also check that cloned file has arrived on the Target Disk
        and is registered in the NGAS DB.
        """
        testData = [ncuSrcDiskId, ncuFileId, "3", nmuTrgDiskId, 1]
        self._test_clone(testData, refFilePat1 % (10, 1))


    def test_ErrExec_1(self):
        """
        Synopsis:
        Error executing CLONE Command: file_id + file_version +
        target_disk_id => 2 files -> but only 1 disk.

        Description:
        The purpose of the test is to exercise the case where there is
        insufficient space to carry out a Clone Request since the cloning
        requires two Disk Sets.

        Expected Result:
        The contacted NG/AMS Server should detect the problem as should
        reject the CLONE Command with an appropriate error message.

        Test Steps:
        - Start two servers (simulated cluster).
        - Archive 5 files onto sub-node (NMU).
        - Clone a given file specifying Target Disk on NMU.
        - Check that the Clone Command is rejected.

        Remarks:
        TODO: Verify that this Test Case is correct.
        """
        testData = [None, nmuFileId, "3", nmuTrgDiskId, 1]
        self._test_clone(testData, refFilePat2 % (1, 1), mail_expected=False)


    def test_CloneCmd_1(self):
        """
        Synopsis:
        Normal execution of CLONE Command/clone one file/async=1.

        Description:
        Test normal execution of the CLONE Command whereby async=1.

        Expected Result:
        An immediate response should be returned indicating that the
        CLONE Command has been accepted for execution. The Clone Status
        Report should be send out indicating that the file was cloned.

        Test Steps:
        - Start 1 NG/AMS Server.
        - Archive file 2 times.
        - Clone one file specifying disk_id, file_id and file_version + async=1.
        - Check that the immediate response is correctly returned.
        - Wait for the execution of the CLONE Command to finish.
        - Check that the Request Info in the NG/AMS Server indicates that the
          Clone Request finished.
        - Check that the cloned file has arrived on the Target Disk.
        - Check that the DB info has been updated as it should.

        Remarks:
        TODO: Re-implement using _execCloneTest().
        """
        srcFile = "src/SmallFile.fits"
        self.start_smtp_server()
        _, dbObj = self.prepExtSrv(cfgProps=(('NgamsCfg.Server[1].RequestDbBackend', 'memory'),))
        for _ in range(2):
            self.archive(srcFile)
        statObj = self.get_status(NGAMS_CLONE_CMD,
                                    pars = [["disk_id", srcDiskId],
                                            ["file_id", nmuFileId],
                                            ["file_version", "1"],
                                            ["async", "1"],
                                            ["notif_email", 'alice@localhost.local']])
        refStatFile = "ref/ngamsCloneCmdTest_test_CloneCmd_1_1_ref"
        msg = "Incorrect status for CLONE command/successfull cloning"
        self.assert_status_ref_file(refStatFile, statObj, msg=msg)

        finalStatObj = waitReqCompl(self, statObj.getRequestId())
        complPer = str(finalStatObj.getCompletionPercent())
        self.assertEqual("100.0", complPer,
                        genErrMsgVals("Incorrect Request Status for CLONE " +\
                                      "Command/Completion Percent", "100.0",
                                      complPer))

        ref_file = "ref/ngamsCloneCmdTest_test_CloneCmd_1_ref"
        msg = "Incorrect/missing CLONE Status Notification Email Msg"
        self.assert_clone_mail(ref_file, msg)

        tmpFitsFile = self.ngas_path("FitsStorage2-Main-3/saf/" +\
                      "2001-05-08/1/TEST.2001-05-08T15:25:00.123.fits.gz")

        unzippedTmp = genTmpFilename()
        unzip(tmpFitsFile, unzippedTmp)
        self.checkFilesEq(srcFile, unzippedTmp, "Incorrect cloned file generated")

        diskId = self.ngas_disk_id("FitsStorage2/Main/3")
        filePrefix = "ngamsCloneCmdTest_test_CloneCmd_1"
        fileInfoRef = "ref/" + filePrefix + "_FileInfo_ref"
        fileInfo = ngamsFileInfo.\
                   ngamsFileInfo().read(getHostName() + ":8888",
                                        dbObj, "TEST.2001-05-08T15:25:00.123",
                                        1, diskId)
        msg = "Incorrect info in DB for cloned file"
        self.assert_status_ref_file(fileInfoRef, fileInfo, msg=msg)


    def test_CloneCmd_2(self):
        """
        Synopsis:
        Normal execution of CLONE Command specifying disk_id (async=1).

        Description:
        Clone an entire disk and check that the Clone Request was successfully
        handled.

        Expected Result:
        The 10 files on the disk specified to be cloned should be cloned
        onto the selected Target Disk.

        Test Steps:
        - Start normal NG/AMS Server.
        - Archive small FITS file 10 times.
        - Issue Clone Request.
        - Wait for Clone Request to terminate.
        - Check that the Clone Status Report indicates that the files were
          cloned as expected.

        Remarks:
        TODO: Re-implement using _execCloneTest().
        """
        srcFile = "src/SmallFile.fits"
        self.start_smtp_server()
        self.prepExtSrv(cfgProps=(('NgamsCfg.Server[1].RequestDbBackend', 'memory'),))
        for _ in range(10):
            self.archive(srcFile)
        diskId = self.ngas_disk_id("FitsStorage1/Main/1")
        statObj = self.get_status(NGAMS_CLONE_CMD,
                                    pars = [["disk_id", diskId],
                                            ["async", "1"],
                                            ["notif_email", 'alice@localhost.local']])
        waitReqCompl(self, statObj.getRequestId(), 20)

        ref_file = "ref/ngamsCloneCmdTest_test_CloneCmd_2_ref"
        msg = "Incorrect/missing CLONE Status Notification Email Msg"
        self.assert_clone_mail(ref_file, msg)