from typing import Callable, Dict, Any, Awaitable, Union

from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession


class DBPoolMiddleware(BaseMiddleware):
    def __init__(self, session_pool):
        self.__session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        data["session_pool"] = self.__session_pool

        # try:
        #     async with session:
        #         result = await handler(event, data)
        # except Exception as err:
        #     raise err
        #
        # return result

        async with self.__session_pool() as session:
            data["session"] = session
            return await handler(event, data)
