import typing as t
from types import NoneType


class BaseDriver:
    def __init__(self, data: t.Optional[t.Mapping | NoneType] = None):
        self.data = data or dict()

    def setup(self, bot):
        self.bot = bot

class MultiDriverAdapter(BaseDriver):
    name = "multidriver"

    def __init__(
        self,
        drivers: t.Optional[t.Sequence[BaseDriver] | NoneType] = None,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.__drivers = drivers or []
        self.bot = None

    def setup(self, bot):
        super().setup(bot)

        for driver in self.__drivers:
            driver.setup(bot)

    def add_driver(self, driver: BaseDriver):
        if self.bot:
            driver.setup(self.bot)
        self.__drivers.append(driver)

    def remove_driver(self, driver):
        self.__drivers.remove(driver)
        return driver


class ScrapyDriver(BaseDriver):
    name = "scrapy"

    def __init__(self, *args, **kwargs):
        pass


class PlaywrightDriver(BaseDriver):
    name = "playwright"

    def __init__(self, *args, **kwargs):
        pass


class NotificationDriver(BaseDriver):
    name = "notify"

    def __init__(self, *args, **kwargs):
        pass

    def log(self, message):
        if message:
            print("Message:", message)

    def add(self, x, y):
        return x + y


DRIVERS = {
    "multidriver": MultiDriverAdapter,
    "scrapy": ScrapyDriver,
    "playwright": PlaywrightDriver,
    "notify": NotificationDriver
}
