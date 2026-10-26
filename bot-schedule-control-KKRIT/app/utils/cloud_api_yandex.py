import io
import aiohttp


PUBLIC_RESOURCE_URL = "https://cloud-api.yandex.net/v1/disk/public/resources"
DOWNLOAD_RESOURCE_URL = "https://cloud-api.yandex.net/v1/disk/public/resources/download"
# Documentation: https://yandex.ru/dev/disk/poligon/


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

    params = {key: str(value) for key, value in locals().items() if value is not None}

    return await _send_request(PUBLIC_RESOURCE_URL, params)


async def download_public_resource(public_key: str, path: str = None):
    params = {key: str(value) for key, value in locals().items() if value is not None}

    return await _send_request(DOWNLOAD_RESOURCE_URL, params)


async def get_bytes_file(file_url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as request:
            return io.BytesIO(await request.content.read())
