Storage
=======

.. _commands.archive:

ARCHIVE
-------

Archive data files within an NGAS node,
calculating and storing the CRC of the archived file
in the NGAS database.

After a successful archiving of a file,
all archiving event handlers are invoked.
Read :ref:`server.archiving_events` for more information
about these events and how to handle them.

The ``ARCHIVE`` command supports two modes of operation: *pull* and *push*.
A pull request is issued by using the ``GET`` method,
and tells an NGAS node to fetch and archive a file based on a valid URI.
A push request, on the other hand, is issued by using the ``POST`` method,
and requires the client to send the file contents as a byte stream to the NGAS server.

When incoming files matching an existing file ID in the NGAS DB,
their contents are stored using a new version number if file versioning is on.
If file versioning is off, they will overwrite an existing file's contents instead.
When overwriting, users can specify a specific file version to overwrite,
which must exist **locally** in the server receiving the request.

**Parameters**

- ``filename``: a valid URI i.e. ``file://, http://, ftp://`` for Pull or filename ie. ``test.fits`` for Push.
- ``mime_type``: describes the content-type of the file.
  If not given, NGAS tries to guess it based on the filename's extension,
  and the :ref:`internal mime-type information <config.mime_types>`
  stored in the NGAS configuration.
- ``versioning``: used to switch the automatic versioning on
  (``1``, the default behavior) or off (``0``).
- ``no_versioning``: The inverse of ``versioning``. This is kept for backwards compatibility.
  If both are specified, ``versioning`` takes precedence.
- ``file_version``: specifies which file version to overwrite.
  Only taken into account when ``versioning=0``/``no_versioning=1``.
- ``crc_variant``: used to explicitly choose which CRC variant will be used to checksum the file,
  overriding the system-wide configuration. See :ref:`server.crc` for details

**Archive Pull Example**

In this case the NGAS server will attempt to retrieve and archive the file ``remote.fits`` from the remote http server::

 curl http://<host>:<port>/ARCHIVE?filename=http://<remotehost>:<remoteport>/remote.fits


**Archive Push Example**

In this example it is expected that the client uploads the file content as a byte stream to the NGAS server::

  curl -X POST -i -H "Content-Type: application/octet-stream" --data-binary "@/tmp/file.fits" http://<host>:<port>/ARCHIVE?filename=file.fits


.. _commands.qarchive:

QARCHIVE
--------

Like :ref:`commands.archive`, but with the following differences:

* The target volume is selected at random from the available volumes in the server.
  This bypasses the server's :ref:`stream configuration <config.streams>`,
  but should yield a more even loading of the available volumes.
* No file replication is carried out,
  even if a storage set declares a replication disk.

The ``QARCHIVE`` command was initially implemented
separately from the ``ARCHIVE`` command,
and therefore they used to differ in more ways.
In particular ``QARCHIVE`` originally was the only one
implementing on-stream checksuming,
while ``ARCHIVE`` didn't.
Nowadays they share the same underlying logic though,
and only the differences documented above remain.

.. _commands.retrieve:

RETRIEVE
--------

Retrieve archived data files from an NGAS server or cluster.

**Parameters**

- ``file_id``: ID of the file to retrieve.
- ``file_version``: version of the file to retrieve.
- ``processing_pars``: invoke a processing plug-in by name that will operate on the file requested. Note that NGAS will send back the result of the processing which may or may not be a file stream.

If multiple files of the same ID exist and ``file_version`` is not specified then the file with the highest version number will be retrieved by default.

If the file was compressed internally by NGAS at archiving time,
at ``RETRIEVE`` time the contents are still returned compressed.
Different clients will handle this differently:
if the client supports ``Content-Encoding: XYZ`` responses
(with ``XYZ`` being the compression used internally in NGAS)
then a filename without the corresponding compression extension will be presented,
as the client automatically decompresses the incoming content
before presenting it to the user.
In the case the client doesn't support this,
a filename with the corresponding extension will be presented
to ensure clients associate the filename and its contents
with the corresponding utilities.

Note that only one file can be retrieved per RETRIEVE request.

**Example**

Get the latest version of a file if it exists::

 curl http://<host>:<port>/RETRIEVE?file_id=file.fits

Get specific version of a file if it exists::

 curl http://<host>:<port>/RETRIEVE?file_id=file.fits&file_version=2


.. _commands.query:

QUERY
-----

The QUERY command is used to list different types of elements
currently known by the server.
Users can use the QUERY command
to find out which files have been archived into the server,
which subscriptions have been created,
which disks are present in the system,
and more.

