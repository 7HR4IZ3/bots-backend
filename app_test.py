import random
import json
import typing as t

from tasker.bots import Bot
from tasker.drivers import DRIVERS

bots: t.Mapping[t.LiteralString, Bot] = {}

with open("./bot.json") as f:
    bot_sample_data = json.loads(f.read())

casts = {
    "string": lambda i: str(i),
    "number": lambda i: int(i),
    "decimal": lambda i: float(i),
    "boolean": lambda i: bool(i)
}


def genarate_bot_id():
    return "bot_" + "".join([str(random.randint(0, 9)) for _ in range(5)])


def evaluate_exec(value, context):

    def exec_handle(*__, **kwargs):
        action = value.get("action")
        macro = value.get("macro")
        args = value.get("args")
        store = value.get("store")
        return_value = None

        if args:
            args = _(args, {**context, "args": kwargs})
        else:
            args = {}

        if action:
            if "driver" in value:
                if value["driver"] == True:
                    driver = context["bot"].drivers.get(
                        context["bot"].default_driver)
                else:
                    driver = context["bot"].drivers.get(value["driver"])
                action = getattr(driver, action)
            else:
                action = context["bot"].actions.get(action)

            if action:
                return_value = action(**args)

        if macro:
            macro = context["bot"].macros.get(macro)
            if macro:
                return_value = macro(**args)

        if store:
            store_splits = store.split(".")

            if len(store_splits) > 1:
                # print(context)
                target = context.get(store_splits[0])
                for split in store_splits[1:-1]:
                    if isinstance(target, dict):
                        target = target.get(split)
                    else:
                        target = getattr(target, split)
            else:
                target = context

            if isinstance(target, dict):
                target[store_splits[-1]] = return_value
            else:
                setattr(target, store_splits[-1], return_value)
        return exec_handle

def evaluate_macro(action, bot):
    macro = action.get("$$macro")
    target = bot.macros.get(macro.get("target"))

    def macro_handle(**kwargs):
        args = macro.get("args")
        if args:
            args = evaluate(args, {"bot": bot, "args": kwargs})
        else:
            args = {}

        if target:
            return target(**args)
    return macro_handle


def evaluate(data: t.Union[t.Mapping, t.LiteralString],
             context: t.Mapping) -> t.Mapping:

    _ = lambda i, ctx=None: evaluate(i, {**context, **(ctx or {})})

    if isinstance(data, str) and data.startswith("$$"):
        splits = data.lstrip("$$").split(".")
        value = context.get(splits[0])

        for split in splits[1:]:
            if isinstance(value, dict):
                value = value.get(split)
            else:
                value = getattr(value, split)
            if not value:
                break

        return value
    elif isinstance(data, list):
        return [_(item) for item in data]
    elif isinstance(data, dict):
        fixed_data = {}
        for key, value in data.items():
            if key == "$$exec" and isinstance(value, dict):
                fixed_data[key] = evaluate_exec(value, context)
            elif key == "$$execs" and isinstance(value, list):
                funcs = [_(item) for item in value]

                def execs(*_, **kwargs):
                    for func in funcs:
                        func(**{**context, **kwargs})

                fixed_data[key] = execs
            elif key == "$$join" and isinstance(value, list):
                return "".join(_(item) for item in value)
            elif key == "$$cast" and isinstance(value, str):
                target = _(data.get("target"))
                cast = _(data.get("$$cast"))

                return casts.get(cast)(target)
            else:
                fixed_data[key] = _(value)
        return fixed_data
    return data


def create_bot(bot_data):
    bot_id = genarate_bot_id()

    bot_config = {"default_driver": None, "drivers": {}, "macros": {}}

    for driver_config in bot_data.get("drivers", []):
        driver_class = DRIVERS.get(driver_config["driver"])
        if not driver_class:
            continue

        driver_name = driver_config.get("name")
        driver = driver_class(**driver_config.get("config", {}))

        if driver_config.get("default"):
            bot_config["default_driver"] = driver_name

        bot_config["drivers"][driver_name] = driver

    bot = Bot(**bot_config)
    bot.data.update(**bot_data.get("data", {}))

    for macro_name, macro in bot_data.get("macros", {}).items():
        macro = evaluate(macro, {"bot": bot})

        if isinstance(macro, dict):
            if "$$exec" in macro:
                macro = macro.get("$$exec")
            elif "$$execs" in macro:
                macro = macro.get("$$execs")

        bot.macros[macro_name] = macro

    for action_name, action in bot_data.get("actions", {}).items():
        action = evaluate(action, {"bot": bot})

        if isinstance(action, dict):
            if "$$exec" in action:
                action = action.get("$$exec")
            elif "$$execs" in action:
                action = action.get("$$execs")
            elif "$$macro" in action:
                action = evaluate_macro(action, bot)

        bot.add_action(action_name, action)

    bots[bot_id] = bot
    return bot


bot = create_bot({
    "data": {
        "name": "Thraize"
    },
    "drivers": [{
        "name": "logger",
        "default": True,
        "driver": "notify",
    }],
    "macros": {
        "log": {
            "$$exec": {
                "action": "log",
                "driver": "logger",
                "args": "$$args",
            }
        }
    },
    "actions": {
        "calculate": {
            "$$exec": {
                "action": "add",
                "driver": "logger",
                "args": {
                    "x": 10,
                    "y": 32
                },
                "store": "bot.data.value"
            }
        },
        "log_name": {
            "$$exec": {
                "macro": "log",
                "args": {
                    "message": {
                        "$$join": [
                            "Hello '", "$$bot.data.name", "'!!", "\nValue: ", {
                                "$$cast": "string",
                                "target": "$$bot.data.value"
                            }
                        ]
                    }
                }
            }
        }
    },
})
bot.execute()
