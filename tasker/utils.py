import asyncio
import queue
from functools import wraps
from threading import Thread, Event
from multiprocessing import Process

def get_event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    return loop

def force_async(fn):
    '''
    Turns a sync function to async function using threads
    '''
    from concurrent.futures import ThreadPoolExecutor

    pool = ThreadPoolExecutor()
    @wraps(fn)
    def wrapper(*args, **kwargs):
        future = pool.submit(fn, *args, **kwargs)
        return asyncio.wrap_future(future)  # make it awaitable
    return wrapper

def force_sync(fn):
    '''
    Turn an async function to sync function
    '''
    @wraps(fn)
    def wrapper(*args, **kwargs):
        res = fn(*args, **kwargs)
        if asyncio.iscoroutine(res):
            return get_event_loop().run_until_complete(res)
        return res
    return wrapper

def run_safe(func, *args, **kwargs):
    return get_event_loop().call_soon(func, *args, **kwargs)

def run_sync(func):
    def wrapper(*a, **kw):
        q = queue.Queue()

        @async_daemon_task
        async def _(): q.put(await func(*a, **kw))

        _()
        return q.get()
    return wrapper

def task(func, handler=Thread, *ta, **tkw):
    @wraps(func)
    def wrapper(*a, **kw):
        thread = handler(*ta, target=func, args=a, kwargs=kw, **tkw)
        thread.start()
        return thread
    return wrapper

def async_task(func, handler=Thread, *ta, **tkw):
    return task(force_sync(func), handler, *ta, **tkw)

def daemon_task(func):
    return task(func, handler=Thread, daemon=True)

def async_daemon_task(func):
    return async_task(func, handler=Thread, daemon=True)

def process(func):
    return task(func, handler=Process)
