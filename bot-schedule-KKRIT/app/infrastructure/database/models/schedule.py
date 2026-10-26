from sqlalchemy import Column, Integer, JSON, TIMESTAMP, String, ARRAY, SmallInteger, DATE, null

from ...database.models.base import DatabaseModel, TimeStampMixin


class Schedule(DatabaseModel, TimeStampMixin):
    id = Column(Integer, autoincrement=True, primary_key=True)

    name = Column(String, nullable=False)
    path = Column(String, nullable=False)

    hull = Column(SmallInteger, nullable=False)
    resource_id = Column(String, nullable=False)

    tapes: dict = Column(JSON, nullable=False)
    old_tapes: dict = Column(JSON, server_default=null(), nullable=True)
    numbers: tuple[str] = Column(ARRAY(String), nullable=False)

    date = Column(DATE, nullable=False)
    created = Column(TIMESTAMP(timezone=True), nullable=False)
    modified = Column(TIMESTAMP(timezone=True), nullable=False)
