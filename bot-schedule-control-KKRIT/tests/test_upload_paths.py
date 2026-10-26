"""Exercise real handlers with local fakes; no Telegram/CloudConvert requests."""
import ast
import importlib.util
import json
import logging
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "temp_document", ROOT / "app/utils/temp_document.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
temporary_document = module.temporary_document


def load_handler(filename, name, values):
    """Keep the handler body intact without importing the bot's live config."""
    tree = ast.parse((ROOT / "app/handlers/groups" / filename).read_text(encoding="utf-8"))
    function = next(item for item in tree.body if getattr(item, "name", None) == name)
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    isolated = ast.fix_missing_locations(ast.Module(body=[future, function], type_ignores=[]))
    namespace = {"json": json, "logging": logging, "temporary_document": temporary_document, **values}
    exec(compile(isolated, str(ROOT / filename), "exec"), namespace)
    return namespace[name]


class UploadPathsTest(unittest.IsolatedAsyncioTestCase):
    async def test_group_extraction_keeps_traversal_name_outside_destination(self):
        for filename in ("../../escape.xlsx", r"C:\private\escape.xlsx", "/tmp/escape.xlsx"):
            with self.subTest(filename=filename):
                paths = []

                async def download(file_id, destination):
                    path = Path(destination)
                    paths.append(path)
                    self.assertEqual(path.name, "document.xlsx")
                    self.assertNotIn("escape", str(path))
                    path.write_bytes(b"local fixture")

                def parse(path):
                    self.assertEqual(Path(path).read_bytes(), b"local fixture")
                    return []

                message = SimpleNamespace(edit_reply_markup=AsyncMock(), answer=AsyncMock())
                callback = SimpleNamespace(answer=AsyncMock(), message=message)
                state = SimpleNamespace(
                    get_data=AsyncMock(return_value={"file_name": filename, "file_id": "id"}),
                    clear=AsyncMock(),
                )
                handler = load_handler("collect_data.py", "parsing_groups_on_schedule", {
                    "SelectParserGroupsOnSchedule": lambda: SimpleNamespace(selected=lambda _: None),
                    "CREATORS_SCHEDULE": {"kr": lambda tables: ({}, ["demo"])},
                    "parse_schedule": parse,
                    "html": SimpleNamespace(code=lambda text: text, quote=lambda text: text),
                })
                await handler(callback, SimpleNamespace(parser="kr"), SimpleNamespace(download=download), state)
                self.assertEqual(len(paths), 1)
                self.assertFalse(paths[0].parent.exists())

    async def test_download_error_cleans_partially_written_file(self):
        paths = []

        async def download(file_id, destination):
            path = Path(destination)
            paths.append(path)
            path.write_bytes(b"partial")
            raise OSError("simulated download failure")

        callback = SimpleNamespace(answer=AsyncMock(), message=SimpleNamespace(
            edit_reply_markup=AsyncMock(), answer=AsyncMock()
        ))
        state = SimpleNamespace(get_data=AsyncMock(return_value={"file_name": "../../a.xlsx", "file_id": "id"}), clear=AsyncMock())
        handler = load_handler("collect_data.py", "parsing_groups_on_schedule", {
            "SelectParserGroupsOnSchedule": lambda: SimpleNamespace(selected=lambda _: None),
        })
        with self.assertLogs(level="ERROR"):
            await handler(callback, SimpleNamespace(parser="kr"), SimpleNamespace(download=download), state)
        self.assertFalse(paths[0].parent.exists())
        callback.message.answer.assert_awaited_once()

    async def test_schedule_parser_error_cleans_input_and_does_not_write_database(self):
        paths = []

        async def download(file_id, destination):
            path = Path(destination)
            paths.append(path)
            self.assertEqual(path.name, "document.xlsx")
            path.write_bytes(b"not a workbook")

        def parse(path):
            raise ValueError("simulated invalid XLSX")

        callback = SimpleNamespace(answer=AsyncMock(), message=SimpleNamespace(
            message_id=1, edit_reply_markup=AsyncMock(), answer=AsyncMock()
        ))
        payload = {"file_name": "../../01.01.xlsx", "file_id": "id", "parser": "kr", "rule": None}
        redis = SimpleNamespace(get=AsyncMock(return_value=json.dumps(payload).encode()), delete=AsyncMock())
        handler = load_handler("add_schedule.py", "lets_go", {
            "ScheduleCatcher": SimpleNamespace(LetsGo=lambda: SimpleNamespace(click=lambda: None)),
            "CREATORS_SCHEDULE": {"kr": lambda tables: ({}, [])},
            "parse_schedule": parse,
        })
        with self.assertLogs(level="ERROR"):
            await handler(callback, SimpleNamespace(download=download), redis, object(), object())
        self.assertFalse(paths[0].parent.exists())
        callback.message.answer.assert_awaited_once()

    async def test_converter_keeps_local_paths_private_and_preserves_display_date(self):
        paths = []

        async def download(file_id, destination):
            path = Path(destination)
            paths.append(path)
            self.assertEqual(path.name, "document.pdf")
            path.write_bytes(b"pdf fixture")

        async def convert(source, destination):
            path = Path(destination)
            paths.append(path)
            self.assertEqual(path.name, "document.xlsx")
            self.assertNotEqual(path.parent, Path(source).parent)
            path.write_bytes(b"xlsx fixture")

        class KeyFile:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def read(self):
                return '{"test": "DUMMY"}'

        async def answer_document(file, **kwargs):
            self.assertTrue(Path(file.path).exists())
            self.assertEqual(file.filename, "01.01.xlsx")

        message = SimpleNamespace(
            document=SimpleNamespace(file_id="id", file_name="../../01.01.pdf"),
            answer_document=AsyncMock(side_effect=answer_document), answer=AsyncMock()
        )
        handler = load_handler("converter.py", "convert_process", {
            "aiofiles": SimpleNamespace(open=lambda *args, **kwargs: KeyFile()),
            "cloudconvert": SimpleNamespace(configure=lambda **kwargs: None),
            "convert_file": convert,
            "ClientError": RuntimeError,
            "FSInputFile": lambda path, filename: SimpleNamespace(path=path, filename=filename),
            "ScheduleCatcher": SimpleNamespace(Question=lambda: SimpleNamespace(get=lambda: None)),
        })
        await handler(message, SimpleNamespace(download=download))
        self.assertEqual(len(paths), 2)
        self.assertTrue(all(not path.parent.exists() for path in paths))
        message.answer_document.assert_awaited_once()

    def test_temp_files_do_not_collide_and_invalid_suffix_is_rejected(self):
        with temporary_document(".xlsx") as first, temporary_document(".xlsx") as second:
            self.assertNotEqual(first, second)
        with self.assertRaises(ValueError):
            with temporary_document("../../unsafe"):
                self.fail("unsafe extension accepted")


if __name__ == "__main__":
    unittest.main()
