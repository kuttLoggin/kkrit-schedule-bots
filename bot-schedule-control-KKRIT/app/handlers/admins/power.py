import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aioredis import Redis


async def handler(m: Message, redis: Redis):
    power = await redis.get("power-schedule")
    power = not int(power if isinstance(power, bytes) else None)
    await redis.set("power-schedule", int(power))

    if power:
        await m.answer("✅ Расписание активно")
    else:
        await m.answer("❌ Расписание неактивно")


def setup(router: Router):
    router.message.register(handler, Command("power_schedule"))
