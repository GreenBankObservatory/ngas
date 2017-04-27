#!/bin/sh
### BEGIN INIT INFO
# Provides:        ngams-cache-server 
# Required-Start:  $all
# Required-Stop:   $local_fs $network
# Default-Start:   2 3 4 5
# Default-Stop:    0 1 6
# Short-Description: NGAS daemon
### END INIT INFO
#
#
# chkconfig: 2345 99 70
# description: Starts and stops the NGAMS server as a daemon

DAEMON=ngamsDaemon

# RH, Centos, Fedora configuration style
if [ -r /etc/sysconfig/ngas ]; then
	. /etc/sysconfig/ngas
# Debian, Ubuntu configuration style
elif [ -r /etc/default/ngas ]; then
	. /etc/default/ngas
else
	echo "Missing configuration file, cannot start NGAS" > /dev/stderr
	exit 1
fi

# The configuration file is used to start the server
# and to ping it during "status"
OPTS="-cfg '${CFGFILE}'"

# See how we were called.
RETVAL=0
case "$1" in
	start)

		# Prepare command-line options based on options file
		if [ "${CACHE}" = "YES" ]; then
			OPTS="$OPTS -cache"
		elif [ "${DATA_MOVER}" = "YES" ]; then
			OPTS="$OPTS -dataMover"
		fi
		if [ "${AUTOONLINE}" = "YES" ]; then
			OPTS="$OPTS -autoonline"
		fi
		if [ -n "${NGAS_PATH}" ]; then
			OPTS="$OPTS -path '${NGAS_PATH}'"
		fi

		su - $USER -c "$DAEMON start $OPTS"
		RETVAL=$?
		echo "NG/AMS startup"
		;;
	stop)
		su - $USER -c "$DAEMON stop $OPTS"
		RETVAL=$?
		echo "NG/AMS shutdown"
		;;
	status)
		echo "Status of $DAEMON: "
		su - $USER -c "$DAEMON status $OPTS" &> /dev/null
		RETVAL=$?
		;;
	restart)
		echo -n "Restarting $DAEMON: "
		$0 stop
		$0 start
		RETVAL=$?
		;;
	*)
		echo "Usage: $0 {start|stop|status|restart}"
		RETVAL=1
esac

exit $RETVAL
