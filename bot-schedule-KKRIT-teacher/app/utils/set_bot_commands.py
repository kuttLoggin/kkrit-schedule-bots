from aiogram import Bot
from aiogram.types import (
    BotCommand, BotCommandScopeChat, BotCommandScopeAllChatAdministrators, BotCommandScopeAllPrivateChats
)

from app.config import Config
from app.services.fluent import FluentService


PRIVATE_CHAT_COMMANDS = {
    "scope": BotCommandScopeAllPrivateChats(),
    "commands": [
        {"command": "settings", "description": "command-settings"},
        {"command": "report", "description": "command-report"}
    ]
}

ADMIN_CHAT_COMMANDS = {
    "scope": BotCommandScopeAllChatAdministrators(),
    "commands": [
        {"command": "settings", "description": "command-settings"}
    ]
}

ADMIN_COMMANDS = [
    {"command": "settings", "description": "Настройки"},
    {"command": "statistics", "description": "Общая статистика"},
    {"command": "report", "description": "Отправить репорт"},
    {"command": "broadcast", "description": "Рассылка"}
]


async def set_commands(bot: Bot, fluent: FluentService) -> None:
    await bot.delete_my_commands()

    for lang in fluent.locales_map:
        i18n = fluent.get_translator_by_locale(lang)

        for commands in (PRIVATE_CHAT_COMMANDS, ADMIN_CHAT_COMMANDS):
            cmds = [
                BotCommand(
                    command=cmd["command"],
                    description=i18n.get(cmd["description"])
                )
                for cmd in commands["commands"]
            ]

            await bot.set_my_commands(cmds, commands["scope"], lang)

    for admin in Config.ADMINS:
        await bot.set_my_commands(ADMIN_COMMANDS, BotCommandScopeChat(chat_id=admin))
