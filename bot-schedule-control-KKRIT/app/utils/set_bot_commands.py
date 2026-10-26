from aiogram import Bot
from aiogram.types import (
    BotCommand, BotCommandScopeChat, BotCommandScopeAllPrivateChats, BotCommandScopeAllChatAdministrators
)

from app.config import Config
from app.services.fluent import FluentService


PRIVATE_CHAT_COMMANDS = {
    "scope": BotCommandScopeAllPrivateChats(),
    "commands": []
}

ADMIN_COMMANDS = [
    {"command": "statistics", "description": "Общая статистика"},
    {"command": "broadcast", "description": "Рассылка"},
    {"command": "power_schedule", "description": "Вкл/выкл отправки расписания"}
]

MODERATE_CHAT = [
    {"command": "show_collect_data", "description": "Показать коллекционные данные"},
    {"command": "update_collect_data_groups", "description": "Обновить группы в коллекционных данных"},
    {"command": "update_collect_data_hulls", "description": "Обновить корпуса в коллекционных данных"},
    {"command": "get_online_hulls", "description": "Получить все доступные корпусы онлайн"},
    {"command": "get_groups_on_schedule", "description": "Получить группы из файла расписания"},
    {"command": "convert", "description": "Конвертировать файл PDF в XLSX"}
]


async def set_commands(bot: Bot, fluent: FluentService) -> None:
    await bot.delete_my_commands()

    for lang in fluent.locales_map:
        i18n = fluent.get_translator_by_locale(lang)

        for commands in (PRIVATE_CHAT_COMMANDS, ):
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

    await bot.set_my_commands(MODERATE_CHAT, BotCommandScopeChat(chat_id=Config.GROUP_ID))
