from sqlalchemy import Column, INTEGER, Integer, VARCHAR, BIGINT, TIMESTAMP, Boolean, ForeignKey, true, false

from ...database.models.base import DatabaseModel, TimeStampMixin


class Chat(DatabaseModel, TimeStampMixin):
    id = Column(Integer, autoincrement=True, primary_key=True)
    tg_id = Column(BIGINT, unique=True, nullable=False)

    title = Column(VARCHAR(255), nullable=False)
    username = Column(VARCHAR(255), nullable=True)

    language = Column(VARCHAR(3), server_default="ru", nullable=False)
    active = Column(Boolean, server_default=true(), nullable=False)
    bot_admin = Column(Boolean, server_default=false(), nullable=False)

    owner = Column(INTEGER, ForeignKey("users.id", ondelete="SET NULL", name="FK__chats_owner"), nullable=True)

    group_type = Column(VARCHAR(255), nullable=False)
