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
# "@(#) $Id: ngamsOfflineCmdTest.py,v 1.5 2008/08/19 20:51:50 jknudstr Exp $"
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# jknudstr  20/11/2003  Created
#
"""
This module contains the Test Suite for the OFFLINE Command.
"""

from ngamsLib.ngamsCore import NGAMS_OFFLINE_CMD
from .ngamsTestLib import ngamsTestSuite, sendExtCmd


class ngamsOfflineCmdTest(ngamsTestSuite):
    """
    Synopsis:
    Test Suite for the OFFLINE Command.

    Description:
    The purpose of the Test Suite is to exercise the OFFLINE Command.
    Both normal case and abnormal cases should be tested. Latter includes:

      - Sending OFFLINE when server is busy.
      - Sending OFFLINE when server is busy and force specified.

    Missing Test Cases:
    - Should be reviewed and the missing Test Cases added.
    """

    def test_StdOffline_1(self):
        """
        Synopsis:
        test standard execution of OFFLINE Command.

        Description:
        The purpose of the Test Case is to specify the normal execution of the
        OFFLINE Command when the server is Online/Idle and the command is
        accepted as expected and the server brought to Offline State.

        Expected Result:
        The server in Online State should accept the OFFLINE Command and should
        go Offline.

        Test Steps:
        - Start server (Auto Online=1).
        - Submit OFFLINE Command.
        - Check the response from the server.

        Remarks:
        TODO: Check that the server is in Offline State.
        """
        self.prepExtSrv()
        tmpStatFile = sendExtCmd(8888, NGAMS_OFFLINE_CMD,
                                 genStatFile = 1)
        refStatFile = "ref/ngamsOfflineCmdTest_test_StdOffline_1_1_ref"
        self.checkFilesEq(refStatFile, tmpStatFile,
                          "Incorrect status returned for OFFLINE command")