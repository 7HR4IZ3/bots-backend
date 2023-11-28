from apscheduler.events import *
from apscheduler.events import (
    JobEvent as __JobEvent,
    JobExecutionEvent as __JobExecutionEvent,
    JobSubmissionEvent as __JobSubmissionEvent
)


class JobEvent(__JobEvent):
    pass


class JobSubmissionEvent(__JobSubmissionEvent):
    pass


class JobSubmissionEvent(__JobSubmissionEvent):
    pass

