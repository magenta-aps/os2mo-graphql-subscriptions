# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
"""Settings handling."""
import logging
from enum import Enum
from functools import cache
from typing import Any

import structlog
from pydantic import BaseSettings
from pydantic import Field


class LogLevel(Enum):
    """Log levels."""

    NOTSET = logging.NOTSET
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


logger = structlog.get_logger()


class Settings(BaseSettings):
    """Settings for OS2mo GraphQL subscriptions.

    Note that AMQP related settings are taken directly by RAMQP:
    * https://git.magenta.dk/rammearkitektur/ramqp/-/blob/master/ramqp/config.py
    """

    # pylint: disable=too-few-public-methods

    commit_tag: str = Field("HEAD", description="Git commit tag.")
    commit_sha: str = Field("HEAD", description="Git commit SHA.")

    queue_prefix: str = Field(
        "os2mo-graphql-subscriptions",
        description="The prefix to attach to queues for this program.",
    )

    log_level: LogLevel = LogLevel.DEBUG

    enable_cors: bool = True


@cache
def get_settings(*args: Any, **kwargs: Any) -> Settings:
    """Fetch settings object.

    Args:
        args: overrides
        kwargs: overrides

    Return:
        Cached settings object.
    """
    settings = Settings(*args, **kwargs)
    logger.debug("Settings fetched", settings=settings, args=args, kwargs=kwargs)
    return settings
