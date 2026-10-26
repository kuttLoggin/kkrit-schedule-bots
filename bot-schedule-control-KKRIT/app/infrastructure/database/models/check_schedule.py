from sqlalchemy import Column, Integer, TIMESTAMP, String, SmallInteger, DATE, Boolean, false

from ...database.models.base import DatabaseModel, TimeStampMixin


class CheckSchedule(DatabaseModel, TimeStampMixin):
    id = Column(Integer, autoincrement=True, primary_key=True)

    name = Column(String, nullable=False)
    path = Column(String, nullable=False)

    hull = Column(SmallInteger, nullable=False)
    resource_id = Column(String, nullable=False)

    ignore = Column(Boolean, default=False, server_default=false(), nullable=False)

    date = Column(DATE, nullable=False)
    created = Column(TIMESTAMP(timezone=True), nullable=False)
    modified = Column(TIMESTAMP(timezone=True), nullable=False)
