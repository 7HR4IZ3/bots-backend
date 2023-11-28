
class BaseTrigger:
    def setup(self, bot):
        self.bot = bot

    def execute(self):
        self.bot.execute()

    def start(self):
        pass
