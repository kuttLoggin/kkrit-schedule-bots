from __future__ import annotations

import logging
from typing import List, Union

import betterlogging as logger


def setup_logger(level: Union[str, int] = "INFO", ignored: List[str] | None = None):
    level_name = logging.getLevelName(level)

    logger.basic_colorized_config(level=level_name)
    logging.getLogger("aiogram").setLevel(logging.WARNING if level in ("INFO", 20) else level_name)
    logging.getLogger('apscheduler').setLevel(logging.ERROR if level in ("INFO", 20) else level_name)
    if ignored:
        for ignore in ignored:
            logger.disable(ignore)
    logging.info("Logging is successfully configured")
