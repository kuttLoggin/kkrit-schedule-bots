import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aioredis import Redis
from sqlalchemy.orm.session import sessionmaker

from app import handlers, middlewares
from app.config import Config
from app.infrastructure.database.functions.setup import create_session_pool
from app.services.fluent import configure_fluent, FluentService
from app.services.scheduler import run_scheduler
from app.utils import logger
from app.utils.broadcast import MemoryBroadcastBotLocker
from app.utils.lock_factory import LockFactory
from app.utils.notifications.startup_notify import notify_superusers
from app.utils.set_bot_commands import set_commands


async def on_startup(bot: Bot, fluent):
    await set_commands(bot, fluent)
    await notify_superusers(bot)


async def main():
    bot = Bot(token=Config.BOT_TOKEN, parse_mode="HTML")
    redis = Redis(host="redis")
    redis_storage = RedisStorage(redis, key_builder=DefaultKeyBuilder(with_destiny=True))
    dp = Dispatcher(redis_storage)
    bot_me = await bot.me()

    session_pool = await create_session_pool(Config.POSTGRES_URL)

    middlewares.setup(dp, session_pool)
    handlers.setup_all_handlers(dp)
    logger.setup_logger()

    lock_factory = LockFactory()
    fluent = configure_fluent(Config.LOCALES_PATH)
    scheduler = run_scheduler(
        redis_connect={"host": "redis"},
        ctx={
            dp: Dispatcher,
            bot: Bot,
            session_pool: sessionmaker,
            redis: Redis,
            fluent: FluentService,
            lock_factory: LockFactory
        }
    )

    await on_startup(bot, fluent)

    environments = dict(
        fluent=fluent,
        redis=redis,
        lock_factory=lock_factory,
        scheduler=scheduler,
        broadcast_locker=MemoryBroadcastBotLocker()
    )

    useful_updates = dp.resolve_used_update_types()

    try:
        # Сбрасываем все старые апдейты
        # await bot.delete_webhook(drop_pending_updates=True)

        logging.info("Run polling for bot @%s id=%d - %r", bot_me.username, bot_me.id, bot_me.full_name)
        await dp.start_polling(bot, allowed_updates=useful_updates, **environments)
    finally:
        logging.warning("Shutting down..")
        await dp.storage.close()
        await bot.session.close()
        logging.warning("Bye!")
