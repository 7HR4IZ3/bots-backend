import time

from . import BaseTrigger

from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger as __IntervalTrigger
from apscheduler.triggers.cron import CronTrigger


class Trigger(BaseTrigger):
    def get_scheduler_trigger(self):
        pass

class IntervalTrigger(Trigger):
    def __init__(self, seconds):
        self.interval_seconds = seconds

    def start(self):
        while True:
            self.execute()
            time.sleep(self.interval_seconds)

    def get_scheduler_trigger(self):
        return __IntervalTrigger(seconds=self.interval_seconds)
