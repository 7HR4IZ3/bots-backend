import random
import typing as t

from tasker.bots import Bot
from tasker.drivers import DRIVERS
from starlette.requests import Request
from starlette.websockets import WebSocket
from starlette.responses import JSONResponse
from starlette.applications import Starlette

app = Starlette()
bots: t.Mapping[str, Bot] = {}

casts = {
    "string": lambda i: str(i),
    "number": lambda i: int(i),
    "decimal": lambda i: float(i),
    "boolean": lambda i: bool(i),
}


def genarate_bot_id():
    return "bot_" + "".join([str(random.randint(0, 9)) for _ in range(5)])


def evaluate_exec(value, context):

    def exec_handle(*__, **kwargs):
        action = value.get("action")
        macro = value.get("macro")
        args = value.get("args")
        store = value.get("store")
        returns = value.get("returns")
        return_value = None

        if not action and not macro:
            return_value = evaluate(value, {**context, "args": kwargs})

        if args:
            args = evaluate(args, {**context, "args": kwargs})
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

        if returns:
            return evaluate(returns, context)

    return exec_handle


def evaluate_if(value: t.Mapping, context: t.Mapping):
    condition = evaluate(value.get("$$if"), context)
    otherwise = value.get("$$else")
    then = value.get("$$then")

    if condition:
        return evaluate(then, context)
    else:
        return evaluate(otherwise, context)


def evaluate_if_shorthand(value: t.Mapping, context: t.Mapping):
    condition = evaluate(value.get("$$?"), context)
    otherwise = value.get("$$:")

    if condition:
        return condition
    else:
        return evaluate(otherwise, context)


def evaluate_macro(action: t.Mapping, bot: Bot):
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


def evaluate(data: t.Any, context: t.Mapping) -> t.Mapping:
    if not data:
        return data

    _ = lambda i, ctx=None: evaluate(i, {**context, **(ctx or {})})

    if isinstance(data, str) and data.startswith("$$"):
        splits = data.lstrip("$$").split(".")
        value = context.get(splits[0]) or (context["bot"].data.get(splits[0])
                                           if "bot" in context else None)

        if not value:
            return None

        for split in splits[1:]:
            if isinstance(value, dict):
                value = value.get(split)
            else:
                value = getattr(value, split, None)
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
            elif key == "$$assert":
                assert evaluate(value, context), _(data.get("$$message")) or ""
                return None
            elif key == "$$if" and "$$then" in data:
                return evaluate_if(data, context)
            elif key == "$$?" and "$$:" in data:
                return evaluate_if_shorthand(data, context)
            else:
                fixed_data[key] = evaluate(value, context)
        return fixed_data
    return data


def create_bot_from_data(bot_data):
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
    return bot


@app.route("/")
def index_page(request: Request):
    return JSONResponse({
        "bots": {
            bot_id: {
                "data": bot.data,
                "actions": list(bot.actions.keys())
            }
            for (bot_id, bot) in bots.items()
        }
    })


@app.route("/bots/create", methods=["POST"])
async def create_bot(request: Request):
    bot_data: dict = await request.json()
    bot_id = bot_data.get("name") or genarate_bot_id()

    try:
        bot = create_bot_from_data(bot_data)
        bots[bot_id] = bot
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": e.__class__.__name__,
            "args": e.args
        })
    return JSONResponse({"success": True})


@app.route("/bots/{bot_id}/start/", methods=["POST"])
async def start_bot(request: Request):
    bot_id = request.path_params.get("bot_id")
    bot = bots.get(bot_id)

    if not bot:
        return JSONResponse({
            "error": "ValueError",
            "args": ["Invalid 'bot_id'."]
        })


@app.route("/bots/{bot_id}/data/", methods=["GET", "POST"])
async def bot_data(request: Request):
    bot_id = request.path_params.get("bot_id")
    bot = bots.get(bot_id)

    if not bot:
        return JSONResponse({
            "error": "ValueError",
            "args": ["Invalid 'bot_id'."]
        })

    return JSONResponse({"bot_id": bot_id, "data": bot.data})


@app.route("/bots/{bot_id}/status/", methods=["POST"])
async def bot_status(request: Request):
    bot_id = request.path_params.get("bot_id")
    bot = bots.get(bot_id)

    if not bot:
        return JSONResponse({
            "error": "ValueError",
            "args": ["Invalid 'bot_id'."]
        })


@app.route("/bots/{bot_id}/trigger", methods=["POST"])
async def bot_trigger(request: Request):
    bot_id = request.path_params.get("bot_id")
    bot = bots.get(bot_id)

    errors = []
    returns = []

    if not bot:
        return JSONResponse({
            "error": "ValueError",
            "args": ["Invalid 'bot_id'."]
        })

    @bot.on("action.execute:error")
    def error_handler(action, exception):
        errors.append({
            "action": action,
            "error": exception.__class__.__name__,
            "args": exception.args,
        })

    @bot.on("action.execute:value")
    def value_handler(action, return_value):
        returns.append({"action": action, "value": return_value})

    try:
        bot.execute(await request.json())
    except RuntimeError:
        pass

    bot.off("action.execute:value", value_handler)
    bot.off("action.execute:error", error_handler)

    return JSONResponse({
        "success": len(errors) == 0,
        "data": bot.data,
        "errors": errors,
        "values": returns
    })


