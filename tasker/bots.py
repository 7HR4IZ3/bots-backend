import re
import json
import inspect
import importlib
import typing as t

from .command import Command
from .drivers import BaseDriver
from .triggers import BaseTrigger
from .scheduler import BaseScheduler

from contextlib import contextmanager


class Bot:
    actions: t.Mapping[str, t.Union[t.Callable, Command]]
    triggers: t.Sequence[BaseTrigger]
    event_listeners: t.Mapping[str, t.Sequence[t.Callable]]

    def __init__(
        self: t.Self,
        config: t.Optional[t.Mapping] = None,
        macros: t.Mapping[str, t.Callable] = None,
        drivers: t.Mapping[str, BaseDriver] = None,
        scheduler: t.Optional[BaseScheduler] = None,
        default_driver: t.Optional[t.LiteralString] = None,
    ):
        self.data = dict()
        self.actions = dict()
        self.config = config or dict()
        self.drivers = drivers or dict()
        self.macros = macros or dict()

        self.scheduler = scheduler
        self.default_driver = default_driver

        self.triggers = []
        self.event_listeners = {}

    @staticmethod
    def fromJSON(self, data):
        pass

    def add_action(
        self: t.Self,
        action_name: str,
        action_class_or_function: t.Union[t.Callable, Command],
        *args,
        **kwargs,
    ):
        with self.dispatch_event("action.add", action=action_name):
            if isinstance(action_class_or_function, type) and issubclass(
                action_class_or_function, Command
            ):
                action_instance = action_class_or_function(*args, **kwargs)
                action_instance.setup(self)
                self.actions[action_name] = action_instance
            elif isinstance(action_class_or_function, Command):
                action_class_or_function.setup(self)
                self.actions[action_name] = action_class_or_function
            elif callable(action_class_or_function):
                self.actions[action_name] = action_class_or_function
            else:
                raise ValueError(f"Invalid action: {action_name}")

    def add_actions_from_json(
        self: t.Self, json_file_or_dict: t.Union[str, t.Mapping]
    ) -> None:
        if isinstance(json_file_or_dict, str):
            with open(json_file_or_dict, "r") as file:
                actions_mapping = json.load(file)
        elif isinstance(json_file_or_dict, dict):
            actions_mapping = json_file_or_dict
        else:
            raise ValueError("Invalid argument for adding actions.")

        for action_name, import_string_or_func in actions_mapping.items():
            try:
                if isinstance(import_string_or_func, str):
                    action_func = getattr(self.driver, import_string_or_func, None)

                    if not action_func:
                        module_name, func_name = import_string_or_func.rsplit(".", 1)
                        module = importlib.import_module(module_name)
                        action_func = getattr(module, func_name)

                if callable(import_string_or_func):
                    action_func = import_string_or_func

                self.add_action(action_name, action_func)
            except (ImportError, AttributeError) as e:
                raise ValueError(
                    f"Error adding action '{action_name}': {e !r}"
                ) from None

    def action(self: t.Self, action_name: str, *args, **kwargs):
        def main(action_function: t.Union[t.Callable, Command]):
            return self.add_action(action_name, action_function, *args, **kwargs)

        return main

    def setup(self: t.Self) -> None:
        with self.dispatch_event("driver.setup"):
            self.driver.setup(self)

        # if self.scheduler:
        #     self.scheduler.add_listener(
        #         self.dispatch, events.EVENT_ALL
        #     )

    def on(
        self: t.Self, event_type: str, listener_func: t.Optional[t.Callable] = None
    ) -> t.Callable:
        def decorator(listener_func: t.Callable):
            self.event_listeners.setdefault(event_type.replace("*", "(.*)"), []).append(
                listener_func
            )
            return listener_func

        return decorator(listener_func) if listener_func else decorator

    def off(self: t.Self, event_type: str, listener_func: t.Callable) -> t.Callable:
        self.event_listeners.setdefault(event_type.replace("*", "(.*)"), []).remove(
            listener_func
        )

        return listener_func

    def dispatch(self: t.Self, event: str, *args, **kwargs):
        for event_name in self.event_listeners:
            if not (event == event_name or re.fullmatch(event, event_name)):
                continue

            for cb in self.event_listeners[event_name]:
                try:
                    cb(*args, **kwargs)
                except BaseException as e:
                    raise RuntimeError(
                        f"Error dispatching event: '{event}' reason: {repr(e)}"
                    ) from None

    @contextmanager
    def dispatch_event(
        self: t.Self,
        event_name: str,
        suffix: str = "before",
        args: t.Mapping = None,
        kwargs: t.Mapping = None,
        *a,
        **kw,
    ) -> t.Self:
        args = args or dict()
        kwargs = kwargs or dict()

        self.dispatch(
            f"{event_name}:{suffix}",
            *args.get("before", []),
            *a,
            **kwargs.get("before", {}),
            **kw,
        )
        yield self
        self.dispatch(
            f"{event_name}", *args.get("after", []), *a, **kwargs.get("after", {}), **kw
        )

    def execute(self: t.Self, context: t.Optional[t.Mapping] = None) -> None:
        for action_name in self.actions:
            self.execute_action(action_name, context)

    def execute_action(
        self: t.Self, action_name: str,
        context: t.Optional[t.Mapping] = None,
        *args, **kwargs
    ) -> None:
        if action_name in self.actions:
            action = self.actions[action_name]

            if isinstance(action, Command):
                func = action.execute
            elif callable(action):
                func = action
            else:
                raise ValueError(f"Invalid action: {action_name}")

            self.dispatch("action.execute:before", action=action_name, function=func)

            success = True
            data_copy = None

            try:
                if context and isinstance(context, dict):
                    data_copy = self.data.copy()
                    self.data.update(**context)

                return_value = func(*args, **kwargs)
                if return_value:
                    self.dispatch(
                        "action.execute:value",
                        action=action_name,
                        return_value=return_value,
                    )
            except BaseException as e:
                success = False
                print(repr(e))
                self.dispatch("action.execute:error", action=action_name, exception=e)
            finally:
                if data_copy:
                    self.data = data_copy

            self.dispatch("action.execute", action=action_name, success=success)

            if not success:
                raise RuntimeError(f"Execution of action {action_name} failed")
        else:
            raise ValueError(f"Action '{action_name}' not found.")

    def add_trigger(self: t.Self, trigger: BaseTrigger) -> None:
        with self.dispatch_event("trigger.setup", trigger=trigger):
            trigger.setup(self)

        with self.dispatch_event("trigger.add", trigger=trigger):
            self.triggers.append(trigger)

        return

    def action(self: t.Self, action_name: str):
        def decorator(func: t.Union[t.Callable, Command]):
            self.actions[action_name] = func
            return func

        return decorator

    def run(self: t.Self, *args, **kwargs) -> None:
        if not self.scheduler:
            raise RuntimeError("Scheduler not configured for the bot.")

        if len(self.triggers):
            for trigger in self.triggers:
                with self.dispatch_event("trigger.start", trigger=trigger):
                    trigger.start()

                if hasattr(trigger, "get_scheduler_trigger"):
                    self.scheduler.add_job(
                        self.execute,
                        trigger=trigger.get_scheduler_trigger(),
                        *args,
                        **kwargs,
                    )
        else:
            self.scheduler.add_job(self.execute, *args, **kwargs)

        with self.dispatch_event("scheduler.start"):
            self.scheduler.start()


class AsyncBotMixin:
    async def execute(self):
        for action_name in self.actions:
            await self.execute_action(action_name)

    async def execute_action(self, action_name: str, *args, **kwargs):
        if action_name in self.actions:
            action = self.actions[action_name]

            if isinstance(action, Command):
                func = action.execute
            elif callable(action):

                def func():
                    return action(self)

            else:
                raise ValueError(f"Invalid action: {action_name}")

            self.dispatch("action.execute:before", action=action_name, function=func)

            success = True

            try:
                if inspect.iscoroutinefunction(func):
                    await func(*args, **kwargs)
                else:
                    func(*args, **kwargs)
            except BaseException as e:
                success = False
                self.dispatch("action.execute:error", action=action_name, exception=e)

            self.dispatch("action.execute", action=action_name, success=success)

            if not success:
                raise RuntimeError(f"Execution of action {action_name} failed")
        else:
            raise ValueError(f"Action '{action_name}' not found.")
