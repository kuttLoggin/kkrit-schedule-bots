from __future__ import annotations

import asyncio
import logging
from asyncio import Lock
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import (
    AsyncGenerator,
    Callable,
    Any,
    Awaitable,
    Iterable,
    DefaultDict,
    Hashable, Union, Optional,
)

from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import Message, InlineKeyboardMarkup, ReplyKeyboardMarkup

logger = logging.getLogger(__name__)


class BroadcastLockException(Exception):
    pass


class BroadcastCancel(Exception):
    pass


async def broadcast_smth(
    chats: AsyncGenerator[int | Any],
    action: Callable[[int, Any, ...], Awaitable[Any, int]],
    with_counter: bool = True,
    attribute: str | None = None,
    **func_kwargs: Any,
) -> int:
    i = 0

    async for chat in chats:
        if attribute:
            chat_id = getattr(chat, attribute)
        else:
            chat_id = chat

        try:
            if with_counter:
                i += await action(chat_id, i, **func_kwargs)
            else:
                await action(chat_id, **func_kwargs)

        except TelegramRetryAfter as e:
            logger.error(
                f"Target [ID:{chat_id}]: Flood limit is exceeded. "
                f"Sleep {e.retry_after} seconds."
            )
            await asyncio.sleep(e.retry_after)

        except Exception as e:
            logger.error(e)

        await asyncio.sleep(0.05)

    return i


async def from_iterable(it: Iterable) -> AsyncGenerator:
    for item in it:
        await asyncio.sleep(0)
        yield item


class MemoryBroadcastBotLocker:
    def __init__(self) -> None:
        self._locks: DefaultDict[Hashable, Lock] = defaultdict(Lock)

    @asynccontextmanager
    async def lock(self, bot_id: int) -> AsyncGenerator[None, None]:
        if self.is_exist(bot_id):
            raise BroadcastLockException

        lock = self._locks[bot_id]
        async with lock:
            yield

        self.delete(bot_id)

    def is_exist(self, bot_id: int) -> bool:
        return True if self._locks.get(bot_id, None) else False

    def delete(self, bot_id: int) -> None:
        self._locks.pop(bot_id)

    def close(self) -> None:
        self._locks.clear()

    def __del__(self):
        self.close()


def send_copy(
    msg: Message,
    chat_id: Union[str, int],
    disable_notification: Optional[bool] = None,
    disable_web_page_preview: Optional[bool] = None,
    reply_to_message_id: Optional[int] = None,
    reply_markup: Union[InlineKeyboardMarkup, ReplyKeyboardMarkup, None] = None,
):
    """
    Send copy of message.

    Is similar to :meth:`aiogram.client.bot.Bot.copy_message`
    but returning the sent message instead of :class:`aiogram.types.message_id.MessageId`

    .. note::

        This method don't use the API method named `copyMessage` and
        historically implemented before the similar method is added to API

    :param msg:
    :param chat_id:
    :param disable_notification:
    :param disable_web_page_preview:
    :param reply_to_message_id:
    :param reply_markup:
    :return:
    """
    from aiogram.methods import (
        SendAnimation,
        SendAudio,
        SendContact,
        SendDice,
        SendDocument,
        SendLocation,
        SendMessage,
        SendPhoto,
        SendPoll,
        SendSticker,
        SendVenue,
        SendVideo,
        SendVideoNote,
        SendVoice,
    )

    kwargs = {
        "chat_id": chat_id,
        "reply_markup": reply_markup or msg.reply_markup,
        "disable_notification": disable_notification,
        "reply_to_message_id": reply_to_message_id,
    }
    text = msg.text or msg.caption
    entities = msg.entities or msg.caption_entities

    if msg.text:
        return SendMessage(text=text, entities=entities, disable_web_page_preview=disable_web_page_preview, **kwargs)
    elif msg.audio:
        return SendAudio(
            audio=msg.audio.file_id,
            caption=text,
            title=msg.audio.title,
            performer=msg.audio.performer,
            duration=msg.audio.duration,
            caption_entities=entities,
            **kwargs,
        )
    elif msg.animation:
        return SendAnimation(
            animation=msg.animation.file_id, caption=text, caption_entities=entities, **kwargs
        )
    elif msg.document:
        return SendDocument(
            document=msg.document.file_id, caption=text, caption_entities=entities, **kwargs
        )
    elif msg.photo:
        return SendPhoto(
            photo=msg.photo[-1].file_id, caption=text, caption_entities=entities, **kwargs
        )
    elif msg.sticker:
        return SendSticker(sticker=msg.sticker.file_id, **kwargs)
    elif msg.video:
        return SendVideo(
            video=msg.video.file_id, caption=text, caption_entities=entities, **kwargs
        )
    elif msg.video_note:
        return SendVideoNote(video_note=msg.video_note.file_id, **kwargs)
    elif msg.voice:
        return SendVoice(voice=msg.voice.file_id, **kwargs)
    elif msg.contact:
        return SendContact(
            phone_number=msg.contact.phone_number,
            first_name=msg.contact.first_name,
            last_name=msg.contact.last_name,
            vcard=msg.contact.vcard,
            **kwargs,
        )
    elif msg.venue:
        return SendVenue(
            latitude=msg.venue.location.latitude,
            longitude=msg.venue.location.longitude,
            title=msg.venue.title,
            address=msg.venue.address,
            foursquare_id=msg.venue.foursquare_id,
            foursquare_type=msg.venue.foursquare_type,
            **kwargs,
        )
    elif msg.location:
        return SendLocation(
            latitude=msg.location.latitude, longitude=msg.location.longitude, **kwargs
        )
    elif msg.poll:
        return SendPoll(
            question=msg.poll.question,
            options=[option.text for option in msg.poll.options],
            **kwargs,
        )
    elif msg.dice:  # Dice value can't be controlled
        return SendDice(**kwargs)
    else:
        raise TypeError("This type of message can't be copied.")