@app.websocket_route("/bots/{bot_id}/watch/")
async def watch_bot(websocket: WebSocket):
    await websocket.accept()

    bot_id = websocket.path_params.get("bot_id")
    bot = bots.get(bot_id)

    if not bot:
        return JSONResponse({
            "error": "ValueError",
            "args": ["Invalid 'bot_id'."]
        })

    @bot.on("action.execute:error")
    async def error_handler(action, exception):
        await websocket.send_json({
            "type": "error",
            "value": {
                "action": action,
                "error": exception.__class__.__name__,
                "args": exception.args,
            }
        })

    @bot.on("action.execute:value")
    async def value_handler(action, return_value):
        await websocket.send_json({
            "type": "return",
            "value": {
                "action": action,
                "value": return_value
            }
        })

    @bot.on("action.execute")
    async def execute_handler(action, success):
        await websocket.send_json({
            "type": "execute",
            "value": {
                "action": action,
                "success": success
            }
        })

    @bot.on("action.execute:before")
    async def before_handler(action, function):
        await websocket.send_json({
            "type": "execute",
            "value": {
                "action": action
            }
        })

    try:
        bot.execute(await websocket.receive_json())
    except RuntimeError:
        pass
    finally:
        bot.off("action.execute", execute_handler)
        bot.off("action.execute:value", value_handler)
        bot.off("action.execute:error", error_handler)
        bot.off("action.execute:before", before_handler)


@app.route("/bots/{bot_id}/add_action", methods=["POST"])
async def add_action(request: Request):
    bot_id = request.path_params.get("bot_id")

    bot = bots.get(bot_id)

    if not bot:
        return JSONResponse({
            "error": "ValueError",
            "args": ["Invalid 'bot_id'."]
        })

    bot_data = await request.json()
    action = evaluate(bot_data.get("action"), {"bot": bot})

    if isinstance(action, dict):
        if "$$exec" in action:
            action = action.get("$$exec")
        elif "$$execs" in action:
            action = action.get("$$execs")
        elif "$$macro" in action:
            action = evaluate_macro(action, bot)
    bot.add_action(bot_data.get("name"), action)

    return JSONResponse({"success": True})


@app.route("/bots/{bot_id}/remove_action/<action>", methods=["POST"])
async def remove_action(request: Request):
    bot_id = request.path_params.get("bot_id")
    bot = bots.get(bot_id)

    if not bot:
        return JSONResponse({
            "error": "ValueError",
            "args": ["Invalid 'bot_id'."]
        })

    bot_data = await request.json()
    action = bot_data.get("action")

    bot.actions = {key: value for (key, value) in bot.actions if key != action}

    return JSONResponse({"success": True})


@app.route("/bots/{bot_id}/execute_action/<action>", methods=["POST"])
async def execute_action(request: Request):
    bot_id = request.path_params.get("bot_id")
    bot = bots.get(bot_id)

    if not bot:
        return JSONResponse({
            "error": "ValueError",
            "args": ["Invalid 'bot_id'."]
        })

    bot_data = await request.json()
    action = bot_data.get("action")

    errors = []
    returns = []

    @bot.on("action.execute:error")
    def error_handler(action, exception):
        errors.append({
            "action": action,
            "error": exception.__class__.__name__,
            "args": exception.args,
        })

    @bot.on("action.execute:value")
    def value_handler(action, return_value):
        returns.append({"action": action, "value": return_value})

    try:
        bot.execute_action(action)
    except RuntimeError:
        pass

    bot.off("action.execute:value", value_handler)
    bot.off("action.execute:error", error_handler)

    return JSONResponse({"success": True})


bots["LoggerBot"] = create_bot_from_data({
    "name": "LoggerBot",
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
                    "x": {
                        "$$if": "$$bot.data.x_arg",
                        "$$then": "$$bot.data.x_arg",
                        "$$else": 10,
                    },
                    "y": {
                        "$$?": "$$bot.data.y_arg",
                        "$$:": 12
                    },
                },
                "store": "bot.data.value",
            }
        },
        "ensure_value": {
            "$$exec": {
                "$$assert": "$$bot.data.value",
                "$$message": "Assertion error message"
            }
        },
        "log_name": {
            "$$exec": {
                "macro": "log",
                "args": {
                    "message": {
                        "$$join": [
                            "Hello '",
                            "$$bot.data.name",
                            "'!!",
                            "\nValue: ",
                            {
                                "$$cast": "string",
                                "target": "$$bot.data.value"
                            },
                        ]
                    }
                },
            }
        },
    },
})
# bot.execute()
