import io
import re
from pprint import pprint
from typing import Optional

import aiohttp
import tabula

from app.utils.sync import run_async

PUBLIC_RESOURCE_URL = "https://cloud-api.yandex.net/v1/disk/public/resources"
DOWNLOAD_RESOURCE_URL = "https://cloud-api.yandex.net/v1/disk/public/resources/download"


async def _send_request(url: str, params: dict):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as request:
            return await request.json()


async def get_public_resource(
        public_key: str,
        path: str = None,
        sort: str = None,
        limit: int = None,
        preview_size: str = None,
        preview_crop: bool = None,
        offset: int = None
):
    """
    https://yandex.ru/dev/disk/api/reference/public.html#meta
    """

    params = {key: str(value) for key, value in locals().items() if value is not None}

    return await _send_request(PUBLIC_RESOURCE_URL, params)


async def download_public_resource(public_key: str, path: str = None):
    """
    https://yandex.ru/dev/disk/api/reference/public.html#download
    """

    params = {key: str(value) for key, value in locals().items() if value is not None}

    return await _send_request(DOWNLOAD_RESOURCE_URL, params)


async def get_bytes_file(file_url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as request:
            return io.BytesIO(await request.content.read())


def get_group_name(string: str):
    if not isinstance(string, str):
        return None

    match = re.match(
        r"(\d?[А-яЕЁ]+-\d.\d\dК?)",
        string.upper(),
        re.RegexFlag.MULTILINE | re.RegexFlag.IGNORECASE
    )

    if match:
        return match.group()


async def get_schedule(file_name: str, file_url: str):
    # Тут такие костыли, это жесть, ненавижу pdf файлы

    file = await get_bytes_file(file_url)

    df = await run_async(tabula.read_pdf, file, pages=1, lattice=True, silent=True)

    data = {}
    numbers = {}

    for pdf in df:
        result_ = pdf.to_dict()

        result = {
            name: strings
            for group, strings in result_.items() if (name := get_group_name(group))
        }

        if " св " in file_name.lower():
            numbers = result_["Unnamed: 1"]
        else:
            numbers = result_["Unnamed: 0"]

        last_num = None
        for key, values in result.copy().items():
            for num, group in values.items():
                if get_group_name(group):
                    last_num = num
                    break
            if last_num:
                break

        numbers = {
            key: int(value) if str(value) != "nan" and value else value
            for key, value in list(numbers.items())[:last_num]
        }

        new_result = {}
        for key, values in result.copy().items():
            new_result[key] = []

            two_num = None
            for num, group in values.items():
                if get_group_name(group):
                    two_num = num
                    break

            for num, value in list(values.items())[:two_num]:
                the_num = numbers[num]
                new_result[key].append([the_num, value])

            if two_num and isinstance(values[two_num], str):
                two_group = get_group_name(values[two_num])
                if two_group:
                    new_result[two_group] = []

                    for num, value in list(values.items())[two_num + 1:]:
                        the_num = numbers[num - two_num - 1]
                        new_result[two_group].append([the_num, value])

        for group in new_result.copy():
            for the_data in new_result[group].copy():
                if isinstance(the_data[1], str):
                    if "_____" in the_data[1]:
                        string = None
                    else:
                        string = the_data[1].replace("\r", " ")
                elif isinstance(the_data[1], float):
                    string = None
                else:
                    string = the_data[1]

                index = new_result[group].index(the_data)
                new_result[group][index] = [the_data[0], string]

            for the_data in reversed(new_result[group].copy()):
                if the_data[1] is None:
                    index = new_result[group].index(the_data)
                    del new_result[group][index]
                else:
                    break

        data.update(**new_result)

    return data, numbers


def get_teacher_schedule(schedule: dict, numbers: dict, teacher_name: str, teacher_groups: Optional[list]):
    # Тут такие костыли, это жесть, ненавижу pdf файлы

    last_name, initials = teacher_name.upper().split()
    initial_one, initials_two = initials.split(".", 1)

    reverse_numbers = {}
    nan = False
    for num, number in numbers.items():
        if str(number) == "nan":
            if nan:
                break
            nan = True

        reverse_numbers[number] = num

    teacher_schedule = []
    for group, schedule in schedule.items():
        for num, item in schedule:
            if not item:
                continue

            match = re.search(
                rf"{last_name}\s+{initial_one}\.\s*{initials_two}",
                item.upper(),
                re.RegexFlag.MULTILINE | re.RegexFlag.IGNORECASE
            )

            if match or (
                group in (teacher_groups or []) and item.upper().startswith("КЛАССНЫЙ ЧАС")
            ):
                teacher_schedule.append([num, group, item])

    return sorted(teacher_schedule, key=lambda a: reverse_numbers[a[0]])
