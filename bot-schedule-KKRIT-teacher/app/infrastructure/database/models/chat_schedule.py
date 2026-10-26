from sqlalchemy import Column, Integer, VARCHAR, BIGINT, Boolean, true, false, JSON, text

from ...database.models.base import DatabaseModel, TimeStampMixin


class ChatSchedule(DatabaseModel, TimeStampMixin):
    id = Column(Integer, autoincrement=True, primary_key=True)
    tg_id = Column(BIGINT, unique=True, nullable=False)
    chat_type = Column(VARCHAR(255), nullable=False)  # "user" or "chat"

    pin_msgs: dict = Column(JSON, nullable=True)
    pin_msg_func = Column(Boolean, server_default=false(), nullable=False)

    sent_schedules: dict = Column(JSON, server_default=text("'{}'"))

    hull = Column(VARCHAR(255), nullable=False)
    groups = Column(JSON(), nullable=False)
    name = Column(VARCHAR(255), nullable=False)

    active = Column(Boolean, server_default=true(), nullable=False)
