import json
from datetime import datetime as dt, timedelta
import time
from tasker import events
from tasker.bots import Bot
from tasker.command import Command
from tasker.driver import BaseDriver
# from tasker.schedulers import BlockingScheduler
# from tasker.triggers import IntervalTrigger

from scheduler import Scheduler, trigger # pyright: ignore

class GoToWebpageCommand(Command):
    def execute(self):
        self.bot.driver.get(self.bot.config['url'])


class FindElementCommand(Command):
    def execute(self):
        self.bot.data["element"] = self.bot.driver.find_element_by_css_selector("#docs")


class GetInnerTextCommand(Command):
    def execute(self):
        if "element" in self.bot.data and self.bot.data["element"]:
            self.bot.data["inner_text"] = self.bot.data["element"].text


class SaveToJsonCommand(Command):
    def execute(self):
        if "inner_text" in self.bot.data and self.bot.data["inner_text"]:
            output_data = {"inner_text": self.bot.data["inner_text"]}
            with open("output.json", "w") as output_file:
                json.dump(output_data, output_file, indent=4)
            raise ValueError("Inner text saved to 'output.json'")
        else:
            raise ValueError("Element not found.")


class OpenFileCommand(Command):
    def execute(self):
        print(self.bot.config.get("message", "Hello World"))
        return True


bot = Bot(
    {"url": "http://127.0.0.1"}, driver=BaseDriver(),
    # scheduler=BlockingScheduler()
)

bot.setup()

# @bot.event("action.execute")
# def on_execute(action, success=False):
#     print(f"[JOB] '{action}' status: '{'Success' if success else 'Failed'}'")

# @bot.event("action.execute:error")
# def on_error(action, exception):
#     print(f"[JOB] '{action}' status: 'Failed' reason: {repr(exception)}")

@bot.action("print")
def _(bot):
    print("Hello World")

# bot.add_action("navigate", GoToWebpageCommand)
# bot.add_action("find_element", FindElementCommand)
# bot.add_action("get_inner_text", GetInnerTextCommand)
# bot.add_action("save_to_json", SaveToJsonCommand)

# bot.add_trigger(IntervalTrigger(seconds=2))

# bot.add_trigger(
#     s.weekly(s.trigger.Monday(
#         dt.time(hour-16, minute=30)
#     ))
# )

# bot.add_trigger(Scheduler())

# bot.add_trigger(ZapierTrigger(client_id="<client_id>"))

# bot.add_trigger(
#     OrTrigger(
#         ZapierTrigger(client_id="<client_id>"),
#         ZapierTrigger(client_id="<client_id>"),
#     )
# )

# bot.run()

scheduler = Scheduler()
scheduler.cyclic(timedelta(seconds=2), bot.execute)

for i in range(10):
    scheduler.exec_jobs()
    time.sleep(1)
