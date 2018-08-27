#!/bin/bash
#
# NGAS test runner script to Travis CI
#
# ICRAR - International Centre for Radio Astronomy Research
# (c) UWA - The University of Western Australia, 2016
# Copyright by UWA (in the framework of the ICRAR)
# All rights reserved
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307  USA

# We know the following variables:
#
# DB                the database used in this run (sqlite3, mysql, postgresql)
# TRAVIS_BUILD_DIR  the directory where the sources are located
# TRAVIS_OS_NAME    the OS under which we are running (linux, osx)
#

# In OSX we create our own virtualenv, see run_build.sh
if [ "${TRAVIS_OS_NAME}" = "osx" ]
then
	source ${TRAVIS_BUILD_DIR}/osx_venv/bin/activate
fi

# These are the user/dbname/passwd that we created on run_build
# sqlite3 is the default so it needs no special attention
NGAS_TESTDB=
if [[ "$DB" == "mysql" ]]; then
	NGAS_TESTDB='<Db Id="blah" Snapshot="0" Interface="MySQLdb" host="127.0.0.1" db="ngas" user="ngas" passwd="ngas"/>'
elif [[ "$DB" == "postgresql" ]]; then
	NGAS_TESTDB='<Db Id="blah" Snapshot="0" Interface="psycopg2" host="127.0.0.1" dbname="ngas" user="ngas" password="ngas"/>'
fi
export NGAS_TESTDB

pip install psutil pytest-cov coveralls
cd ${TRAVIS_BUILD_DIR}/test
py.test --cov
