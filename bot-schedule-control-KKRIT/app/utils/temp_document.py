from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator


@contextmanager
def temporary_document(suffix: str) -> Iterator[str]:
    """Use a private temporary directory, independent of Telegram filenames."""
    if suffix not in {".pdf", ".xlsx"}:
        raise ValueError("Unsupported document extension")
    with TemporaryDirectory(prefix="schedule-document-") as directory:
        yield str(Path(directory) / ("document" + suffix))
