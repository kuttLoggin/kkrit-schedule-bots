from sqlalchemy import Column, Integer, VARCHAR, BIGINT, Boolean, true
from sqlalchemy.sql.expression import null

from ...database.models.base import DatabaseModel, TimeStampMixin


class User(DatabaseModel, TimeStampMixin):
    id = Column(Integer, autoincrement=True, primary_key=True)
    tg_id = Column(BIGINT, unique=True, nullable=False)

    first_name = Column(VARCHAR(255), server_default=null(), nullable=True)
    last_name = Column(VARCHAR(255), server_default=null(), nullable=True)
    username = Column(VARCHAR(255), server_default=null(), nullable=True)

    language = Column(VARCHAR(3), server_default=null(), nullable=True)
    real_language = Column(VARCHAR(3), server_default="ru", nullable=False)
    active = Column(Boolean, server_default=true(), nullable=False)

    @property
    def full_name(self):
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name
