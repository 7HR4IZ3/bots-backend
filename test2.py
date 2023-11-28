from datetime import timedelta
import json

class Scheduler:
    def __init__(self):
        self.tasks = []

    def add_task(self, task_function, interval):
        self.tasks.append((task_function, interval))

    def run(self):
        while True:
            for task_function, interval in self.tasks:
                task_function()
                time.sleep(interval.total_seconds())

class Bot:
    def __init__(self, config, driver):
        self.config = config
        self.driver = driver
        self.actions = []
        self.data = {}

    def add_action(self, action_name, action_function):
        self.actions.append((action_name, action_function))

    def setup(self):
        self.driver.setup(self.config)
        
    def run(self):
        task_scheduler = Scheduler()

        for action_name, action_function in self.actions:
            interval_hours = float(input(f"Enter interval in hours for action '{action_name}': "))
            task_scheduler.add_task(action_function, timedelta(hours=interval_hours))

        task_scheduler.run()

# Define a sample driver class
class SampleDriver:
    def __init__(self):
        self.browser = None
        self.page = None

    def setup(self, config):
        # Implement the setup logic here
        pass

    def get(self, url):
        # Implement the get logic here
        pass

    def query_selector(self, selector):
        # Implement the query selector logic here
        pass

    def get_text(self, element):
        # Implement the get text logic here
        pass

    # Other methods as needed

if __name__ == "__main__":
    bot_config = {
        "url": "http://127.0.0.1"
    }

    sample_driver = SampleDriver()

    bot = Bot(bot_config, sample_driver)
    bot.setup()

    def go_to_webpage():
        bot.driver.get(bot.config['url'])

    def find_element():
        bot.data["element"] = bot.driver.query_selector("#docs")

    def get_inner_text():
        if "element" in bot.data and bot.data["element"]:
            bot.data["inner_text"] = bot.driver.get_text(bot.data["element"])

    def save_to_json():
        if "inner_text" in bot.data and bot.data["inner_text"]:
            output_data = {"inner_text": bot.data["inner_text"]}
            with open("output.json", "w") as output_file:
                json.dump(output_data, output_file, indent=4)
            print("Inner text saved to 'output.json'")
        else:
            print("Element not found.")

    bot.add_action("navigate", go_to_webpage)
    bot.add_action("find_element", find_element)
    bot.add_action("get_inner_text", get_inner_text)
    bot.add_action("save_to_json", save_to_json)

    bot.run()
