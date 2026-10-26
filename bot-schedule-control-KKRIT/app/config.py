from pathlib import Path
from typing import NamedTuple

from environs import Env


class Config(NamedTuple):
    __env = Env()
    __env.read_env()

    BASE_DIR = Path(__name__).resolve().parent.parent
    LOCALES_PATH = 'locales'

    BOT_TOKEN = __env.str("BOT_TOKEN")

    ADMINS = __env.list("ADMIN_ID")
    GROUP_ID = __env.int("GROUP_ID")

    KKRIT_DISK = __env.str("KKRIT_DISK")

    POSTGRES_DB = __env.str("POSTGRES_DB")
    POSTGRES_USER = __env.str("POSTGRES_USER")
    POSTGRES_PASSWORD = __env.str("POSTGRES_PASSWORD")
    DB_PORT = __env.str("DB_PORT")
    DB_HOST = __env.str("DB_HOST")

    POSTGRES_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_HOST}:{DB_PORT}/{POSTGRES_DB}"
