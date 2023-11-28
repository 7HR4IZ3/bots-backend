import json
from datetime import datetime, timedelta
import importlib
import time

class Command:
    def setup(self, bot):
        self.bot = bot

    def execute(self):
        pass

class GoToWebpageCommand(Command):
    def execute(self):
        try:
            self.bot.driver.get(self.bot.config['url'])
            return True  # Indicate success
        except Exception as e:
            print(f"Error executing action: {e}")
            return False  # Indicate failure

# ... (Rest of the Command classes and SampleDriver class)

class Trigger:
    def setup(self, bot):
        self.bot = bot

    def execute(self):
        self.bot.execute()

class Interval(Trigger):
    def __init__(self, interval_seconds):
        self.interval_seconds = interval_seconds

    def start(self):
        while True:
            self.execute()
            time.sleep(self.interval_seconds)

class Bot:
    def __init__(self, config, driver):
        self.config = config
        self.driver = driver
        self.actions = {}  # Using a dictionary
        self.data = {}
        self.event_listeners = {}
        self.triggers = []

    def add_trigger(self, trigger):
        trigger.setup(self)
        self.triggers.append(trigger)

    def action(self, action_name):
        def decorator(func):
            self.actions[action_name] = func
            return func
        return decorator

    def event(self, event_type):
        def decorator(listener_func):
            if event_type not in self.event_listeners:
                self.event_listeners[event_type] = []
            self.event_listeners[event_type].append(listener_func)
            return listener_func
        return decorator

    def run(self):
        for trigger in self.triggers:
            trigger.start()

# ... (Rest of the Bot class, Command classes, SampleDriver class, and other code)

if __name__ == "__main__":
    bot_config = {
        "url": "http://127.0.0.1"
    }

    sample_driver = SampleDriver()

    bot = Bot(bot_config, sample_driver)
    bot.setup()

    @bot.event("job_executed")
    def on_execute():
        print("Job executed")

    @bot.event("job_error")
    def on_error():
        print("Job error")

    bot.add_action("navigate", GoToWebpageCommand)  # Adding action manually

    # Adding actions from a JSON file or a dictionary
    actions_input = input("Enter JSON file path or JSON dictionary (press Enter for default): ").strip()
    if actions_input:
        try:
            actions = json.loads(actions_input)
            bot.add_actions_from_json(actions)
        except (ValueError, TypeError):
            print("Invalid JSON input. Adding actions from default JSON file.")
            bot.add_actions_from_json("actions_mapping.json")

    interval_hours = float(input("Enter interval in hours for bot run: "))
    interval_seconds = interval_hours * 3600

    interval_trigger = Interval(interval_seconds)
    bot.add_trigger(interval_trigger)

    bot.run()
