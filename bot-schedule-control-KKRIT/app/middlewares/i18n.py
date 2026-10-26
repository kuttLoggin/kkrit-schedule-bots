from typing import Callable, Dict, Any, Awaitable, Union

from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery
from fluentogram import TranslatorRunner

from app.services.fluent import FluentService


class I18nMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        fluent: FluentService = data["fluent"]

        lang = "ru"

        translator_runner: TranslatorRunner = fluent.get_translator_by_locale(lang)

        data["i18n"] = translator_runner
        data["i18n_hub"] = fluent.hub
        data["i18n_lang"] = lang
        return await handler(event, data)
