import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import wraps, partial
from typing import Any, TypeVar

Result = TypeVar("Result")


def run_sync_decorator(func: Callable[..., Any]):
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    return wrapper


async def run_sync(func: Callable[..., Result], *args: Any, **kwargs: Any) -> Result:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))


def run_async_decorator(func: Callable[..., Any]) -> Result:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any):
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            return await loop.run_in_executor(
                pool, partial(func, *args, **kwargs)
            )

    return wrapper


async def run_async(func: Callable[..., Result], *args: Any, **kwargs: Any) -> Result:
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(
            pool, partial(func, *args, **kwargs)
        )
