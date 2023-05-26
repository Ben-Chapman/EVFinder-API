import asyncio
import time
from functools import partial, wraps


def timeit(function_to_time):
    @wraps(function_to_time)
    def timed(*args, **kw):
        start_time = time.perf_counter_ns()
        output = function_to_time(*args, **kw)
        end_time = time.perf_counter_ns()
        total_time = end_time - start_time

        # TODO: Push this to a custom metric
        print(f"Function {function_to_time.__name__} took {total_time/1000000:.5f} ms")

        return output

    return timed


def async_timeit(function_to_time):
    @wraps(function_to_time)
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter_ns()
        try:
            return await function_to_time(*args, **kwargs)
        finally:
            total_time = time.perf_counter_ns() - start_time
            # TODO: Push this to a custom metric
            print(
                f"Function {function_to_time.__name__} took {total_time/1000000:.5f} ms"
            )

    return wrapper


def fire_and_forget(f):
    """https://dotmethod.me/posts/python-async-fire-and-forget/"""

    @wraps(f)
    def wrapped(*args, **kwargs):
        loop = asyncio.get_event_loop()
        if callable(f):
            return loop.run_in_executor(None, partial(f, *args, **kwargs))
        else:
            raise TypeError("Task must be a callable")

    return wrapped
