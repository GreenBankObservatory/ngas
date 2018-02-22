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
# cwu      2013/02/25  Created
#
"""
This plug-in command  explicitly triggers subscriptionThread.

Existing triggering mechanisms include:
1. ngas server startup
2. archive cmd (including normal archive, mirror archive, quick archive)
3. subscription cmd

However, the above three triggering methods cannot explicitly trigger files in the backlog.
Backlog files are not re-tried unless other trigger mechanisms are used, which sometimes is
not desirable. For example, after we fixed the problem preventing files from being delivered,
we simply want to re-deliver these files from the backlog without having to
re-subscribe, re-archive, or re-start the server

"""

def handleCmd(srv, reqPropsObj, httpRef):
    """
    Handle the TRIGGERSUBSCRIPTION Command.
    """
    srv.triggerSubscriptionThread()