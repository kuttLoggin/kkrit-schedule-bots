from sqlalchemy import Column, Integer, JSON, TIMESTAMP, String, SmallInteger, DATE, null

from ...database.models.base import DatabaseModel, TimeStampMixin


class Schedule(DatabaseModel, TimeStampMixin):
    id = Column(Integer, autoincrement=True, primary_key=True)

    name = Column(String, nullable=False)
    path = Column(String, nullable=True)  # Скорее информационное поле на данный момент

    hull = Column(String, nullable=False)
    # Скорее информационное поле на данный момент.
    # Будет использоваться для автоматического парсинга расписания в будущем.
    resource_id = Column(String, nullable=True)

    tapes: dict = Column(JSON, nullable=False)
    old_tapes: dict = Column(JSON, default=None, server_default=null(), nullable=True)

    date = Column(DATE, nullable=False)
    created = Column(TIMESTAMP(timezone=True), nullable=True)
    modified = Column(TIMESTAMP(timezone=True), nullable=True)
