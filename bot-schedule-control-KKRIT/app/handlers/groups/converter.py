import json
import logging

import aiofiles
import cloudconvert
from aiogram import F, Router, Bot
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, CallbackQuery
from cloudconvert.exceptions.exceptions import ClientError

from app.keyboards.admin.inline import ConvertFilePDFToXLSX, ScheduleCatcher
from app.utils.sync import run_async_decorator
from app.utils.temp_document import temporary_document


@run_async_decorator
def convert_file(file_path: str, converted_file_path: str):
    job = cloudconvert.Job.create(payload={
        "tasks": {
            "upload-my-file": {
                "operation": "import/upload"
            }
        }
    })

    upload_task_id = job["tasks"][0]["id"]

    upload_task = cloudconvert.Task.find(id=upload_task_id)
    cloudconvert.Task.upload(file_name=file_path, task=upload_task)
    cloudconvert.Task.wait(id=upload_task_id)  # Wait for job completion

    job = cloudconvert.Job.create(payload={
        "tasks": {
            "convert-my-file": {
                "operation": "convert",
                "input": upload_task_id,
                "output_format": "xlsx",
            },
            "export-my-file": {
                "operation": "export/url",
                "input": "convert-my-file"
            }
        }
    })

    task_id = job["tasks"][1]["id"]

    res = cloudconvert.Task.wait(id=task_id)  # Wait for job completion
    file = res.get("result").get("files")[0]

    cloudconvert.download(filename=converted_file_path, url=file["url"])

    return converted_file_path


async def convert_process(m: Message, bot: Bot):
    file_id = m.document.file_id
    file_name = m.document.file_name

    file_api_keys = "data/cloudconvert_api_keys.json"
    async with aiofiles.open(file_api_keys, mode="r", encoding="UTF-8") as file:
        api_keys = json.loads(await file.read())

    # The original filename is presentation data, never a local destination.
    output_name = file_name.replace("\\", "/").rsplit("/", 1)[-1] or "schedule.pdf"
    output_name = output_name.rsplit(".", 1)[0] + ".xlsx"
    with temporary_document(".pdf") as file_path, temporary_document(".xlsx") as output_path:
        await bot.download(file_id, file_path)
        converted = False
        for name, api_key in api_keys.items():
            cloudconvert.configure(api_key=api_key, sandbox=False)
            try:
                await convert_file(file_path, output_path)
            except ClientError as err:
                logging.warning(f"CloudConvert API KEY [{name}] - {err}")
            else:
                converted = True
                break

        if converted:
            await m.answer_document(
                FSInputFile(output_path, filename=output_name),
                reply_markup=ScheduleCatcher.Question().get()
            )
        else:
            await m.answer("❌ Похоже что у всех <b>API токенов</b> закончились credits")


async def convert_command(m: Message, bot: Bot):
    msg = m.reply_to_message

    await convert_process(msg, bot)


async def convert_button(c: CallbackQuery, bot: Bot):
    await convert_process(c.message, bot)


def setup(router: Router):
    router.message.register(
        convert_command,
        Command("convert"),
        F.reply_to_message,
        F.reply_to_message.content_type == "document",
        F.reply_to_message.document.file_name.lower().split(".")[-1] == "pdf"
    )
    router.callback_query.register(
        convert_button,
        ConvertFilePDFToXLSX.CD.filter()
    )
