from sqlalchemy import Column, Integer, VARCHAR, Boolean, ForeignKey, true, null

from ...database.models.base import DatabaseModel, TimeStampMixin


class LocalChatUser(DatabaseModel, TimeStampMixin):
    id = Column(Integer, autoincrement=True, primary_key=True)

    chat_id = Column(
        Integer,
        ForeignKey("chats.id", onupdate="CASCADE", ondelete="CASCADE", name="FK__local_chat_users_chat_id"),
        nullable=False
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE", name="FK__local_chat_users_user_id"),
        nullable=False
    )

    active = Column(Boolean, server_default=true(), nullable=False)
