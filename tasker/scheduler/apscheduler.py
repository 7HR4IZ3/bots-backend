from types import NoneType
from typing import Callable, Optional
from apscheduler.schedulers import background

from . import BaseScheduler as __BaseScheduler
from ..utils import Event
from ..triggers.apscheduler import BaseTrigger, DateTrigger

class BaseScheduler(background.BaseScheduler, __BaseScheduler):
    def __init__(self,  *args, **kwargs):
        super().__init__( *args, **kwargs)
        self.__event = Event()

    @property
    def running(self):
        return self.__event.is_set()

    def shutdown(self, *args, **kwargs):
        self.__event.clear()
        super().shutdown( *args, **kwargs)

    def wait(self, timeout=None):
        return self.__event.wait(timeout)

    def start(self, *args, **kwargs):
        self.__event.set()
        super().start( *args, **kwargs)

    def add_task(
        self, task_function: Callable,
        trigger: Optional[BaseTrigger | NoneType] = None
    ):
        if not trigger:
            trigger = DateTrigger()
        self.add_job(task_function, trigger)

class Scheduler(BaseScheduler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class BackgroundScheduler(BaseScheduler, background.BackgroundScheduler):
    pass

class BlockingScheduler(BaseScheduler, background.BlockingScheduler):
    pass