**Parameters**

* ``query``: The query to run, the only required argument. Valid values are:

  * ``files_list``: a list of all files in the system.
  * ``subscribers_list``: a list of all subscriptions in the system.
  * ``subscribers_like``: a list of subscriptions in the database
    belonging to hosts matching the given ``like`` value (see below).
  * ``disks_list``: a list of all disks in the system.
  * ``hosts_list``: a list of all hosts that are part of the same cluster.
  * ``files_like``: a list of files whose ID matches
    the given ``like`` value (see below).
  * ``files_location``: a list of all files in the system,
    but with information about their physical location on disk.
  * ``lastver_location``: like ``files_location``,
    but only listing the last version of each file.
  * ``files_between``: a list of files archived into the system
    between ``start`` and ``end`` date (see below).
  * ``files_stats``: the total size of all archived files, in [MB].
  * ``files_list_recent``: a list of the last 300 archived files.

* ``format``: the format in which the result of the query
  will be returned to the client.
  Valid values are ``list`` (a textual, table-like representation),
  ``pickle`` (a python pickled version of the data),
  ``json`` (a json representation of the data),
  and ``python-list`` (a ``str`` representation of the direct result of the
  query).
* ``like``: indicate the value to use in the ``*_like`` queries.
  If no string is given, ``%`` will be used,
  therefore matching all values for the corresponding attribute.
* ``start`` and ``end``: indicate the beginning and the end
  of the time interval used for the ``files_between`` query.
  Both parameters must be specified
  in order for the interval to be properly defined.
  If any of the two is (or both are) missing,
  no interval is used.

**Example**

Get list of all subscriptions the system in json format::

 curl http://<host>:<port>/QUERY?query=subscribers_list&format=json

Get list of all files in the system::

 curl http://<host>:<port>/QUERY?query=files_list&format=list

.. _commands.clone:

CLONE
-----

The CLONE Command is used to create copies of a single file or sets of files.
In order for the CLONE Command to be accepted by an NGAS node,
the system must be configured to accept Archive Requests.
NGAS will calculate if there is enough space to execute the request, if not then an error is returned.
If the files to be cloned are located on other NGAS host,
these will be requested automatically during the cloning (if possible).
If the NGAS hosts are suspended, they will be woken up automatically.

**Parameters**

- ``disk_id``: disk ID where the files to be cloned exist.
- ``file_id``: ID of the files to be cloned.
- ``file_version``: file version of the files to be cloned.
- ``notif_email``: list of comma separated email addresses to where the Clone Status Report can be sent.

The actions of the various combinations of these parameters are explained below:

+---------+---------+--------------+----------------------------------------------------------------------------------------------------------+
| disk_id | file_id | file_version | Action                                                                                                   |
+=========+=========+==============+==========================================================================================================+
|         |    *    |              | Clone one file with the given ID. Latest version of the file is taken.                                   |
+---------+---------+--------------+----------------------------------------------------------------------------------------------------------+
|    *    |    *    |              | Clone one file stored on the given disk. Latest version on that disk is taken.                           |
+---------+---------+--------------+----------------------------------------------------------------------------------------------------------+
|         |    *    |       *      | Clone all files found with the given File Version. Storage location (Disk ID) is not taken into account. |
+---------+---------+--------------+----------------------------------------------------------------------------------------------------------+
|    *    |    *    |       *      | Clone one file on the given disk with the given File Version.                                            |
+---------+---------+--------------+----------------------------------------------------------------------------------------------------------+
|    *    |         |              | Clone all files from the disk with the given ID.                                                         |
+---------+---------+--------------+----------------------------------------------------------------------------------------------------------+
|    *    |         |       *      | Clone all files with the given File Version from the disk with the ID given.                             |
+---------+---------+--------------+----------------------------------------------------------------------------------------------------------+
|         |         |       *      | Illegal. Not accepted to clone arbitrarily files given by only the File Version.                         |
+---------+---------+--------------+----------------------------------------------------------------------------------------------------------+


CHECKFILE
---------

The CHECKFILE command is used to check the consistency of a specific file.

**Parameters**

- ``disk_id``: disk ID where the file to be checked exists.
- ``file_id``: ID of the file to check.
- ``file_version``: version of the file to check.


CACHEDEL
--------

The CACHEDEL command is used to remove a file from an NGAS cluster. Only the ``ngamsCacheServer`` version supports this command.

**WARNING:** Once the command completes successfully the file is permanently deleted from the NGAS database and the underlying file system.

**Parameters**

