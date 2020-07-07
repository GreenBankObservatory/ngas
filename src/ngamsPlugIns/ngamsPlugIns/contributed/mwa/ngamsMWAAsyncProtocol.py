import uuid

class AsyncListRetrieveProtocolError:
    OK = 0
    INVALID_REQUEST = 1
    FILE_NOT_FOUND = 2
    FILE_NOT_ONLINE = 3
    GENERAL_ERROR = 4
    THREAD_STOP_TIMEOUT = 5
    INVALID_UUID = 6 # cannot find retrieval request or thread associated with this session_uuid
    NO_UUID_IN_REQUEST = 7
    NO_COMMAND_IN_REQUEST = 8
    UNKNOWN_COMMAND_IN_REQUEST = 9

class AsyncListRetrieveRequest:
    def __init__(self, file_id, url):
        # session UUID
        self.session_uuid = str(uuid.uuid4())
        # List of Strings
        self.file_id = file_id
        # URL of client HTTP server
        self.url = url
        # Whether use files on one host only or all hosts in the cluster
        one_host = 0

class FileInfo:
    def __init__(self, file_id, filesize, status):
        self.file_id = file_id
        self.filesize = filesize
        # boolean, online or offline
        self.status = status

class AsyncListRetrieveResponse:
    def __init__(self, session, err, file_info):
        # AsyncListRetrieveRequest UUID
        self.session_uuid = session
        self.errorcode = err
        # list of file info objects for each file_id
        self.file_info = file_info

class AsyncRetrieveListSummary:
    # AsyncListRetrieveRequest UUID
    uuid = None
    # error code for each file id requested (Not Found, Error, Ok etc)
    results = []

class AsyncListRetrieveCancelRequest:
    session_uuid = None

class AsyncListRetrieveCancelResponse:
    session_uuid = None
    errorcode = None

class AsyncListRetrieveSuspendRequest:
    session_uuid = None

class AsyncListRetrieveSuspendResponse:
    session_uuid = None
    # the next file that will be sent on a successful resume
    current_fileid = None
    errorcode = None

class AsyncListRetrieveResumeRequest:
    session_uuid = None

class AsyncListRetrieveResumeResponse:
    session_uuid = None
    # the next file that will be sent on a successful resume
    current_fileid = None
    errorcode = None

class AsyncListRetrieveStatusRequest:
    session_uuid = None
    errorcode = None

class AsyncListRetrieveStatusResponse:
    session_uuid = None
    number_files_delivered = 0
    number_files_to_be_delivered = 0
    number_files_to_be_staged = 0
    number_bytes_delivered = 0
    number_bytes_to_be_delivered = 0
    number_bytes_to_be_staged = 0
    errorcode = None