- ``disk_id``: disk ID where the file to be deleted exists.
- ``file_id``: ID of the file to be deleted.
- ``file_version``: version of the file to be deleted.

REMDISK
-------

The REMDISK command is used to remove storage media from an NGAS node.
The command removes both the information about the storage media and the files stored on said media.
NGAS will not remove the files from the system unless there are at least three (3) independent copies of the files.
Three independent copies refers to three copies of the file stored on three independent storage media.
In order for the REMDISK command to be accepted the system must be configured to allow remove requests i.e. ``NgamsCfg.Server:AllowRemoveReq`` is set in the configuration file.
If the command is executed without the ``execute`` parameter, the information about the disk is not deleted,
but a report is generated indicating what will be deleted if the execution is requested i.e. ``execute = 1``.

**WARNING:** Once the command completes successfully the files associated with the storage media are permanently deleted from the NGAS database and the underlying file system.

**Parameters**

- ``disk_id``: ID of disk/media to remove from NGAS node.
- ``execute``: (0 or 1) 0: is a dummy run which will only report what will happen if the command is executed. 1: executes the command which will deleted the storage media and the associated files.
- ``notif_email``: list of comma separated email addresses to where the REMDISK Status Report can be sent.


REMFILE
-------

The REMFILE command removes a single file from an NGAS node. NGAS will not remove the files from the system unless there are at least three (3) independent copies of the files.
In order for the REMFILE command to be accepted the system must be configured to allow remove requests i.e. ``NgamsCfg.Server:AllowRemoveReq`` is set in the configuration file.

**Parameters**

- ``disk_id``: disk ID where the file to be deleted exists.
- ``file_id``: ID of the file to be deleted.
- ``file_version``: version of the file to be deleted.
- ``execute``: (0 or 1) 0: is a dummy run which will only report what will happen if the command is executed. 1: executes the command which will delete the file.
- ``notif_email``: list of comma separated email addresses to where the REMFILE Status Report can be sent.

The actions of the various combinations of these parameters are explained below:

+---------+---------+--------------+----------------------------------------------------------------------------------------------------------+
| disk_id | file_id | file_version | Action                                                                                                   |
+=========+=========+==============+==========================================================================================================+
|         |    *    |              | All files matching the given File ID pattern on the contacted NGAS host are selected.                    |
+---------+---------+--------------+----------------------------------------------------------------------------------------------------------+
|    *    |    *    |              | All files with the given File ID on the disk with the given ID will be selected.                         |
+---------+---------+--------------+----------------------------------------------------------------------------------------------------------+
|         |    *    |       *      | All files with the given File ID pattern and the given File Version are selected.                        |
+---------+---------+--------------+----------------------------------------------------------------------------------------------------------+
|    *    |    *    |       *      | The referenced file with the given File ID and File Version on the given ID is selected (if this exists).|
+---------+---------+--------------+----------------------------------------------------------------------------------------------------------+
|    *    |         |              | Illegal.                                                                                                 |
+---------+---------+--------------+----------------------------------------------------------------------------------------------------------+
|    *    |         |       *      | No files are selected.                                                                                   |
+---------+---------+--------------+----------------------------------------------------------------------------------------------------------+
|         |         |       *      | No files are selected.                                                                                   |
+---------+---------+--------------+----------------------------------------------------------------------------------------------------------+


REGISTER
--------

The REGISTER command is used to register files already stored on an NGAS disk.
It is possible to register single files or entire sets of files by specifying a root path.
Only files that are known to NGAS (with a mime-type defined in the configuration) will be taking into account.
It is also possible to explicitly specify a comma separated list of mime-types that will be registered.
Files with other mime-types than specified in this list will be ignored.

**Parameters**

- ``mime_type``: comma separated list of mime-types. A single mime-type can also be specified.
- ``path``: The root path under which NGAS will look for candidate files to register. It is also possible to specify a complete path to a single file.
- ``notif_email``: email address to send file registration report.


REARCHIVE
---------

The purpose of the REARCHIVE command is to register a file in the NGAS DB that has already been generated when the file was archived with the QARCHIVE command.
This means that the process of extracting the meta-information and other processing can be skipped whilst re-archiving the file making the processing more efficient.

The meta-information about the file is contained in the special HTTP header named ``NGAS-File-Info``.
It is stored as a ``base64`` encoded NGAS XML block for the file (NGAS File Info).
This encoding can be accomplished by means of the Python module ``base64`` using ``base64.b64encode()``.

The command does not require any parameters but the data to be re-archived should be contained in the body of the HTTP request similar to QARCHIVE Push or Pull.
